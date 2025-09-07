# IMPORTS #
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware  # pyright: ignore[reportMissingImports]
from typing import List, Dict, Any, Tuple
from pydantic import BaseModel
from typing import Optional, List, Dict, Any


# PDF & DOCX libs
import re
import fitz  # PyMuPDF  # pyright: ignore[reportMissingImports]
from docx import Document  # python-docx  # pyright: ignore[reportMissingImports]

import os, json
import itertools

# API Key Env Variables


app = FastAPI()

# CORS (ensure your frontend origin is allowed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- Helpers ----------

def normalize_text(t: str) -> str:
    # remove weird spacing, collapse multiple spaces/newlines
    t = t.replace("\r", "")
    # keep paragraph breaks but collapse excessive newlines to max 2
    t = re.sub(r"\n{3,}", "\n\n", t)
    # collapse runs of spaces/tabs
    t = re.sub(r"[ \t]{2,}", " ", t)
    return t.strip()

def extract_text_from_pdf_bytes(b: bytes) -> str:
    # Load PDF from memory bytes
    with fitz.open(stream=b, filetype="pdf") as doc:
        parts = []
        for page in doc:
            txt = page.get_text("text")  # layout-aware text
            parts.append(txt)
    return "\n".join(parts)

def extract_text_from_docx_bytes(b: bytes) -> str:
    # python-docx needs a file-like; bytes can be written to memory
    # But python-docx can open via a bytes buffer using a workaround:
    # We’ll save to a temp in-memory buffer (NamedTemporaryFile alternative is okay, but here simpler route)
    import io
    file_obj = io.BytesIO(b)
    document = Document(file_obj)
    paras = []
    for p in document.paragraphs:
        if p.text and p.text.strip():
            paras.append(p.text)
    return "\n".join(paras)


def guess_kind(filename: str | None, content_type: str | None) -> str:
    name = (filename or "").lower()
    ct = (content_type or "").lower()
    if name.endswith(".pdf") or "pdf" in ct:
        return "pdf"
    if name.endswith(".docx") or "officedocument.wordprocessingml.document" in ct:
        return "docx"
    return "unknown"


# ---------- Models (pydantic) ----------
class Obligation(BaseModel):
    party: str
    action: str
    trigger: Optional[str] = None
    deadline: Optional[str] = None
    amount: Optional[str] = None
    clause_ref: Optional[str] = None

class ExtractionResponse(BaseModel):
    obligations: List[Obligation]
    meta: dict


    # --------------- Helpers ------------------
def _extract_first_top_level_json(s: str):
    """Return the first valid top-level JSON object/array found in s.
    Tries {...} then [...], scanning with a small bracket-matching parser.
    Raises ValueError if not found.
    """
    def scan(opener: str, closer: str):
        start = s.find(opener)
        while start != -1:
            depth = 0
            i = start
            while i < len(s):
                ch = s[i]
                if ch == opener:
                    depth += 1
                elif ch == closer:
                    depth -= 1
                    if depth == 0:
                        candidate = s[start:i+1]
                        try:
                            return json.loads(candidate)
                        except json.JSONDecodeError:
                            break  # keep searching further occurrences
                i += 1
            start = s.find(opener, start + 1)
        return None
    out = scan('{', '}')
    if out is not None:
        return out
    out = scan('[', ']')
    if out is not None:
        return out
    raise ValueError("No JSON found in LLM output") 



# --- 1) HELPERS: deterministic clause splitter ---


# Numbered: 1., 1.1, 2.3.4, optionally followed by ")" or "."
_RE_NUMBERED = re.compile(r'^\s*((?:\d+\.){1,4}\d+|\d+)[\.)]?\s*(.*)$')
# Section/Article: Section 2.1, Sec. 3(b), Article IV, ARTICLE IV
_RE_SECTION = re.compile(r"^\s*(?:sec(?:tion)?\.?\s+([\dA-Za-z\.\(\)]+)|article\s+([ivxlcdmIVXLCDM]+))[:\.)\-–—]?\s*(.*)$", re.IGNORECASE)
# Parenthetical: (a), (i), (A)
_RE_PAREN = re.compile(r"^\s*\(([A-Za-z]{1,3}|[ivxlcdmIVXLCDM]{1,4})\)[\.)]?\s+(.+)$")
# Bullets: -, •, ·, *
_RE_BULLET = re.compile(r"^\s*([\-•·\*])\s+(.+)$")
# ALL‑CAPS heading lines (with basic punctuation allowed) - made more flexible
_RE_ALLCAPS = re.compile(r"^[A-Z0-9][A-Z0-9\s\-/,.&()]{2,}$")
# Title lines ending with a colon (often used as headings) - made more flexible
_RE_TITLE_COLON = re.compile(r"^\s*([A-Z][A-Za-z0-9 ,/&\-]{1,}):\s*$")
# Additional patterns for common heading formats
_RE_ROMAN_NUMERAL = re.compile(r"^\s*([IVX]+)\.?\s+(.+)$", re.IGNORECASE)
_RE_LETTERED = re.compile(r"^\s*([A-Z])\.?\s+(.+)$")

_MAX_BLOCK_LEN = 1800   # characters; split overly long blocks
_MIN_HEADING_BODY = 40  # merge a heading‑only fragment into the next body


def split_into_clause_blocks(text: str) -> List[Dict[str, str]]:
    """Split contract text into stable clause blocks.
    Returns: [{"clause_id", "heading", "text"}]
    Rules:
      • New block on numbered/section/article/paren headings, bullets, ALL‑CAPS lines, or Title: lines
      • If no headings found, fall back to blank‑line paragraph blocks
      • Merge tiny heading‑only fragments with following block
      • Split very long blocks on safe boundaries (";\n", double newlines)
    """
    lines = text.splitlines()
    
    blocks: List[Dict[str, str]] = []
    buf: List[str] = []
    current_heading: str | None = None
    heading_seen = False

    def is_heading(line: str):
        # Return (True, clean_heading) if line starts a heading; else (False, None)
        m = _RE_NUMBERED.match(line)
        if m:
            title = m.group(2) or ""
            result = _clean_heading(title) if title else line.strip()
            return True, result
            
        m = _RE_SECTION.match(line)
        if m:
            # Combine section number with title for better context
            section_num = m.group(1) or m.group(2) or ""
            title_part = m.group(3) or ""
            if section_num and title_part:
                full_title = f"{section_num} {title_part}".strip()
            else:
                full_title = (title_part or section_num or "").strip()
            # Don't use _clean_heading here as it removes section numbers
            result = full_title if full_title else _strip_leading_marker(line)
            return True, result
            
        m = _RE_PAREN.match(line)
        if m:
            result = _clean_heading(m.group(2))
            return True, result
            
        if _RE_BULLET.match(line):
            result = _strip_leading_bullet(line)
            return True, result
            
        if _RE_TITLE_COLON.match(line):
            result = line.strip().rstrip(":")
            return True, result
            
        m = _RE_ROMAN_NUMERAL.match(line)
        if m:
            result = _clean_heading(m.group(2))
            return True, result
            
        m = _RE_LETTERED.match(line)
        if m:
            result = _clean_heading(m.group(2))
            return True, result
            
        if _RE_ALLCAPS.match(line.strip()) and len(line.strip()) <= 120:
            result = line.strip()
            return True, result
            
        return False, None

    def flush_block():
        nonlocal buf, current_heading
        if not buf:
            current_heading = None
            return
        body = "\n".join(buf).strip()
        if not body:
            buf = []
            current_heading = None
            return
        idx = len(blocks) + 1
        heading = current_heading or _first_words(body, 9)
        clause_id = f"C{idx:03d}"
        # Optionally split very long blocks for downstream LLM calls
        for chunk in _split_overlong_block(body):
            blocks.append({"clause_id": clause_id if chunk is body else f"{clause_id}a",
                           "heading": heading,
                           "text": chunk})
        buf = []
        current_heading = None

    for raw in lines:
        line = raw.rstrip()
        if not line.strip():
            # preserve paragraph breaks within a block
            if buf and buf[-1] != "":
                buf.append("")
            continue
        is_head, title = is_heading(line)
        if is_head:
            # if current buffer looks like a tiny heading‑only fragment, merge later
            if buf:
                flush_block()
            heading_seen = True
            current_heading = title or _first_words(line, 9)
            buf.append(line)  # include the heading line in the body for traceability
        else:
            buf.append(line)

    flush_block()

    # Fallback: if we detected no headings at all, split on blank lines
    if not heading_seen and len(blocks) <= 1:
        blocks = []
        for idx, group in enumerate(_split_on_blank_lines(lines), start=1):
            body = "\n".join(group).strip()
            if not body:
                continue
            clause_id = f"C{idx:03d}"
            blocks.append({"clause_id": clause_id,
                           "heading": _first_words(body, 9),
                           "text": body})

    # Merge tiny heading‑only fragments into the following block
    blocks = _merge_tiny_heading_fragments(blocks)

    # Final touch: normalize headings for clause_ref readability
    for b in blocks:
        # Don't clean section headings that contain numbers followed by text
        if re.match(r"^\d+(\.\d+)*\s*-\s*\w+", b["heading"]) or re.match(r"^[IVX]+\s*-\s*\w+", b["heading"]):
            # Keep section headings as-is
            pass
        else:
            b["heading"] = _clean_heading(b["heading"]) or _first_words(b["text"], 9)

    return blocks


# --- helpers ---

def _split_on_blank_lines(lines: List[str]):
    group: List[str] = []
    for ln in lines:
        if ln.strip():
            group.append(ln)
        else:
            if group:
                yield group
                group = []
    if group:
        yield group


def _first_words(s: str, n: int) -> str:
    words = s.replace("\n", " ").split()
    label = " ".join(words[:n])
    return (label + ("…" if len(words) > n else "")).strip()


def _strip_leading_marker(line: str) -> str:
    return re.sub(r"^\s*(?:section\s+\d+(?:\.\d+)*|sec\.?\s+\d+(?:\.\d+)*|article\s+[ivxlcdmIVXLCDM]+|\d+(?:\.\d+){0,3}|\([A-Za-zivxlcdmIVXLCDM]{1,4}\))[\.)]?[:\-–—]?\s*",
                  "", line, flags=re.IGNORECASE).strip()


def _strip_leading_bullet(line: str) -> str:
    return re.sub(r"^\s*[\-•·\*]\s+", "", line).strip()


def _merge_tiny_heading_fragments(blocks: List[Dict[str, str]]) -> List[Dict[str, str]]:
    if not blocks:
        return blocks
    merged: List[Dict[str, str]] = []
    i = 0
    while i < len(blocks):
        b = blocks[i]
        body_wo_heading = _remove_first_line_if_heading_like(b["text"]) or b["text"]
        if len(body_wo_heading) < _MIN_HEADING_BODY and i + 1 < len(blocks):
            # merge with next
            nxt = blocks[i + 1]
            merged_text = (b["text"].rstrip() + "\n\n" + nxt["text"]).strip()
            merged.append({
                "clause_id": b["clause_id"],
                "heading": b["heading"] or nxt["heading"],
                "text": merged_text,
            })
            i += 2
        else:
            merged.append(b)
            i += 1
    return merged


def _remove_first_line_if_heading_like(text: str) -> str:
    first, *rest = text.splitlines()
    # if first line looks like a heading/bullet/ALLCAPS/title:
    if (_RE_NUMBERED.match(first) or _RE_SECTION.match(first) or _RE_PAREN.match(first)
            or _RE_BULLET.match(first) or _RE_TITLE_COLON.match(first)
            or (_RE_ALLCAPS.match(first.strip()) and len(first.strip()) <= 120)):
        return "\n".join(rest)
    return text


def _split_overlong_block(body: str) -> List[str]:
    if len(body) <= _MAX_BLOCK_LEN:
        return [body]
    # Try to split on a safe boundary first: ";\n" or double newlines
    parts = re.split(r";\s*\n|\n\n", body)
    out: List[str] = []
    cur = ""
    for p in parts:
        test = (cur + ("\n\n" if cur else "") + p).strip()
        if len(test) > _MAX_BLOCK_LEN and cur:
            out.append(cur)
            cur = p.strip()
        else:
            cur = test
    if cur:
        out.append(cur)
    return out


def _clean_heading(h: str) -> str:
    # Remove leading numbers/parentheses and compress spaces
    h = re.sub(r"^\s*((?:\d+\.){1,4}\d+|\d+(?:\.\d+){0,3}|\([A-Za-zivxlcdmIVXLCDM]{1,4}\))[\.)]?[:\-–—]?\s*", "", h)
    h = re.sub(r"\s+", " ", h).strip()
    return h


# ----------------- Stubbed Heuristic Function ---------------------
# === STEP 5: Smarter stub + quick summary (works for many contract types) ===
# Goal: Keep using NO API KEY, but improve results across NDAs, MSAs, SOWs, etc.


# --- 1) REPLACE your current stub with this smarter version ---

def call_llm_for_extraction(text: str) -> ExtractionResponse:  # STILL A STUB
    t = (text or "").strip()
    if not t:
        return ExtractionResponse(obligations=[], meta={})

    lower = t.lower()
    obs: List[Obligation] = []

    # Party hints (generic pairs seen across contracts)
    party_map = [
        ("buyer", "Buyer"), ("purchaser", "Buyer"), ("customer", "Customer"),
        ("seller", "Seller"), ("supplier", "Supplier"), ("vendor", "Supplier"),
        ("licensee", "Licensee"), ("licensor", "Licensor"),
        ("landlord", "Landlord"), ("tenant", "Tenant"),
        ("employer", "Employer"), ("employee", "Employee"),
        ("recipient", "Recipient"), ("discloser", "Discloser"),
        ("party a", "Party A"), ("party b", "Party B"),
        ("contractor", "Contractor"), ("client", "Client"),
    ]

    DUTY_RE = re.compile(r'\b(shall|must|agrees?|undertakes|will)\b', re.IGNORECASE)

    def guess_party(default="Both parties"):
        # explicit mutual
        if re.search(r'\b(each\s+party|both\s+parties)\b', lower):
            return "Both parties"
        # contextual party within ~50 chars of a duty verb
        for key, label in party_map:
            for m in re.finditer(rf'\b{re.escape(key)}\b', lower):
                window = lower[max(0, m.start()-50): m.end()+50]
                if DUTY_RE.search(window):
                    return label
        return default

    # --- Amount / Deadline helpers ---
    m_amount = re.search(r"((?:usd|gbp|eur)\s*[0-9.,]+|[\$£€]\s*[0-9.,]+)", t, flags=re.IGNORECASE)
    def find_amount():
        return m_amount.group(1) if m_amount else None

    def find_deadline():
        # Net 7 / within 10 days / no later than 30 days / by 1 Jan 2026
        pats = [
            r"net\s*\d+",
            r"within\s+\d+\s+(?:business\s+)?days",
            r"no\s+later\s+than\s+\d+\s+days",
            r"by\s+\w+\s+\d{1,2},?\s+\d{4}",
            r"by\s+\d{1,2}\s+\w+\s+\d{4}",
        ]
        for p in pats:
            m = re.search(p, lower)
            if m:
                return m.group(0)
        return None

    def find_trigger():
        m = re.search(r'(?:\b(?:upon|if|unless|subject to)\b[^\n\.;,]+)', t, flags=re.IGNORECASE)
        return m.group(0).strip() if m else None

    # --- Heuristic families ---

    # 1) Payment
    if re.search(r"\bpay(?:ment)?\b|\binvoice\b|\bfee[s]?\b|\bconsideration\b", lower):
        obs.append(Obligation(
            party=guess_party("Buyer"),
            action="Pay amounts due",
            trigger=find_trigger() or ("On invoice" if "invoice" in lower else None),
            deadline=find_deadline(),
            amount=find_amount(),
            clause_ref=None,
        ))

    # 2) Delivery / performance
    if re.search(r"\bdeliver\b|\bshipment\b|\bprovide\b|\bperform\b", lower):
        obs.append(Obligation(
            party=guess_party("Seller"),
            action="Deliver/provide the goods or services",
            trigger=find_trigger(),
            deadline=find_deadline(),
            amount=None,
            clause_ref=None,
        ))

    # 3) Confidentiality core (NDA/general)
    if re.search(r"\bconfidential\b|\bnon\-disclosure\b|\bnda\b", lower):
        # hold in confidence
        if re.search(r"hold|keep\s+.*confiden", lower):
            obs.append(Obligation(
                party=guess_party("Recipient"),
                action="Keep Confidential Information secret",
                trigger=find_trigger() or "From disclosure onward",
                deadline=None,
                amount=None,
                clause_ref=None,
            ))
        # use solely/only for purpose
        if re.search(r"use\s+(?:solely|only)|purpose", lower):
            obs.append(Obligation(
                party=guess_party("Recipient"),
                action="Use Confidential Information solely for the stated purpose",
                trigger=find_trigger(),
                deadline=None,
                amount=None,
                clause_ref=None,
            ))
        # do not disclose
        if re.search(r"not\s+disclose|without\s+prior\s+written\s+consent", lower):
            obs.append(Obligation(
                party=guess_party("Recipient"),
                action="Do not disclose to third parties without prior written consent",
                trigger=find_trigger(),
                deadline=None,
                amount=None,
                clause_ref=None,
            ))
        # return or destroy
        if re.search(r"return|destroy|destruction", lower):
            obs.append(Obligation(
                party=guess_party("Recipient"),
                action="Return or destroy Confidential Information on request",
                trigger="Upon request" if re.search(r"return.*request|destroy.*request|destruction.*request", lower) else find_trigger(),
                deadline=None,
                amount=None,
                clause_ref=None,
            ))

    # 4) Notices
    if re.search(r"\bnotice[s]?\b|\bnotify\b|\bwritten\s+notice\b", lower):
        obs.append(Obligation(
            party=guess_party("Both parties"),
            action="Send/receive notices per contract rules",
            trigger=find_trigger(),
            deadline=find_deadline(),
            amount=None,
            clause_ref=None,
        ))

    # 5) Compliance / law / policy
    if re.search(r"\bcomply\b|\bcompliance\b|\bapplicable\s+law\b|\bgdpr\b|\bdata\s+protection\b", lower):
        obs.append(Obligation(
            party=guess_party("Both parties"),
            action="Comply with applicable laws and policies",
            trigger=find_trigger(),
            deadline=None,
            amount=None,
            clause_ref=None,
        ))

    # 6) Indemnity / warranties (high-level)
    if re.search(r"\bindemnif(y|ication)\b", lower):
        obs.append(Obligation(
            party=guess_party(),
            action="Indemnify the other party for specified losses",
            trigger=find_trigger(),
            deadline=None,
            amount=None,
            clause_ref=None,
        ))
    if re.search(r"\bwarrant\b|\brepresent\b", lower):
        obs.append(Obligation(
            party=guess_party(),
            action="Provide warranties/representations as stated",
            trigger=find_trigger(),
            deadline=None,
            amount=None,
            clause_ref=None,
        ))

    # 7) Termination cues
    if re.search(r"\bterminate\b|\btermination\b|\bbreach\b", lower):
        obs.append(Obligation(
            party=guess_party("Both parties"),
            action="Observe termination rights and post-termination obligations",
            trigger=find_trigger(),
            deadline=None,
            amount=None,
            clause_ref=None,
        ))

    return ExtractionResponse(obligations=obs, meta={})


# --- 2)  `/extract-obligations` endpoint with per‑clause processing ---
@app.post("/extract-obligations", response_model=ExtractionResponse)
async def extract_obligations(
    file: UploadFile | None = File(default=None),
    contract_text: str | None = Form(default=None),
):
    """Phase 2 (no key): DOCX or pasted text -> split into clause blocks -> stub per block.
    Returns one flat list of obligations with solid clause_ref values.
    """
    if not file and not (contract_text and contract_text.strip()):
        raise HTTPException(status_code=400, detail="Provide a .pdf/.docx file or contract_text.")

    # 1) Get raw text from DOCX or form
    if file is not None:
        if not (file.filename or "").lower().endswith((".docx", ".pdf")):
            raise HTTPException(status_code=400, detail="Accepts .docx and .pdf files only.")
        try:
            content = await file.read()
            filename_lower = (file.filename or "").lower()
            if filename_lower.endswith(".pdf"):
                raw_text = extract_text_from_pdf_bytes(content)
                src_meta = {"source": "pdf", "filename": file.filename}
            elif filename_lower.endswith(".docx"):
                raw_text = extract_text_from_docx_bytes(content)
                src_meta = {"source": "docx", "filename": file.filename}
            else:
                raise HTTPException(status_code=400, detail="Unsupported file type")
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"File parsing failed: {e}")
    else:
        raw_text = (contract_text or "").strip()
        src_meta = {"source": "text"}

    text = normalize_text(raw_text)

    # 2) Split into deterministic blocks
    blocks = split_into_clause_blocks(text)

    # 3) Run the stub per block and attach clause_ref
    all_obs: list[Obligation] = []
    for blk in blocks:
        result = call_llm_for_extraction(blk["text"])  # STUB currently
        # attach clause_ref if missing
        label = blk["heading"] or blk["clause_id"]
        ref = f"{blk['clause_id']} — {label}"
        for ob in result.obligations:
            if not ob.clause_ref:
                ob.clause_ref = ref
            all_obs.append(ob)

    # 4) Return a single, flat list with meta
    meta = {**src_meta, "mode": "stub", "blocks": len(blocks), "obligations": len(all_obs)}
    return ExtractionResponse(obligations=all_obs, meta=meta)



@app.get("/dummy-data", response_model=ExtractionResponse)
def dummy_data():
    return {
        "obligations": [
            {
                "party": "Seller",
                "action": "Deliver the goods",
                "trigger": "Upon receipt of payment",
                "deadline": "within 3 days",
                "amount": None,
                "clause_ref": "2.1",
            },
            {
                "party": "Buyer",
                "action": "Pay the purchase price",
                "trigger": "On invoice",
                "deadline": "Net 7",
                "amount": "USD 50,000",
                "clause_ref": "3.2",
            },
        ],
        "meta": {"source": "dummy"},
    }

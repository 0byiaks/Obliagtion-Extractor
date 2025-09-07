# services/export_service.py
import csv
import io
from typing import Iterable, List, Any

class ExportService:
    def to_csv(self, obligations: Iterable[Any]) -> str:
        """
        obligations: iterable of ObligationItem (either flat or structured).
        Returns CSV as a string.
        """
        rows: List[dict] = []
        for o in obligations:
            # Support both dict-like and attribute models (Pydantic)
            get = (lambda k, default=None:
                   (o.get(k, default) if isinstance(o, dict) else getattr(o, k, default)))

            flat = {}

            # Core fields (flat-compatible)
            flat["id"] = get("id")
            flat["party"] = get("party")
            flat["action"] = get("action")
            flat["trigger"] = get("trigger")
            flat["clause_id"] = get("clause_id") or get("clause_reference")
            flat["confidence_score"] = get("confidence_score")

            # Amount (handle structured or flat)
            amount = get("amount")
            if amount and not isinstance(amount, (str,)):
                # structured: object/dict with raw/value/currency
                flat["amount_raw"] = getattr(amount, "raw", None) if not isinstance(amount, dict) else amount.get("raw")
                flat["amount_value"] = getattr(amount, "value", None) if not isinstance(amount, dict) else amount.get("value")
                flat["amount_currency"] = getattr(amount, "currency", None) if not isinstance(amount, dict) else amount.get("currency")
            else:
                # flat string
                flat["amount_raw"] = amount
                flat["amount_value"] = None
                flat["amount_currency"] = None

            # Deadline (handle structured or flat)
            deadline = get("deadline")
            if deadline and not isinstance(deadline, (str,)):
                flat["deadline_raw"] = getattr(deadline, "raw", None) if not isinstance(deadline, dict) else deadline.get("raw")
                flat["deadline_normalized"] = getattr(deadline, "normalized", None) if not isinstance(deadline, dict) else deadline.get("normalized")
            else:
                flat["deadline_raw"] = deadline
                flat["deadline_normalized"] = None

            rows.append(flat)

        # Choose a stable header order
        header_order = [
            "id", "clause_id", "party", "action", "trigger",
            "deadline_raw", "deadline_normalized",
            "amount_raw", "amount_value", "amount_currency",
            "confidence_score",
        ]
        # Include any extra keys that may appear
        all_keys = list(header_order)
        for r in rows:
            for k in r.keys():
                if k not in all_keys:
                    all_keys.append(k)

        buf = io.StringIO(newline="")
        writer = csv.DictWriter(buf, fieldnames=all_keys, extrasaction="ignore")
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
        return buf.getvalue()

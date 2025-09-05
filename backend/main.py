from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/ping")
def ping():
    return {"status": "ok", "message": "Hello from FastAPI"}


@app.post("/extract")
async def extract(
    file: UploadFile | None = File(default=None),
     text: str | None = Form(default=None),
):
    # Validate input: require at least one
    if file is None and (text is None or text.strip() == ""):
        raise HTTPException(status_code=400, detail="Provide either a file or text")

    if file is not None:
        # Read a small chunk to preview without loading huge files into memory
        sample = await file.read(4000)  # 4KB preview
        # Reset file pointer if you plan to read it again later (not needed in this echo step)
        # await file.seek(0)
        preview = sample.decode(errors="ignore")[:200]
        return {
            "mode": "file",
            "filename": file.filename,
            "content_type": file.content_type,
            "bytes_read_for_preview": len(sample),
            "preview": preview,
        }

    # Text mode
    cleaned = text.strip()
    return {
        "mode": "text",
        "length": len(cleaned),
        "preview": cleaned[:300],
    }




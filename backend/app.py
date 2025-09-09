from fastapi import FastAPI
from api.routes import ingest as ingest_routes

app = FastAPI(title="Obligation Extractor (Demo)")

app.include_router(ingest_routes.router)

@app.get("/ping")
def ping():
    return {"status": "ok"}
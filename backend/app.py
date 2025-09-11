from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import extract as extract_routes

app = FastAPI(title="Obligation Extractor (Demo)")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

app.include_router(extract_routes.router)

@app.get("/ping")
def ping():
    return {"status": "ok"}
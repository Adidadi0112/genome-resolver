from fastapi import FastAPI
from .routes import routes
from .services import report_generation

app = FastAPI(title="Genomic Analysis API")

# Include routers for text generation and any other endpoints
app.include_router(routes.router, prefix="/text", tags=["Text Generation"])

# Additional endpoints can be added here as needed

# Example root endpoint to verify the app is running
@app.get("/")
def read_root():
    return {"message": "Genomic Analysis API is running!"}

# run app: uvicorn app.main:app --reload

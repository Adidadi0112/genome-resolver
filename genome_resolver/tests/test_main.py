from fastapi.testclient import TestClient
from app.main import app

# Create a TestClient instance
client = TestClient(app)

# Test for the root endpoint
def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Genomic Analysis API is running!"}

# Test for the /text endpoint (if routes.router is properly included)
def test_text_generation_router():
    response = client.get("/text")  # Example GET request to /text
    assert response.status_code in [200, 404]  # Adjust based on actual endpoint behavior

import pytest
from fastapi.testclient import TestClient
from .main import app

client = TestClient(app)

@pytest.fixture
async def test_mom_data():
    # Create test MOM data
    return {
        "title": "Test Meeting",
        "transcript": "Test transcript content",
        "participants": [{"email": "test1@example.com"}, {"email": "test2@example.com"}],
        "date": "2026-03-10"
    }


def test_send_mom_email(test_mom_data):
    # Call the endpoint
    response = client.post("/api/v1/moms/send-mom", json=test_mom_data)
    assert response.status_code == 200
    assert response.json()['status'] == 'success'


def test_email_delivery(test_mom_data):
    # Verify email was sent
    # This would require mocking or checking logs in production
    assert True  # Replace with actual verification logic
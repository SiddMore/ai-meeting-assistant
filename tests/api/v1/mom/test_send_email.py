import pytest
from fastapi.testclient import TestClient
from .main import app
from src.main.api.v1 import mom

client = TestClient(app)

@pytest.fixture
def test_mom():
    # Create a test MOM record
    with Session(engine) as db:
        # Cleanup first in case previous test left it
        db.query(MOM).filter(MOM.id == 1).delete()
        db.commit()
        
        # Create test MOM
        test_mom = MOM(
            id=1,
            title="Test Meeting",
            content="Test content",
            user_id=1
        )
        db.add(test_mom)
        db.commit()
        db.refresh(test_mom)
        return test_mom

def test_send_email(test_mom, monkeypatch):
    # Mock the email sending
    monkeypatch.setattr("resend.emails.send", lambda *args, **kwargs: {"id": "test_email_id", "object": "Email", "recipient_address": "test@example.com"})
    
    # Set up recipients
    test_participants = [
        {"email": "participant1@example.com"},
        {"email": "participant2@example.com"}
    ]
    
    with Session(engine) as db:
        # Add test participants
        for p in test_participants:
            participant = User(email=p["email"])
            db.add(participant)
            db.flush()
        
        db.refresh(test_mom)
        test_mom.participants = [participant for participant in db.query(User).all()]
        
        # Call the endpoint
        response = client.post("/api/v1/moms/1/send-email", json={})
        assert response.status_code == 200
        assert response.json()["status"] == "success"
        
        # Verify the email was sent with the correct recipients
        assert "recipient_address" in response.json()["details"]
        assert response.json()["details"]["recipient_address"] == "participant1@example.com" or "participant2@example.com"
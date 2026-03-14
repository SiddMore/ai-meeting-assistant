from fastapi import HTTPException, Depends, status
from fastapi.encoders import jsonable_encoder
from .service import send_mom_email_service
from .schemas import EmailResponse
from ..models import MOM
from ..models.user import User
from typing import List, Optional
from sqlalchemy.orm import Session
from . import models, schemas
from .deps import get_db

def get_recipients(mom: MOM, db: Session) -> List[str]:
    """Get all recipients for a MOM"""
    return [participant.email for participant in mom.participants]

async def send_mom_email(mom_id: int, db: Session = Depends(get_db)) -> EmailResponse:
    try:
        mom = db.query(MOM).filter(MOM.id == mom_id).first()
        if not mom:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="MOM not found")
        
        recipients = get_recipients(mom, db)
        if not recipients:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No recipients found")
        
        email_data = {
            "subject": f"MOM: {mom.title}",
            "html": generate_mom_email_html(mom)
        }
        
        result = send_mom_email_service(email_data, recipients, db)
        return result
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

def generate_mom_email_html(mom: MOM) -> str:
    action_items = "\n".join([f"- {item.task}" for item in mom.action_items])
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{mom.title}</title>
    </head>
    <body>
        <h1>{mom.title}</h1>
        <p>{mom.content}</p>
        <h2>Action Items</h2>
        <ul>
            {action_items}
        </ul>
    </body>
    </html>
    """
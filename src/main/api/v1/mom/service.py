from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from .models import MOM, User
from .schemas import EmailResponse
import os
import resend

# Initialize resend client
resend_api_key = os.getenv("RESEND_API_KEY")
if not resend_api_key:
    raise RuntimeError("RESEND_API_KEY environment variable not set")

resend = resend.Resend(resend_api_key)

def send_mom_email(mom_id: int, db: Session, recipients: List[str] = None):
    try:
        mom = db.query(MOM).filter(MOM.id == mom_id).first()
        if not mom:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="MOM not found")
        
        # If recipients are not provided, get from meeting participants
        if not recipients:
            recipients = [participant.email for participant in mom.participants]
        
        if not recipients:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No recipients found")
        
        # Generate email content
        subject = f"MOM: {mom.title}"
        html = generate_mom_email_html(mom)
        
        # Send email
        response = resend.emails.send({
            "from": "MOM Generator <onboarding@resend.dev>",
            "to": recipients,
            "subject": subject,
            "html": html
        })
        
        return EmailResponse(
            status="success",
            message="Email sent successfully",
            details=response
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

def generate_mom_email_html(mom: MOM):
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
            {''.join(f"<li>{item.task}</li>" for item in mom.action_items)}
        </ul>
    </body>
    </html>
    """
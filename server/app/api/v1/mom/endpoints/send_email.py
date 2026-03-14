from fastapi import APIRouter, HTTPException
from app.services.mom_service import generate_mom
from app.services.email_service import send_email
from app.models.mom import Mom
from datetime import datetime

router = APIRouter()

@router.post("/send-mom")
async def send_mom_endpoint(mom: Mom):
    try:
        # Generate MOM content
        mom_data = await generate_mom(
            meeting_title=mom.title,
            transcript_text=mom.transcript,
            participants=[{
                "name": p.name,
                "email": p.email
            } for p in mom.participants],
            meeting_date=mom.date
        )

        # Send email with template
        email_content = f"""
{ mom_data['full_content'] }
"""

        await send_email(
            to=mom.recipients,
            subject="Meeting Minutes",
            html_content=email_content
        )

        return {"status": "success", "message": "MOM sent successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
from pydantic import BaseModel
from datetime import datetime

class EmailResponse(BaseModel):
    status: str
    message: str
    details: dict

class EmailTemplate(BaseModel):
    subject: str
    html: str
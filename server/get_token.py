# get_token.py
import asyncio
from app.core.security import create_access_token
from app.core.config import settings

async def generate_dev_token():
    # Apni user ID yahan daal do (database se dekh kar)
    # Agar testing kar rahe ho toh koi bhi random UUID chalegi
    test_user_id = "your-user-id-here" 
    
    token = create_access_token(subject=test_user_id)
    print("\n🚀 TERA BEARER TOKEN YE RAHA:")
    print(f"Bearer {token}\n")

if __name__ == "__main__":
    asyncio.run(generate_dev_token())
    
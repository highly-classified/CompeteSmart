import os
import firebase_admin
from firebase_admin import credentials, auth
from fastapi import Header, HTTPException, status, Depends
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

# Path to the Firebase service account JSON file
SERVICE_ACCOUNT_PATH = os.path.join(os.getcwd(), "service-account.json")

# Initialize Firebase Admin SDK
if not firebase_admin._apps:
    try:
        cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        print(f"Error initializing Firebase Admin SDK: {e}")

async def get_current_user(authorization: Optional[str] = Header(None)):
    """
    FastAPI dependency to verify Firebase ID tokens.
    Extracts the 'uid' from the verified token.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = authorization.split(" ")[1]
    
    try:
        # Verify the Firebase ID token
        decoded_token = auth.verify_id_token(token)
        user_id = decoded_token.get("uid")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing 'uid' claim",
            )
            
        return user_id
        
    except auth.ExpiredIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Firebase ID token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except auth.InvalidIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Firebase ID token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

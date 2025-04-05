from datetime import datetime, timedelta
from jose import jwt
from fastapi import HTTPException, Security
from fastapi.security import OAuth2PasswordBearer
from app.config import settings
import redis
from datetime import timezone
from fastapi import status
from jose import JWTError
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

SECRET_KEY = settings.SECRET_KEY

if not SECRET_KEY:
    raise ValueError("SECRET_KEY must be set in environment variables!")

ALGORITHM = settings.ALGORITHM

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="users/login")

redis_client = redis.StrictRedis(host="localhost", port=6379, db=0, decode_responses=True)

def create_access_token(data: dict, expires_delta: timedelta = timedelta(days=1)):

    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta  
    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str = Security(oauth2_scheme)):

    try:

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        if redis_client.get(f"blacklist:{token}") == "blacklisted":
            raise HTTPException(status_code=401, detail="Token has been invalidated (logged out)")
        
        return payload
    
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))

def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        logger.info(f"Decoded Token: {payload}")
        user_id: int = payload.get("user_id")  
        exp: int = payload.get("exp")  

        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

        if datetime.now(timezone.utc).timestamp() > exp:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")

        return {"user_id": user_id, "exp": exp}

    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
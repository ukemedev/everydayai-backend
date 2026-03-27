from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import get_db
import models
import auth

router = APIRouter(prefix="/auth", tags=["auth"])

class RegisterRequest(BaseModel):
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

class ApiKeyRequest(BaseModel):
    openai_api_key: str

@router.post("/register")
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    existing_user = db.query(models.User).filter(
        models.User.email == request.email
    ).first()
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )
    hashed = auth.hash_password(request.password)
    user = models.User(email=request.email, hashed_password=hashed)
    db.add(user)
    db.commit()
    db.refresh(user)
    token = auth.create_token({"sub": user.email})
    return {"access_token": token, "token_type": "bearer"}

@router.post("/login")
def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(
        models.User.email == request.email
    ).first()
    if not user or not auth.verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )
    token = auth.create_token({"sub": user.email})
    return {"access_token": token, "token_type": "bearer"}

@router.put("/api-key")
def save_api_key(
    request: ApiKeyRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    current_user.openai_api_key = request.openai_api_key
    db.commit()
    return {"message": "API key saved successfully"}
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import get_db
import models
import auth
import os
import json
import urllib.request
import urllib.error

router = APIRouter(prefix="/auth", tags=["auth"])

PLAN_AGENT_LIMITS = {
    "free": 1,
    "starter": 5,
    "pro": 12,
    "agency": None,
}

PLAN_PRICES_USD_CENTS = {
    "starter": 900,
    "pro": 2200,
    "agency": 7500,
}


class RegisterRequest(BaseModel):
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

class ApiKeyRequest(BaseModel):
    openai_api_key: str

class PaymentVerifyRequest(BaseModel):
    reference: str
    plan: str


@router.post("/register")
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    existing_user = db.query(models.User).filter(
        models.User.email == request.email
    ).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed = auth.hash_password(request.password)
    user = models.User(email=request.email, hashed_password=hashed, plan="free")
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
        raise HTTPException(status_code=401, detail="Invalid email or password")
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


@router.get("/me")
def get_me(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    agent_count = db.query(models.Agent).filter(
        models.Agent.owner_id == current_user.id
    ).count()
    plan = current_user.plan or "free"
    agent_limit = PLAN_AGENT_LIMITS.get(plan)
    return {
        "email": current_user.email,
        "plan": plan,
        "agent_count": agent_count,
        "agent_limit": agent_limit,
        "message_count": current_user.message_count or 0,
        "has_openai_key": bool(current_user.openai_api_key),
    }


@router.post("/verify-payment")
def verify_payment(
    request: PaymentVerifyRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    if request.plan not in PLAN_PRICES_USD_CENTS:
        raise HTTPException(status_code=400, detail="Invalid plan")

    paystack_secret = os.getenv("PAYSTACK_SECRET_KEY")
    if not paystack_secret:
        raise HTTPException(status_code=503, detail="Payment processing not configured")

    try:
        url = f"https://api.paystack.co/transaction/verify/{request.reference}"
        req = urllib.request.Request(
            url,
            headers={"Authorization": f"Bearer {paystack_secret}"}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        raise HTTPException(status_code=400, detail="Payment verification failed")
    except Exception:
        raise HTTPException(status_code=500, detail="Could not reach payment provider")

    if not data.get("status") or data.get("data", {}).get("status") != "success":
        raise HTTPException(status_code=400, detail="Payment was not successful")

    current_user.plan = request.plan
    db.commit()
    db.refresh(current_user)

    return {
        "message": f"Plan upgraded to {request.plan}",
        "plan": request.plan,
    }

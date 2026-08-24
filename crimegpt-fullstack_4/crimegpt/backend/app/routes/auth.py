import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import OFFICE_LOCATIONS
from app.database import get_db
from app.models import User, AuditLog
from app.schemas.auth import LoginRequest, RegisterRequest
from app.security import verify_password, hash_password, create_token

router = APIRouter(prefix="/api/auth", tags=["auth"])


def log_action(db: Session, username: str, role: str, action: str, details: str):
    db.add(AuditLog(id=f"log_{uuid.uuid4().hex[:12]}", username=username, role=role, action=action, details=details))
    db.commit()


def user_public(u: User) -> dict:
    return {
        "id": u.id, "username": u.username, "role": u.role, "name": u.name,
        "designation": u.designation, "badgeId": u.badgeId, "email": u.email,
        "department": u.department, "lastLogin": u.lastLogin,
        "officeLocation": u.officeLocation or "Central District",
        "status": u.status or "Active",
    }


@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username.ilike(payload.username)).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if user.status == "Pending":
        raise HTTPException(status_code=403, detail="Your account is pending authorization by an administrator.")
    if user.status == "Suspended":
        raise HTTPException(status_code=403, detail="Your account has been suspended. Please contact administration.")

    user.lastLogin = datetime.now(timezone.utc).isoformat()
    db.commit()

    office_location = user.officeLocation or "Central District"
    token = create_token(user.id, user.username, user.role, user.name, office_location)
    log_action(db, user.username, user.role, "User Login", "Successfully logged into the console.")

    return {"token": token, "user": user_public(user)}


@router.post("/register")
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    exists = db.query(User).filter(User.username.ilike(payload.username)).first()
    if exists:
        raise HTTPException(status_code=400, detail="Username already exists")

    if payload.officeLocation not in OFFICE_LOCATIONS:
        raise HTTPException(status_code=400, detail="Invalid office location selected")

    designation = payload.designation or (
        f"{payload.department} (Badge #{payload.badgeId})" if payload.department and payload.badgeId else ""
    )
    if not designation:
        raise HTTPException(status_code=400, detail="All fields are required")

    new_id = f"u{db.query(User).count() + 1}"
    user = User(
        id=new_id, username=payload.username, hashed_password=hash_password(payload.password),
        role=payload.role, name=payload.name, designation=designation,
        badgeId=payload.badgeId or "", email=payload.email or "", department=payload.department or "",
        officeLocation=payload.officeLocation, status="Pending",
    )
    db.add(user)
    db.commit()

    log_action(db, user.username, user.role, "User Registration", f"New account registered under designation: {designation}")

    token = create_token(user.id, user.username, user.role, user.name, user.officeLocation)
    return {"token": token, "user": user_public(user)}

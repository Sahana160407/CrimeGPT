from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import User
from app.routes.auth import log_action
from app.schemas.auth import ProfileUpdateRequest, SettingsUpdateRequest, SecurityUpdateRequest
from app.security import verify_password, hash_password

router = APIRouter(prefix="/api/user", tags=["profile"])


def _get_user_or_404(db: Session, current_user: dict) -> User:
    user = db.query(User).filter(User.id == current_user["id"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def _profile_response(u: User) -> dict:
    """Mirrors server.ts's GET /api/user/profile - fills sensible defaults for any missing fields."""
    return {
        "id": u.id, "username": u.username, "role": u.role, "name": u.name,
        "designation": u.designation, "badgeId": u.badgeId, "email": u.email,
        "phone": u.phone, "department": u.department,
        "notificationsEnabled": u.notificationsEnabled, "language": u.language,
        "twoFactorEnabled": u.twoFactorEnabled, "loginNotificationsEnabled": u.loginNotificationsEnabled,
        "passwordLastChanged": u.passwordLastChanged, "accountStatus": u.accountStatus,
        "lastLogin": u.lastLogin, "officeLocation": u.officeLocation or "Central District",
    }


@router.get("/profile")
def get_profile(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    user = _get_user_or_404(db, current_user)
    return _profile_response(user)


@router.put("/profile")
def update_profile(payload: ProfileUpdateRequest, db: Session = Depends(get_db),
                    current_user: dict = Depends(get_current_user)):
    user = _get_user_or_404(db, current_user)

    if payload.name:
        user.name = payload.name
    if payload.badgeId:
        user.badgeId = payload.badgeId
    if payload.email:
        user.email = payload.email
    if payload.phone:
        user.phone = payload.phone
    if payload.department:
        user.department = payload.department
        user.designation = payload.department  # kept in sync, matching server.ts

    db.commit()
    log_action(db, user.username, user.role, "Update Profile", "Updated personal profile information.")
    return _profile_response(user)


@router.put("/settings")
def update_settings(payload: SettingsUpdateRequest, db: Session = Depends(get_db),
                     current_user: dict = Depends(get_current_user)):
    user = _get_user_or_404(db, current_user)

    if payload.username and payload.username.lower() != user.username.lower():
        exists = db.query(User).filter(User.username.ilike(payload.username)).first()
        if exists:
            raise HTTPException(status_code=400, detail="Username already exists.")
        user.username = payload.username
    if payload.email:
        user.email = payload.email
    if payload.notificationsEnabled is not None:
        user.notificationsEnabled = payload.notificationsEnabled
    if payload.language:
        user.language = payload.language

    db.commit()
    log_action(db, user.username, user.role, "Update Settings", "Updated account preferences and configuration.")
    return _profile_response(user)


@router.put("/password")
def update_password(payload: SecurityUpdateRequest, db: Session = Depends(get_db),
                     current_user: dict = Depends(get_current_user)):
    user = _get_user_or_404(db, current_user)

    if payload.currentPassword or payload.newPassword:
        if not payload.currentPassword or not payload.newPassword:
            raise HTTPException(status_code=400, detail="Both current password and new password are required.")
        if not verify_password(payload.currentPassword, user.hashed_password):
            raise HTTPException(status_code=400, detail="Current password is incorrect.")
        user.hashed_password = hash_password(payload.newPassword)
        user.passwordLastChanged = datetime.now(timezone.utc).isoformat()
        log_action(db, user.username, user.role, "Change Password", "Successfully updated account password.")

    if payload.twoFactorEnabled is not None:
        user.twoFactorEnabled = payload.twoFactorEnabled
        log_action(db, user.username, user.role, "Toggle 2FA",
                   f"Two-factor authentication {'enabled' if payload.twoFactorEnabled else 'disabled'}.")

    if payload.loginNotificationsEnabled is not None:
        user.loginNotificationsEnabled = payload.loginNotificationsEnabled
        log_action(db, user.username, user.role, "Toggle Login Notifications",
                   f"Login notifications {'enabled' if payload.loginNotificationsEnabled else 'disabled'}.")

    db.commit()
    return {"success": True, "message": "Security settings updated successfully."}

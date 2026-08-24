from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import User, AuditLog
from app.routes.auth import log_action, user_public

router = APIRouter(prefix="/api", tags=["users"])


@router.get("/users")
def list_users(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ("Admin", "Supervisor"):
        raise HTTPException(status_code=403, detail="Access denied. Admin or Supervisor clearance required.")
    return [user_public(u) for u in db.query(User).all()]


@router.delete("/users/{user_id}")
def delete_user(user_id: str, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "Admin":
        raise HTTPException(status_code=403, detail="Only Admins can delete users.")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    username = user.username
    db.delete(user)
    db.commit()

    log_action(db, current_user["username"], current_user["role"], "Delete User", f"Deleted user account: {username}")
    return {"success": True, "message": "User deleted successfully."}


@router.put("/users/{user_id}/role")
def update_user_role(user_id: str, payload: dict, db: Session = Depends(get_db),
                      current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "Admin":
        raise HTTPException(status_code=403, detail="Only Admins can change user roles.")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.role = payload.get("role", user.role)
    db.commit()

    log_action(db, current_user["username"], current_user["role"], "Update User Role",
               f"Assigned role {user.role} to {user.username}")
    return user_public(user)


@router.put("/users/{user_id}/status")
def update_user_status(user_id: str, payload: dict, db: Session = Depends(get_db),
                        current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ("Admin", "Supervisor"):
        raise HTTPException(status_code=403, detail="Access denied. Only Admins or Supervisors can change user status.")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.status = payload.get("status", user.status)
    db.commit()

    log_action(db, current_user["username"], current_user["role"], "Update User Status",
               f"Set status of user {user.username} to {user.status}")
    return user_public(user)


@router.get("/audit-logs")
def get_audit_logs(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ("Admin", "Supervisor"):
        raise HTTPException(status_code=403, detail="Access denied.")

    logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).all()
    return [{"id": l.id, "username": l.username, "role": l.role, "action": l.action,
             "details": l.details, "timestamp": str(l.timestamp)} for l in logs]

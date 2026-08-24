from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Criminal
from app.routes.auth import log_action
from app.schemas.case import CriminalCreateRequest

router = APIRouter(prefix="/api/criminals", tags=["criminals"])


def criminal_out(c: Criminal) -> dict:
    return {"criminalId": c.criminalId, "name": c.name, "age": c.age, "gender": c.gender,
            "address": c.address, "criminalHistory": c.criminalHistory, "riskScore": c.riskScore}


@router.get("")
def list_criminals(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    return [criminal_out(c) for c in db.query(Criminal).all()]


@router.post("")
def create_criminal(payload: CriminalCreateRequest, db: Session = Depends(get_db),
                     current_user: dict = Depends(get_current_user)):
    if not payload.name or not payload.criminalHistory:
        raise HTTPException(status_code=400, detail="Criminal name and history are required")

    criminal = Criminal(
        criminalId=f"c{db.query(Criminal).count() + 1}", name=payload.name, age=payload.age or 30,
        gender=payload.gender or "Male", address=payload.address or "Unknown",
        criminalHistory=payload.criminalHistory, riskScore=payload.riskScore or 50,
    )
    db.add(criminal)
    db.commit()

    log_action(db, current_user["username"], current_user["role"], "Create Criminal Record", f"Registered profile for {payload.name}")
    return criminal_out(criminal)

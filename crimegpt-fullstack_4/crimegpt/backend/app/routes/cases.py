import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import DISTRICT_COORDS, OFFICE_LOCATIONS
from app.database import get_db
from app.deps import get_current_user
from app.models import Case, Victim, Criminal, Evidence
from app.routes.auth import log_action
from app.schemas.case import CaseCreateRequest, CaseUpdateRequest, EvidenceCreateRequest, SuspectLinkRequest
from app.services.location_util import is_location_restricted, user_location

router = APIRouter(prefix="/api/cases", tags=["cases"])


def case_out(c: Case) -> dict:
    return {
        "firNumber": c.firNumber, "date": c.date, "crimeType": c.crimeType,
        "description": c.description, "status": c.status,
        "investigatingOfficer": c.investigatingOfficer, "district": c.district,
        "coordinates": {"lat": c.lat, "lng": c.lng},
        "victimId": c.victimId, "criminalIds": c.criminalIds or [], "riskScore": c.riskScore,
    }


@router.get("")
def list_cases(
    search: str | None = None, crimeType: str | None = None,
    district: str | None = None, status: str | None = None,
    db: Session = Depends(get_db), current_user: dict = Depends(get_current_user),
):
    cases = db.query(Case).all()

    if search:
        s = search.lower()
        cases = [c for c in cases if s in c.firNumber.lower() or s in c.description.lower()
                 or s in c.investigatingOfficer.lower()]
    if crimeType and crimeType != "All":
        cases = [c for c in cases if c.crimeType == crimeType]

    # Location scoping matches server.ts exactly: non-admins are ALWAYS locked to
    # their own office location (a ?district= override is ignored for them).
    # Admins can optionally pass ?district= to filter, or see everything if omitted.
    if is_location_restricted(current_user):
        cases = [c for c in cases if c.district == user_location(current_user)]
    elif district and district != "All":
        cases = [c for c in cases if c.district == district]

    if status and status != "All":
        cases = [c for c in cases if c.status == status]

    return [case_out(c) for c in cases]


@router.get("/{fir_number}")
def get_case(fir_number: str, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    case = db.query(Case).filter(Case.firNumber == fir_number).first()
    if not case:
        raise HTTPException(status_code=404, detail="FIR not found")

    if is_location_restricted(current_user) and case.district != user_location(current_user):
        raise HTTPException(status_code=403, detail="Access Denied: You do not have authorization to view files from this district.")

    victim = db.query(Victim).filter(Victim.victimId == case.victimId).first()
    criminals = db.query(Criminal).filter(Criminal.criminalId.in_(case.criminalIds or [])).all()
    evidence = db.query(Evidence).filter(Evidence.firNumber == case.firNumber).all()

    log_action(db, current_user["username"], current_user["role"], "View Case Details",
               f"Accessed case files for {fir_number}")

    result = case_out(case)
    result["victim"] = {"victimId": victim.victimId, "name": victim.name, "age": victim.age,
                         "gender": victim.gender, "address": victim.address} if victim else None
    result["criminals"] = [{"criminalId": c.criminalId, "name": c.name, "age": c.age, "gender": c.gender,
                             "address": c.address, "criminalHistory": c.criminalHistory,
                             "riskScore": c.riskScore} for c in criminals]
    result["evidence"] = [{"evidenceId": e.evidenceId, "firNumber": e.firNumber, "description": e.description,
                            "fileName": e.fileName, "fileSize": e.fileSize,
                            "dateUploaded": e.dateUploaded} for e in evidence]
    return result


@router.put("/{fir_number}")
def update_case(fir_number: str, payload: CaseUpdateRequest, db: Session = Depends(get_db),
                 current_user: dict = Depends(get_current_user)):
    case = db.query(Case).filter(Case.firNumber == fir_number).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    if payload.status is not None:
        case.status = payload.status
    if payload.description is not None:
        case.description = payload.description
    if payload.investigatingOfficer is not None:
        case.investigatingOfficer = payload.investigatingOfficer
    if payload.riskScore is not None:
        case.riskScore = payload.riskScore

    db.commit()
    log_action(db, current_user["username"], current_user["role"], "Update Case", f"Modified details of case {fir_number}")
    return case_out(case)


@router.post("")
def create_case(payload: CaseCreateRequest, db: Session = Depends(get_db),
                 current_user: dict = Depends(get_current_user)):
    # Non-admins can only file cases under their own office location, regardless
    # of what district they submit - matches server.ts's finalDistrict logic.
    final_district = payload.district
    if is_location_restricted(current_user):
        final_district = user_location(current_user)

    if not final_district:
        raise HTTPException(status_code=400, detail="Missing required FIR fields")

    if final_district not in OFFICE_LOCATIONS:
        raise HTTPException(status_code=400, detail=f"'{final_district}' is not a recognized location.")

    new_victim_id = f"v{db.query(Victim).count() + 1}"
    db.add(Victim(victimId=new_victim_id, name=payload.victimName, age=payload.victimAge,
                   gender=payload.victimGender, address=payload.victimAddress))

    current_year = datetime.now().year
    next_serial = db.query(Case).count() + 1024
    fir_number = f"FIR-{current_year}-{next_serial}"

    lat, lng = DISTRICT_COORDS.get(final_district, (12.9716, 77.5946))

    case = Case(
        firNumber=fir_number, date=datetime.now().strftime("%Y-%m-%d"), crimeType=payload.crimeType,
        description=payload.description, status=payload.status or "Pending",
        investigatingOfficer=payload.investigatingOfficer, district=final_district,
        lat=lat, lng=lng, victimId=new_victim_id, criminalIds=[], riskScore=payload.riskScore or 50,
    )
    db.add(case)
    db.commit()

    log_action(db, current_user["username"], current_user["role"], "Create Case", f"Registered a new FIR: {fir_number}")
    return case_out(case)


@router.post("/{fir_number}/evidence")
def add_evidence(fir_number: str, payload: EvidenceCreateRequest, db: Session = Depends(get_db),
                  current_user: dict = Depends(get_current_user)):
    evidence = Evidence(
        evidenceId=f"ev{db.query(Evidence).count() + 1}", firNumber=fir_number,
        description=payload.description, fileName=payload.fileName,
        fileSize=payload.fileSize or "1.2 MB", dateUploaded=datetime.now().strftime("%Y-%m-%d"),
    )
    db.add(evidence)
    db.commit()

    log_action(db, current_user["username"], current_user["role"], "Upload Evidence",
               f"Added evidence file ({payload.fileName}) to {fir_number}")
    return {"evidenceId": evidence.evidenceId, "firNumber": evidence.firNumber, "description": evidence.description,
            "fileName": evidence.fileName, "fileSize": evidence.fileSize, "dateUploaded": evidence.dateUploaded}


@router.post("/{fir_number}/suspects")
def link_suspect(fir_number: str, payload: SuspectLinkRequest, db: Session = Depends(get_db),
                  current_user: dict = Depends(get_current_user)):
    case = db.query(Case).filter(Case.firNumber == fir_number).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    ids = case.criminalIds or []
    if payload.criminalId not in ids:
        ids.append(payload.criminalId)
        case.criminalIds = ids
        db.commit()
        log_action(db, current_user["username"], current_user["role"], "Link Suspect",
                   f"Linked criminal ID {payload.criminalId} to case {fir_number}")

    return case_out(case)

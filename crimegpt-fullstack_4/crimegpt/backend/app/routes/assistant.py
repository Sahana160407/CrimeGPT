from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Case, Victim, Criminal, Evidence
from app.routes.auth import log_action
from app.schemas.chat import ChatRequest, FirNumberRequest, SpeakRequest
from app.services.fallback_engine import fallback_reply
from app.services.gemini_service import call_gemini, gemini_available
from app.services.location_util import is_location_restricted, user_location

router = APIRouter(prefix="/api", tags=["assistant"])

SYSTEM_PROMPT = """You are "CrimeGPT", an advanced AI-powered Conversational Crime Investigation and
Analytics platform for law enforcement agencies. Your target users are police officers, investigators,
and district crime analysts.

CRITICAL WORKFLOW RULES:
1. Rely strictly on the CURRENT DATABASE DATA CONTEXT provided. Do not invent fictitious cases or details.
2. If the user asks for cases, criminals, status, or counts, search the provided context and return the actual match.
3. Support dual languages natively - English or Kannada. Answer in the queried language.
4. Always cite specific data records in your answer (e.g. FIR numbers, officer names, suspect IDs).
5. Present structured answers with clean Markdown lists, bold keys, and sections."""


def _local_cases(db: Session, current_user: dict) -> list[Case]:
    cases = db.query(Case).all()
    if is_location_restricted(current_user):
        cases = [c for c in cases if c.district == user_location(current_user)]
    return cases


def build_db_context(local_cases: list[Case], criminals: list[Criminal]) -> str:
    lines = ["CURRENT DATABASE DATA CONTEXT:\n\n-- FIRs/Cases:"]
    for c in local_cases:
        lines.append(f"{c.firNumber} | {c.crimeType} | {c.status} | {c.district} | Officer: {c.investigatingOfficer} | "
                      f"Risk: {c.riskScore} | {c.description}")
    lines.append("\n-- Criminal Suspects:")
    for c in criminals:
        lines.append(f"{c.criminalId} | {c.name} | Risk: {c.riskScore} | {c.criminalHistory}")
    return "\n".join(lines)


@router.post("/chatbot")
def chatbot(payload: ChatRequest, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    log_action(db, current_user["username"], current_user["role"], "Chat Query",
               f'Queried CrimeGPT: "{payload.message[:60]}..."')

    local_cases = _local_cases(db, current_user)
    criminals = db.query(Criminal).all()

    if gemini_available():
        contents = []
        for h in (payload.history or []):
            contents.append({"role": "user" if h.sender == "user" else "model", "parts": [{"text": h.text}]})
        contents.append({"role": "user", "parts": [{"text": f"{build_db_context(local_cases, criminals)}\n\nUSER QUESTION: {payload.message}"}]})

        text = call_gemini(contents, SYSTEM_PROMPT)
        if text:
            return {"text": text}

    return {"text": fallback_reply(local_cases, criminals, payload.message, current_user["name"])}


@router.post("/assistant/summary")
def case_summary(payload: FirNumberRequest, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    case = db.query(Case).filter(Case.firNumber == payload.firNumber).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found.")
    if is_location_restricted(current_user) and case.district != user_location(current_user):
        raise HTTPException(status_code=403, detail="Access Denied: You do not have authorization to view files from this district.")

    victim = db.query(Victim).filter(Victim.victimId == case.victimId).first()
    criminals = db.query(Criminal).filter(Criminal.criminalId.in_(case.criminalIds or [])).all()
    evidence = db.query(Evidence).filter(Evidence.firNumber == case.firNumber).all()

    if gemini_available():
        prompt_text = (
            f"Analyze this crime case and provide an executive summary:\n"
            f"FIR: {case.firNumber}, Type: {case.crimeType}, Status: {case.status}, District: {case.district}, "
            f"Officer: {case.investigatingOfficer}, Risk: {case.riskScore}, Description: {case.description}\n\n"
            f"Provide markdown with: 1. Executive Summary (3 sentences) 2. Critical Risk Factors "
            f"3. Identified Patterns & Leads 4. Suggested Next Investigative Actions (3-4 steps)"
        )
        text = call_gemini([{"role": "user", "parts": [{"text": prompt_text}]}], SYSTEM_PROMPT)
        if text:
            return {"summary": text}

    evidence_lines = "\n".join(f"- *{e.fileName}*: {e.description}" for e in evidence) or "- No evidence catalogued yet."
    suspects = ", ".join(c.name for c in criminals) or "Unknown suspects"
    summary = f"""### 📑 Executive Case Brief: {case.firNumber}

- **Overview**: This is a **{case.crimeType}** incident registered on **{case.date}** within **{case.district}** district. Currently **{case.status}**, handled by **{case.investigatingOfficer}**.

- **Critical Risk Factors**:
  - Risk Score: **{case.riskScore}/100**.
  - Victim: **{victim.name if victim else "Unknown"}**, age {victim.age if victim else "N/A"}.

- **Evidence Extracted**:
{evidence_lines}

- **Suggested Next Investigative Actions**:
  1. Verify alibis of linked suspect(s): {suspects}.
  2. Retrieve nearby CCTV footage around {case.date}.
  3. Interview key witnesses and log statements.
  4. Compile chargesheet details for judicial presentation."""
    return {"summary": summary}


@router.post("/assistant/timeline")
def case_timeline(payload: FirNumberRequest, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    case = db.query(Case).filter(Case.firNumber == payload.firNumber).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found.")
    if is_location_restricted(current_user) and case.district != user_location(current_user):
        raise HTTPException(status_code=403, detail="Access Denied: You do not have authorization to view files from this district.")

    evidence = db.query(Evidence).filter(Evidence.firNumber == case.firNumber).all()

    timeline = [{"date": case.date, "title": "FIR Registered",
                 "description": f"Official complaint filed and FIR {case.firNumber} assigned to {case.investigatingOfficer}.",
                 "type": "system"}]
    for e in evidence:
        timeline.append({"date": e.dateUploaded, "title": "Evidence Catalogued",
                          "description": f"Evidence added: {e.description} (File: {e.fileName}).", "type": "evidence"})

    timeline.sort(key=lambda t: t["date"])

    try:
        projected = (datetime.strptime(case.date, "%Y-%m-%d") + timedelta(days=15)).strftime("%Y-%m-%d")
    except ValueError:
        projected = case.date
    timeline.append({"date": projected, "title": "Projected Chargesheet Submission",
                      "description": "Deadline to file formal chargesheet based on standard investigation guidelines.",
                      "type": "deadline"})
    return timeline


@router.post("/assistant/similar")
def similar_cases(payload: FirNumberRequest, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    case = db.query(Case).filter(Case.firNumber == payload.firNumber).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    if is_location_restricted(current_user) and case.district != user_location(current_user):
        raise HTTPException(status_code=403, detail="Access Denied: You do not have authorization to view files from this district.")

    others = db.query(Case).filter(Case.firNumber != payload.firNumber).all()
    if is_location_restricted(current_user):
        others = [f for f in others if f.district == user_location(current_user)]

    results = []
    for f in others:
        if f.crimeType != case.crimeType and f.district != case.district:
            continue
        score = 0
        if f.crimeType == case.crimeType:
            score += 50
        if f.district == case.district:
            score += 30
        common = set(f.criminalIds or []) & set(case.criminalIds or [])
        if common:
            score += 40
        results.append({"firNumber": f.firNumber, "crimeType": f.crimeType, "status": f.status,
                         "district": f.district, "date": f.date, "investigatingOfficer": f.investigatingOfficer,
                         "matchConfidence": min(score, 100)})

    results.sort(key=lambda r: r["matchConfidence"], reverse=True)
    return results[:3]


@router.post("/assistant/speak")
def speak(payload: SpeakRequest, current_user: dict = Depends(get_current_user)):
    # No Gemini TTS integration in this build - the frontend already handles this
    # gracefully by falling back to the browser's built-in speech synthesis.
    return {"clientFallback": True}

from collections import Counter
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Case, Criminal, AuditLog
from app.services.location_util import is_location_restricted, user_location

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

MONTH_BASELINE = {"Jan": 0, "Feb": 0, "Mar": 0, "Apr": 0, "May": 0, "Jun": 0}

# Matches server.ts's allHotspots list exactly, tagged by district for scoping.
ALL_HOTSPOTS = [
    {"name": "Sector 1, Central District", "count": 3, "riskLevel": "Medium", "district": "Central District"},
    {"name": "Sector 6, Central District", "count": 2, "riskLevel": "Medium", "district": "Central District"},
    {"name": "Sector 2, Central District", "count": 4, "riskLevel": "High", "district": "Central District"},
    {"name": "Sector 3 Palace Area", "count": 1, "riskLevel": "Low", "district": "Central District"},
    {"name": "Palace Road, District C", "count": 1, "riskLevel": "Low", "district": "District C"},
    {"name": "Hampankatta, District E", "count": 2, "riskLevel": "High", "district": "District E"},
    {"name": "Hubli Road, District D", "count": 1, "riskLevel": "Low", "district": "District D"},
    {"name": "Sector 5, North District", "count": 2, "riskLevel": "High", "district": "North District"},
    {"name": "Sector 2 Parking Lot, South District", "count": 3, "riskLevel": "High", "district": "South District"},
    {"name": "Puducherry Central", "count": 0, "riskLevel": "Low", "district": "Puducherry"},
    {"name": "Bengaluru Town Hall", "count": 0, "riskLevel": "Low", "district": "Bengaluru"},
]


@router.get("/trends")
def get_trends(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    all_cases = db.query(Case).all()
    criminals = db.query(Criminal).all()

    local_cases = all_cases
    if is_location_restricted(current_user):
        local_cases = [c for c in all_cases if c.district == user_location(current_user)]

    total_crimes = len(local_cases)
    open_cases = len([c for c in local_cases if c.status in ("Pending", "Under Investigation")])
    closed_cases = len([c for c in local_cases if c.status in ("Closed", "Chargesheet Filed")])

    local_criminal_ids = set()
    for c in local_cases:
        local_criminal_ids.update(c.criminalIds or [])
    high_risk_offenders = len([c for c in criminals if c.criminalId in local_criminal_ids and c.riskScore >= 80])

    type_counts = Counter(c.crimeType for c in local_cases)
    crimes_by_type = [{"name": k, "value": v} for k, v in type_counts.items()]

    district_counts = Counter(c.district for c in local_cases)
    crimes_by_district = [{"name": k, "value": v} for k, v in district_counts.items()]

    monthly = dict(MONTH_BASELINE)
    for c in local_cases:
        try:
            month = datetime.strptime(c.date, "%Y-%m-%d").strftime("%b")
            monthly[month] = monthly.get(month, 0) + 1
        except ValueError:
            pass
    crime_trends = [{"month": k, "cases": v} for k, v in monthly.items()]

    recent_cases = local_cases[-3:]
    recent_logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(3).all()
    recent_activities = (
        [{"id": c.firNumber, "type": "FIR Registered", "title": f"New Case Registered: {c.firNumber}",
          "description": f"{c.crimeType} crime at {c.district} was registered under status {c.status}.",
          "timestamp": c.date} for c in recent_cases]
        + [{"id": log.id, "type": "Audit Log", "title": f"{log.action} by {log.username}",
            "description": log.details, "timestamp": str(log.timestamp)[:10]} for log in recent_logs]
    )
    recent_activities.sort(key=lambda a: a["timestamp"], reverse=True)

    hotspots = ALL_HOTSPOTS
    if is_location_restricted(current_user):
        hotspots = [h for h in ALL_HOTSPOTS if h["district"] == user_location(current_user)]

    return {
        "kpis": {"totalCrimes": total_crimes, "openCases": open_cases, "closedCases": closed_cases,
                 "highRiskOffenders": high_risk_offenders},
        "crimesByType": crimes_by_type,
        "crimesByDistrict": crimes_by_district,
        "crimeTrends": crime_trends,
        "recentActivities": recent_activities[:6],
        "hotspots": [{"name": h["name"], "count": h["count"], "riskLevel": h["riskLevel"]} for h in hotspots],
    }

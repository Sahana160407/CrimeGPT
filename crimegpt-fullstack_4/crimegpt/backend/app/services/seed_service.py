import json
import uuid

from sqlalchemy.orm import Session

from app.config import SEED_JSON_PATH, ROLES, OFFICE_LOCATIONS, DISTRICT_COORDS
from app.models import User, Case, Criminal, Victim, Evidence, AuditLog, Role, Location
from app.security import hash_password

DEFAULT_BADGE_BY_USERNAME = {
    "admin": "POL-2026-0001", "vinay": "POL-2026-1024",
    "sneha": "POL-2026-2048", "satish": "POL-2026-4096",
}
DEFAULT_LOCATION_BY_USERNAME = {
    "admin": "All", "vinay": "Central District", "sneha": "South District",
    "satish": "District C", "siva": "District E", "sah": "District E",
}

# DEMO DATA - additional users/cases/criminals for the newly requested cities, so
# the app is demonstrable across multiple locations immediately. Clearly marked as
# demo data, seeded only on first run alongside your existing db_seed.json content.
DEMO_CITY_USERS = [
    {"id": "u_demo_mysuru", "username": "kavya", "password": "kavya123", "role": "Investigator",
     "name": "Inspector Kavya Rao", "department": "Mysuru City Police", "officeLocation": "Mysuru",
     "badgeId": "POL-2026-5001"},
    {"id": "u_demo_mangaluru", "username": "arjun", "password": "arjun123", "role": "Investigator",
     "name": "Inspector Arjun Shetty", "department": "Mangaluru City Police", "officeLocation": "Mangaluru",
     "badgeId": "POL-2026-5002"},
    {"id": "u_demo_belagavi", "username": "meera", "password": "meera123", "role": "Analyst",
     "name": "ACP Meera Desai", "department": "Belagavi Crime Branch", "officeLocation": "Belagavi",
     "badgeId": "POL-2026-5003"},
    {"id": "u_demo_tumakuru", "username": "rakesh", "password": "rakesh123", "role": "Investigator",
     "name": "Inspector Rakesh Naik", "department": "Tumakuru District Police", "officeLocation": "Tumakuru",
     "badgeId": "POL-2026-5004"},
]

DEMO_CITY_CASES = [
    {"firNumber": "FIR-2026-5001", "date": "2026-05-03", "crimeType": "Theft", "district": "Mysuru",
     "description": "Chain snatching reported near Mysuru Palace east gate during evening crowd hours.",
     "investigatingOfficer": "Inspector Kavya Rao", "status": "Under Investigation", "riskScore": 55},
    {"firNumber": "FIR-2026-5002", "date": "2026-05-18", "crimeType": "Cybercrime", "district": "Mysuru",
     "description": "Victim reported unauthorized UPI transactions after a phishing SMS link.",
     "investigatingOfficer": "Inspector Kavya Rao", "status": "Pending", "riskScore": 40},
    {"firNumber": "FIR-2026-5003", "date": "2026-04-22", "crimeType": "Burglary", "district": "Mangaluru",
     "description": "Residential break-in reported near Kadri Hills, jewellery and electronics stolen.",
     "investigatingOfficer": "Inspector Arjun Shetty", "status": "Closed", "riskScore": 60},
    {"firNumber": "FIR-2026-5004", "date": "2026-06-02", "crimeType": "Assault", "district": "Mangaluru",
     "description": "Altercation outside a college campus resulted in minor injuries to two students.",
     "investigatingOfficer": "Inspector Arjun Shetty", "status": "Chargesheet Filed", "riskScore": 45},
    {"firNumber": "FIR-2026-5005", "date": "2026-05-11", "crimeType": "Fraud", "district": "Belagavi",
     "description": "Investment scheme fraud reported affecting multiple local investors.",
     "investigatingOfficer": "ACP Meera Desai", "status": "Under Investigation", "riskScore": 70},
    {"firNumber": "FIR-2026-5006", "date": "2026-03-29", "crimeType": "Theft", "district": "Tumakuru",
     "description": "Two-wheeler theft reported from a bus stand parking area.",
     "investigatingOfficer": "Inspector Rakesh Naik", "status": "Pending", "riskScore": 35},
]

DEMO_CITY_CRIMINALS = [
    {"criminalId": "c_demo_1", "name": "Ravi Poojary", "age": 34, "gender": "Male",
     "address": "Kadri, Mangaluru", "criminalHistory": "Prior conviction for residential burglary (2023).",
     "riskScore": 78},
    {"criminalId": "c_demo_2", "name": "Suma Gowda", "age": 29, "gender": "Female",
     "address": "Vontikoppal, Mysuru", "criminalHistory": "Named suspect in an ongoing cybercrime/UPI fraud ring.",
     "riskScore": 65},
]


def load_seed_json() -> dict:
    if SEED_JSON_PATH.exists():
        with open(SEED_JSON_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"users": [], "firs": [], "criminals": [], "victims": [], "evidence": [], "auditLogs": []}


def seed_lookup_tables(db: Session):
    """Roles and Locations are lookup tables - safe to (re)sync every startup,
    since they're reference data, not user-created content."""
    for role_name in ROLES:
        if not db.query(Role).filter(Role.name == role_name).first():
            db.add(Role(name=role_name, description=f"{role_name} role"))

    for loc_name in OFFICE_LOCATIONS:
        if not db.query(Location).filter(Location.name == loc_name).first():
            lat, lng = DISTRICT_COORDS.get(loc_name, (12.9716, 77.5946))
            db.add(Location(name=loc_name, latitude=lat, longitude=lng))

    # "All" is a sentinel for Admin accounts, not a real filterable location, but it
    # still needs a Locations row to satisfy the FK constraint on User.officeLocation.
    if not db.query(Location).filter(Location.name == "All").first():
        db.add(Location(name="All", latitude=0, longitude=0))

    db.commit()


def seed_database(db: Session):
    """Only seeds USER-FACING data if the users table is empty - never overwrites
    real data on restart. Lookup tables (Roles/Locations) are handled separately
    above since they're safe to sync every time."""
    if db.query(User).first() is not None:
        return

    data = load_seed_json()

    for u in data.get("users", []):
        username = u["username"]
        office_location = u.get("officeLocation") or DEFAULT_LOCATION_BY_USERNAME.get(username, "Central District")
        db.add(User(
            id=u["id"], username=username,
            hashed_password=hash_password(u["password"]),
            role=u["role"], name=u["name"],
            designation=u.get("designation", ""),
            badgeId=u.get("badgeId") or DEFAULT_BADGE_BY_USERNAME.get(username, ""),
            email=u.get("email") or f"{username}@crimegpt.gov.in",
            phone=u.get("phone", ""),
            department=u.get("department", ""),
            officeLocation=office_location,
            status=u.get("status", "Active"),
            lastLogin=u.get("lastLogin"),
            notificationsEnabled=u.get("notificationsEnabled", True),
            language=u.get("language", "English"),
            twoFactorEnabled=u.get("twoFactorEnabled", False),
            loginNotificationsEnabled=u.get("loginNotificationsEnabled", True),
        ))
    db.commit()  # committed before cases, since cases don't depend on users but keeps stages clean

    for v in data.get("victims", []):
        db.add(Victim(victimId=v["victimId"], name=v["name"], age=v.get("age", 30),
                       gender=v.get("gender", "Male"), address=v.get("address", "")))

    for c in data.get("criminals", []):
        db.add(Criminal(criminalId=c["criminalId"], name=c["name"], age=c.get("age", 30),
                         gender=c.get("gender", "Male"), address=c.get("address", ""),
                         criminalHistory=c.get("criminalHistory", ""), riskScore=c.get("riskScore", 50)))
    db.commit()  # victims/criminals must exist before cases can FK-reference them

    for f in data.get("firs", []):
        coords = f.get("coordinates", {"lat": 12.9716, "lng": 77.5946})
        db.add(Case(
            firNumber=f["firNumber"], date=f["date"], crimeType=f["crimeType"],
            description=f.get("description", ""), status=f.get("status", "Pending"),
            investigatingOfficer=f.get("investigatingOfficer", ""), district=f.get("district", ""),
            lat=coords.get("lat", 12.9716), lng=coords.get("lng", 77.5946),
            victimId=f.get("victimId"), criminalIds=f.get("criminalIds", []),
            riskScore=f.get("riskScore", 50),
        ))
    db.commit()  # cases must exist before evidence can FK-reference them

    for e in data.get("evidence", []):
        db.add(Evidence(evidenceId=e["evidenceId"], firNumber=e["firNumber"],
                         description=e.get("description", ""), fileName=e.get("fileName", ""),
                         fileSize=e.get("fileSize", "1.2 MB"), dateUploaded=e.get("dateUploaded", "")))

    for log in data.get("auditLogs", []):
        db.add(AuditLog(id=log["id"], username=log["username"], role=log["role"],
                         action=log["action"], details=log.get("details", "")))

    db.commit()

    # --- DEMO DATA for the newly requested cities ---
    for u in DEMO_CITY_USERS:
        db.add(User(
            id=u["id"], username=u["username"], hashed_password=hash_password(u["password"]),
            role=u["role"], name=u["name"], designation=u["department"], badgeId=u["badgeId"],
            email=f"{u['username']}@crimegpt.gov.in", department=u["department"],
            officeLocation=u["officeLocation"], status="Active",
        ))
    db.commit()

    for c in DEMO_CITY_CRIMINALS:
        db.add(Criminal(criminalId=c["criminalId"], name=c["name"], age=c["age"], gender=c["gender"],
                         address=c["address"], criminalHistory=c["criminalHistory"], riskScore=c["riskScore"]))
    db.commit()

    for i, f in enumerate(DEMO_CITY_CASES):
        victim_id = f"v_demo_{i}"
        db.add(Victim(victimId=victim_id, name=f"Demo Victim {i+1}", age=30 + i, gender="Male" if i % 2 == 0 else "Female",
                       address=f"{f['district']}, Karnataka"))
    db.commit()  # victims committed before the cases that reference them

    for i, f in enumerate(DEMO_CITY_CASES):
        victim_id = f"v_demo_{i}"
        lat, lng = DISTRICT_COORDS.get(f["district"], (12.9716, 77.5946))
        criminal_ids = ["c_demo_1"] if f["district"] == "Mangaluru" else (["c_demo_2"] if f["district"] == "Mysuru" else [])
        db.add(Case(
            firNumber=f["firNumber"], date=f["date"], crimeType=f["crimeType"],
            description=f["description"], status=f["status"], investigatingOfficer=f["investigatingOfficer"],
            district=f["district"], lat=lat, lng=lng, victimId=victim_id, criminalIds=criminal_ids,
            riskScore=f["riskScore"],
        ))
    db.commit()

    print(f"Seeded database: {len(data.get('users', []))} original users + {len(DEMO_CITY_USERS)} demo city users, "
          f"{len(data.get('firs', []))} original cases + {len(DEMO_CITY_CASES)} demo city cases, "
          f"{len(data.get('criminals', []))} original criminals + {len(DEMO_CITY_CRIMINALS)} demo city criminals.")

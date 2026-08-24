import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

JWT_SECRET_KEY = os.getenv("JWT_SECRET", "crimegpt-super-secret-key-2026-v1")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 24

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Now reads from .env - defaults to a local SQLite file if not set.
# To switch to PostgreSQL later, just set DATABASE_URL in .env to something like:
#   postgresql://user:password@localhost:5432/crimegpt
# No code changes needed elsewhere - SQLAlchemy handles both transparently.
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'crimegpt.db'}")

SEED_JSON_PATH = BASE_DIR / "db_seed.json"

FRONTEND_DIST_PATH = BASE_DIR.parent / "frontend"

# Roles - matches the roles the frontend's registration form and RBAC checks use.
ROLES = ["Admin", "Investigator", "Analyst", "Supervisor"]

# Valid office locations. The original 7 (district-style) values match the frontend's
# registration dropdown exactly. The 5 additional cities (Mysuru, Mangaluru, Belagavi,
# Tumakuru, plus Bengaluru already present) are DEMO locations seeded directly into the
# database for demonstration purposes - the registration dropdown wasn't touched (per
# "do not redesign the frontend"), so these are populated via seed data / admin action,
# not through frontend self-registration.
OFFICE_LOCATIONS = [
    "Central District", "North District", "South District",
    "District C", "District D", "District E", "Bengaluru", "Puducherry",
    "Mysuru", "Mangaluru", "Belagavi", "Tumakuru",
]

# Real approximate coordinates for every location, used both for map plotting and
# for auto-assigning coordinates when a new case is filed under a given district.
DISTRICT_COORDS = {
    "Central District": (12.9716, 77.5946),
    "District C": (12.3051, 76.6551),
    "District E": (12.8701, 74.8400),
    "District D": (15.3647, 75.1240),
    "North District": (13.0210, 77.5921),
    "South District": (12.9352, 77.6244),
    "Bengaluru": (12.9716, 77.5946),
    "Puducherry": (11.9416, 79.8083),
    "Mysuru": (12.2958, 76.6394),
    "Mangaluru": (12.9141, 74.8560),
    "Belagavi": (15.8497, 74.4977),
    "Tumakuru": (13.3379, 77.1173),
}

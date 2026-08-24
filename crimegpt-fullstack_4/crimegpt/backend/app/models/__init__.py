from sqlalchemy import Column, String, Integer, Float, JSON, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Role(Base):
    """Lookup table - the fixed set of valid roles. Referenced by User.role."""
    __tablename__ = "roles"
    name = Column(String, primary_key=True)  # Admin, Investigator, Analyst, Supervisor
    description = Column(String, default="")


class Location(Base):
    """Lookup table - every valid office/case location, with real coordinates.
    Referenced by User.officeLocation and Case.district."""
    __tablename__ = "locations"
    name = Column(String, primary_key=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)


class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, ForeignKey("roles.name"), nullable=False)
    name = Column(String, nullable=False)
    designation = Column(String, default="")
    badgeId = Column(String, default="")
    email = Column(String, default="")
    phone = Column(String, default="")
    department = Column(String, default="")
    # "All" is a special sentinel (not a real Location row) meaning "not restricted to
    # any single location" - only ever assigned to Admin accounts, so it's stored
    # without a FK constraint check bypass built into the seed/route logic instead.
    officeLocation = Column(String, default="Central District")
    status = Column(String, default="Active")  # Active, Pending, Suspended, Inactive
    lastLogin = Column(String, nullable=True)

    notificationsEnabled = Column(Boolean, default=True)
    language = Column(String, default="English")

    twoFactorEnabled = Column(Boolean, default=False)
    loginNotificationsEnabled = Column(Boolean, default=True)
    passwordLastChanged = Column(String, default="2026-07-15T09:12:00.000Z")
    accountStatus = Column(String, default="Active - Level 4 Clearance")

    role_ref = relationship("Role", foreign_keys=[role])


class Victim(Base):
    __tablename__ = "victims"
    victimId = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    age = Column(Integer, default=30)
    gender = Column(String, default="Male")
    address = Column(String, default="")


class Criminal(Base):
    __tablename__ = "criminals"
    criminalId = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    age = Column(Integer, default=30)
    gender = Column(String, default="Male")
    address = Column(String, default="")
    criminalHistory = Column(String, default="")
    riskScore = Column(Integer, default=50)


class Case(Base):
    """The 'firs' table - each row is one FIR/case."""
    __tablename__ = "cases"
    firNumber = Column(String, primary_key=True)
    date = Column(String, nullable=False)
    crimeType = Column(String, nullable=False)
    description = Column(String, default="")
    status = Column(String, default="Pending")
    investigatingOfficer = Column(String, default="")
    district = Column(String, ForeignKey("locations.name"), default="")
    lat = Column(Float, default=12.9716)
    lng = Column(Float, default=77.5946)
    victimId = Column(String, ForeignKey("victims.victimId"), nullable=True)
    criminalIds = Column(JSON, default=list)
    riskScore = Column(Integer, default=50)

    location_ref = relationship("Location", foreign_keys=[district])
    victim_ref = relationship("Victim", foreign_keys=[victimId])


class Evidence(Base):
    __tablename__ = "evidence"
    evidenceId = Column(String, primary_key=True)
    firNumber = Column(String, ForeignKey("cases.firNumber"), nullable=False)
    description = Column(String, default="")
    fileName = Column(String, default="")
    fileSize = Column(String, default="1.2 MB")
    dateUploaded = Column(String, nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(String, primary_key=True)
    username = Column(String, nullable=False)
    role = Column(String, nullable=False)
    action = Column(String, nullable=False)
    details = Column(String, default="")
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

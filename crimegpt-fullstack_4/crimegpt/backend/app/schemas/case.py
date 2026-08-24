from pydantic import BaseModel


class CaseCreateRequest(BaseModel):
    crimeType: str
    description: str
    status: str | None = "Pending"
    investigatingOfficer: str
    district: str | None = None
    victimName: str
    victimAge: int | None = 30
    victimGender: str | None = "Male"
    victimAddress: str | None = "Unknown Address"
    riskScore: int | None = 50


class CaseUpdateRequest(BaseModel):
    status: str | None = None
    description: str | None = None
    investigatingOfficer: str | None = None
    riskScore: int | None = None


class EvidenceCreateRequest(BaseModel):
    description: str
    fileName: str
    fileSize: str | None = "1.2 MB"


class SuspectLinkRequest(BaseModel):
    criminalId: str


class CriminalCreateRequest(BaseModel):
    name: str
    age: int | None = 30
    gender: str | None = "Male"
    address: str | None = "Unknown"
    criminalHistory: str
    riskScore: int | None = 50

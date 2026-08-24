from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str
    role: str
    name: str
    designation: str | None = None
    badgeId: str | None = None
    email: str | None = None
    department: str | None = None
    officeLocation: str


class ProfileUpdateRequest(BaseModel):
    name: str | None = None
    badgeId: str | None = None
    email: str | None = None
    phone: str | None = None
    department: str | None = None


class SettingsUpdateRequest(BaseModel):
    username: str | None = None
    email: str | None = None
    notificationsEnabled: bool | None = None
    language: str | None = None
    smsNotifs: bool | None = None
    sysBulletins: bool | None = None


class SecurityUpdateRequest(BaseModel):
    currentPassword: str | None = None
    newPassword: str | None = None
    twoFactorEnabled: bool | None = None
    loginNotificationsEnabled: bool | None = None

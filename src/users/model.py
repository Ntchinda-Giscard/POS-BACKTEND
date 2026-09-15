from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class UserResponse(BaseModel):
    code: str                 # AUTILIS.USR_0
    name: str                 # NOMUSR_0
    login: Optional[str] = None
    email: Optional[str] = None
    profile: Optional[str] = None   # PRFFCT_0 (profil fonction) – used as the role
    role: str = "cashier"           # admin | manager | cashier (derived from the profile)
    has_pin: bool = False
    last_login_at: Optional[datetime] = None


class LoginRequest(BaseModel):
    user_code: str
    pin: str


class ChangePinRequest(BaseModel):
    user_code: str
    old_pin: Optional[str] = None
    new_pin: str

import hashlib
import hmac
import os
import sqlite3
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from database.models import UserPin
from database.sync_data import get_db_file
from .model import UserResponse

# X3 function profiles that get elevated rights at the till. Everything else is a cashier.
ADMIN_PROFILES = {"ADMIN", "ADMCA", "FU00"}
MANAGER_PROFILES = {"CGES", "COMM", "MAGA", "RESS", "SUMP", "PLAN"}


def role_for_profile(profile: Optional[str]) -> str:
    p = (profile or "").strip().upper()
    if p in ADMIN_PROFILES:
        return "admin"
    if p in MANAGER_PROFILES:
        return "manager"
    return "cashier"


def _hash_pin(pin: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"), bytes.fromhex(salt), 120_000).hex()


def _x3_users(db: Session, user_code: Optional[str] = None):
    db_path = get_db_file(db)
    if not db_path:
        return []
    conn = sqlite3.connect(db_path)
    try:
        query = """
            SELECT USR_0, NOMUSR_0, LOGIN_0, ADDEML_0, PRFFCT_0
            FROM AUTILIS
            WHERE ENAFLG_0 = '2'
        """
        params: tuple = ()
        if user_code:
            query += " AND USR_0 = ?"
            params = (user_code,)
        query += " ORDER BY NOMUSR_0"
        return conn.execute(query, params).fetchall()
    finally:
        conn.close()


def list_users(db: Session) -> List[UserResponse]:
    pins = {p.user_code: p for p in db.query(UserPin).all()}
    users = []
    for code, name, login, email, profile in _x3_users(db):
        code = (code or "").strip()
        pin = pins.get(code)
        users.append(UserResponse(
            code=code,
            name=(name or "").strip() or code,
            login=(login or "").strip() or None,
            email=(email or "").strip() or None,
            profile=(profile or "").strip() or None,
            role=role_for_profile(profile),
            has_pin=pin is not None,
            last_login_at=pin.last_login_at if pin else None,
        ))
    return users


def get_user(db: Session, user_code: str) -> Optional[UserResponse]:
    rows = _x3_users(db, user_code.strip())
    if not rows:
        return None
    code, name, login, email, profile = rows[0]
    pin = db.query(UserPin).filter(UserPin.user_code == code.strip()).first()
    return UserResponse(
        code=code.strip(), name=(name or "").strip() or code.strip(),
        login=(login or "").strip() or None, email=(email or "").strip() or None,
        profile=(profile or "").strip() or None, role=role_for_profile(profile),
        has_pin=pin is not None, last_login_at=pin.last_login_at if pin else None,
    )


def login(db: Session, user_code: str, pin: str) -> UserResponse:
    """First login sets the PIN; later logins verify it."""
    user = get_user(db, user_code)
    if not user:
        raise ValueError("Utilisateur inconnu ou inactif dans Sage X3")
    if len(pin) < 4:
        raise ValueError("Le code PIN doit contenir au moins 4 caractères")

    record = db.query(UserPin).filter(UserPin.user_code == user.code).first()
    if record is None:
        salt = os.urandom(16).hex()
        record = UserPin(user_code=user.code, salt=salt, pin_hash=_hash_pin(pin, salt))
        db.add(record)
    elif not hmac.compare_digest(record.pin_hash, _hash_pin(pin, record.salt)):
        raise ValueError("Code PIN incorrect")

    record.last_login_at = datetime.now()
    db.commit()
    user.has_pin = True
    user.last_login_at = record.last_login_at
    return user


def change_pin(db: Session, user_code: str, old_pin: Optional[str], new_pin: str, by_admin: bool = False) -> None:
    if len(new_pin) < 4:
        raise ValueError("Le nouveau code PIN doit contenir au moins 4 caractères")
    record = db.query(UserPin).filter(UserPin.user_code == user_code.strip()).first()
    if record is None:
        raise ValueError("Cet utilisateur n'a pas encore de code PIN")
    if not by_admin and not hmac.compare_digest(record.pin_hash, _hash_pin(old_pin or "", record.salt)):
        raise ValueError("Ancien code PIN incorrect")
    record.salt = os.urandom(16).hex()
    record.pin_hash = _hash_pin(new_pin, record.salt)
    db.commit()

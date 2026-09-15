from typing import Dict, Optional
from sqlalchemy.orm import Session
from database.models import AppSetting

# Every till setting with its default. Keys are also what the frontend edits.
DEFAULTS: Dict[str, str] = {
    "low_stock_threshold": "10",          # used when ITMFACILIT.SAFSTO_0 is 0
    "export_folder": r"C:\poswaza\temp\export",
    "export_recipient": "",               # mailbox that Sage X3 imports from (POS → X3)
    "smtp_server": "",                    # blank = reuse the IMAP host with "imap" → "smtp"
    "smtp_port": "587",
    "receipt_footer": "Merci de votre visite",
    "auto_export_after_close": "0",       # 1 = export to X3 when the cash session closes
}

SECRET_KEYS = set()


def get_setting(db: Session, key: str, default: Optional[str] = None) -> Optional[str]:
    row = db.query(AppSetting).filter(AppSetting.key == key).first()
    if row is not None and row.value is not None:
        return row.value
    return DEFAULTS.get(key, default) if default is None else default


def get_all_settings(db: Session) -> Dict[str, str]:
    values = dict(DEFAULTS)
    for row in db.query(AppSetting).all():
        if row.value is not None:
            values[row.key] = row.value
    return values


def set_settings(db: Session, values: Dict[str, Optional[str]]) -> Dict[str, str]:
    for key, value in values.items():
        if key not in DEFAULTS:
            continue
        row = db.query(AppSetting).filter(AppSetting.key == key).first()
        if row is None:
            row = AppSetting(key=key)
            db.add(row)
        row.value = "" if value is None else str(value)
    db.commit()
    return get_all_settings(db)

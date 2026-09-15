import sqlite3
from typing import List, Optional
from sqlalchemy.orm import Session
from database.sync_data import get_db_file
from .model import SiteInfo


def _t(value) -> Optional[str]:
    value = (value or "").strip() if isinstance(value, str) else value
    return value or None


def _address(conn: sqlite3.Connection, bp_number: str, address_code: Optional[str]):
    query = "SELECT BPAADDLIG_0, BPAADDLIG_1, BPAADDLIG_2, POSCOD_0, CTY_0, SAT_0, CRY_0, CRYNAM_0, TEL_0, MOB_0, WEB_0, WEB_1 FROM BPADDRESS WHERE BPANUM_0 = ?"
    params = [bp_number]
    if address_code:
        query += " AND BPAADD_0 = ?"
        params.append(address_code)
    query += " ORDER BY BPAADDFLG_0 DESC LIMIT 1"
    return conn.execute(query, params).fetchone()


def get_site_info(db: Session, site: Optional[str]) -> Optional[SiteInfo]:
    db_path = get_db_file(db)
    if not db_path:
        return None
    conn = sqlite3.connect(db_path)
    try:
        if site:
            fac = conn.execute("SELECT FCY_0, FCYNAM_0, FCYSHO_0, LEGCPY_0, LEG_0, BPAADD_0, CRY_0 FROM FACILITY WHERE FCY_0 = ?", (site.strip(),)).fetchone()
        else:
            fac = conn.execute("SELECT FCY_0, FCYNAM_0, FCYSHO_0, LEGCPY_0, LEG_0, BPAADD_0, CRY_0 FROM FACILITY LIMIT 1").fetchone()
        if not fac:
            return None
        code, name, short, company, legislation, address_code, country = [_t(x) for x in fac]

        info = SiteInfo(code=code, name=name or code, short_name=short, company_code=company,
                        legislation=legislation, country=country)

        if company:
            cpy = conn.execute("SELECT CPYNAM_0, LEG_0, ACCCUR_0, EECNUM_0, CRN_0, BPAADD_0 FROM COMPANY WHERE CPY_0 = ?", (company,)).fetchone()
            if cpy:
                info.company_name = _t(cpy[0])
                info.legislation = _t(cpy[1]) or info.legislation
                info.currency = _t(cpy[2])
                info.vat_number = _t(cpy[3])
                info.company_registration = _t(cpy[4])

        addr = _address(conn, code, address_code) or (_address(conn, company, None) if company else None)
        if addr:
            info.address_lines = [line for line in (_t(addr[0]), _t(addr[1]), _t(addr[2])) if line]
            info.postal_code = _t(addr[3])
            info.city = _t(addr[4])
            info.state = _t(addr[5])
            info.country = _t(addr[6]) or info.country
            info.country_name = _t(addr[7])
            info.phone = _t(addr[8])
            info.mobile = _t(addr[9])
            web0, web1 = _t(addr[10]), _t(addr[11])
            for w in (web0, web1):
                if w and "@" in w and not info.email:
                    info.email = w
                elif w and not info.website:
                    info.website = w
        return info
    finally:
        conn.close()


def list_sites(db: Session) -> List[SiteInfo]:
    db_path = get_db_file(db)
    if not db_path:
        return []
    conn = sqlite3.connect(db_path)
    try:
        codes = [r[0] for r in conn.execute("SELECT FCY_0 FROM FACILITY ORDER BY FCY_0").fetchall()]
    finally:
        conn.close()
    return [s for s in (get_site_info(db, c) for c in codes) if s]

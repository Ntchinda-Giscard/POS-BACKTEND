import logging
import sqlite3
from typing import List, Optional
from sqlalchemy import func
from sqlalchemy.orm import Session
from database.models import Payment
from database.sync_data import get_db_file
from ..clients.model import ClientDetail, ClientFactureResponse, ClientOrder, ClientResponse, TierResponse

logger = logging.getLogger(__name__)


def _num(value) -> float:
    try:
        return float(str(value).strip()) if value not in (None, "") else 0.0
    except ValueError:
        return 0.0


def _t(value) -> Optional[str]:
    value = value.strip() if isinstance(value, str) else value
    return value or None


def get_clients(db) -> List[ClientResponse]:
    """Fetch clients from the database."""
    db_path = get_db_file(db)
    sqlite_conn = sqlite3.connect(db_path) # type: ignore
    result = []
    cursor = sqlite_conn.cursor()
    cursor.execute("""
            SELECT
                BPCNUM_0,
                BPCNAM_0,
                CUR_0,
                IME_0
            FROM
                BPCUSTOMER
            ORDER BY
            BPCNUM_0 ASC""")

    for row in cursor.fetchall():
        client = ClientResponse(
            code=row[0],
            name=row[1],
            cur=row[2],
            mode_fac=str(row[3])
        )
        result.append(client)
    sqlite_conn.close()
    return result


def get_tiers(customer_code: str, db: Session) -> TierResponse:
    """" Get tiers """
    db_path = get_db_file(db)
    sqlite_conn = sqlite3.connect(db_path) # type: ignore

    cursor = sqlite_conn.cursor()
    cursor.execute(("""SELECT "BPCPYR_0", "BPCNAM_0" FROM BPARTNER
    JOIN BPCUSTOMER
    ON BPCUSTOMER.BPCNUM_0 = BPARTNER.BPRNUM_0
    WHERE BPCUSTOMER.BPCNUM_0  = ? """), (customer_code,))

    row = cursor.fetchone()
    sqlite_conn.close()
    if not row:
        return TierResponse(code=customer_code, name="")
    return TierResponse(code=row[0], name=row[1])


def get_client_facture(code_client: str, db) -> ClientFactureResponse:
    """Invoice customer (BPCINV_0) of a customer."""
    db_path = get_db_file(db)
    sqlite_conn = sqlite3.connect(db_path) # type: ignore
    cursor = sqlite_conn.cursor()
    cursor.execute("SELECT BPCINV_0 FROM BPCUSTOMER WHERE BPCNUM_0 = ? ", (code_client,))
    row = cursor.fetchone()
    sqlite_conn.close()
    return ClientFactureResponse(code=row[0] if row else code_client)


def get_client_detail(code_client: str, db: Session) -> Optional[ClientDetail]:
    db_path = get_db_file(db)
    if not db_path:
        return None
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            """
            SELECT C.BPCNUM_0, C.BPCNAM_0, C.BPCSHO_0, C.BCGCOD_0, C.CUR_0, C.PTE_0, C.VACBPR_0, C.PRITYP_0,
                   C.OSTAUZ_0, C.OSTCTL_0, C.BPCINV_0, C.BPCPYR_0, C.BPCSTA_0, C.CNTNAM_0, C.BPAADD_0,
                   (SELECT LANDESSHO_0 FROM TABPAYTERM T WHERE T.PTE_0 = C.PTE_0 AND T.LANDESSHO_0 LIKE 'FRA~%' LIMIT 1),
                   (SELECT LANDESSHO_0 FROM TABPAYTERM T WHERE T.PTE_0 = C.PTE_0 LIMIT 1)
            FROM BPCUSTOMER C WHERE C.BPCNUM_0 = ?
            """,
            (code_client,),
        ).fetchone()
        if not row:
            return None
        term_label = _t(row[15]) or _t(row[16])
        if term_label and "~" in term_label:
            parts = term_label.split("~")
            term_label = parts[1] if len(parts) > 1 else parts[0]
        detail = ClientDetail(
            code=row[0].strip(), name=(row[1] or "").strip(), short_name=_t(row[2]), category=_t(row[3]),
            currency=_t(row[4]), payment_term=_t(row[5]), payment_term_label=term_label,
            tax_rule=_t(row[6]), price_type=_t(row[7]), credit_limit=_num(row[8]), credit_control=_t(row[9]),
            invoice_customer=_t(row[10]), payer=_t(row[11]), is_active=str(row[12]).strip() != "1",
            contact=_t(row[13]),
        )
        addr = conn.execute(
            "SELECT BPAADDLIG_0, BPAADDLIG_1, BPAADDLIG_2, POSCOD_0, CTY_0, CRY_0, TEL_0, MOB_0, WEB_0 FROM BPADDRESS WHERE BPANUM_0 = ? ORDER BY CASE WHEN BPAADD_0 = ? THEN 0 ELSE 1 END LIMIT 1",
            (code_client, _t(row[14]) or ""),
        ).fetchone()
        if addr:
            detail.address_lines = [l for l in (_t(addr[0]), _t(addr[1]), _t(addr[2])) if l]
            detail.postal_code = _t(addr[3])
            detail.city = _t(addr[4])
            detail.country = _t(addr[5])
            detail.phone = _t(addr[6])
            detail.mobile = _t(addr[7])
            web = _t(addr[8])
            if web and "@" in web:
                detail.email = web
        stats = conn.execute(
            "SELECT COUNT(*), COALESCE(SUM(CAST(ORDATI_0 AS REAL)), 0), MAX(ORDDAT_0) FROM SORDER WHERE BPCORD_0 = ?",
            (code_client,),
        ).fetchone()
        detail.orders_count = int(stats[0] or 0)
        detail.orders_total_ttc = _num(stats[1])
        detail.last_order_date = (stats[2] or "")[:10] or None
    finally:
        conn.close()

    pay = db.query(func.count(Payment.id), func.coalesce(func.sum(Payment.amount), 0.0), func.max(Payment.created_at)) \
        .filter(Payment.customer_code == code_client, Payment.status == "success").first()
    detail.payments_count = int(pay[0] or 0)
    detail.payments_total = float(pay[1] or 0.0)
    detail.last_payment_at = pay[2].isoformat() if pay[2] else None
    return detail


def get_client_orders(code_client: str, db: Session, limit: int = 100) -> List[ClientOrder]:
    db_path = get_db_file(db)
    if not db_path:
        return []
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            """
            SELECT S.SOHNUM_0, S.SOHTYP_0, S.ORDDAT_0, S.SALFCY_0, S.CUR_0, S.ORDNOT_0, S.ORDATI_0, S.ORDSTA_0, S.CREUSR_0,
                   (SELECT COUNT(*) FROM SORDERP P WHERE P.SOHNUM_0 = S.SOHNUM_0), S.ZTRANSFERT_0
            FROM SORDER S WHERE S.BPCORD_0 = ?
            ORDER BY COALESCE(S.CREDATTIM_0, S.ORDDAT_0) DESC, S.ROWID DESC LIMIT ?
            """,
            (code_client, limit),
        ).fetchall()
    finally:
        conn.close()

    order_ids = [r[0] for r in rows]
    paid = {}
    if order_ids:
        for order_id, total, methods in (
            db.query(Payment.order_id, func.sum(Payment.amount), func.group_concat(Payment.method.distinct()))
            .filter(Payment.order_id.in_(order_ids), Payment.status == "success").group_by(Payment.order_id).all()
        ):
            paid[order_id] = (float(total or 0), sorted(set((methods or "").split(","))) if methods else [])

    return [
        ClientOrder(
            order_id=r[0], order_type=_t(r[1]), date=(r[2] or "")[:10] or None, site=_t(r[3]), currency=_t(r[4]),
            total_ht=_num(r[5]), total_ttc=_num(r[6]), status=_t(r[7]), created_by=_t(r[8]), lines=int(r[9] or 0),
            paid=paid.get(r[0], (0.0, []))[0], payment_methods=paid.get(r[0], (0.0, []))[1],
            source="x3" if _t(r[10]) else "pos",
        )
        for r in rows
    ]

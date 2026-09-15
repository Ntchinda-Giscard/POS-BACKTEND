import sqlite3
import uuid
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from database.models import CashSession, Payment
from database.sync_data import get_db_file
from .model import PaymentDetail, PaymentLine, PaymentRequest, PaymentResponse


def _num(value: Any) -> float:
    try:
        return float(str(value).strip()) if value not in (None, "") else 0.0
    except ValueError:
        return 0.0


def _customer_names(db: Session, codes: List[str]) -> Dict[str, str]:
    codes = [c for c in set(codes) if c]
    db_path = get_db_file(db)
    if not codes or not db_path:
        return {}
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            f"SELECT BPCNUM_0, BPCNAM_0 FROM BPCUSTOMER WHERE BPCNUM_0 IN ({','.join('?' * len(codes))})", codes
        ).fetchall()
    finally:
        conn.close()
    return {r[0]: (r[1] or "").strip() for r in rows}


def to_response(payment: Payment, customer_name: Optional[str] = None) -> PaymentResponse:
    return PaymentResponse(
        transactionId=payment.transaction_id,
        orderId=payment.order_id,
        method=payment.method,
        amount=payment.amount,
        amountTendered=payment.amount_tendered,
        change=payment.change,
        reference=payment.reference,
        provider=payment.provider,
        phone=payment.phone,
        currency=payment.currency,
        customerCode=payment.customer_code,
        customerName=customer_name,
        userCode=payment.user_code,
        cashSessionId=payment.cash_session_id,
        site=payment.site,
        status=payment.status,
        createdAt=payment.created_at,
    )


def open_session_for(db: Session, site: Optional[str]) -> CashSession:
    q = db.query(CashSession).filter(CashSession.status == "open")
    if site:
        q = q.filter(CashSession.site == site)
    session = q.order_by(CashSession.opened_at.desc()).first()
    if not session:
        raise LookupError("Aucune caisse ouverte : ouvrez la caisse avant d'enregistrer un paiement")
    return session


def record_payment(request: PaymentRequest, details: Dict[str, Any], db: Session) -> PaymentResponse:
    """Persist a validated payment. `details` are the method-specific fields returned by the PaymentService."""
    session = open_session_for(db, request.site)
    payment = Payment(
        transaction_id=f"TXN{uuid.uuid4().hex[:12].upper()}",
        order_id=request.orderId,
        method=request.method,
        amount=request.amount,
        amount_tendered=details.get("amountTendered"),
        change=details.get("change"),
        reference=details.get("reference"),
        provider=details.get("provider"),
        phone=details.get("phone"),
        currency=request.currency or session.currency,
        customer_code=request.customerCode,
        user_code=request.userCode or session.user_code,
        cash_session_id=session.id,
        site=request.site or session.site,
        status="success",
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    names = _customer_names(db, [payment.customer_code])
    return to_response(payment, names.get(payment.customer_code))


def list_payments(
    db: Session,
    order_id: Optional[str] = None,
    day: Optional[date] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    method: Optional[str] = None,
    user_code: Optional[str] = None,
    session_id: Optional[int] = None,
    search: Optional[str] = None,
    limit: int = 200,
) -> List[PaymentResponse]:
    query = db.query(Payment)
    if order_id:
        query = query.filter(Payment.order_id == order_id)
    if day:
        start = datetime.combine(day, datetime.min.time())
        query = query.filter(Payment.created_at >= start, Payment.created_at < start + timedelta(days=1))
    if date_from:
        query = query.filter(Payment.created_at >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        query = query.filter(Payment.created_at < datetime.combine(date_to, datetime.min.time()) + timedelta(days=1))
    if method:
        query = query.filter(Payment.method == method)
    if user_code:
        query = query.filter(Payment.user_code == user_code)
    if session_id:
        query = query.filter(Payment.cash_session_id == session_id)
    if search:
        like = f"%{search.strip()}%"
        query = query.filter(
            (Payment.transaction_id.ilike(like)) | (Payment.order_id.ilike(like))
            | (Payment.reference.ilike(like)) | (Payment.customer_code.ilike(like)) | (Payment.phone.ilike(like))
        )
    rows = query.order_by(Payment.created_at.desc()).limit(limit).all()
    names = _customer_names(db, [p.customer_code for p in rows])
    return [to_response(p, names.get(p.customer_code)) for p in rows]


def get_payment_detail(db: Session, transaction_id: str) -> Optional[PaymentDetail]:
    payment = db.query(Payment).filter(Payment.transaction_id == transaction_id).first()
    if not payment:
        return None
    names = _customer_names(db, [payment.customer_code])
    base = to_response(payment, names.get(payment.customer_code))
    detail = PaymentDetail(**base.model_dump())

    db_path = get_db_file(db)
    if not db_path:
        return detail
    conn = sqlite3.connect(db_path)
    try:
        header = conn.execute(
            "SELECT ORDNOT_0, ORDATI_0, ORDDAT_0 FROM SORDER WHERE SOHNUM_0 = ?", (payment.order_id,)
        ).fetchone()
        if header:
            detail.total_ht = _num(header[0])
            detail.total_ttc = _num(header[1])
            detail.order_date = (header[2] or "")[:10] or None
        rows = conn.execute(
            """
            SELECT P.SOPLIN_0, P.ITMREF_0, COALESCE(NULLIF(TRIM(P.ITMDES_0), ''), M.ITMDES1_0),
                   Q.QTY_0, COALESCE(NULLIF(TRIM(P.SAU_0), ''), M.SAU_0),
                   P.GROPRI_0, P.NETPRINOT_0, P.NETPRIATI_0, P.VAT_0, P.FOCFLG_0
            FROM SORDERP P
            LEFT JOIN SORDERQ Q ON Q.SOHNUM_0 = P.SOHNUM_0 AND Q.ITMREF_0 = P.ITMREF_0
                 AND (Q.SOPLIN_0 = P.SOPLIN_0 OR P.SOPLIN_0 IS NULL)
            LEFT JOIN ITMMASTER M ON M.ITMREF_0 = P.ITMREF_0
            WHERE P.SOHNUM_0 = ?
            ORDER BY P.ROWID
            """,
            (payment.order_id,),
        ).fetchall()
    finally:
        conn.close()

    detail.lines = [
        PaymentLine(
            line=int(_num(r[0])) or i + 1,
            item_code=(r[1] or "").strip(),
            description=(r[2] or "").strip(),
            quantity=_num(r[3]),
            unit=(r[4] or "").strip() or None,
            gross_price=_num(r[5]),
            net_price_ht=_num(r[6]),
            net_price_ttc=_num(r[7]),
            tax_code=(r[8] or "").strip() or None,
            free=str(r[9]).strip() == "1",
        )
        for i, r in enumerate(rows)
    ]
    return detail

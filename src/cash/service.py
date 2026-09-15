from datetime import datetime
from typing import Any, Dict, Optional
from sqlalchemy import func
from sqlalchemy.orm import Session
from database.models import CashMovement, CashSession, Payment
from .model import CloseSessionRequest, MovementRequest, MovementResponse, OpenSessionRequest, SessionResponse


def _totals(db: Session, session: CashSession) -> Dict[str, Any]:
    """Live figures for a session: cash sales, in/out movements, sales split by method."""
    by_method = dict(
        db.query(Payment.method, func.coalesce(func.sum(Payment.amount), 0.0))
        .filter(Payment.cash_session_id == session.id, Payment.status == "success")
        .group_by(Payment.method).all()
    )
    count = db.query(func.count(Payment.id)).filter(Payment.cash_session_id == session.id).scalar() or 0
    cash_in = db.query(func.coalesce(func.sum(CashMovement.amount), 0.0)).filter(
        CashMovement.session_id == session.id, CashMovement.type == "in").scalar() or 0.0
    cash_out = db.query(func.coalesce(func.sum(CashMovement.amount), 0.0)).filter(
        CashMovement.session_id == session.id, CashMovement.type == "out").scalar() or 0.0
    cash_sales = float(by_method.get("cash", 0.0))
    return {
        "cash_sales": cash_sales,
        "cash_in": float(cash_in),
        "cash_out": float(cash_out),
        # what should physically be in the drawer (change is already netted out of `amount`)
        "expected": round(float(session.opening_amount or 0.0) + cash_sales + float(cash_in) - float(cash_out), 2),
        "count": int(count),
        "by_method": {k: float(v) for k, v in by_method.items()},
    }


def to_response(db: Session, session: CashSession) -> SessionResponse:
    t = _totals(db, session)
    movements = db.query(CashMovement).filter(CashMovement.session_id == session.id).order_by(CashMovement.created_at).all()
    is_open = session.status == "open"
    return SessionResponse(
        id=session.id, site=session.site, user_code=session.user_code, closed_by=session.closed_by,
        opened_at=session.opened_at, closed_at=session.closed_at,
        opening_amount=session.opening_amount or 0.0,
        cash_sales=t["cash_sales"] if is_open else (session.cash_sales or 0.0),
        cash_in=t["cash_in"], cash_out=t["cash_out"],
        expected_amount=t["expected"] if is_open else (session.expected_amount or 0.0),
        closing_amount=session.closing_amount, difference=session.difference,
        currency=session.currency, status=session.status, notes=session.notes,
        payments_count=t["count"], sales_by_method=t["by_method"],
        movements=[MovementResponse(id=m.id, type=m.type, amount=m.amount, reason=m.reason,
                                    user_code=m.user_code, created_at=m.created_at) for m in movements],
    )


def current_session(db: Session, site: Optional[str] = None) -> Optional[CashSession]:
    q = db.query(CashSession).filter(CashSession.status == "open")
    if site:
        q = q.filter(CashSession.site == site)
    return q.order_by(CashSession.opened_at.desc()).first()


def open_session(db: Session, request: OpenSessionRequest) -> CashSession:
    if request.opening_amount < 0:
        raise ValueError("Le fond de caisse ne peut pas être négatif")
    if current_session(db, request.site):
        raise ValueError(f"Une caisse est déjà ouverte sur le site {request.site}")
    session = CashSession(
        site=request.site, user_code=request.user_code, opening_amount=request.opening_amount,
        currency=request.currency, notes=request.notes, status="open",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def add_movement(db: Session, session_id: int, request: MovementRequest) -> CashMovement:
    session = db.query(CashSession).filter(CashSession.id == session_id).first()
    if not session or session.status != "open":
        raise ValueError("Aucune caisse ouverte")
    if request.type not in ("in", "out"):
        raise ValueError("Type de mouvement invalide (in | out)")
    if request.amount <= 0:
        raise ValueError("Le montant doit être supérieur à zéro")
    movement = CashMovement(session_id=session.id, type=request.type, amount=request.amount,
                            reason=request.reason, user_code=request.user_code)
    db.add(movement)
    db.commit()
    db.refresh(movement)
    return movement


def close_session(db: Session, session_id: int, request: CloseSessionRequest) -> CashSession:
    session = db.query(CashSession).filter(CashSession.id == session_id).first()
    if not session or session.status != "open":
        raise ValueError("Aucune caisse ouverte")
    if request.closing_amount < 0:
        raise ValueError("Le montant compté ne peut pas être négatif")
    t = _totals(db, session)
    session.cash_sales = t["cash_sales"]
    session.cash_in = t["cash_in"]
    session.cash_out = t["cash_out"]
    session.expected_amount = t["expected"]
    session.closing_amount = request.closing_amount
    session.difference = round(request.closing_amount - float(t["expected"]), 2)
    session.closed_at = datetime.now()
    session.closed_by = request.user_code
    session.status = "closed"
    if request.notes:
        session.notes = (session.notes + "\n" if session.notes else "") + request.notes
    db.commit()
    db.refresh(session)
    return session

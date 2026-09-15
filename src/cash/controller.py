from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database.models import CashSession
from database.session import get_db
from .model import CloseSessionRequest, MovementRequest, OpenSessionRequest, SessionResponse
from .service import add_movement, close_session, current_session, open_session, to_response
from src.settings.service import get_setting
from src.export.service import run_export
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cash", tags=["Cash sessions"])


@router.get("/current", response_model=Optional[SessionResponse])
def read_current(site: Optional[str] = None, db: Session = Depends(get_db)):
    session = current_session(db, site)
    return to_response(db, session) if session else None


@router.post("/open", response_model=SessionResponse)
def open_cash(request: OpenSessionRequest, db: Session = Depends(get_db)):
    try:
        return to_response(db, open_session(db, request))
    except ValueError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e))


@router.post("/{session_id}/movement", response_model=SessionResponse)
def cash_movement(session_id: int, request: MovementRequest, db: Session = Depends(get_db)):
    try:
        add_movement(db, session_id, request)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    return to_response(db, db.query(CashSession).filter(CashSession.id == session_id).first())


@router.post("/{session_id}/close", response_model=SessionResponse)
def close_cash(session_id: int, request: CloseSessionRequest, db: Session = Depends(get_db)):
    try:
        session = close_session(db, session_id, request)
    except ValueError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e))
    if get_setting(db, "auto_export_after_close") == "1":
        try:
            result = run_export(db, session.site, send_email=True)
            logger.info(f"auto export after close: batch {result.batch}, {result.total_rows} rows, emailed={result.emailed}")
        except Exception as e:  # closing the till must not fail because of the export
            logger.error(f"auto export after close failed: {e}")
    return to_response(db, session)


@router.get("/sessions", response_model=List[SessionResponse])
def read_sessions(site: Optional[str] = None, limit: int = 50, db: Session = Depends(get_db)):
    q = db.query(CashSession)
    if site:
        q = q.filter(CashSession.site == site)
    return [to_response(db, s) for s in q.order_by(CashSession.opened_at.desc()).limit(limit).all()]


@router.get("/sessions/{session_id}", response_model=SessionResponse)
def read_session(session_id: int, db: Session = Depends(get_db)):
    session = db.query(CashSession).filter(CashSession.id == session_id).first()
    if not session:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session introuvable")
    return to_response(db, session)

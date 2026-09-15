from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database.session import get_db
from .model import ExportBatch, ExportResult, PendingExport
from .service import history, pending, run_export

router = APIRouter(prefix="/export", tags=["Export to X3"])


@router.get("/pending", response_model=PendingExport)
def read_pending(site: Optional[str] = None, db: Session = Depends(get_db)):
    """Rows created by the till that Sage X3 has not received yet."""
    return pending(db, site)


@router.post("/x3", response_model=ExportResult)
def export_to_x3(site: Optional[str] = None, send_email: bool = True, db: Session = Depends(get_db)):
    """Write the pending rows to CSV files (inbound layout) and email them to the X3 mailbox if configured."""
    return run_export(db, site, send_email=send_email)


@router.get("/history", response_model=List[ExportBatch])
def read_history(limit: int = 50, db: Session = Depends(get_db)):
    return history(db, limit)

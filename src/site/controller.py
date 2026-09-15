from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database.session import get_db
from .model import SiteInfo
from .service import get_site_info, list_sites

router = APIRouter(prefix="/site", tags=["Site"])


@router.get("/", response_model=List[SiteInfo])
def read_sites(db: Session = Depends(get_db)):
    return list_sites(db)


@router.get("/info", response_model=SiteInfo)
def read_site_info(site: Optional[str] = None, db: Session = Depends(get_db)):
    """Store identity for receipts: name, address, phone, company, VAT number (FACILITY / BPADDRESS / COMPANY)."""
    info = get_site_info(db, site)
    if not info:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Site introuvable")
    return info

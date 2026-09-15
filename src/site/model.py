from typing import List, Optional
from pydantic import BaseModel


class SiteInfo(BaseModel):
    code: str                      # FACILITY.FCY_0
    name: str                      # FCYNAM_0
    short_name: Optional[str] = None
    company_code: Optional[str] = None
    company_name: Optional[str] = None
    legislation: Optional[str] = None
    currency: Optional[str] = None       # COMPANY.ACCCUR_0
    address_lines: List[str] = []
    postal_code: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    country_name: Optional[str] = None
    phone: Optional[str] = None
    mobile: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    vat_number: Optional[str] = None     # COMPANY.EECNUM_0
    company_registration: Optional[str] = None   # COMPANY.CRN_0

from typing import Optional
from pydantic import BaseModel

class TaxeResponse(BaseModel):
    code: str


class AppliedTaxResponse(BaseModel):
    item_code: str
    code_taxe: str
    taux: float
    compte_comptable: Optional[str] = None
    exonere: Optional[bool] = None
    regle: Optional[str] = None
    legislation: Optional[str] = None
    description: Optional[str] = None
    warning: Optional[str] = None


class AppliedTaxInput(BaseModel):
    item_code: str
    regime_taxe_tiers: str
    site: Optional[str] = None            # sales site (FACILITY.FCY_0); legislation/state derive from it
    groupe_societe: Optional[str] = None
    type_taxe: Optional[str] = None
    date: Optional[str] = None            # ISO date for the rate lookup (default today)

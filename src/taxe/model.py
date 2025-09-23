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


class AppliedTaxInput(BaseModel):
    item_code: str
    regime_taxe_tiers: str
    # niveau_taxe_article: str
    groupe_societe: Optional[str] = None
    type_taxe: Optional[str] = None
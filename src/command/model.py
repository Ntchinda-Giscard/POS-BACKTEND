from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from datetime import date

class CommandTypeRRequest(BaseModel):
    code: str
    description: str


class LigneCommande(BaseModel):
    num_comd: str
    item_code: str
    quantity: int
    prix_brut: Optional[float] = None
    prix_net_ht: float
    prix_net_ttc: float
    free_items: List[Dict[str, Any]] = None # type: ignore


class CreateCommandRequest(BaseModel):
    num_comd: str
    site_vente: str
    currency: str
    client_comd: str
    client_payeur: str
    client_facture: str
    total_ht: float
    total_ttc: float
    valo_ht: float
    valo_ttc: float
    price_type: int
    regime_taxe: str
    comd_type: str
    date_comd: Optional[str] = date.today().isoformat()
    ligne: List[LigneCommande]

from typing import Any, Dict, List
from pydantic import BaseModel

class CommandTypeRRequest(BaseModel):
    code: str
    description: str


class LigneCommande(BaseModel):
    num_comd: str
    item_code: str
    prix_net_ht: str
    prix_net_ttc: str
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
    comd_type: str
    ligne: List[LigneCommande]

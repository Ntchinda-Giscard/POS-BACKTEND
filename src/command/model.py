from typing import Any, Dict, List, Optional
from pydantic import BaseModel

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
    description: Optional[str] = None   # ITMDES_0 (defaults to ITMMASTER.ITMDES1_0)
    unit: Optional[str] = None          # SAU_0
    tax_code: Optional[str] = None      # VAT_0 as determined by /taxe/applied


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
    ligne: List[LigneCommande]
    user_code: Optional[str] = None     # CREUSR_0 (cashier)
    site_stock: Optional[str] = None    # STOFCY_0 (defaults to site_vente)
    order_date: Optional[str] = None    # ORDDAT_0, ISO date (defaults to today)

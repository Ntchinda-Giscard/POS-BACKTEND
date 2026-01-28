from pydantic import BaseModel
from typing import Optional
from uuid import UUID

class ModeDeLivraisonRequest(BaseModel):
    code: str

class TransPorteurResponse(BaseModel):
    code: str
    description: str


class LivraisonHeader(BaseModel):
    id: UUID.uuid4()
    description: Optional[str]
    type: Optional[str]
    date_expedition: Optional[str]
    date_livraison: Optional[str]
    client_livre: Optional[str]
    commande_livre: str
    site_vente: Optional[str]
    statut: Optional[str]
    
    
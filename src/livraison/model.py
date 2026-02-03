from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID, uuid4

class ModeDeLivraisonRequest(BaseModel):
    code: str

class TransPorteurResponse(BaseModel):
    code: str
    description: str


class LivraisonHeader(BaseModel):
    id: UUID
    type: Optional[str]
    date_expedition: Optional[str]
    date_livraison: Optional[str]
    client_livre: Optional[str]
    commande_livre: str
    site_vente: Optional[str]
    statut: Optional[str]


livraison_quantite: List[CommandeQuantite]


class AddLivraisonRequest(BaseModel):
    livraison: LivraisonHeader
    livraison_quantite: List[CommandeQuantite]

class LivraisonType(BaseModel):
    code: str


class CommandeLivraison(BaseModel):
    code: str
    client_livre: str
    client_comm: str

class CommandeQuantite(BaseModel):
    code: str
    quantite: float
    quantite_total: float
    description: str
from pydantic import BaseModel

class ModeDeLivraisonRequest(BaseModel):
    code: str

class TransPorteurResponse(BaseModel):
    code: str
    description: str


class LivraisonHeader(BaseModel):
    code: str
    description: str
    type: str
    date_expedition: str
    date_livraison: str
    client_livre: str
    commande_livre: str
    
    
    
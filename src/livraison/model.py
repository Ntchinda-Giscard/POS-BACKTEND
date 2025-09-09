from pydantic import BaseModel

class ModeDeLivraisonRequest(BaseModel):
    code: str

class TransPorteurResponse(BaseModel):
    code: str
    description: str

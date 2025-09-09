from pydantic import BaseModel

class ModeDeLivraisonRequest(BaseModel):
    code: str

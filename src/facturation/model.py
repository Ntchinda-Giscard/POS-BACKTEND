from pydantic import BaseModel

class PayementMode(BaseModel):
    code: str

class Escomte(BaseModel):
    code: str


class CondFacResponse(BaseModel):
    code: str
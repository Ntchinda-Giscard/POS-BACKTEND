from pydantic import BaseModel

class ClientResponse(BaseModel):
    code: str
    name: str
    cur: str
    mode_fac: str

class ClientFactureResponse(BaseModel):
    code: str


class TierResponse(BaseModel):
    code: str
    name: str
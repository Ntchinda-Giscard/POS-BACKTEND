from pydantic import BaseModel

class ClientResponse(BaseModel):
    code: str
    name: str
    cur: str

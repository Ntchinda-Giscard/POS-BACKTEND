from pydantic import BaseModel

class ClientResponse(BaseModel):
    code: int
    name: str

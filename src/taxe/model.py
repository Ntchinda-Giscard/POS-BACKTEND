from pydantic import BaseModel

class TaxeResponse(BaseModel):
    code: str
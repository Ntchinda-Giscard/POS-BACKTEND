from pydantic import BaseModel

class CurrencyResponse(BaseModel):
    code: str

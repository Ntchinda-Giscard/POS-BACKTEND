from typing import Optional
from pydantic import BaseModel

class AddressRequest(BaseModel):
    code: str
    description: str

class AddressInput(BaseModel):
    site_id: str
from typing import Optional
from pydantic import BaseModel

class AddressRequest(BaseModel):
    code: str
    description: str
    leg_comp: str

class AddressInput(BaseModel):
    site_id: str

class AddressLivrasonREsponse(BaseModel):
    code: str
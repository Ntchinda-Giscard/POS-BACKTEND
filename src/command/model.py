from typing import Optional
from pydantic import BaseModel

class CommandTypeRRequest(BaseModel):
    code: str
    description: str
from pydantic import BaseModel

class PayementMode(BaseModel):
    code: str
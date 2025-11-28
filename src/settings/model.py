from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from datetime import datetime


class SettingsInput(BaseModel):
    pop_server: str
    username: str
    port: int
    password: str
    updated_at: datetime = datetime.now()
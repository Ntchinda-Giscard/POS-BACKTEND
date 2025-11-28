from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from datetime import datetime


class SettingsInput(BaseModel):
    popServer: str
    username: str
    port: int
    password: str
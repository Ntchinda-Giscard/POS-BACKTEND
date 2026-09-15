from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel


class PendingExport(BaseModel):
    site: Optional[str] = None
    counts: Dict[str, int] = {}       # table -> rows waiting
    total: int = 0


class ExportedFile(BaseModel):
    table: str
    path: str
    rows: int


class ExportResult(BaseModel):
    batch: str
    folder: str
    files: List[ExportedFile] = []
    total_rows: int = 0
    emailed: bool = False
    recipient: Optional[str] = None
    email_error: Optional[str] = None


class ExportBatch(BaseModel):
    batch: str
    exported_at: datetime
    tables: Dict[str, int] = {}
    files: List[str] = []
    emailed: bool = False

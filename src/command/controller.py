from typing import List
from src.command.service import get_command_types
from .model import CommandTypeRRequest
from fastapi import APIRouter

router = APIRouter(
    prefix="/command",
    tags=["command"]
)

@router.get("/type", response_model=List[CommandTypeRRequest])
def read_commande_types():
    return get_command_types()
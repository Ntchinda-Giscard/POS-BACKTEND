from typing import List
from src.command.service import create_commande, get_command_types
from .model import CommandTypeRRequest, CreateCommandRequest
from fastapi import APIRouter

router = APIRouter(
    prefix="/command",
    tags=["command"]
)

@router.get("/type", response_model=List[CommandTypeRRequest])
def read_commande_types():
    return get_command_types()


@router.post("/add")
def insert_commande(input: CreateCommandRequest):
    return create_commande(input)
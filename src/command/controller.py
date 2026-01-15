from typing import List
from src.command.service import create_commande, get_command_types
from .model import CommandTypeRRequest, CreateCommandRequest
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database.session import get_db

router = APIRouter(
    prefix="/command",
    tags=["command"]
)

@router.get("/type", response_model=List[CommandTypeRRequest])
def read_commande_types(db: Session = Depends(get_db)):
    return get_command_types(db)


@router.post("/add")
def insert_commande(input: CreateCommandRequest, db: Session = Depends(get_db)):
    return create_commande(input, db)
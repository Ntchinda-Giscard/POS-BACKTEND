from typing import List
from src.addresse.service import get_adresse_vente
from .model import AddressInput, AddressRequest
from fastapi import APIRouter

router = APIRouter(
    prefix="/adresse",
    tags=["adresse"]
)

@router.get("/vente", response_model=List[AddressRequest])
def read_adresse_vente():
    return get_adresse_vente()
from typing import List
from src.addresse.service import get_adresse_expedition, get_adresse_livraison, get_adresse_vente
from .model import AddressInput, AddressLivrasonREsponse, AddressRequest
from fastapi import APIRouter

router = APIRouter(
    prefix="/adresse",
    tags=["adresse"]
)

@router.get("/vente", response_model=List[AddressRequest])
def read_adresse_vente():
    return get_adresse_vente()

@router.get("/livraison", response_model=List[AddressLivrasonREsponse])
def read_adresse_livraison(code_client: str):
    return get_adresse_livraison(code_client)

@router.get("/expedition", response_model=List[AddressRequest])
def read_adresse_expedition(legacy_comp: str):
    return get_adresse_expedition(legacy_comp)
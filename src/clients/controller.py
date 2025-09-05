from typing import List
from src.clients.serivce import get_clients, get_tiers
from .model import ClientResponse, TierResponse
from fastapi import APIRouter

router = APIRouter(
    prefix="/clients",
    tags=["clients"]
)

@router.get("/", response_model=List[ClientResponse])
def read_clients():
    return get_clients()

@router.get("/tiers/", response_model=TierResponse)
def read_tiers(customer_code: str):
    return get_tiers(customer_code)
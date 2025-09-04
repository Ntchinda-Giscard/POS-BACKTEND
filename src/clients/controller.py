from typing import List
from src.clients.serivce import get_clients
from .model import ClientResponse
from fastapi import APIRouter

router = APIRouter(
    prefix="/clients",
    tags=["clients"]
)

@router.get("/", response_model=List[ClientResponse])
def read_clients():
    return get_clients()
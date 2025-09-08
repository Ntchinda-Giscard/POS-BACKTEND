from typing import List
from src.taxe.service import get_regime_taxe 
from .model import TaxeResponse
from fastapi import APIRouter

router = APIRouter(
    prefix="/taxe",
    tags=["taxe"]
)

@router.get("/regime", response_model=TaxeResponse)
def read_regime_taxe(customer_code: str):

    return get_regime_taxe(customer_code)
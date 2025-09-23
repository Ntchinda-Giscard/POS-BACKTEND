from typing import List
from src.taxe.service import get_applied_tax, get_regime_taxe 
from .model import AppliedTaxInput, AppliedTaxResponse, TaxeResponse
from fastapi import APIRouter

router = APIRouter(
    prefix="/taxe",
    tags=["taxe"]
)

@router.get("/regime", response_model=TaxeResponse)
def read_regime_taxe(customer_code: str):

    return get_regime_taxe(customer_code)


@router.post("/applied", response_model=List[AppliedTaxResponse])
def get_taxe_code(criterias: List[AppliedTaxInput]):

    return get_applied_tax(criterias)
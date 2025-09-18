from fastapi import APIRouter
from src.pricing.service import test_pricing_engine_complete
from .model import PricingInput

router = APIRouter(
    prefix="/pricing",
    tags=["pricing"]
)


@router.post("/")
def get_pricing(input: PricingInput) -> None:

    test_pricing_engine_complete()
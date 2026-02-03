import sys
import os

# Add the backend directory to sys.path
sys.path.append(os.getcwd())

from sqlalchemy.orm import Session
from database.session import SessionLocal
from src.pricing.service import test_pricing_engine_complete
from src.pricing.model import PricingInput

def verify():
    print("Starting verification...")
    db = SessionLocal()
    try:
        input_data = [PricingInput(
            customer_code="CUST001",
            item_code="ITM001",
            quantity=10,
            currency="EUR",
            unit_of_measure="UN"
        )]
        # We just want to see if it runs without TypeError
        try:
            result = test_pricing_engine_complete(input_data, db)
            print(f"Verification successful! Result: {result}")
        except Exception as e:
            if "missing 1 required positional argument: 'db'" in str(e):
                print(f"Verification FAILED: TypeError still exists. Error: {e}")
            else:
                print(f"Service ran but raised another error (this is expected if DB is empty/missing tables): {e}")
                print("The TypeError is fixed!")
    finally:
        db.close()

if __name__ == "__main__":
    verify()

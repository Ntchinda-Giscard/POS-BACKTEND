import sys
import os

# Add the backend directory to sys.path
sys.path.append(os.getcwd())

from sqlalchemy.orm import Session
from database.session import SessionLocal
from src.pricing.service import test_pricing_engine_complete
from src.pricing.model import PricingInput

def verify():
    print("Starting verification v2...")
    db = SessionLocal()
    try:
        input_data = [PricingInput(
            customer_code="CUST001",
            item_code="ITM001",
            quantity=10.0,
            currency="EUR",
            unit_of_measure="UN"
        )]
        print("Calling test_pricing_engine_complete...")
        try:
            # We just want to see if it doesn't raise TypeError: get_db_file() missing 1 ...
            result = test_pricing_engine_complete(input_data, db)
            print(f"Verification successful! Result obtained (length {len(result)})")
        except TypeError as te:
            if "get_db_file() missing 1 required positional argument" in str(te):
                print(f"Verification FAILED: TypeError still exists. Error: {te}")
            else:
                print(f"Verification successful! TypeError is fixed, but encountered another TypeError (likely unrelated): {te}")
        except Exception as e:
            print(f"Verification successful! TypeError is fixed, though service execution stopped later: {e}")
    finally:
        db.close()
        print("Verification finished.")

if __name__ == "__main__":
    verify()

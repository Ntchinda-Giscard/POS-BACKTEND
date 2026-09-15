from abc import ABC, abstractmethod
from typing import Any, Dict
from .model import PaymentRequest


class PaymentService(ABC):
    """Validates a payment of one method and returns the method-specific fields to persist."""

    @abstractmethod
    def pay(self, request: PaymentRequest) -> Dict[str, Any]:
        raise NotImplementedError("Subclasses must implement the pay method")

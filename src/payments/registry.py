from typing import Callable
from typing import Dict
from .base import PaymentService

class PayementRgistry:
    _items: Dict[str, type[PaymentService]] = {}
    
    @classmethod
    def register(cls, name: str) -> Callable:
        def decorator(item) -> type[PaymentService]:
            if name in cls._items:
                raise ValueError(f" '{name}' already exist ")
            cls._items[name] = item
            return item
        return decorator
    
    @classmethod
    def get(cls, name: str) -> type[PaymentService]:
        if name not in cls._items:
            raise ValueError(f"'{name}' not found in registry ")
        
        return cls._items.get(name)


payment_registry = PayementRgistry()
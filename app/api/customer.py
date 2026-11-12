import string
import secrets
import time
from typing import Annotated

from pydantic import BaseModel, Field

# This binds your regex, min/max lengths, and str type into a single definition.
CustomerTokenStr = Annotated[
    str,
    Field(
        min_length=15,
        max_length=30,
        pattern=r"^C_[A-Za-z0-9]{13,28}$"
    )
]

class Customer(BaseModel):
    customer_token: CustomerTokenStr
    created_at: float

def generate_exact_customer_token(length: int = 15) -> str:
    assert 13 <= length <= 28
    pool = string.ascii_letters + string.digits
    random_part = "".join(secrets.choice(pool) for _ in range(length))
    return f"C_{random_part}"

def generate_random_customer() -> Customer:
    return Customer(
        customer_token= generate_exact_customer_token(),
        created_at= time.time()
    )
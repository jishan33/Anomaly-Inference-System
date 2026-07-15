import string
import secrets
import time

from pydantic import BaseModel, Field

class Customer(BaseModel):
    customer_token:str = Field(
        min_length=15,
        max_length=60,
        pattern=r"^C_[A-Za-z0-9]{10,40}$"
    ),
    created_at: float

def generate_exact_customer_token(length: int = 32) -> str:
    # Ensure length respects the 10 to 40 alphanumeric range requirement
    assert 10 <= length <= 40, "Alphanumeric component must be between 10 and 40 characters"

    # Pool of characters allowed by your regex: A-Z, a-z, 0-9
    pool = string.ascii_letters + string.digits

    # Securely pick 'length' characters from the pool
    random_part = "".join(secrets.choice(pool) for _ in range(length))

    return f"C_{random_part}"

def generate_random_customer() -> Customer:
    return Customer(
        customer_token= generate_exact_customer_token(),
        created_at= time.time()
    )
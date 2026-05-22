from pydantic import BaseModel, Field


class CustomerRequest(BaseModel):
    customer_token:str = Field(
        min_length=15,
        max_length=60,
        pattern=r"^C_[A-Za-z0-9]{10,40}$"
    )

"""
schemas.py  —  request/response schemas for a small e-commerce order API.

Written against Pydantic v1. Needs to be migrated to Pydantic v2.
"""

from __future__ import annotations

import json
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, root_validator, validator
from pydantic import conint, constr


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class OrderStatus(str, Enum):
    pending   = "pending"
    confirmed = "confirmed"
    shipped   = "shipped"
    delivered = "delivered"
    cancelled = "cancelled"


class PaymentMethod(str, Enum):
    card   = "card"
    upi    = "upi"
    wallet = "wallet"
    cod    = "cod"


# ---------------------------------------------------------------------------
# Address
# ---------------------------------------------------------------------------

class Address(BaseModel):
    line1   : constr(min_length=1, max_length=200)
    line2   : Optional[str]
    city    : constr(min_length=1, max_length=100)
    state   : constr(min_length=2, max_length=100)
    pincode : constr(regex=r"^\d{6}$")
    country : str = "India"

    class Config:
        orm_mode = True


# ---------------------------------------------------------------------------
# Product
# ---------------------------------------------------------------------------

class ProductBase(BaseModel):
    name     : constr(min_length=1, max_length=200)
    sku      : constr(min_length=3, max_length=50)
    price    : float
    category : Optional[str]

    @validator("price")
    def price_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError("price must be greater than zero")
        return round(v, 2)

    @validator("sku")
    def sku_must_be_uppercase(cls, v):
        return v.upper()


class ProductResponse(ProductBase):
    id         : int
    created_at : datetime

    class Config:
        orm_mode = True


# ---------------------------------------------------------------------------
# Order item
# ---------------------------------------------------------------------------

class OrderItem(BaseModel):
    product_id : int
    quantity   : conint(ge=1, le=100)
    unit_price : float

    @validator("unit_price")
    def unit_price_must_be_positive(cls, v):
        return round(v, 2)

    @property
    def subtotal(self) -> float:
        return round(self.quantity * self.unit_price, 2)


# ---------------------------------------------------------------------------
# Order
# ---------------------------------------------------------------------------

class OrderCreate(BaseModel):
    customer_id     : int
    items           : List[OrderItem]
    shipping_address: Address
    payment_method  : PaymentMethod
    notes           : Optional[str]

    @validator("items")
    def items_must_not_be_empty(cls, v):
        if not v:
            raise ValueError("order must contain at least one item")
        return v

    @root_validator(pre=False)
    def cod_limit_check(cls, values):
        method = values.get("payment_method")
        items  = values.get("items", [])
        total  = sum(i.quantity * i.unit_price for i in items)
        if method == PaymentMethod.cod and total > 5000:
            raise ValueError("Cash on delivery is not available for orders above ₹5000")
        return values


class OrderResponse(BaseModel):
    id               : int
    customer_id      : int
    items            : List[OrderItem]
    shipping_address : Address
    payment_method   : PaymentMethod
    status           : OrderStatus = OrderStatus.pending
    notes            : Optional[str]
    total_amount     : float
    created_at       : datetime
    updated_at       : Optional[datetime]

    class Config:
        orm_mode = True


# ---------------------------------------------------------------------------
# Customer
# ---------------------------------------------------------------------------

class CustomerCreate(BaseModel):
    name    : constr(min_length=1, max_length=100)
    email   : str
    phone   : Optional[constr(regex=r"^\+?[\d\s\-]{7,15}$")]
    address : Optional[Address]

    @validator("email")
    def email_must_be_valid(cls, v):
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("invalid email address")
        return v.lower().strip()

    @root_validator(pre=True)
    def strip_whitespace_from_name(cls, values):
        if "name" in values and isinstance(values["name"], str):
            values["name"] = values["name"].strip()
        return values


class CustomerResponse(BaseModel):
    id         : int
    name       : str
    email      : str
    phone      : Optional[str]
    address    : Optional[Address]
    created_at : datetime

    class Config:
        orm_mode = True


# ---------------------------------------------------------------------------
# Pagination / list wrappers
# ---------------------------------------------------------------------------

class PaginatedOrders(BaseModel):
    items      : List[OrderResponse]
    total      : int
    page       : conint(ge=1)
    page_size  : conint(ge=1, le=100)
    total_pages: int

    @root_validator(pre=False)
    def compute_total_pages(cls, values):
        total     = values.get("total", 0)
        page_size = values.get("page_size", 1)
        if page_size:
            values["total_pages"] = max(1, -(-total // page_size))
        return values


# ---------------------------------------------------------------------------
# Utility helpers used by the API layer — these MUST keep working after migration
# ---------------------------------------------------------------------------

def serialise_order(order: OrderResponse) -> str:
    """Return the order as a compact JSON string."""
    return order.json(exclude_none=True)


def deserialise_order(payload: str) -> OrderResponse:
    """Parse a JSON string back into an OrderResponse."""
    return OrderResponse.parse_raw(payload)


def order_from_orm(orm_obj) -> OrderResponse:
    """Build an OrderResponse from an ORM model instance."""
    return OrderResponse.from_orm(orm_obj)


def get_schema() -> dict:
    """Return the JSON schema for OrderResponse."""
    return OrderResponse.schema()


def get_field_names(model_cls) -> List[str]:
    """Return a list of field names for a given model class."""
    return list(model_cls.__fields__.keys())


def export_order(order: OrderResponse, exclude_none: bool = True) -> dict:
    """Export order to a plain dict, optionally dropping None values."""
    return order.dict(exclude_none=exclude_none)

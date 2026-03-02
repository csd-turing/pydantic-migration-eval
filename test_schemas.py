"""
test_schemas.py — test suite for the Pydantic v2 migrated schemas.

Every test here is written for Pydantic v2. Running against the unmigrated
v1 code will produce AttributeError, ValidationError, or TypeError failures.
"""

import json
from datetime import datetime
from types import SimpleNamespace

import pytest
from pydantic import ValidationError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_address(**overrides):
    data = {
        "line1"  : "12 MG Road",
        "city"   : "Bangalore",
        "state"  : "Karnataka",
        "pincode": "560001",
    }
    data.update(overrides)
    return data


def make_item(**overrides):
    data = {"product_id": 1, "quantity": 2, "unit_price": 250.0}
    data.update(overrides)
    return data


def make_order_create(**overrides):
    data = {
        "customer_id"     : 1,
        "items"           : [make_item()],
        "shipping_address": make_address(),
        "payment_method"  : "card",
    }
    data.update(overrides)
    return data


def make_order_response(**overrides):
    data = {
        "id"              : 1,
        "customer_id"     : 1,
        "items"           : [make_item()],
        "shipping_address": make_address(),
        "payment_method"  : "card",
        "status"          : "pending",
        "total_amount"    : 500.0,
        "created_at"      : datetime(2024, 1, 15, 10, 0, 0),
    }
    data.update(overrides)
    return data


# ---------------------------------------------------------------------------
# TestAddressModel
# ---------------------------------------------------------------------------

class TestAddressModel:

    def test_valid_address_creates_successfully(self):
        from schemas import Address
        addr = Address(**make_address())
        assert addr.city == "Bangalore"
        assert addr.country == "India"

    def test_pincode_must_be_six_digits(self):
        from schemas import Address
        with pytest.raises(ValidationError):
            Address(**make_address(pincode="12345"))

    def test_pincode_rejects_letters(self):
        from schemas import Address
        with pytest.raises(ValidationError):
            Address(**make_address(pincode="ABCDEF"))

    def test_line2_is_truly_optional(self):
        """line2 typed Optional must default to None without being passed."""
        from schemas import Address
        addr = Address(**make_address())
        assert addr.line2 is None

    def test_address_model_dump_returns_dict(self):
        """model_dump() must work — not .dict()."""
        from schemas import Address
        addr = Address(**make_address())
        result = addr.model_dump()
        assert isinstance(result, dict)
        assert result["city"] == "Bangalore"

    def test_address_model_dump_exclude_none(self):
        """model_dump(exclude_none=True) must drop None fields."""
        from schemas import Address
        addr = Address(**make_address())
        result = addr.model_dump(exclude_none=True)
        assert "line2" not in result


# ---------------------------------------------------------------------------
# TestProductSchemas
# ---------------------------------------------------------------------------

class TestProductSchemas:

    def test_price_validator_rounds_to_two_decimal_places(self):
        from schemas import ProductBase
        p = ProductBase(name="Widget", sku="WDG-01", price=9.999)
        assert p.price == 10.0

    def test_price_must_be_positive(self):
        from schemas import ProductBase
        with pytest.raises(ValidationError):
            ProductBase(name="Widget", sku="WDG-01", price=0)

    def test_sku_converted_to_uppercase(self):
        from schemas import ProductBase
        p = ProductBase(name="Widget", sku="wdg-01", price=10.0)
        assert p.sku == "WDG-01"

    def test_field_validator_is_classmethod(self):
        """In v2, @field_validator must be a classmethod — verify it doesn't break instantiation."""
        from schemas import ProductBase
        p = ProductBase(name="Gadget", sku="GDG-99", price=199.0)
        assert p.price == 199.0

    def test_category_is_optional_with_none_default(self):
        from schemas import ProductBase
        p = ProductBase(name="Widget", sku="WDG-01", price=10.0)
        assert p.category is None


# ---------------------------------------------------------------------------
# TestOrderItem
# ---------------------------------------------------------------------------

class TestOrderItem:

    def test_quantity_must_be_at_least_one(self):
        from schemas import OrderItem
        with pytest.raises(ValidationError):
            OrderItem(product_id=1, quantity=0, unit_price=100.0)

    def test_quantity_cannot_exceed_100(self):
        from schemas import OrderItem
        with pytest.raises(ValidationError):
            OrderItem(product_id=1, quantity=101, unit_price=100.0)

    def test_subtotal_property(self):
        from schemas import OrderItem
        item = OrderItem(product_id=1, quantity=3, unit_price=150.0)
        assert item.subtotal == 450.0


# ---------------------------------------------------------------------------
# TestOrderCreate
# ---------------------------------------------------------------------------

class TestOrderCreate:

    def test_valid_order_creates_successfully(self):
        from schemas import OrderCreate
        order = OrderCreate(**make_order_create())
        assert order.customer_id == 1

    def test_empty_items_raises_validation_error(self):
        from schemas import OrderCreate
        with pytest.raises(ValidationError):
            OrderCreate(**make_order_create(items=[]))

    def test_cod_above_5000_raises_validation_error(self):
        from schemas import OrderCreate
        expensive_items = [{"product_id": 1, "quantity": 1, "unit_price": 6000.0}]
        with pytest.raises(ValidationError):
            OrderCreate(**make_order_create(items=expensive_items, payment_method="cod"))

    def test_cod_at_5000_is_allowed(self):
        from schemas import OrderCreate
        items = [{"product_id": 1, "quantity": 1, "unit_price": 5000.0}]
        order = OrderCreate(**make_order_create(items=items, payment_method="cod"))
        assert order.payment_method.value == "cod"

    def test_notes_is_optional(self):
        from schemas import OrderCreate
        order = OrderCreate(**make_order_create())
        assert order.notes is None

    def test_model_validator_runs_after_field_validation(self):
        """Cross-field root validator must work correctly in v2."""
        from schemas import OrderCreate
        items = [{"product_id": 1, "quantity": 2, "unit_price": 3000.0}]
        with pytest.raises(ValidationError) as exc_info:
            OrderCreate(**make_order_create(items=items, payment_method="cod"))
        assert "5000" in str(exc_info.value)


# ---------------------------------------------------------------------------
# TestCustomerCreate
# ---------------------------------------------------------------------------

class TestCustomerCreate:

    def test_email_normalised_to_lowercase(self):
        from schemas import CustomerCreate
        c = CustomerCreate(name="Ravi", email="Ravi@EXAMPLE.COM")
        assert c.email == "ravi@example.com"

    def test_invalid_email_raises_error(self):
        from schemas import CustomerCreate
        with pytest.raises(ValidationError):
            CustomerCreate(name="Ravi", email="not-an-email")

    def test_name_whitespace_stripped(self):
        """pre root_validator strips whitespace from name."""
        from schemas import CustomerCreate
        c = CustomerCreate(name="  Priya  ", email="priya@example.com")
        assert c.name == "Priya"

    def test_phone_regex_validation(self):
        from schemas import CustomerCreate
        with pytest.raises(ValidationError):
            CustomerCreate(name="Ravi", email="ravi@x.com", phone="abc")

    def test_phone_is_optional(self):
        from schemas import CustomerCreate
        c = CustomerCreate(name="Ravi", email="ravi@example.com")
        assert c.phone is None


# ---------------------------------------------------------------------------
# TestPaginatedOrders
# ---------------------------------------------------------------------------

class TestPaginatedOrders:

    def test_total_pages_computed_correctly(self):
        from schemas import PaginatedOrders
        p = PaginatedOrders(items=[], total=25, page=1, page_size=10, total_pages=0)
        assert p.total_pages == 3

    def test_total_pages_rounds_up(self):
        from schemas import PaginatedOrders
        p = PaginatedOrders(items=[], total=11, page=1, page_size=10, total_pages=0)
        assert p.total_pages == 2

    def test_page_must_be_at_least_one(self):
        from schemas import PaginatedOrders
        with pytest.raises(ValidationError):
            PaginatedOrders(items=[], total=0, page=0, page_size=10, total_pages=1)


# ---------------------------------------------------------------------------
# TestUtilityHelpers
# ---------------------------------------------------------------------------

class TestUtilityHelpers:

    def test_serialise_order_returns_json_string(self):
        from schemas import OrderResponse, serialise_order
        order = OrderResponse(**make_order_response())
        result = serialise_order(order)
        assert isinstance(result, str)
        parsed = json.loads(result)
        assert parsed["id"] == 1

    def test_serialise_order_excludes_none_fields(self):
        from schemas import OrderResponse, serialise_order
        order = OrderResponse(**make_order_response())
        result = serialise_order(order)
        parsed = json.loads(result)
        assert "notes" not in parsed
        assert "updated_at" not in parsed

    def test_deserialise_order_round_trips(self):
        from schemas import OrderResponse, serialise_order, deserialise_order
        original = OrderResponse(**make_order_response())
        json_str = serialise_order(original)
        recovered = deserialise_order(json_str)
        assert recovered.id == original.id
        assert recovered.customer_id == original.customer_id

    def test_order_from_orm_uses_from_attributes(self):
        """from_orm() removed in v2 — must use model_validate() with from_attributes=True in config."""
        from schemas import OrderResponse, order_from_orm
        orm_obj = SimpleNamespace(**make_order_response())
        result = order_from_orm(orm_obj)
        assert result.id == 1

    def test_get_schema_returns_dict_with_properties(self):
        """Model.schema() removed in v2 — must use model_json_schema()."""
        from schemas import get_schema
        schema = get_schema()
        assert isinstance(schema, dict)
        assert "properties" in schema

    def test_get_field_names_returns_list_of_strings(self):
        """__fields__ returns FieldInfo objects in v2 — must use model_fields."""
        from schemas import OrderResponse, get_field_names
        names = get_field_names(OrderResponse)
        assert isinstance(names, list)
        assert "id" in names
        assert "status" in names

    def test_export_order_returns_dict(self):
        """order.dict() must be replaced with order.model_dump()."""
        from schemas import OrderResponse, export_order
        order = OrderResponse(**make_order_response())
        result = export_order(order)
        assert isinstance(result, dict)
        assert result["id"] == 1

    def test_export_order_exclude_none_drops_nulls(self):
        from schemas import OrderResponse, export_order
        order = OrderResponse(**make_order_response())
        result = export_order(order, exclude_none=True)
        assert "notes" not in result
        assert "updated_at" not in result

    def test_export_order_include_none_keeps_nulls(self):
        from schemas import OrderResponse, export_order
        order = OrderResponse(**make_order_response())
        result = export_order(order, exclude_none=False)
        assert "notes" in result


# ---------------------------------------------------------------------------
# TestOrmModeConfig
# ---------------------------------------------------------------------------

class TestOrmModeConfig:

    def test_address_created_from_orm_object(self):
        """Config must use from_attributes=True (not orm_mode=True) in v2."""
        from schemas import Address
        orm_obj = SimpleNamespace(
            line1="5 Park St", line2=None, city="Chennai",
            state="Tamil Nadu", pincode="600001", country="India"
        )
        addr = Address.model_validate(orm_obj)
        assert addr.city == "Chennai"

    def test_customer_response_from_orm_object(self):
        from schemas import CustomerResponse
        orm_obj = SimpleNamespace(
            id=1, name="Anita", email="anita@example.com",
            phone=None, address=None,
            created_at=datetime(2024, 3, 1, 9, 0, 0)
        )
        customer = CustomerResponse.model_validate(orm_obj)
        assert customer.name == "Anita"

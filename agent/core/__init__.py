"""Core contracts and compatibility helpers for the PPT Agent pipeline."""

from .compatibility import upgrade_slide_plan_v1
from .contracts import ContractRef, get_contract, list_contracts
from .validation import validate_document, validate_or_raise

__all__ = [
    "ContractRef",
    "get_contract",
    "list_contracts",
    "upgrade_slide_plan_v1",
    "validate_document",
    "validate_or_raise",
]

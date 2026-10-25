"""Trial eligibility free-text -> structured, checkable logic."""

from eligible.criteria.parser import CriteriaParser
from eligible.criteria.schema import Criterion, ParsedEligibility

__all__ = ["CriteriaParser", "Criterion", "ParsedEligibility"]

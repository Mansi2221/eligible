"""Parser structure test using a fake LLM client (no API key needed)."""

from eligible.criteria import CriteriaParser
from eligible.criteria.parser import _extract_json
from eligible.llm.client import LLMResponse


class FakeClient:
    """Returns a canned JSON payload, mimicking DeepSeekClient.complete."""

    def __init__(self, content: str) -> None:
        self._content = content

    def complete(self, messages, **kwargs) -> LLMResponse:
        return LLMResponse(content=self._content, reasoning=None, model="fake", usage={})


CANNED = """```json
{"criteria": [
  {"kind":"inclusion","text":"Age 18-70 years","category":"demographic",
   "attribute":"age","operator":"in","value":"18-70","unit":"years","temporal":null},
  {"kind":"inclusion","text":"clinically diagnosed type 2 diabetes","category":"condition",
   "attribute":"type 2 diabetes","operator":"exists","value":null,"unit":null,"temporal":null},
  {"kind":"exclusion","text":"patients with type 1 diabetes","category":"condition",
   "attribute":"type 1 diabetes","operator":"exists","value":null,"unit":null,"temporal":null}
]}
```"""


def test_parser_maps_response_to_schema():
    parser = CriteriaParser(client=FakeClient(CANNED))
    parsed = parser.parse("NCT05307731", "…free text…")
    assert parsed.nct_id == "NCT05307731"
    assert len(parsed.criteria) == 3
    assert len(parsed.inclusion) == 2
    assert len(parsed.exclusion) == 1
    age = parsed.inclusion[0]
    assert age.category == "demographic" and age.operator == "in" and age.unit == "years"


def test_extract_json_tolerates_code_fences():
    assert _extract_json('```json\n{"criteria": []}\n```') == {"criteria": []}
    assert _extract_json('Here you go: {"criteria": []} done') == {"criteria": []}

import datetime as _dt
import pytest
from tools import life_events

def test_list_journeys():
    res = life_events.list_journeys()
    assert "journeys" in res
    assert "disclaimer" in res
    assert "rules_year" in res
    assert len(res["journeys"]) == 6
    
    for j in res["journeys"]:
        assert "key" in j
        assert "title" in j
        assert "icon" in j
        assert "tagline" in j
        assert "steps" in j
        # steps in list_journeys is the count, not the full steps list
        assert isinstance(j["steps"], int)
        assert j["steps"] >= 4

def test_unique_lowercase_keys():
    res = life_events.list_journeys()
    keys = [j["key"] for j in res["journeys"]]
    assert len(keys) == len(set(keys))
    for k in keys:
        assert k == k.lower()

def test_get_journey_valid():
    res = life_events.get_journey("baby")
    assert res["key"] == "baby"
    assert res["title"] == "Welcoming a Newborn"
    assert res["icon"] == "fa-baby"
    assert "intro" in res
    assert "disclaimer" in res
    assert "rules_year" in res
    
    assert len(res["steps"]) >= 4
    for s in res["steps"]:
        assert "title" in s
        assert "agency" in s
        assert "timing" in s
        assert "detail" in s
        assert "url" in s
        assert "link_label" in s
        assert "tool" in s

def test_get_journey_invalid():
    with pytest.raises(ValueError, match="unknown life-event journey"):
        life_events.get_journey("does-not-exist")

def test_get_journey_case_insensitive():
    res = life_events.get_journey("BABY")
    assert res["key"] == "baby"

def test_step_tool_validation():
    allowed_tools = {"benefits", "upfront", "cpflife", "scam", None}
    for j_summary in life_events.list_journeys()["journeys"]:
        j = life_events.get_journey(j_summary["key"])
        for s in j["steps"]:
            assert s["tool"] in allowed_tools

def test_step_url_starts_with_https():
    for j_summary in life_events.list_journeys()["journeys"]:
        j = life_events.get_journey(j_summary["key"])
        for s in j["steps"]:
            if s["url"]:
                assert s["url"].startswith("https://")

def test_freshness_constants():
    assert life_events.RULES_YEAR == "2026"
    
    # Verify dates parse successfully
    last_reviewed = _dt.date.fromisoformat(life_events.RULES_LAST_REVIEWED)
    review_by = _dt.date.fromisoformat(life_events.RULES_REVIEW_BY)
    assert last_reviewed < review_by

from core.match_generator import generate_match

from agents.grounding_checker import GroundingCheckerAgent
from agents.pipeline import ScoutsEyePipeline


def test_pipeline_produces_grounded_narratives_for_a_progressive_passer():
    _, events = generate_match(seed=3)
    metrics, entries = ScoutsEyePipeline().run_for_player(events, "h_cm1")
    assert len(entries) >= 1
    for entry in entries:
        assert entry.narrative["grounded"] == "True"
        assert entry.narrative["analyst_en"]
        for lang in ("en", "sv", "es"):
            assert entry.narrative[f"fan_{lang}"]


def test_pipeline_respects_minute_cutoff():
    _, events = generate_match(seed=3)
    _, early_entries = ScoutsEyePipeline().run_for_player(events, "h_cm1", up_to_minute=5)
    _, full_entries = ScoutsEyePipeline().run_for_player(events, "h_cm1", up_to_minute=90)
    assert len(early_entries) <= len(full_entries)


def test_grounding_checker_rejects_fabricated_citations():
    _, events = generate_match(seed=3)
    _, entries = ScoutsEyePipeline().run_for_player(events, "h_cm1")
    entry = entries[0]
    checker = GroundingCheckerAgent()

    result = checker.run(entry, "This never happened [e99999].")

    assert result.grounded is False
    assert "e99999" in result.unverifiable_ids


def test_grounding_checker_accepts_real_citations():
    _, events = generate_match(seed=3)
    _, entries = ScoutsEyePipeline().run_for_player(events, "h_cm1")
    entry = entries[0]
    checker = GroundingCheckerAgent()

    real_id = entry.evidence.event_ids[0]
    result = checker.run(entry, f"Confirmed by event [{real_id}].")

    assert result.grounded is True

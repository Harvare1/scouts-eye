from core.detectors import run_all_detectors
from core.match_generator import generate_match
from core.metrics import compute_metrics


def _entries_for(player_id, events):
    metrics = compute_metrics(events, player_id)
    player_events = [e for e in events if e.player_id == player_id]
    return run_all_detectors(player_events, player_id, metrics)


def test_progressive_passer_archetype_gets_strength():
    _, events = generate_match(seed=3)
    entries = _entries_for("h_cm1", events)  # Okafor, progressive_passer
    assert any(e.category == "progressive_passing" and e.kind == "strength" for e in entries)


def test_flank_vulnerable_archetype_gets_watch_point():
    _, events = generate_match(seed=3)
    entries = _entries_for("h_rb", events)  # Oduya, flank_vulnerable
    assert any(e.category == "duels" and e.kind == "watch_point" for e in entries)


def test_dominant_duelist_archetype_gets_strength():
    _, events = generate_match(seed=3)
    entries = _entries_for("h_cb1", events)  # Marchetti, dominant_duelist
    assert any(e.category == "duels" and e.kind == "strength" for e in entries)


def test_undisciplined_archetype_gets_discipline_watch_point():
    _, events = generate_match(seed=3)
    entries = _entries_for("h_lb", events)  # Vargas, undisciplined
    assert any(e.category == "discipline" for e in entries)


def test_clinical_finisher_gets_finishing_strength():
    _, events = generate_match(seed=3)
    entries = _entries_for("h_st", events)  # Correia, clinical_finisher
    assert any(e.category == "finishing" and e.kind == "strength" for e in entries)


def test_wasteful_finisher_gets_finishing_watch_point():
    _, events = generate_match(seed=3)
    entries = _entries_for("a_st", events)  # Dragomir, wasteful_finisher
    assert any(e.category == "finishing" and e.kind == "watch_point" for e in entries)


def test_every_entry_is_grounded_in_real_events_for_that_player():
    players, events = generate_match(seed=3)
    for player in players:
        entries = _entries_for(player.id, events)
        player_event_ids = {e.id for e in events if e.player_id == player.id}
        for entry in entries:
            assert set(entry.evidence.event_ids).issubset(player_event_ids)
            assert len(entry.evidence.event_ids) > 0

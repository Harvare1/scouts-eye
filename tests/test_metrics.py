from core.match_generator import generate_match
from core.metrics import compute_metrics


def test_metrics_only_count_this_players_events():
    _, events = generate_match(seed=3)
    metrics = compute_metrics(events, "h_rb")
    assert metrics.player_id == "h_rb"
    assert metrics.passes_attempted > 0


def test_metrics_respect_up_to_minute_cutoff():
    _, events = generate_match(seed=3)
    early = compute_metrics(events, "h_cm1", up_to_minute=10)
    full = compute_metrics(events, "h_cm1", up_to_minute=90)
    assert early.passes_attempted <= full.passes_attempted


def test_pass_completion_and_duel_win_rate_bounds():
    _, events = generate_match(seed=3)
    metrics = compute_metrics(events, "h_cb1")
    assert 0.0 <= metrics.pass_completion <= 1.0
    assert 0.0 <= metrics.duel_win_rate <= 1.0

"""Aggregates raw events into per-player summary metrics.

`distance_m` is a rough synthetic proxy (event-to-event displacement plus a
fixed per-action allowance) — it stands in for real tracking data, which
this project does not have. See the README's "Honest boundaries" section.
"""
import math

from core.models import Event, PlayerMetrics

_ACTION_DISTANCE_ALLOWANCE = 4.0


def _dist(e: Event) -> float:
    if e.target_x is None or e.target_y is None:
        return _ACTION_DISTANCE_ALLOWANCE
    return math.hypot(e.target_x - e.x, e.target_y - e.y) + _ACTION_DISTANCE_ALLOWANCE


def compute_metrics(events: list[Event], player_id: str, up_to_minute: int = 90) -> PlayerMetrics:
    mine = [e for e in events if e.player_id == player_id and e.minute <= up_to_minute]
    passes = [e for e in mine if e.type == "pass"]
    completed = [e for e in passes if e.outcome == "success"]
    progressive = [
        e for e in completed
        if e.target_x is not None and (e.target_x - e.x) >= 15
    ]
    tackles_interceptions = [e for e in mine if e.type in ("tackle", "interception")]
    duels_won = [e for e in tackles_interceptions if e.outcome == "success"]
    duels_lost = [e for e in tackles_interceptions if e.outcome == "failed"]
    interceptions = [e for e in mine if e.type == "interception"]
    fouls = [e for e in mine if e.type == "foul"]
    shots = [e for e in mine if e.type in ("shot", "goal")]
    shots_on_target = [e for e in shots if e.outcome == "success" or e.type == "goal"]
    goals = [e for e in mine if e.type == "goal"]

    return PlayerMetrics(
        player_id=player_id,
        minutes_tracked=up_to_minute,
        passes_attempted=len(passes),
        passes_completed=len(completed),
        progressive_passes=len(progressive),
        carries=len([e for e in mine if e.type == "carry"]),
        duels_won=len(duels_won),
        duels_lost=len(duels_lost),
        interceptions=len(interceptions),
        fouls_committed=len(fouls),
        shots=len(shots),
        shots_on_target=len(shots_on_target),
        goals=len(goals),
        distance_m=round(sum(_dist(e) for e in mine), 1),
    )

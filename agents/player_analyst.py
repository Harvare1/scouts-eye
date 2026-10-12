"""Agent 1 — Player Analyst.

Computes a player's aggregate metrics and runs the rule-based detectors
against their event history. Kept separate from the detector functions
themselves so a future version could swap in a learned model here without
touching anything downstream, as long as it still returns `DossierEntry`
objects grounded in real event ids.
"""
from core.detectors import run_all_detectors
from core.metrics import compute_metrics
from core.models import DossierEntry, Event, PlayerMetrics


class PlayerAnalystAgent:
    name = "player-analyst"

    def run(self, events: list[Event], player_id: str, up_to_minute: int = 90) -> tuple[PlayerMetrics, list[DossierEntry]]:
        metrics = compute_metrics(events, player_id, up_to_minute)
        player_events = [e for e in events if e.player_id == player_id and e.minute <= up_to_minute]
        entries = run_all_detectors(player_events, player_id, metrics)
        return metrics, entries

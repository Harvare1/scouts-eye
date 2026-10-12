"""Core data model for Scout's Eye.

Pitch coordinates: x in [0, 105] (length, metres), y in [0, 68] (width,
metres). Every player's team always attacks toward x=105, so "progressive"
and zone math never needs to branch on which half a team is defending.
"""
from dataclasses import dataclass, field
from typing import Literal

EventType = Literal[
    "pass", "carry", "tackle", "interception", "foul", "shot", "goal", "save",
]


@dataclass(frozen=True)
class Player:
    id: str
    team: Literal["home", "away"]
    name: str
    position: str
    archetype: str  # drives how the generator biases this player's events


@dataclass(frozen=True)
class Event:
    id: str
    minute: int
    second: int
    type: EventType
    team: Literal["home", "away"]
    player_id: str
    x: float
    y: float
    target_x: float | None = None
    target_y: float | None = None
    outcome: Literal["success", "failed"] = "success"
    opponent_id: str | None = None  # the duel/tackle/foul counterpart, when relevant

    @property
    def timestamp(self) -> str:
        return f"{self.minute:02d}:{self.second:02d}"


@dataclass(frozen=True)
class PlayerMetrics:
    player_id: str
    minutes_tracked: int
    passes_attempted: int
    passes_completed: int
    progressive_passes: int
    carries: int
    duels_won: int
    duels_lost: int
    interceptions: int
    fouls_committed: int
    shots: int
    shots_on_target: int
    goals: int
    distance_m: float

    @property
    def pass_completion(self) -> float:
        return self.passes_completed / self.passes_attempted if self.passes_attempted else 0.0

    @property
    def duel_win_rate(self) -> float:
        total = self.duels_won + self.duels_lost
        return self.duels_won / total if total else 0.0


@dataclass(frozen=True)
class Evidence:
    """A pointer from a dossier line back to the raw events that justify it."""
    event_ids: list[str]
    metric: str
    value: float
    description: str


@dataclass(frozen=True)
class DossierEntry:
    id: str
    player_id: str
    kind: Literal["strength", "watch_point"]
    category: Literal[
        "progressive_passing", "duels", "pressing_workrate",
        "discipline", "finishing",
    ]
    headline: str
    evidence: Evidence
    confidence: float
    params: dict = field(default_factory=dict)
    narrative: dict[str, str] = field(default_factory=dict)  # lang -> text

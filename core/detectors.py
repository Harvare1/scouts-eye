"""Per-player pattern detectors.

Every detector only ever looks at one player's `Event`s and that player's
computed `PlayerMetrics`, and returns `DossierEntry` objects whose
`Evidence.event_ids` point back at the exact events behind the claim.
Nothing downstream is allowed to add a claim that isn't traceable to this
evidence — that traceability is the whole point of a "scouting report an
agent can't bluff its way through."
"""
from core.models import DossierEntry, Event, Evidence, PlayerMetrics

_EID = [0]


def _next_id() -> str:
    _EID[0] += 1
    return f"dossier{_EID[0]}"


def detect_progressive_passing(
    events: list[Event], player_id: str, metrics: PlayerMetrics,
    min_passes: int = 15, strength_share: float = 0.35,
) -> list[DossierEntry]:
    completed = [e for e in events if e.player_id == player_id and e.type == "pass" and e.outcome == "success"]
    if len(completed) < min_passes:
        return []
    progressive = [e for e in completed if e.target_x is not None and (e.target_x - e.x) >= 15]
    share = len(progressive) / len(completed)
    if share < strength_share:
        return []
    return [DossierEntry(
        id=_next_id(), player_id=player_id, kind="strength", category="progressive_passing",
        headline="Progresses the ball through passing",
        evidence=Evidence(
            event_ids=[e.id for e in progressive], metric="progressive_share", value=round(share, 2),
            description=f"{len(progressive)} of {len(completed)} completed passes ({share:.0%}) advanced the ball 15m+.",
        ),
        confidence=min(0.95, 0.4 + share),
        params={"share": round(share, 2), "count": len(progressive)},
    )]


def detect_ball_retention(
    events: list[Event], player_id: str, metrics: PlayerMetrics,
    min_passes: int = 12, strength_rate: float = 0.85, watch_rate: float = 0.65,
) -> list[DossierEntry]:
    passes = [e for e in events if e.player_id == player_id and e.type == "pass"]
    if len(passes) < min_passes:
        return []
    completed = [e for e in passes if e.outcome == "success"]
    rate = len(completed) / len(passes)
    if rate >= strength_rate:
        return [DossierEntry(
            id=_next_id(), player_id=player_id, kind="strength", category="ball_retention",
            headline="Rarely gives the ball away",
            evidence=Evidence(
                event_ids=[e.id for e in completed], metric="pass_completion", value=round(rate, 2),
                description=f"{len(completed)} of {len(passes)} passes ({rate:.0%}) completed.",
            ),
            confidence=min(0.95, 0.3 + rate),
            params={"rate": round(rate, 2)},
        )]
    if rate <= watch_rate:
        failed = [e for e in passes if e.outcome == "failed"]
        return [DossierEntry(
            id=_next_id(), player_id=player_id, kind="watch_point", category="ball_retention",
            headline="Gives the ball away more than you'd like",
            evidence=Evidence(
                event_ids=[e.id for e in failed], metric="pass_completion", value=round(rate, 2),
                description=f"Only {len(completed)} of {len(passes)} passes ({rate:.0%}) completed.",
            ),
            confidence=min(0.95, 0.3 + (1 - rate)),
            params={"rate": round(rate, 2)},
        )]
    return []


def detect_duel_profile(
    events: list[Event], player_id: str, metrics: PlayerMetrics,
    min_duels: int = 6, strength_rate: float = 0.60, watch_rate: float = 0.40,
) -> list[DossierEntry]:
    duels = [e for e in events if e.player_id == player_id and e.type in ("tackle", "interception")]
    if len(duels) < min_duels:
        return []
    won = [e for e in duels if e.outcome == "success"]
    lost = [e for e in duels if e.outcome == "failed"]
    rate = len(won) / len(duels)
    if rate >= strength_rate:
        return [DossierEntry(
            id=_next_id(), player_id=player_id, kind="strength", category="duels",
            headline="Wins the majority of defensive duels",
            evidence=Evidence(
                event_ids=[e.id for e in won], metric="duel_win_rate", value=round(rate, 2),
                description=f"Won {len(won)} of {len(duels)} tackles/interceptions ({rate:.0%}).",
            ),
            confidence=min(0.95, 0.3 + rate),
            params={"rate": round(rate, 2)},
        )]
    if rate <= watch_rate:
        return [DossierEntry(
            id=_next_id(), player_id=player_id, kind="watch_point", category="duels",
            headline="Loses most of his defensive duels",
            evidence=Evidence(
                event_ids=[e.id for e in lost], metric="duel_win_rate", value=round(rate, 2),
                description=f"Won only {len(won)} of {len(duels)} tackles/interceptions ({rate:.0%}).",
            ),
            confidence=min(0.95, 0.3 + (1 - rate)),
            params={"rate": round(rate, 2)},
        )]
    return []


def detect_pressing_workrate(
    events: list[Event], player_id: str, metrics: PlayerMetrics,
    min_actions: int = 4, high_zone_x: float = 52.5,
) -> list[DossierEntry]:
    high_actions = [
        e for e in events
        if e.player_id == player_id and e.type in ("tackle", "interception")
        and e.outcome == "success" and e.x >= high_zone_x
    ]
    if len(high_actions) < min_actions:
        return []
    return [DossierEntry(
        id=_next_id(), player_id=player_id, kind="strength", category="pressing_workrate",
        headline="Regains the ball high up the pitch",
        evidence=Evidence(
            event_ids=[e.id for e in high_actions], metric="high_regains", value=len(high_actions),
            description=f"{len(high_actions)} successful tackles/interceptions in the opponent half.",
        ),
        confidence=min(0.95, 0.4 + 0.05 * len(high_actions)),
        params={"count": len(high_actions)},
    )]


def detect_discipline(
    events: list[Event], player_id: str, metrics: PlayerMetrics, min_fouls: int = 2,
) -> list[DossierEntry]:
    fouls = [e for e in events if e.player_id == player_id and e.type == "foul"]
    if len(fouls) < min_fouls:
        return []
    return [DossierEntry(
        id=_next_id(), player_id=player_id, kind="watch_point", category="discipline",
        headline="Picks up fouls at a concerning rate",
        evidence=Evidence(
            event_ids=[e.id for e in fouls], metric="fouls", value=len(fouls),
            description=f"{len(fouls)} fouls committed so far.",
        ),
        confidence=min(0.95, 0.35 + 0.1 * len(fouls)),
        params={"count": len(fouls)},
    )]


def detect_finishing(
    events: list[Event], player_id: str, metrics: PlayerMetrics,
    min_shots: int = 3, strength_rate: float = 0.50, watch_rate: float = 0.38,
) -> list[DossierEntry]:
    shots = [e for e in events if e.player_id == player_id and e.type in ("shot", "goal")]
    if len(shots) < min_shots:
        return []
    on_target = [e for e in shots if e.type == "goal" or e.outcome == "success"]
    rate = len(on_target) / len(shots)
    if rate >= strength_rate:
        return [DossierEntry(
            id=_next_id(), player_id=player_id, kind="strength", category="finishing",
            headline="Tests the goalkeeper consistently",
            evidence=Evidence(
                event_ids=[e.id for e in on_target], metric="on_target_rate", value=round(rate, 2),
                description=f"{len(on_target)} of {len(shots)} shots ({rate:.0%}) on target.",
            ),
            confidence=min(0.95, 0.3 + rate),
            params={"rate": round(rate, 2)},
        )]
    if rate <= watch_rate:
        return [DossierEntry(
            id=_next_id(), player_id=player_id, kind="watch_point", category="finishing",
            headline="Struggles to hit the target",
            evidence=Evidence(
                event_ids=[e.id for e in shots], metric="on_target_rate", value=round(rate, 2),
                description=f"Only {len(on_target)} of {len(shots)} shots ({rate:.0%}) on target.",
            ),
            confidence=min(0.95, 0.3 + (1 - rate)),
            params={"rate": round(rate, 2)},
        )]
    return []


def run_all_detectors(events: list[Event], player_id: str, metrics: PlayerMetrics) -> list[DossierEntry]:
    entries = []
    entries += detect_progressive_passing(events, player_id, metrics)
    entries += detect_ball_retention(events, player_id, metrics)
    entries += detect_duel_profile(events, player_id, metrics)
    entries += detect_pressing_workrate(events, player_id, metrics)
    entries += detect_discipline(events, player_id, metrics)
    entries += detect_finishing(events, player_id, metrics)
    return entries

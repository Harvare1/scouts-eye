"""Generates a synthetic, football-realistic per-player event stream.

Each player is given an "archetype" that deterministically biases how their
events are generated (pass accuracy, duel outcomes, where on the pitch they
act). This is what makes the later dossier patterns real and checkable:
a player's "wins few duels on his flank" dossier line traces back to actual
generated duel events for that exact player, not an invented claim.
"""
import random

from core.models import Event, Player

TEAM_NAMES = {"home": "Albion United", "away": "Caldervale FC"}

# (id, position, name, archetype)
HOME_PLAYERS = [
    ("h_gk", "GK", "Petrova", "balanced"),
    ("h_rb", "RB", "Oduya", "flank_vulnerable"),
    ("h_cb1", "CB", "Marchetti", "dominant_duelist"),
    ("h_cb2", "CB", "Lindqvist", "balanced"),
    ("h_lb", "LB", "Vargas", "undisciplined"),
    ("h_cm1", "CM", "Okafor", "progressive_passer"),
    ("h_cm2", "CM", "Dvorak", "pressing_menace"),
    ("h_rw", "RW", "Saito", "balanced"),
    ("h_am", "AM", "Bergstrom", "balanced"),
    ("h_lw", "LW", "Haidari", "balanced"),
    ("h_st", "ST", "Correia", "clinical_finisher"),
]
AWAY_PLAYERS = [
    ("a_gk", "GK", "Nowak", "balanced"),
    ("a_rb", "RB", "Thiombane", "balanced"),
    ("a_cb1", "CB", "Kowalczyk", "balanced"),
    ("a_cb2", "CB", "Hallgrimsson", "dominant_duelist"),
    ("a_lb", "LB", "Pereira", "flank_vulnerable"),
    ("a_cm1", "CM", "Novotny", "progressive_passer"),
    ("a_rm", "RM", "Asante", "pressing_menace"),
    ("a_am", "AM", "Soderberg", "balanced"),
    ("a_lw", "LW", "Benitez", "balanced"),
    ("a_rb2", "RB2", "Kowalski", "undisciplined"),
    ("a_st", "ST", "Dragomir", "wasteful_finisher"),
]

_ZONES = {
    "GK": (10, 34, 6, 6), "CB": (24, 34, 10, 16), "RB": (30, 10, 16, 8),
    "LB": (30, 58, 16, 8), "RB2": (55, 10, 16, 8), "RM": (55, 58, 16, 8),
    "CM": (50, 34, 16, 18), "AM": (68, 34, 14, 16), "RW": (72, 12, 16, 8),
    "LW": (72, 56, 16, 8), "ST": (88, 34, 10, 14),
}

_ACTION_BUDGET = {
    "GK": {"pass": 18}, "CB": {"pass": 38, "tackle": 10, "interception": 6},
    "RB": {"pass": 32, "tackle": 12, "interception": 4, "foul": 1},
    "LB": {"pass": 32, "tackle": 12, "interception": 4, "foul": 1},
    "RB2": {"pass": 32, "tackle": 12, "interception": 4, "foul": 1},
    "RM": {"pass": 36, "tackle": 8, "interception": 5, "foul": 1},
    "CM": {"pass": 55, "tackle": 8, "interception": 7, "foul": 1},
    "AM": {"pass": 40, "shot": 3, "foul": 1},
    "RW": {"pass": 28, "shot": 4, "tackle": 2},
    "LW": {"pass": 28, "shot": 4, "tackle": 2},
    "ST": {"pass": 16, "shot": 12},
}

_ARCHETYPE_BIAS = {
    "balanced": {"pass_ok": 0.80, "progressive": 0.18, "duel_win": 0.50, "on_target": 0.45, "goal_given_ot": 0.22},
    "progressive_passer": {"pass_ok": 0.84, "progressive": 0.48, "duel_win": 0.50, "on_target": 0.45, "goal_given_ot": 0.22},
    "flank_vulnerable": {"pass_ok": 0.74, "progressive": 0.14, "duel_win": 0.28, "on_target": 0.45, "goal_given_ot": 0.22},
    "dominant_duelist": {"pass_ok": 0.80, "progressive": 0.14, "duel_win": 0.78, "on_target": 0.45, "goal_given_ot": 0.22},
    "pressing_menace": {"pass_ok": 0.78, "progressive": 0.20, "duel_win": 0.58, "on_target": 0.45, "goal_given_ot": 0.22, "press": True},
    "undisciplined": {"pass_ok": 0.76, "progressive": 0.16, "duel_win": 0.46, "on_target": 0.45, "goal_given_ot": 0.22, "foul_mult": 4},
    "clinical_finisher": {"pass_ok": 0.80, "progressive": 0.18, "duel_win": 0.50, "on_target": 0.68, "goal_given_ot": 0.42},
    "wasteful_finisher": {"pass_ok": 0.80, "progressive": 0.18, "duel_win": 0.50, "on_target": 0.30, "goal_given_ot": 0.12, "shot_mult": 2},
}


def build_players() -> list[Player]:
    players = [Player(pid, "home", name, pos, arch) for pid, pos, name, arch in HOME_PLAYERS]
    players += [Player(pid, "away", name, pos, arch) for pid, pos, name, arch in AWAY_PLAYERS]
    return players


def _zone_point(rng: random.Random, position: str) -> tuple[float, float]:
    cx, cy, spread_x, spread_y = _ZONES[position]
    x = max(2.0, min(103.0, rng.uniform(cx - spread_x, cx + spread_x)))
    y = max(2.0, min(66.0, rng.uniform(cy - spread_y, cy + spread_y)))
    return x, y


def _opponent_for(rng: random.Random, roster: list[Player], player: Player) -> Player:
    opponents = [p for p in roster if p.team != player.team]
    return rng.choice(opponents)


def generate_match(seed: int = 3) -> tuple[list[Player], list[Event]]:
    rng = random.Random(seed)
    players = build_players()
    roster_by_team = {"home": [p for p in players if p.team == "home"], "away": [p for p in players if p.team == "away"]}
    events: list[Event] = []
    eid = [0]

    def next_id() -> str:
        eid[0] += 1
        return f"e{eid[0]}"

    def minute_second() -> tuple[int, int]:
        m = rng.randint(0, 89)
        s = rng.randint(0, 59)
        return m, s

    for player in players:
        bias = _ARCHETYPE_BIAS[player.archetype]
        budget = _ACTION_BUDGET[player.position]
        for action, count in budget.items():
            count = int(count * bias.get("shot_mult", 1)) if action == "shot" else count
            count = int(count * bias.get("foul_mult", 1)) if action == "foul" else count
            for _ in range(count):
                minute, second = minute_second()
                x, y = _zone_point(rng, player.position)
                if bias.get("press") and action in ("interception", "tackle") and rng.random() < 0.6:
                    x = min(102.0, x + rng.uniform(15, 30))  # pushed into the opponent half

                if action == "pass":
                    progressive = rng.random() < bias["progressive"]
                    advance = rng.uniform(18, 32) if progressive else rng.uniform(2, 14)
                    target_x = min(104.0, x + advance)
                    target_y = max(2.0, min(66.0, y + rng.uniform(-10, 10)))
                    success = rng.random() < bias["pass_ok"]
                    events.append(Event(
                        id=next_id(), minute=minute, second=second, type="pass", team=player.team,
                        player_id=player.id, x=x, y=y, target_x=target_x, target_y=target_y,
                        outcome="success" if success else "failed",
                    ))
                elif action in ("tackle", "interception"):
                    opponent = _opponent_for(rng, players, player)
                    won = rng.random() < bias["duel_win"]
                    events.append(Event(
                        id=next_id(), minute=minute, second=second, type=action, team=player.team,
                        player_id=player.id, x=x, y=y, opponent_id=opponent.id,
                        outcome="success" if won else "failed",
                    ))
                elif action == "foul":
                    opponent = _opponent_for(rng, players, player)
                    events.append(Event(
                        id=next_id(), minute=minute, second=second, type="foul", team=player.team,
                        player_id=player.id, x=x, y=y, opponent_id=opponent.id, outcome="failed",
                    ))
                elif action == "shot":
                    on_target = rng.random() < bias["on_target"]
                    goal = on_target and rng.random() < bias["goal_given_ot"]
                    events.append(Event(
                        id=next_id(), minute=minute, second=second, type="goal" if goal else "shot",
                        team=player.team, player_id=player.id, x=x, y=y, target_x=104.5, target_y=34.0,
                        outcome="success" if on_target else "failed",
                    ))

    events.sort(key=lambda e: (e.minute, e.second, e.id))
    return players, events

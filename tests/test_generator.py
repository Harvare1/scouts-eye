from core.match_generator import generate_match


def test_generate_match_is_deterministic():
    players1, events1 = generate_match(seed=3)
    players2, events2 = generate_match(seed=3)
    assert [e.id for e in events1] == [e.id for e in events2]
    assert [(e.x, e.y) for e in events1] == [(e.x, e.y) for e in events2]


def test_22_players_with_archetypes():
    players, _ = generate_match(seed=3)
    assert len(players) == 22
    assert len({p.id for p in players}) == 22
    assert all(p.archetype for p in players)


def test_events_stay_within_90_minutes_and_pitch_bounds():
    _, events = generate_match(seed=3)
    assert all(0 <= e.minute <= 89 for e in events)
    assert all(0 <= e.x <= 105 and 0 <= e.y <= 68 for e in events)


def test_every_event_belongs_to_a_real_player():
    players, events = generate_match(seed=3)
    ids = {p.id for p in players}
    assert all(e.player_id in ids for e in events)

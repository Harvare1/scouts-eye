# Scout's Eye

**Live, evidence-grounded scouting dossiers — built as the match unfolds.**

A different take on Microsoft & the Premier League's *Inside the Game* hackathon brief: instead of a live tactical dashboard for analysts, Scout's Eye generates an automatic **scouting report per player**, growing minute by minute, for scouts, academies and agents. Every strength or watch-point it writes cites the exact synthetic events it's based on, and a dedicated agent mechanically rejects any sentence that cites evidence outside that set.

## Run locally

```sh
python server.py
```

Open <http://localhost:8090>, pick a player from either roster, and scrub the match timeline — the dossier grows as more evidence becomes available.

```sh
pytest -q
docker build -t scouts-eye .
docker run --rm -p 8090:8090 scouts-eye
```

Endpoints:

- `GET /api/match` — synthetic players and the full event stream
- `GET /api/dossier?player=<id>&minute=<0-90>` — that player's metrics and grounded dossier entries up to that minute
- `GET /health` — container health probe

## How it works

A synthetic 22-player match is generated with each player assigned an **archetype** (progressive passer, flank-vulnerable full-back, dominant duelist, high-pressing midfielder, undisciplined defender, clinical or wasteful finisher, or balanced) that biases how their individual events are generated — this is what makes the dossiers real, checkable patterns rather than flavor text.

A four-stage agent pipeline (`agents/`) turns that event stream into a dossier:

1. **Player Analyst** — computes the player's metrics and runs rule-based detectors (progressive passing share, duel win rate, high-press regains, foul rate, shot accuracy).
2. **Dossier Writer** — drafts a sentence per finding, citing the exact event ids behind it.
3. **Grounding Checker** — mechanically parses those citations and rejects any sentence that cites an id outside the finding's own evidence, falling back to a safe placeholder instead of ever shipping an unverifiable claim.
4. **Localization Agent** — produces a plain-language one-liner in English, Swedish and Spanish for each finding, built from structured data rather than translated prose.

Set `AZURE_FOUNDRY_ENDPOINT` + `AZURE_FOUNDRY_KEY` (and optionally `AZURE_FOUNDRY_DEPLOYMENT`) to let a real model rephrase the analyst sentence — it only ever gets the fixed facts and citations to rephrase, never free rein to invent a claim. Without credentials, the deterministic template output is used, so the demo never depends on a live API.

## Honest boundaries

All data is synthetic and generated locally; `distance_m` is a rough proxy (event-to-event displacement, not real tracking data). No real players, clubs, match feeds or footage are used or implied. A dossier entry only appears once there is enough sample size behind it (e.g. 8+ duels, 4+ shots) — thin evidence produces no claim rather than a shaky one.

## Submission checklist

- [x] Reproducible synthetic match with per-player archetypes
- [x] Four-stage agent pipeline with mechanical grounding checks
- [x] Evidence-linked strengths/watch-points per player, growing live over the match timeline
- [x] English/Swedish/Spanish localization
- [x] Docker image, health endpoint, CI tests
- [x] Optional Microsoft Foundry narration with deterministic fallback
- [ ] Azure Container Apps deployment
- [ ] Public GitHub repository and sub-two-minute demo video

"""Agent 3 — Grounding Checker.

Mechanically verifies that every event id cited in a generated dossier
line actually appears in that entry's evidence. This is what keeps the
"evidence-based scouting report, not an AI guessing" promise honest even
if the dossier writer is later swapped to a real LLM: a model that cites
an id outside the evidence set gets caught here, not shipped to a scout.
"""
import re
from dataclasses import dataclass

from core.models import DossierEntry

_CITATION_RE = re.compile(r"\be\d+\b")

FALLBACK_TEXT = "Observation withheld: generated text referenced evidence outside the verified event set."


@dataclass(frozen=True)
class GroundingResult:
    text: str
    grounded: bool
    cited_ids: list[str]
    unverifiable_ids: list[str]


class GroundingCheckerAgent:
    name = "grounding-checker"

    def run(self, entry: DossierEntry, text: str) -> GroundingResult:
        cited = sorted(set(_CITATION_RE.findall(text)))
        evidence_set = set(entry.evidence.event_ids)
        unverifiable = [c for c in cited if c not in evidence_set]
        if unverifiable:
            return GroundingResult(FALLBACK_TEXT, grounded=False, cited_ids=cited, unverifiable_ids=unverifiable)
        return GroundingResult(text, grounded=True, cited_ids=cited, unverifiable_ids=[])

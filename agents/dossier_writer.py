"""Agent 2 — Dossier Writer.

Turns a grounded DossierEntry into a readable scouting-report sentence.
Every sentence embeds the exact event ids it is based on as "[e12, e13]"
citations, so Agent 3 (grounding_checker) can mechanically verify nothing
was invented.
"""
from core.models import DossierEntry

from agents.llm_backend import LLMBackend, TemplateBackend


def _cite(event_ids: list[str]) -> str:
    shown = event_ids[:4]
    suffix = f", +{len(event_ids) - 4} more" if len(event_ids) > 4 else ""
    return f"[{', '.join(shown)}{suffix}]"


_TEMPLATES = {
    ("strength", "progressive_passing"): "{headline}: {desc} {cite}",
    ("strength", "ball_retention"): "{headline}: {desc} {cite}",
    ("watch_point", "ball_retention"): "{headline}: {desc} {cite}",
    ("strength", "duels"): "{headline}: {desc} {cite}",
    ("watch_point", "duels"): "{headline}: {desc} Worth checking on video before relying on him defensively. {cite}",
    ("strength", "pressing_workrate"): "{headline}: {desc} A real asset in a high press. {cite}",
    ("watch_point", "discipline"): "{headline}: {desc} {cite}",
    ("strength", "finishing"): "{headline}: {desc} {cite}",
    ("watch_point", "finishing"): "{headline}: {desc} {cite}",
}


class DossierWriterAgent:
    name = "dossier-writer"

    def __init__(self, backend: LLMBackend | None = None):
        self.backend = backend or TemplateBackend()

    def run(self, entry: DossierEntry) -> str:
        template = _TEMPLATES.get((entry.kind, entry.category), "{headline}: {desc} {cite}")
        return template.format(
            headline=entry.headline,
            desc=entry.evidence.description,
            cite=_cite(entry.evidence.event_ids),
        )

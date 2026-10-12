"""Orchestrates the four-agent pipeline end to end.

    Player Analyst -> Dossier Writer -> Grounding Checker -> Localization

Each stage only consumes the previous stage's typed output, which is what
makes any one of them swappable later (e.g. player_analyst backed by a
trained model) without touching the others.
"""
import dataclasses

from core.models import DossierEntry, Event, PlayerMetrics

from agents.dossier_writer import DossierWriterAgent
from agents.grounding_checker import GroundingCheckerAgent
from agents.localization_agent import LocalizationAgent
from agents.player_analyst import PlayerAnalystAgent


class ScoutsEyePipeline:
    def __init__(self):
        self.player_analyst = PlayerAnalystAgent()
        self.dossier_writer = DossierWriterAgent()
        self.grounding_checker = GroundingCheckerAgent()
        self.localization_agent = LocalizationAgent()

    def run_for_player(self, events: list[Event], player_id: str, up_to_minute: int = 90) -> tuple[PlayerMetrics, list[DossierEntry]]:
        metrics, entries = self.player_analyst.run(events, player_id, up_to_minute)
        enriched = []
        for entry in entries:
            draft_text = self.dossier_writer.run(entry)
            grounding = self.grounding_checker.run(entry, draft_text)

            narrative = {"analyst_en": grounding.text, "grounded": str(grounding.grounded)}
            narrative.update({f"fan_{lang}": text for lang, text in self.localization_agent.run(entry).items()})

            enriched.append(dataclasses.replace(entry, narrative=narrative))
        return metrics, enriched

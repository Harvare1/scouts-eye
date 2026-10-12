"""Agent 4 — Localization Agent.

Produces a short, plain-language one-liner per language for each dossier
entry, built from (kind, category) — not from parsing the English analyst
sentence — so each language reads naturally instead of like a translation,
while only ever restating exactly what the detector found.
"""
from core.models import DossierEntry

_TEMPLATES = {
    "en": {
        ("strength", "progressive_passing"): "Breaks lines with his passing — a real progressive threat.",
        ("strength", "duels"): "Wins the ball back consistently in one-on-ones.",
        ("watch_point", "duels"): "Struggling to win the ball back in duels right now.",
        ("strength", "pressing_workrate"): "Causes problems by winning the ball high up the pitch.",
        ("watch_point", "discipline"): "Picking up fouls at a rate worth keeping an eye on.",
        ("strength", "finishing"): "Testing the keeper regularly — a real goal threat.",
        ("watch_point", "finishing"): "Getting into good positions but not hitting the target.",
    },
    "sv": {
        ("strength", "progressive_passing"): "Bryter linjer med sina passningar — ett verkligt progressivt hot.",
        ("strength", "duels"): "Vinner bollen konsekvent i närkamper.",
        ("watch_point", "duels"): "Har svårt att vinna tillbaka bollen i närkamper just nu.",
        ("strength", "pressing_workrate"): "Skapar problem genom att vinna bollen högt upp på planen.",
        ("watch_point", "discipline"): "Drar på sig frisparkar i en takt värd att hålla koll på.",
        ("strength", "finishing"): "Testar målvakten regelbundet — ett verkligt målhot.",
        ("watch_point", "finishing"): "Kommer till bra lägen men träffar inte målet.",
    },
    "es": {
        ("strength", "progressive_passing"): "Rompe líneas con sus pases: una amenaza progresiva real.",
        ("strength", "duels"): "Gana el balón de forma consistente en los duelos.",
        ("watch_point", "duels"): "Le está costando recuperar el balón en los duelos.",
        ("strength", "pressing_workrate"): "Genera problemas recuperando el balón en campo rival.",
        ("watch_point", "discipline"): "Comete faltas a un ritmo que conviene vigilar.",
        ("strength", "finishing"): "Pone a prueba al portero con regularidad: una amenaza de gol real.",
        ("watch_point", "finishing"): "Llega a buenas posiciones pero no encuentra la portería.",
    },
}

SUPPORTED_LANGUAGES = ("en", "sv", "es")


class LocalizationAgent:
    name = "localization-agent"

    def run(self, entry: DossierEntry, languages: tuple[str, ...] = SUPPORTED_LANGUAGES) -> dict[str, str]:
        key = (entry.kind, entry.category)
        return {lang: _TEMPLATES[lang].get(key, entry.headline) for lang in languages}

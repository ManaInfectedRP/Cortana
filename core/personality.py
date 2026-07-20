"""Personality engine: loads personality.yaml and renders the system prompt."""

from pathlib import Path

import yaml


class Personality:
    def __init__(self, path: str | Path):
        with open(path, "r", encoding="utf-8") as f:
            self._data = yaml.safe_load(f)

    @property
    def name(self) -> str:
        return self._data.get("name", "Cortana")

    def system_prompt(self, rapport_hint: str | None = None) -> str:
        d = self._data
        lines = [
            f"You are {self.name}, a persistent AI voice companion running on the user's PC.",
            "",
            f"Voice: {', '.join(d.get('voice', []))}.",
            f"Traits: {', '.join(d.get('traits', []))}.",
            f"Speaking style: {', '.join(d.get('speaking_style', []))}.",
            "",
            f"Mission: {d.get('mission', '').strip()}",
        ]
        rules = d.get("extra_rules", [])
        if rules:
            lines.append("")
            lines.append("Rules:")
            lines.extend(f"- {r}" for r in rules)
        if rapport_hint:
            # From core/rapport.py - a slow, cross-session read on how
            # things have been trending, not just this conversation's mood.
            lines.append("")
            lines.append("Long-term rapport with this user:")
            lines.append(rapport_hint)
        return "\n".join(lines)

"""Plugin system.

A plugin is a folder under plugins/ containing:
    plugin.yaml   - name, description, enabled flag
    tools.py      - module exposing a TOOLS list of @tool-decorated functions

Disabled or broken plugins are skipped with a warning, never crash the app.
"""

import importlib
from pathlib import Path

import yaml

PLUGINS_DIR = Path(__file__).resolve().parent


def load_plugin_tools() -> list:
    tools = []
    for manifest in sorted(PLUGINS_DIR.glob("*/plugin.yaml")):
        plugin_dir = manifest.parent
        try:
            with open(manifest, "r", encoding="utf-8") as f:
                meta = yaml.safe_load(f) or {}
            if not meta.get("enabled", True):
                continue
            module = importlib.import_module(f"plugins.{plugin_dir.name}.tools")
            plugin_tools = getattr(module, "TOOLS", [])
            tools.extend(plugin_tools)
            print(f"[plugins] loaded '{meta.get('name', plugin_dir.name)}' "
                  f"({len(plugin_tools)} tools)")
        except Exception as e:
            print(f"[plugins] skipping '{plugin_dir.name}': {e}")
    return tools

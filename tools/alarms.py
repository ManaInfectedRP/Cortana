"""Alarm tools: set/list/cancel alarms, persisted to disk.

A daemon watcher thread (started by main.py) rings due alarms with beeps and
a Windows notification. Alarms only ring while Cortana is running.
"""

import asyncio
import datetime
import json
import threading
import uuid
from pathlib import Path

from claude_agent_sdk import tool

ALARMS_FILE = Path(__file__).resolve().parent.parent / "data" / "alarms.json"
_LOCK = threading.Lock()
TIME_FMT = "%Y-%m-%d %H:%M"


def _load() -> list[dict]:
    if not ALARMS_FILE.exists():
        return []
    try:
        return json.loads(ALARMS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def _save(alarms: list[dict]) -> None:
    ALARMS_FILE.parent.mkdir(parents=True, exist_ok=True)
    ALARMS_FILE.write_text(json.dumps(alarms, indent=2), encoding="utf-8")


@tool("set_alarm", "Set an alarm. 'when' must be an absolute time formatted "
      "exactly as 'YYYY-MM-DD HH:MM' (24-hour). Convert relative requests like "
      "'in 20 minutes' or 'tomorrow at 7' to absolute using the current time "
      "given in the conversation.", {"when": str, "label": str})
async def set_alarm(args: dict) -> dict:
    try:
        when = datetime.datetime.strptime(args["when"], TIME_FMT)
    except ValueError:
        return {"content": [{"type": "text", "text":
                "Invalid time format - use 'YYYY-MM-DD HH:MM' (24-hour)."}]}
    if when <= datetime.datetime.now():
        return {"content": [{"type": "text", "text":
                f"{args['when']} is in the past - alarm not set."}]}

    alarm = {
        "id": uuid.uuid4().hex[:6],
        "when": args["when"],
        "label": args.get("label", "Alarm"),
    }
    with _LOCK:
        alarms = _load()
        alarms.append(alarm)
        _save(alarms)
    return {"content": [{"type": "text", "text":
            f"Alarm '{alarm['label']}' set for {alarm['when']} "
            f"(id {alarm['id']}). Note: it only rings while Cortana is running."}]}


@tool("list_alarms", "List all pending alarms.", {})
async def list_alarms(args: dict) -> dict:
    with _LOCK:
        alarms = _load()
    if not alarms:
        return {"content": [{"type": "text", "text": "No alarms set."}]}
    lines = [f"{a['when']} - {a['label']} (id {a['id']})"
             for a in sorted(alarms, key=lambda a: a["when"])]
    return {"content": [{"type": "text", "text": "\n".join(lines)}]}


@tool("cancel_alarm", "Cancel a pending alarm by its id (use list_alarms to "
      "find it).", {"alarm_id": str})
async def cancel_alarm(args: dict) -> dict:
    with _LOCK:
        alarms = _load()
        remaining = [a for a in alarms if a["id"] != args["alarm_id"]]
        if len(remaining) == len(alarms):
            return {"content": [{"type": "text", "text":
                    f"No alarm with id {args['alarm_id']}."}]}
        _save(remaining)
    return {"content": [{"type": "text", "text": "Alarm cancelled."}]}


TOOLS = [set_alarm, list_alarms, cancel_alarm]


# ---------------------------------------------------------------- watcher ---

def _ring(label: str) -> None:
    try:
        from plyer import notification
        notification.notify(title="⏰ Cortana Alarm", message=label,
                            app_name="Cortana", timeout=15)
    except Exception:
        pass
    try:
        import winsound
        for _ in range(6):
            winsound.Beep(880, 250)
            winsound.Beep(1175, 350)
    except Exception:
        print("\a")
    print(f"\n⏰ ALARM: {label}")


def start_alarm_watcher(stop_event: threading.Event) -> None:
    """Start the daemon thread that rings due alarms."""

    def watch():
        while not stop_event.is_set():
            now = datetime.datetime.now()
            due = []
            with _LOCK:
                alarms = _load()
                keep = []
                for a in alarms:
                    try:
                        when = datetime.datetime.strptime(a["when"], TIME_FMT)
                    except ValueError:
                        continue  # drop malformed entries
                    (due if when <= now else keep).append(a)
                if due:
                    _save(keep)
            for a in due:
                threading.Thread(target=_ring, args=(a["label"],),
                                 daemon=True).start()
            stop_event.wait(5)

    threading.Thread(target=watch, daemon=True, name="alarm-watcher").start()

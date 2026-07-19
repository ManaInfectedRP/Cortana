"""Desktop tools: launch/close apps, clipboard, notifications."""

import asyncio
import subprocess

from claude_agent_sdk import tool


@tool("launch_app", "Launch an application or open a file on this PC. Accepts an "
      "executable name (e.g. 'notepad', 'chrome'), a full path, or a document path.",
      {"target": str})
async def launch_app(args: dict) -> dict:
    target = args["target"]

    def run():
        subprocess.Popen(f'start "" "{target}"', shell=True)

    await asyncio.to_thread(run)
    return {"content": [{"type": "text", "text": f"Launched {target}."}]}


@tool("close_app", "Close a running application by its process name (e.g. "
      "'notepad.exe'). Only use when the user explicitly asks to close it.",
      {"process_name": str})
async def close_app(args: dict) -> dict:
    name = args["process_name"]
    if not name.lower().endswith(".exe"):
        name += ".exe"
    result = await asyncio.to_thread(
        lambda: subprocess.run(["taskkill", "/IM", name],
                               capture_output=True, text=True)
    )
    if result.returncode == 0:
        return {"content": [{"type": "text", "text": f"Closed {name}."}]}
    return {"content": [{"type": "text",
                         "text": f"Could not close {name}: {result.stderr.strip()}"}]}


@tool("get_clipboard", "Read the current text content of the clipboard.", {})
async def get_clipboard(args: dict) -> dict:
    result = await asyncio.to_thread(
        lambda: subprocess.run(
            ["powershell", "-NoProfile", "-Command", "Get-Clipboard"],
            capture_output=True, text=True,
        )
    )
    return {"content": [{"type": "text", "text": result.stdout.strip() or "(empty)"}]}


@tool("set_clipboard", "Put text on the clipboard.", {"text": str})
async def set_clipboard(args: dict) -> dict:
    def run():
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", "Set-Clipboard -Value ([Console]::In.ReadToEnd())"],
            input=args["text"], text=True, capture_output=True,
        )

    await asyncio.to_thread(run)
    return {"content": [{"type": "text", "text": "Copied to clipboard."}]}


@tool("notify", "Show a Windows desktop notification.",
      {"title": str, "message": str})
async def notify(args: dict) -> dict:
    def run():
        try:
            from plyer import notification
            notification.notify(
                title=args["title"], message=args["message"],
                app_name="Cortana", timeout=6,
            )
            return "Notification shown."
        except Exception as e:
            return f"Notification failed: {e}"

    text = await asyncio.to_thread(run)
    return {"content": [{"type": "text", "text": text}]}


TOOLS = [launch_app, close_app, get_clipboard, set_clipboard, notify]

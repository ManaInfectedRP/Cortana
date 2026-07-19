"""Filesystem tools (write actions).

Reading and searching use Claude's built-in Read/Glob/Grep tools; these cover
creation, renaming and (recycle-bin) deletion.
"""

import asyncio
import subprocess
from pathlib import Path

from claude_agent_sdk import tool


@tool("create_document", "Create or overwrite a text file with the given "
      "content - lists, notes, drafts, anything the user wants saved. Use "
      "this whenever the user asks you to make/write/save a list, note, or "
      "document, not just describe one out loud. 'path' can be just a "
      "filename (e.g. 'shopping-list.txt') and it will be saved to the "
      "user's Desktop; give a full absolute path only if they name a "
      "specific location.", {"path": str, "content": str})
async def create_document(args: dict) -> dict:
    path = Path(args["path"])
    if not path.is_absolute():
        path = Path.home() / "Desktop" / path

    def run():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(args["content"], encoding="utf-8")

    await asyncio.to_thread(run)
    return {"content": [{"type": "text", "text": f"Wrote {path}."}]}


@tool("rename_file", "Rename or move a file or folder.",
      {"source": str, "destination": str})
async def rename_file(args: dict) -> dict:
    src, dst = Path(args["source"]), Path(args["destination"])
    if not src.exists():
        return {"content": [{"type": "text", "text": f"{src} does not exist."}]}
    await asyncio.to_thread(src.rename, dst)
    return {"content": [{"type": "text", "text": f"Moved {src} -> {dst}."}]}


@tool("delete_file", "Move a file to the Windows Recycle Bin. IMPORTANT: always "
      "ask the user for verbal confirmation first, then call with confirmed=true.",
      {"path": str, "confirmed": bool})
async def delete_file(args: dict) -> dict:
    if not args.get("confirmed"):
        return {"content": [{"type": "text", "text":
                "Not deleted - ask the user to confirm first, then retry with "
                "confirmed=true."}]}
    path = Path(args["path"])
    if not path.exists():
        return {"content": [{"type": "text", "text": f"{path} does not exist."}]}

    # recycle bin via VisualBasic FileIO so it's recoverable
    ps = (
        "Add-Type -AssemblyName Microsoft.VisualBasic; "
        f"[Microsoft.VisualBasic.FileIO.FileSystem]::DeleteFile('{path}', "
        "'OnlyErrorDialogs', 'SendToRecycleBin')"
    )
    result = await asyncio.to_thread(
        lambda: subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                               capture_output=True, text=True)
    )
    if result.returncode == 0:
        return {"content": [{"type": "text",
                             "text": f"Moved {path} to the Recycle Bin."}]}
    return {"content": [{"type": "text",
                         "text": f"Delete failed: {result.stderr.strip()}"}]}


TOOLS = [create_document, rename_file, delete_file]

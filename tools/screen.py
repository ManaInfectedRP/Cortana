"""Screen awareness: capture the screen so Claude can look at it.

Claude's built-in Read tool understands images, so the flow is:
capture_screen -> saved PNG -> Read the returned path -> Claude sees the screen.
Covers the design doc's Screen Awareness and Vision modules
("What error is on my screen?", "What does this graph mean?").
"""

import asyncio
import datetime
from pathlib import Path

from claude_agent_sdk import tool

SHOT_DIR = Path(__file__).resolve().parent.parent / "data" / "screenshots"


@tool("capture_screen", "Take a screenshot of the user's screen and save it as a "
      "PNG. Then use the Read tool on the returned path to actually see it. Only "
      "capture when the user asks about their screen.", {})
async def capture_screen(args: dict) -> dict:
    def run() -> str:
        from PIL import ImageGrab

        SHOT_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = SHOT_DIR / f"screen_{stamp}.png"
        img = ImageGrab.grab()
        # keep it under Read's size limits
        if img.width > 1920:
            ratio = 1920 / img.width
            img = img.resize((1920, int(img.height * ratio)))
        img.save(path)
        return str(path)

    path = await asyncio.to_thread(run)
    return {"content": [{"type": "text", "text":
            f"Screenshot saved to {path}. Use the Read tool on that path to view it."}]}


TOOLS = [capture_screen]

"""Browser tools. Web search/summarize use Claude's built-in WebSearch/WebFetch;
these open things in the user's actual browser."""

import asyncio
import urllib.parse
import webbrowser

from claude_agent_sdk import tool


@tool("open_url", "Open a URL in the user's default web browser.", {"url": str})
async def open_url(args: dict) -> dict:
    await asyncio.to_thread(webbrowser.open, args["url"])
    return {"content": [{"type": "text", "text": f"Opened {args['url']}."}]}


@tool("open_search", "Open a web search for a query in the user's browser (use "
      "when they want to *see* results; use WebSearch to research silently).",
      {"query": str})
async def open_search(args: dict) -> dict:
    url = "https://www.google.com/search?q=" + urllib.parse.quote(args["query"])
    await asyncio.to_thread(webbrowser.open, url)
    return {"content": [{"type": "text", "text": f"Opened search for {args['query']}."}]}


TOOLS = [open_url, open_search]

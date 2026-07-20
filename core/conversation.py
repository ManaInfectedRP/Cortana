"""Conversation manager — the brain.

Talks to Claude through the Claude Agent SDK, which authenticates via your
existing Claude Code login (Pro subscription). No API key required.

Flow per turn:
    transcription -> emotion update -> memory retrieval -> build prompt
    -> Claude (+ tool calls via the MCP tool manager) -> response
"""

import asyncio

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    TextBlock,
)

from core.emotion import EmotionTracker
from core.memory import MemoryManager
from core.personality import Personality
from core.prompt import build_turn_prompt
from core.rapport import Rapport


class ConversationManager:
    def __init__(
        self,
        personality: Personality,
        memory: MemoryManager,
        model: str | None = None,
        max_turns: int = 12,
        tool_manager=None,
        builtin_tools: list[str] | None = None,
        emotion_enabled: bool = True,
        emotion_device: str = "cpu",
    ):
        self.personality = personality
        self.memory = memory
        self.emotion = EmotionTracker(enabled=emotion_enabled, device=emotion_device)
        self.rapport = Rapport()

        allowed = list(builtin_tools or [])
        mcp_servers = {}
        if tool_manager is not None:
            mcp_servers = tool_manager.mcp_servers()
            allowed.extend(tool_manager.allowed_tools())

        self._options = ClaudeAgentOptions(
            system_prompt=personality.system_prompt(self.rapport.describe()),
            model=model,
            max_turns=max_turns,
            mcp_servers=mcp_servers,
            allowed_tools=allowed,
        )
        self._client: ClaudeSDKClient | None = None

    async def start(self) -> None:
        self._client = ClaudeSDKClient(options=self._options)
        await self._client.connect()

    async def stop(self) -> None:
        if self._client:
            await self._client.disconnect()
            self._client = None
        # Fold this session's average mood into the long-term signal so the
        # next launch's system prompt reflects it - skipped for a session
        # where nothing was actually said.
        if self.emotion.has_data:
            self.rapport.record_session(*self.emotion.session_averages())

    async def ask(self, user_text: str) -> str:
        """Send one user utterance, return Cortana's spoken reply."""
        assert self._client is not None, "call start() first"

        # The classifier is a blocking CPU call (~50-300ms) - keep it off
        # the event loop like the other model calls in this codebase.
        await asyncio.to_thread(self.emotion.update, user_text)
        memories = self.memory.recall(user_text)
        prompt = build_turn_prompt(user_text, memories, self.emotion.describe())

        await self._client.query(prompt)

        chunks: list[str] = []
        async for message in self._client.receive_response():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        chunks.append(block.text)

        reply = " ".join(c.strip() for c in chunks if c.strip()).strip()
        if not reply:
            reply = "Sorry, I didn't get a response. Try again?"

        self.memory.remember_exchange(user_text, reply)
        return reply

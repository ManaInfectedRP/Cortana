"""Conversation manager — the brain.

Talks to Claude through the Claude Agent SDK, which authenticates via your
existing Claude Code login (Pro subscription). No API key required.

Flow per turn:
    transcription -> emotion update -> memory retrieval -> build prompt
    -> Claude (+ tool calls via the MCP tool manager) -> response
"""

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


class ConversationManager:
    def __init__(
        self,
        personality: Personality,
        memory: MemoryManager,
        model: str | None = None,
        max_turns: int = 12,
        tool_manager=None,
        builtin_tools: list[str] | None = None,
    ):
        self.personality = personality
        self.memory = memory
        self.emotion = EmotionTracker()

        allowed = list(builtin_tools or [])
        mcp_servers = {}
        if tool_manager is not None:
            mcp_servers = tool_manager.mcp_servers()
            allowed.extend(tool_manager.allowed_tools())

        self._options = ClaudeAgentOptions(
            system_prompt=personality.system_prompt(),
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

    async def ask(self, user_text: str) -> str:
        """Send one user utterance, return Cortana's spoken reply."""
        assert self._client is not None, "call start() first"

        self.emotion.update(user_text)
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

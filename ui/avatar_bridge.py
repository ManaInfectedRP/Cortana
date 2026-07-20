"""WebSocket bridge broadcasting Cortana's state + mouth amplitude to a
connected avatar renderer (Unity/Unreal/Godot - see AVATAR_3D.md and the
Unity-side CortanaWebSocketClient.cs in the Unity project).

Wire protocol - one JSON object per message:
    {"state": "idle" | "listening" | "thinking" | "speaking"}
    {"state": "speaking", "mouth": 0.0-1.0}   # sent repeatedly while talking
    {"emotion": "happy"|"angry"|"sad"|"relaxed"|"surprised"|"neutral"|""}
        # core/emotion.py's read on the user's mood; "" clears it back to
        # the current state's default expression (see FacialExpression.cs -
        # empty string rather than JSON null, since Unity's JsonUtility
        # doesn't reliably round-trip null for string fields)
    {"reaction": "gratitude"}
        # one-shot avatar voice reaction - see core/emotion.py's REACTIONS
        # and Unity's AvatarSfx.cs/CortanaAnimatorDriver.TriggerReaction().
        # Fires once per detection, not repeated while the mood is active.

Runs as a local-only server (ws://localhost:8765 by default). If no avatar
app is connected, broadcasts are cheap no-ops - Cortana works identically
with or without a listener.
"""

import asyncio
import json
import threading

try:
    import websockets
except ImportError:
    websockets = None

_clients: set = set()
_loop: asyncio.AbstractEventLoop | None = None
_thread: threading.Thread | None = None


async def _handler(websocket):
    _clients.add(websocket)
    try:
        async for _ in websocket:
            pass  # the avatar app doesn't send anything back (yet)
    finally:
        _clients.discard(websocket)


async def _broadcast(payload: dict) -> None:
    if not _clients:
        return
    message = json.dumps(payload)
    dead = []
    for ws in list(_clients):
        try:
            await ws.send(message)
        except Exception:
            dead.append(ws)
    for ws in dead:
        _clients.discard(ws)


def _run_server(port: int) -> None:
    global _loop

    async def main():
        async with websockets.serve(_handler, "localhost", port):
            await asyncio.Future()  # run forever

    _loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_loop)
    try:
        _loop.run_until_complete(main())
    except Exception as e:
        print(f"[avatar] bridge stopped: {e}")


def start(port: int = 8765) -> None:
    """Start the bridge in a background daemon thread. Safe to call even if
    no avatar app ever connects."""
    global _thread
    if websockets is None:
        print("[avatar] 'websockets' package not available - avatar bridge disabled")
        return
    if _thread is not None:
        return
    _thread = threading.Thread(
        target=_run_server, args=(port,), daemon=True, name="avatar-bridge"
    )
    _thread.start()
    print(f"[avatar] bridge listening on ws://localhost:{port} "
          "(no-op until a Unity/Unreal/Godot avatar connects)")


def set_state(state: str) -> None:
    """Push a state change to any connected avatar app."""
    if _loop is None:
        return
    asyncio.run_coroutine_threadsafe(_broadcast({"state": state}), _loop)


def set_emotion(name: str | None) -> None:
    """Push a facial-expression override to any connected avatar app, or
    None to clear it (falls back to the current state's default expression).
    """
    if _loop is None:
        return
    asyncio.run_coroutine_threadsafe(_broadcast({"emotion": name or ""}), _loop)


def trigger_reaction(name: str) -> None:
    """Push a one-shot avatar voice reaction (e.g. "gratitude") to any
    connected avatar app. See core/emotion.py's REACTIONS."""
    if _loop is None:
        return
    asyncio.run_coroutine_threadsafe(_broadcast({"reaction": name}), _loop)


def send_mouth_amplitude(amplitude: float) -> None:
    """Push a mouth-openness sample (0-1) while Cortana is speaking."""
    if _loop is None:
        return
    asyncio.run_coroutine_threadsafe(
        _broadcast({"state": "speaking", "mouth": float(amplitude)}), _loop
    )

"""ECHO — a persistent AI companion inspired by Halo's Cortana.

Usage:
    python main.py            # full voice mode (wake word -> STT -> Claude -> TTS)
    python main.py --text     # text mode (type instead of talking; no audio models)
    python main.py --push     # push-to-talk: press Enter to speak, no wake word
    python main.py --no-ui    # disable the floating orb
"""

import argparse
import asyncio
import os
import subprocess
import sys
import threading
from pathlib import Path

import yaml

ROOT = Path(__file__).parent

# set on shutdown so blocking audio loops in worker threads exit promptly
SHUTDOWN = threading.Event()

from core.conversation import ConversationManager
from core.memory import MemoryManager
from core.personality import Personality


def load_settings() -> dict:
    with open(ROOT / "config" / "settings.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_conversation(settings: dict) -> ConversationManager:
    personality = Personality(ROOT / "config" / "personality.yaml")
    memory = MemoryManager(
        ROOT / settings["memory"]["dir"], top_k=settings["memory"]["top_k"]
    )

    tool_manager = None
    if settings.get("tools", {}).get("enabled", True):
        from tools.manager import ToolManager

        tool_manager = ToolManager(
            plugins_enabled=settings.get("plugins", {}).get("enabled", True)
        )
        print(f"[init] {len(tool_manager.tools)} tools registered")

    builtin = list(settings["claude"].get("builtin_tools", []))
    if settings.get("tools", {}).get("allow_bash", False):
        builtin.append("Bash")

    emotion_cfg = settings.get("emotion", {})

    return ConversationManager(
        personality, memory,
        model=settings["claude"]["model"],
        max_turns=settings["claude"]["max_turns"],
        tool_manager=tool_manager,
        builtin_tools=builtin,
        emotion_enabled=emotion_cfg.get("enabled", True),
        emotion_device=emotion_cfg.get("device", "cpu"),
    )


async def text_loop(convo: ConversationManager):
    print("Text mode. Type your message (or 'quit').\n")
    while True:
        try:
            user_text = await asyncio.to_thread(input, "You: ")
        except (EOFError, KeyboardInterrupt):
            break
        user_text = user_text.strip()
        if not user_text or user_text.lower() in ("quit", "exit"):
            break
        reply = await convo.ask(user_text)
        print(f"Cortana: {reply}\n")


async def voice_loop(convo: ConversationManager, settings: dict,
                     push_to_talk: bool, set_state):
    from ui import avatar_bridge
    from voice import greetings
    from voice.audio import record_utterance, select_input_device
    from voice.tts import create_tts
    from voice.whisper import SpeechRecognizer

    audio_cfg = settings["audio"]
    mic = select_input_device(audio_cfg.get("input_device"))
    print(f"[init] microphone: {mic}")
    stt_cfg = settings["stt"]
    tts_cfg = settings["tts"]

    print("[init] loading speech recognizer...")
    stt = SpeechRecognizer(
        model_size=stt_cfg["model"], device=stt_cfg["device"],
        language=stt_cfg["language"],
    )
    print(f"[init] whisper '{stt_cfg['model']}' on {stt.device}")

    print("[init] loading TTS...")
    tts = create_tts(
        tts_cfg["engine"], device=tts_cfg["device"],
        speaker=tts_cfg["speaker"], language=tts_cfg["language"],
        speaker_wav=tts_cfg.get("speaker_wav"),
    )

    listener = None
    if not push_to_talk:
        from voice.wakeword import WakeWordListener, create_wakeword_listener

        ww_cfg = settings["wake_word"]
        print("[init] loading wake word model...")
        try:
            listener = create_wakeword_listener(ww_cfg)
        except Exception as e:
            print(f"[init] configured wake word unavailable ({e}); "
                  "falling back to 'hey_jarvis'")
            listener = WakeWordListener("hey_jarvis", ww_cfg.get("threshold", 0.5))
        print(f"[init] wake word: '{listener.model_name}'")

    print("\nCortana is online.")
    set_state("speaking")
    if await asyncio.to_thread(greetings.play_startup):
        print("[greeting] played startup line")

    try:
        while True:
            set_state("idle")
            if listener:
                print(f"[listening for wake word: '{listener.model_name}']")
                woke = await asyncio.to_thread(
                    listener.wait_for_wake, audio_cfg["sample_rate"], SHUTDOWN
                )
                if not woke:
                    return
                print("[wake word detected — speak now]")
            else:
                await asyncio.to_thread(input, "\n[press Enter, then speak]")

            set_state("listening")
            audio = await asyncio.to_thread(
                lambda: record_utterance(
                    sample_rate=audio_cfg["sample_rate"],
                    max_seconds=audio_cfg["max_utterance_s"],
                    silence_seconds=audio_cfg["silence_s"],
                    stop_event=SHUTDOWN,
                    threshold_override=audio_cfg.get("threshold"),
                )
            )
            if SHUTDOWN.is_set():
                return
            if audio is None:
                print("[no speech detected]")
                continue

            set_state("thinking")
            user_text = await asyncio.to_thread(stt.transcribe, audio)
            if not user_text:
                print("[could not transcribe]")
                continue
            print(f"You: {user_text}")

            reply = await convo.ask(user_text)
            print(f"Cortana: {reply}")
            avatar_bridge.set_emotion(convo.emotion.expression())
            reaction = convo.emotion.triggered_reaction()
            if reaction:
                avatar_bridge.trigger_reaction(reaction)

            set_state("speaking")
            try:
                await asyncio.to_thread(tts.speak, reply)
            except Exception as e:
                print(f"[tts] speech failed ({type(e).__name__}: {e}) - "
                      "reply shown above in text")
            if listener:
                print(f"[say '{listener.model_name}' again for the next question]")
    finally:
        # Runs on a normal SHUTDOWN-triggered return AND on Ctrl+C (which
        # raises through whichever await was active) - either way she gets
        # to say goodbye.
        set_state("speaking")
        if await asyncio.to_thread(greetings.play_shutdown):
            print("[greeting] played shutdown line")


def _avatar_will_launch(settings: dict) -> bool:
    """True if run_assistant will actually spawn the Unity avatar process -
    used to decide whether the orb should also show (avoid two competing
    visual presences at once, but keep the orb as an automatic fallback if
    the avatar is disabled or hasn't been built yet)."""
    avatar_cfg = settings.get("avatar", {})
    if not avatar_cfg.get("enabled", True):
        return False
    exe_path = avatar_cfg.get("exe_path")
    return bool(exe_path and Path(exe_path).exists())


async def run_assistant(args, settings: dict, set_state=lambda s: None):
    convo = build_conversation(settings)
    if settings.get("tools", {}).get("enabled", True):
        from tools.alarms import start_alarm_watcher

        start_alarm_watcher(SHUTDOWN)

    avatar_process = None
    avatar_enabled = settings.get("avatar", {}).get("enabled", True) and not args.text
    if avatar_enabled:
        from ui import avatar_bridge

        avatar_bridge.start(settings.get("avatar", {}).get("port", 8765))
        _orb_set_state = set_state

        def set_state(state: str) -> None:  # noqa: F811 - intentional shadow
            _orb_set_state(state)
            avatar_bridge.set_state(state)

    # Claude connection first - it's the core dependency. Launching Unity's
    # heavy startup (D3D11 init, shader compile, asset load) at the same
    # moment as this handshake caused the SDK's "initialize" control request
    # to occasionally time out under simultaneous CPU/disk contention.
    await convo.start()

    if avatar_enabled:
        if _avatar_will_launch(settings):
            exe_path = settings["avatar"]["exe_path"]
            avatar_process = subprocess.Popen([exe_path])
            print(f"[avatar] launched {Path(exe_path).name}")
        elif settings.get("avatar", {}).get("exe_path"):
            print("[avatar] exe_path set but not found at "
                  f"{settings['avatar']['exe_path']} - build it in Unity "
                  "first (File > Build Settings > Build), or clear "
                  "avatar.exe_path in settings.yaml")
    try:
        if args.text:
            await text_loop(convo)
        else:
            await voice_loop(convo, settings, push_to_talk=args.push,
                             set_state=set_state)
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        SHUTDOWN.set()  # unblock any audio threads so the process can exit
        if avatar_process is not None:
            avatar_process.terminate()
        try:
            await asyncio.wait_for(convo.stop(), timeout=5)
        except Exception:
            pass


def main():
    parser = argparse.ArgumentParser(description="ECHO / Cortana voice companion")
    parser.add_argument("--text", action="store_true", help="text mode, no audio")
    parser.add_argument("--push", action="store_true", help="push-to-talk mode")
    parser.add_argument("--no-ui", action="store_true", help="disable the orb")
    args = parser.parse_args()

    settings = load_settings()
    ui_enabled = (
        settings.get("ui", {}).get("enabled", True)
        and not args.no_ui and not args.text
        and not _avatar_will_launch(settings)  # avoid orb + avatar both showing
    )

    try:
        if ui_enabled:
            try:
                from ui.overlay import run_with_orb
            except Exception as e:
                print(f"[ui] orb unavailable ({e}); running headless")
                ui_enabled = False
            else:
                run_with_orb(
                    lambda set_state: run_assistant(args, settings, set_state),
                    shutdown_event=SHUTDOWN,
                )
        if not ui_enabled:
            asyncio.run(run_assistant(args, settings))
    except KeyboardInterrupt:
        pass
    except Exception:
        # Without this, any startup/runtime error (bad config, a failed
        # model load, ...) would silently vanish - the bare os._exit(0)
        # below runs regardless and kills the process before Python ever
        # gets a chance to print an uncaught exception's traceback.
        import traceback
        traceback.print_exc()
    finally:
        SHUTDOWN.set()
        print("\nCortana signing off.")
        sys.stdout.flush()
        # hard-exit: a blocked input()/audio thread must never hold the
        # process hostage after the user asked to quit
        os._exit(0)


if __name__ == "__main__":
    main()

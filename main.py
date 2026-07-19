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

    return ConversationManager(
        personality, memory,
        model=settings["claude"]["model"],
        max_turns=settings["claude"]["max_turns"],
        tool_manager=tool_manager,
        builtin_tools=builtin,
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

        set_state("speaking")
        try:
            await asyncio.to_thread(tts.speak, reply)
        except Exception as e:
            print(f"[tts] speech failed ({type(e).__name__}: {e}) - "
                  "reply shown above in text")
        if listener:
            print(f"[say '{listener.model_name}' again for the next question]")


async def run_assistant(args, settings: dict, set_state=lambda s: None):
    convo = build_conversation(settings)
    if settings.get("tools", {}).get("enabled", True):
        from tools.alarms import start_alarm_watcher

        start_alarm_watcher(SHUTDOWN)
    await convo.start()
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
                    lambda set_state: run_assistant(args, settings, set_state)
                )
        if not ui_enabled:
            asyncio.run(run_assistant(args, settings))
    except KeyboardInterrupt:
        pass
    finally:
        SHUTDOWN.set()
        print("\nCortana signing off.")
        sys.stdout.flush()
        # hard-exit: a blocked input()/audio thread must never hold the
        # process hostage after the user asked to quit
        os._exit(0)


if __name__ == "__main__":
    main()

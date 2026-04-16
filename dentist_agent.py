import argparse
import json
import os
from datetime import datetime, UTC
from pathlib import Path

from app.agent import DentistAIAgent


def _supports_color() -> bool:
    term = os.getenv("TERM", "")
    no_color = os.getenv("NO_COLOR")
    return bool(term) and term.lower() != "dumb" and not no_color


def _colorize(text: str, code: str, use_color: bool) -> str:
    if not use_color:
        return text
    return f"\033[{code}m{text}\033[0m"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dentist_agent.py",
        description="CLI chatbot assistant for a dental clinic.",
    )
    parser.add_argument(
        "-m",
        "--message",
        help="Run in one-shot mode with a single user message.",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colored terminal output.",
    )
    parser.add_argument(
        "--export",
        help="Export chat transcript to a JSON file.",
    )
    parser.add_argument(
        "--export-dir",
        help="Export transcript to this directory using an auto-generated filename.",
    )
    return parser


def _resolve_export_path(export_path: str | None, export_dir: str | None) -> str | None:
    if export_path:
        return export_path
    if not export_dir:
        return None

    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    filename = f"cli_transcript_{ts}.json"
    return str(Path(export_dir) / filename)


def _save_transcript(path: str, messages: list[dict[str, str]]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "exported_at": datetime.now(UTC).isoformat(),
        "message_count": len(messages),
        "messages": messages,
    }
    with output.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def run_chat(
    message: str | None = None,
    use_color: bool = True,
    export_path: str | None = None,
    export_dir: str | None = None,
) -> None:
    agent = DentistAIAgent()
    transcript: list[dict[str, str]] = []
    resolved_export_path = _resolve_export_path(export_path, export_dir)

    if message is not None:
        transcript.append({"role": "user", "text": message})
        reply = agent.respond(message)
        transcript.append({"role": "assistant", "text": reply})
        bot_prefix = _colorize("Bot", "36", use_color)
        print(f"{bot_prefix}: {reply}")
        if resolved_export_path:
            _save_transcript(resolved_export_path, transcript)
            print(f"Transcript saved to: {resolved_export_path}")
        return

    welcome = _colorize("Dentist AI Agent is ready. Type 'exit' to quit.", "32", use_color)
    print(f"{welcome}\n")

    while True:
        you_prefix = _colorize("You", "34", use_color)
        user_input = input(f"{you_prefix}: ").strip()
        if user_input.lower() in {"exit", "quit", "bye"}:
            bot_prefix = _colorize("Bot", "36", use_color)
            print(f"{bot_prefix}: Thanks for chatting. Take care of your smile! 😄")
            break

        transcript.append({"role": "user", "text": user_input})
        reply = agent.respond(user_input)
        transcript.append({"role": "assistant", "text": reply})
        bot_prefix = _colorize("Bot", "36", use_color)
        print(f"{bot_prefix}: {reply}\n")

    if resolved_export_path:
        _save_transcript(resolved_export_path, transcript)
        print(f"Transcript saved to: {resolved_export_path}")


if __name__ == "__main__":
    args = _build_parser().parse_args()
    run_chat(
        message=args.message,
        use_color=(_supports_color() and not args.no_color),
        export_path=args.export,
        export_dir=args.export_dir,
    )

import argparse
import os

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
    return parser


def run_chat(message: str | None = None, use_color: bool = True) -> None:
    agent = DentistAIAgent()

    if message is not None:
        bot_prefix = _colorize("Bot", "36", use_color)
        print(f"{bot_prefix}: {agent.respond(message)}")
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

        reply = agent.respond(user_input)
        bot_prefix = _colorize("Bot", "36", use_color)
        print(f"{bot_prefix}: {reply}\n")


if __name__ == "__main__":
    args = _build_parser().parse_args()
    run_chat(message=args.message, use_color=(_supports_color() and not args.no_color))

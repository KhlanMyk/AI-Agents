import argparse

from app.agent import DentistAIAgent


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
    return parser


def run_chat(message: str | None = None) -> None:
    agent = DentistAIAgent()

    if message is not None:
        print(f"Bot: {agent.respond(message)}")
        return

    print("Dentist AI Agent is ready. Type 'exit' to quit.\n")

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in {"exit", "quit", "bye"}:
            print("Bot: Thanks for chatting. Take care of your smile! 😄")
            break

        reply = agent.respond(user_input)
        print(f"Bot: {reply}\n")


if __name__ == "__main__":
    args = _build_parser().parse_args()
    run_chat(message=args.message)

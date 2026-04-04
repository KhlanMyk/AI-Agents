from app.agent import DentistAIAgent


def run_chat() -> None:
    agent = DentistAIAgent()
    print("Dentist AI Agent is ready. Type 'exit' to quit.\n")

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in {"exit", "quit", "bye"}:
            print("Bot: Thanks for chatting. Take care of your smile! 😄")
            break

        reply = agent.respond(user_input)
        print(f"Bot: {reply}\n")


if __name__ == "__main__":
    run_chat()

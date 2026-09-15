from intent import parse_event_request
from main_event_pipeline import run_pipeline


def main():
    print("=== EventScout ===")
    print("Tell me what kind of event you're looking for, and where.")
    print("Example: 'Find me a music event in Utrecht'\n")

    while True:
        user_input = input("You: ").strip()

        if user_input.lower() in ("quit", "exit"):
            print("Goodbye!")
            break

        if not user_input:
            continue

        request = parse_event_request(user_input)

        if not request:
            print("Sorry, I couldn't understand that. Try again.\n")
            continue

        print(
            f"Got it — searching for '{request.event_type}' events in {request.location}...\n"
        )
        run_pipeline(request.location, request.event_type)
        print()


if __name__ == "__main__":
    main()

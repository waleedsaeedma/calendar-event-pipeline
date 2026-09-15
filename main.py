from dotenv import load_dotenv
from openai import OpenAI
import os

load_dotenv()
client = OpenAI(api_key=os.getenv("API_KEY"))

from pipeline import process_calendar_request


def main():
    print("=== Calendar Event Pipeline ===")
    print("Type a sentence describing an event (or 'quit' to exit).\n")

    while True:
        user_input = input("Your input: ").strip()

        if user_input.lower() in ("quit", "exit"):
            print("Goodbye!")
            break

        if not user_input:
            continue

        result = process_calendar_request(user_input)

        if result:
            print(f"\nConfirmation: {result.confirmation_message}")
            if result.calendar_link:
                print(f"Calendar Link: {result.calendar_link}")
        else:
            print("\nThis doesn't appear to be a calendar event request.")

        print()  # spacing between runs


if __name__ == "__main__":
    main()

import os

from dotenv import load_dotenv
from openai import OpenAI
from models import EventRequest
from datetime import datetime

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")


def parse_event_request(user_input: str) -> EventRequest | None:
    """Extract city, event type, and requested date period."""

    today = datetime.now()

    date_context = (
        f"Today is {today.strftime('%A, %B %d, %Y')}."
    )

    try:
        completion = client.beta.chat.completions.parse(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"{date_context}\n\n"
                        "Extract the city, event type, and requested date "
                        "period from the user's request.\n\n"
                        "Return start_date and end_date in YYYY-MM-DD format.\n"
                        "Use today's date as the reference for relative dates.\n\n"
                        "Examples:\n"
                        "- this weekend = the upcoming Saturday and Sunday\n"
                        "- next week = the next Monday through Sunday\n"
                        "- upcoming week = the next 7 days starting today\n"
                        "- next month = the next calendar month\n"
                        "- from 12 October to 30 October = October 12 through October 30\n\n"
                        "If no date period is specified, return null for both dates."
                    ),
                },
                {
                    "role": "user",
                    "content": user_input,
                },
            ],
            response_format=EventRequest,
        )
    except Exception as e:
        print(f"Could not understand the request: {e}")
        return None

    return completion.choices[0].message.parsed

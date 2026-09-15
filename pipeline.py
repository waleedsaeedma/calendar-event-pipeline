import os
import logging
from datetime import datetime

from dotenv import load_dotenv
from openai import OpenAI

from models import EventExtraction, EventDetails, EventConfirmation

# --------------------------------------------------------------
# Setup
# --------------------------------------------------------------

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.7"))


# --------------------------------------------------------------
# Step 1: Extract - is this even a calendar event?
# --------------------------------------------------------------


def extract_event_info(user_input: str) -> EventExtraction | None:
    logger.info("Starting event extraction analysis")

    today = datetime.now()
    date_context = f"Today is {today.strftime('%A, %B %d, %Y')}."

    try:
        completion = client.beta.chat.completions.parse(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": f"{date_context} Analyze if the text describes a calendar event.",
                },
                {"role": "user", "content": user_input},
            ],
            response_format=EventExtraction,
        )
    except Exception as e:
        logger.error(f"OpenAI call failed during extraction: {e}")
        return None

    result = completion.choices[0].message.parsed
    logger.info(
        f"Extraction complete - Is calendar event: {result.is_calendar_event}, "
        f"Confidence: {result.confidence_score:.2f}"
    )
    return result


# --------------------------------------------------------------
# Step 2: Parse specific event details
# --------------------------------------------------------------


def parse_event_details(description: str) -> EventDetails | None:
    logger.info("Starting event details parsing")

    today = datetime.now()
    date_context = f"Today is {today.strftime('%A, %B %d, %Y')}."

    try:
        completion = client.beta.chat.completions.parse(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"{date_context} Extract detailed event information. "
                        "When dates reference 'next Tuesday' or similar relative "
                        "dates, use this current date as reference."
                    ),
                },
                {"role": "user", "content": description},
            ],
            response_format=EventDetails,
        )
    except Exception as e:
        logger.error(f"OpenAI call failed during detail parsing: {e}")
        return None

    result = completion.choices[0].message.parsed
    logger.info(
        f"Parsed event details - Name: {result.name}, Date: {result.date}, "
        f"Duration: {result.duration_minutes}min"
    )
    return result


# --------------------------------------------------------------
# Step 3: Generate confirmation message
# --------------------------------------------------------------


def generate_confirmation(event_details: EventDetails) -> EventConfirmation | None:
    logger.info("Generating confirmation message")

    try:
        completion = client.beta.chat.completions.parse(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "Generate a natural confirmation message for the event.",
                },
                {"role": "user", "content": str(event_details.model_dump())},
            ],
            response_format=EventConfirmation,
        )
    except Exception as e:
        logger.error(f"OpenAI call failed during confirmation generation: {e}")
        return None

    result = completion.choices[0].message.parsed
    logger.info("Confirmation message generated successfully")
    return result


# --------------------------------------------------------------
# Orchestrator: chains the 3 steps together with a gate
# --------------------------------------------------------------


def process_calendar_request(user_input: str) -> EventConfirmation | None:
    logger.info("Processing calendar request")

    initial_extraction = extract_event_info(user_input)
    if initial_extraction is None:
        return None

    # Gate check
    if (
        not initial_extraction.is_calendar_event
        or initial_extraction.confidence_score < CONFIDENCE_THRESHOLD
    ):
        logger.warning(
            f"Gate check failed - is_calendar_event: {initial_extraction.is_calendar_event}, "
            f"confidence: {initial_extraction.confidence_score:.2f}"
        )
        return None

    logger.info("Gate check passed, proceeding with event processing")

    event_details = parse_event_details(initial_extraction.description)
    if event_details is None:
        return None

    confirmation = generate_confirmation(event_details)
    return confirmation


if __name__ == "__main__":
    test_input = "Let's schedule a 1h team meeting next Tuesday at 2pm with Alice and Bob to discuss the project roadmap."
    result = process_calendar_request(test_input)

    if result:
        print(f"Confirmation: {result.confirmation_message}")
        if result.calendar_link:
            print(f"Calendar Link: {result.calendar_link}")
    else:
        print("This doesn't appear to be a calendar event request.")

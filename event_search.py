import json
import logging
import os
from datetime import datetime

from dotenv import load_dotenv
from openai import OpenAI
from tavily import TavilyClient

from models import EventCandidate


load_dotenv()


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)


tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

MODEL = os.getenv(
    "OPENAI_MODEL",
    "gpt-4o",
)


def search_music_events(
    location: str = "Utrecht",
    event_type: str = "music",
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict]:
    """Searches the web for pages likely to contain upcoming events."""

    if start_date and end_date:
        query = (
            f"{event_type} events {location} "
            f"from {start_date} to {end_date}"
        )
    elif start_date:
        query = (
            f"upcoming {event_type} events {location} "
            f"from {start_date}"
        )
    else:
        query = f"upcoming {event_type} events {location} 2026"

    logger.info(
        "Searching for: %s",
        query,
    )

    try:
        response = tavily_client.search(
            query=query,
            search_depth="advanced",
            max_results=5,
        )

    except Exception as e:
        logger.error(
            "Tavily search failed: %s",
            e,
        )

        return []

    results = response.get(
        "results",
        [],
    )

    logger.info(
        "Found %d raw results",
        len(results),
    )

    return results


def fetch_page_content(
    urls: list[str],
) -> dict[str, str]:
    """Fetches full page content."""

    logger.info(
        "Fetching full content for %d pages",
        len(urls),
    )

    try:
        response = tavily_client.extract(urls=urls)

    except Exception as e:
        logger.error(
            "Tavily extract failed: %s",
            e,
        )

        return {}

    content_by_url = {}

    for item in response.get(
        "results",
        [],
    ):
        url = item.get("url")

        if not url:
            continue

        content_by_url[url] = item.get(
            "raw_content",
            "",
        )

    logger.info(
        "Successfully extracted content from %d pages",
        len(content_by_url),
    )

    return content_by_url


def extract_events_from_content(
    url: str,
    content: str,
    event_type: str = "music",
) -> list[EventCandidate]:
    """Uses OpenAI to extract structured event data."""

    logger.info(
        "Extracting events from: %s",
        url,
    )

    trimmed_content = content[:12000]

    try:
        completion = openai_client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"Extract a list of {event_type} events "
                        "from this page content.\n\n"
                        "Only include events with a clearly stated "
                        "specific date.\n\n"
                        f"Only include events that genuinely match "
                        f"the requested type '{event_type}'.\n\n"
                        "Return ONLY a JSON array.\n\n"
                        "Each object must contain these keys:\n"
                        "name, date, duration_minutes, venue, price, "
                        "description, is_relevant_event, "
                        "source_url, event_url\n\n"
                        "date must be ISO 8601 or null.\n\n"
                        "duration_minutes must contain the duration "
                        "in minutes only when the page clearly states "
                        "the duration. Otherwise use null. "
                        "Never guess.\n\n"
                        "price must be the ticket price in euros if "
                        "clearly stated. Use 0 for free events. "
                        "Use null when unknown. Never guess.\n\n"
                        "description should be a short useful summary "
                        "of the event when available. "
                        "Use null when unavailable.\n\n"
                        "event_url must be the direct URL to the "
                        "specific event or ticket page if clearly "
                        "available in the page content. "
                        "Otherwise use null.\n\n"
                        "NEVER invent URLs.\n\n"
                        f"Use '{url}' as source_url."
                    ),
                },
                {
                    "role": "user",
                    "content": trimmed_content,
                },
            ],
        )

    except Exception as e:
        logger.error(
            "OpenAI extraction failed for %s: %s",
            url,
            e,
        )

        return []

    raw_text = completion.choices[0].message.content.strip()

    raw_text = (
        raw_text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    )

    try:
        raw_events = json.loads(raw_text)

    except json.JSONDecodeError:
        logger.warning(
            "Could not parse JSON from model output for %s",
            url,
        )

        return []

    candidates = []

    for item in raw_events:
        try:
            candidates.append(EventCandidate(**item))

        except Exception as e:
            logger.warning(
                "Skipping malformed event: %s",
                e,
            )

    logger.info(
        "Extracted %d event candidates from %s",
        len(candidates),
        url,
    )

    return candidates


def find_music_event_candidates(
    location: str = "Utrecht",
    event_type: str = "music",
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[EventCandidate]:
    """Full search pipeline."""

    search_results = search_music_events(
        location,
        event_type,
        start_date,
        end_date,
    )

    if not search_results:
        logger.warning("No search results found")

        return []

    urls = [result["url"] for result in search_results if result.get("url")]

    content_by_url = fetch_page_content(urls)

    all_candidates = []

    for url, content in content_by_url.items():
        if not content:
            continue

        candidates = extract_events_from_content(
            url,
            content,
            event_type,
        )

        all_candidates.extend(candidates)

    now = datetime.now()

    valid_candidates = []

    for candidate in all_candidates:
        if not candidate.is_relevant_event or candidate.date is None:
            continue

        try:
            event_datetime = datetime.fromisoformat(candidate.date)

        except ValueError:
            logger.warning(
                "Skipping event with invalid date: %s (%s)",
                candidate.name,
                candidate.date,
            )

            continue

        if event_datetime < now:
            logger.info(
                "Skipping past event: %s (%s)",
                candidate.name,
                candidate.date,
            )

            continue

        valid_candidates.append(candidate)

    # Remove exact duplicates from multiple source pages.
    unique_candidates = {}

    for event in valid_candidates:
        key = (
            event.name.strip().lower(),
            event.date,
        )

        if key not in unique_candidates:
            unique_candidates[key] = event

    valid_candidates = list(unique_candidates.values())

    # Filter by requested date range.
    filtered_candidates = []

    for event in valid_candidates:
        event_datetime = datetime.fromisoformat(event.date)

        if start_date:
            start_datetime = datetime.fromisoformat(start_date)
            if event_datetime < start_datetime:
                continue

        if end_date:
            end_datetime = datetime.fromisoformat(end_date).replace(
                hour=23,
                minute=59,
                second=59,
            )
            if event_datetime > end_datetime:
                continue

        filtered_candidates.append(event)

    valid_candidates = filtered_candidates

    # Earliest event first.
    valid_candidates.sort(
        key=lambda event: datetime.fromisoformat(event.date)
    )

    logger.info(
        "Found %d valid, dated, upcoming event candidates",
        len(valid_candidates),
    )

    return valid_candidates


if __name__ == "__main__":
    candidates = find_music_event_candidates("Utrecht")

    for candidate in candidates:
        print(
            f"{candidate.name} | "
            f"{candidate.date} | "
            f"{candidate.duration_minutes} min | "
            f"{candidate.venue} | "
            f"{candidate.price} | "
            f"{candidate.event_url}"
        )

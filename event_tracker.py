import json
import logging
import os


logger = logging.getLogger(__name__)


TRACKER_FILE = "sent_events.json"


def _load_sent_events() -> set[str]:
    """Loads processed event keys from disk."""

    if not os.path.exists(TRACKER_FILE):
        return set()

    try:
        with open(
            TRACKER_FILE,
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)

        return set(data)

    except (
        json.JSONDecodeError,
        IOError,
    ) as e:
        logger.warning(
            "Could not read tracker file: %s",
            e,
        )

        return set()


def _save_sent_events(
    sent_events: set[str],
) -> None:
    """Saves processed event keys."""

    with open(
        TRACKER_FILE,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            sorted(sent_events),
            file,
            indent=2,
        )


def make_event_key(
    name: str,
    date: str,
) -> str:
    """Creates a stable unique key for an event."""

    normalized_name = " ".join(name.strip().lower().split())

    return f"{normalized_name}|{date}"


def has_been_processed(
    name: str,
    date: str,
) -> bool:
    """Returns True if the event was already processed."""

    sent_events = _load_sent_events()

    return (
        make_event_key(
            name,
            date,
        )
        in sent_events
    )


def mark_as_processed(
    name: str,
    date: str,
) -> None:
    """Marks an event as processed."""

    sent_events = _load_sent_events()

    sent_events.add(
        make_event_key(
            name,
            date,
        )
    )

    _save_sent_events(sent_events)

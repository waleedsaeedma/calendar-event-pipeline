
import logging

from intent import parse_event_request
from event_search import find_music_event_candidates

logger = logging.getLogger(__name__)


def run_pipeline_for_user(
    request_text,
    creds_json,
    preview_only=False,
):

    print("USER REQUEST:", request_text)
    print("CREDENTIALS RECEIVED:", bool(creds_json))

    # ----------------------------------------------------------
    # Step 1: Understand the user's request
    # ----------------------------------------------------------

    request = parse_event_request(request_text)

    if request is None:
        return {
            "message": "Sorry, I couldn't understand your event request.",
            "event": None,
        }

    print(
        f"Parsed request: {request.event_type} events "
        f"in {request.location}"
    )

    print(
        f"Requested period: "
        f"{request.start_date} -> {request.end_date}"
    )

    # ----------------------------------------------------------
    # Step 2: Search for real events
    # ----------------------------------------------------------

    candidates = find_music_event_candidates(
        location=request.location,
        event_type=request.event_type,
        start_date=request.start_date,
        end_date=request.end_date,
    )

    if not candidates:
        return {
            "message": (
                f"I couldn't find any upcoming {request.event_type} "
                f"events in {request.location} for the requested period."
            ),
            "event": None,
        }

    # ----------------------------------------------------------
    # Step 3: Select the nearest upcoming event
    # ----------------------------------------------------------

    selected_event = candidates[0]

    # ----------------------------------------------------------
    # Step 4: Preview mode
    # ----------------------------------------------------------

    if preview_only:
        return {
            "message": "Events found.",
            "event": selected_event,
            "events": candidates,
        }

    # ----------------------------------------------------------
    # Step 5: Normal return
    # Calendar creation is handled separately by the Flask app.
    # ----------------------------------------------------------

    return {
        "message": "Events found.",
        "event": selected_event,
        "events": candidates,
    }

from typing import Optional

from pydantic import BaseModel, Field


class EventExtraction(BaseModel):
    """Step 1 output: is this text even a calendar event?"""

    description: str = Field(description="Raw description of the event")

    is_calendar_event: bool = Field(
        description="Whether this text describes a calendar event"
    )

    confidence_score: float = Field(description="Confidence score between 0 and 1")


class EventDetails(BaseModel):
    """Step 2 output: the structured event details"""

    name: str = Field(description="Name of the event")

    date: str = Field(
        description="Date and time of the event. Use ISO 8601 to format this value."
    )

    duration_minutes: int = Field(description="Expected duration in minutes")

    participants: list[str] = Field(description="List of participants")


class EventConfirmation(BaseModel):
    """Step 3 output: confirmation message for the user"""

    confirmation_message: str = Field(
        description="Natural language confirmation message"
    )

    calendar_link: Optional[str] = Field(
        default=None, description="Generated calendar link if applicable"
    )


class EventCandidate(BaseModel):
    """A real event extracted from web content."""

    name: str = Field(description="Name of the event")

    date: Optional[str] = Field(
        default=None,
        description=(
            "Date and time in ISO 8601 format if clearly stated. "
            "Null if no specific date is available."
        ),
    )

    duration_minutes: Optional[int] = Field(
        default=None,
        description=(
            "Event duration in minutes if clearly stated or explicitly "
            "available from the page. Null if unknown. Never guess."
        ),
    )

    venue: Optional[str] = Field(
        default=None,
        description="Venue or location name",
    )

    price: Optional[float] = Field(
        default=None,
        description=(
            "Ticket price in euros if clearly stated. "
            "Use 0 for free events. "
            "Use null when no clear price is stated. "
            "Never guess."
        ),
    )

    description: Optional[str] = Field(
        default=None,
        description=(
            "Short description of the event if clearly available. Null if unavailable."
        ),
    )

    is_relevant_event: bool = Field(
        description=("Whether this genuinely matches the requested event type.")
    )

    source_url: str = Field(description="URL where the event information was found")

    event_url: Optional[str] = Field(
        default=None,
        description=(
            "Direct URL to this specific event or ticket page "
            "if clearly available. Null if unavailable."
        ),
    )


class EventRequest(BaseModel):
    """Parsed intent from a natural language request."""

    location: str = Field(
        description="City to search for events in"
    )

    event_type: str = Field(
        description="Type of event, e.g. music, festival, food market"
    )

    start_date: Optional[str] = Field(
        default=None,
        description=(
            "Start date of the requested event period in YYYY-MM-DD format. "
            "Resolve relative expressions such as 'this weekend', "
            "'next week', 'upcoming week', or 'next month' using today's date. "
            "Null if the user did not specify a date period."
        ),
    )

    end_date: Optional[str] = Field(
        default=None,
        description=(
            "End date of the requested event period in YYYY-MM-DD format. "
            "Resolve relative expressions such as 'this weekend', "
            "'next week', 'upcoming week', or 'next month' using today's date. "
            "Null if the user did not specify a date period."
        ),
    )


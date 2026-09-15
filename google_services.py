import base64
import logging
from datetime import datetime, timedelta
from email.mime.text import MIMEText

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


logger = logging.getLogger(__name__)


def create_calendar_event(
    creds,
    name: str,
    start_iso: str,
    duration_minutes: int,
    venue: str | None = None,
    description: str | None = None,
) -> str | None:
    """Creates an event on the user's primary Google Calendar."""

    try:
        service = build(
            "calendar",
            "v3",
            credentials=creds,
        )

        start_dt = datetime.fromisoformat(start_iso)

        end_dt = start_dt + timedelta(minutes=duration_minutes)

        event = {
            "summary": name,
            "start": {
                "dateTime": start_dt.isoformat(),
                "timeZone": "Europe/Amsterdam",
            },
            "end": {
                "dateTime": end_dt.isoformat(),
                "timeZone": "Europe/Amsterdam",
            },
        }

        if venue:
            event["location"] = venue

        if description:
            event["description"] = description

        created_event = (
            service.events()
            .insert(
                calendarId="primary",
                body=event,
            )
            .execute()
        )

        calendar_link = created_event.get("htmlLink")

        logger.info(
            "Calendar event created: %s",
            calendar_link,
        )

        return calendar_link

    except HttpError as e:
        logger.error(
            "Google Calendar API error: %s",
            e,
        )

        return None


def get_gmail_profile_email(
    creds,
) -> str | None:
    """Returns the authenticated Google account email."""

    try:
        service = build(
            "gmail",
            "v1",
            credentials=creds,
        )

        profile = service.users().getProfile(userId="me").execute()

        return profile.get("emailAddress")

    except HttpError as e:
        logger.error(
            "Could not get Gmail profile: %s",
            e,
        )

        return None


def send_confirmation_email(
    creds,
    to_email: str,
    subject: str,
    body: str,
) -> bool:
    """Sends a plain-text Gmail confirmation."""

    try:
        service = build(
            "gmail",
            "v1",
            credentials=creds,
        )

        message = MIMEText(body)

        message["to"] = to_email
        message["subject"] = subject

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

        (
            service.users()
            .messages()
            .send(
                userId="me",
                body={"raw": raw},
            )
            .execute()
        )

        logger.info(
            "Confirmation email sent to %s",
            to_email,
        )

        return True

    except HttpError as e:
        logger.error(
            "Gmail API error: %s",
            e,
        )

        return False

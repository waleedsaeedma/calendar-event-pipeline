# EventScout

EventScout is a Python application that turns natural-language event requests into real, structured event recommendations.

A user can write something like:

> Find me a music event in Utrecht

EventScout understands the request, searches the web, extracts real event information, displays event cards, provides direct ticket links, and can add an event directly to Google Calendar.

After adding an event, EventScout can also send a Gmail confirmation.

---

# What EventScout Does

The application follows this pipeline:

User request

↓

Natural-language intent extraction

↓

Web search with Tavily

↓

Full webpage extraction

↓

Structured event extraction with OpenAI

↓

Validation and filtering

↓

Duplicate removal

↓

Event cards

↓

Direct ticket/event URL

↓

Google Calendar

↓

Gmail confirmation

---

# Main Features

## 1. Natural-language event search

The user does not need to use a strict command.

Examples:

```text
Find me a music event in Utrecht
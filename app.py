from pathlib import Path
import json
import logging
import os

from dotenv import load_dotenv

from flask import (
    Flask,
    redirect,
    request,
    session,
    render_template_string,
    Response,
)

from google.oauth2.credentials import Credentials

from web_auth import (
    get_authorization_url,
    exchange_code_for_credentials,
)

from google_services import (
    create_calendar_event,
)

from event_tracker import (
    mark_as_processed,
)

from main_event_pipeline import (
    run_pipeline_for_user,
)


load_dotenv()


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


app = Flask(__name__)

app.secret_key = os.getenv("FLASK_SECRET_KEY")

if not app.secret_key:
    raise RuntimeError("FLASK_SECRET_KEY is not configured.")


app.config["SESSION_COOKIE_SECURE"] = False
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"


HOME_PAGE = """
<!DOCTYPE html>
<html lang="en">

<head>

    <meta charset="UTF-8">

    <meta
        name="viewport"
        content="width=device-width, initial-scale=1.0"
    >

    <meta
        name="theme-color"
        content="#0f172a"
    >

    <meta
        name="description"
        content="EventScout - Discover events and add them to Google Calendar."
    >

    <link
        rel="manifest"
        href="/manifest.json"
    >

    <title>EventScout</title>

    <script>
        if ("serviceWorker" in navigator) {
            window.addEventListener("load", () => {
                navigator.serviceWorker.register("/service-worker.js")
                    .then(() => {
                        console.log("EventScout service worker registered.");
                    })
                    .catch((error) => {
                        console.error("Service worker registration failed:", error);
                    });
            });
        }
    </script>

    <style>

        * {
            box-sizing: border-box;
        }

        body {
            font-family: Arial, sans-serif;
            margin: 0;
            min-height: 100vh;
            background: #f8fafc;
            color: #0f172a;
        }

        .container {
            width: 100%;
            max-width: 700px;
            margin: 0 auto;
            padding: 60px 20px;
            text-align: center;
        }

        .logo {
            font-size: 42px;
            font-weight: 800;
            margin-bottom: 10px;
        }

        .subtitle {
            color: #64748b;
            margin-bottom: 35px;
        }

        .search-box {
            background: white;
            padding: 25px;
            border-radius: 16px;
            box-shadow: 0 8px 30px rgba(15, 23, 42, 0.08);
        }

        input[type="text"] {
            width: 100%;
            padding: 14px;
            border: 1px solid #cbd5e1;
            border-radius: 10px;
            font-size: 16px;
            margin-bottom: 12px;
        }

        button {
            width: 100%;
            padding: 14px;
            border: none;
            border-radius: 10px;
            background: #0f172a;
            color: white;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
        }

        button:disabled {
            opacity: 0.6;
            cursor: wait;
        }

        .connect-button {
            display: inline-block;
            padding: 14px 20px;
            background: #0f172a;
            color: white;
            text-decoration: none;
            border-radius: 10px;
            font-weight: 600;
        }

        @media (max-width: 600px) {

            .container {
                padding: 40px 15px;
            }

            .logo {
                font-size: 34px;
            }

            .search-box {
                padding: 20px;
            }

        }

    </style>

</head>

<body>

<div class="container">

    <div class="logo">
        EventScout
    </div>

    <p class="subtitle">
        Discover events and add them to your Google Calendar.
    </p>

    {% if connected %}

        <div class="search-box">

            <p>
                Google Calendar connected!
            </p>

            <form
                action="/search"
                method="post"
                onsubmit="
                    this.querySelector('button').disabled = true;
                    this.querySelector('button').innerText = 'Searching...';
                "
            >

                <input
                    type="text"
                    name="request_text"
                    placeholder="Find me a music event in Utrecht"
                    required
                >

                <button type="submit">
                    Search
                </button>

            </form>

        </div>

    {% else %}

        <div class="search-box">

            <p>
                Connect your Google Calendar to get started.
            </p>

            <a
                href="/connect"
                class="connect-button"
            >
                Connect Google Calendar
            </a>

        </div>

    {% endif %}

</div>

</body>

</html>
"""


@app.route("/")
def home():

    connected = "credentials" in session

    return render_template_string(
        HOME_PAGE,
        connected=connected,
    )


@app.route("/manifest.json")
def manifest():

    manifest_data = {
        "name": "EventScout",
        "short_name": "EventScout",
        "description": ("Discover events and add them to your Google Calendar."),
        "start_url": "/",
        "display": "standalone",
        "background_color": "#f8fafc",
        "theme_color": "#0f172a",
        "orientation": "portrait-primary",
        "icons": [
            {
                "src": "/static/icon-192.png",
                "sizes": "192x192",
                "type": "image/png",
            },
            {
                "src": "/static/icon-512.png",
                "sizes": "512x512",
                "type": "image/png",
            },
        ],
    }

    return Response(
        json.dumps(manifest_data),
        mimetype="application/manifest+json",
    )


@app.route("/service-worker.js")
def service_worker():

    service_worker_code = """
const CACHE_NAME = "eventscout-v1";

const APP_SHELL = [
    "/",
    "/manifest.json"
];

self.addEventListener("install", event => {

    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => cache.addAll(APP_SHELL))
    );

    self.skipWaiting();
});


self.addEventListener("activate", event => {

    event.waitUntil(
        caches.keys().then(keys =>
            Promise.all(
                keys
                    .filter(key => key !== CACHE_NAME)
                    .map(key => caches.delete(key))
            )
        )
    );

    self.clients.claim();
});


self.addEventListener("fetch", event => {

    event.respondWith(
        fetch(event.request)
            .catch(() => caches.match(event.request))
    );

});
"""

    response = Response(
        service_worker_code,
        mimetype="application/javascript",
    )

    response.headers["Service-Worker-Allowed"] = "/"

    return response


@app.route("/static/icon-512.png")
def icon_512():

    return Response(
        status=204,
        mimetype="image/png",
    )


@app.route("/connect")
def connect():

    auth_url, state, code_verifier = get_authorization_url()

    session["state"] = state
    session["code_verifier"] = code_verifier

    return redirect(auth_url)


@app.route("/oauth2callback")
def oauth2callback():

    code_verifier = session.get("code_verifier")

    if not code_verifier:
        return (
            "Missing code verifier in session.",
            400,
        )

    try:
        creds = exchange_code_for_credentials(
            request.url,
            code_verifier,
        )

        credentials_json = creds.to_json()

        session["credentials"] = credentials_json

        Path("user_credentials.json").write_text(
            credentials_json,
            encoding="utf-8",
        )

        session.pop(
            "code_verifier",
            None,
        )

        return redirect("/")

    except Exception as e:
        logger.error(
            "Google OAuth failed: %s",
            e,
        )

        return (
            """
            <html>
            <head>
                <meta
                    name="viewport"
                    content="width=device-width, initial-scale=1.0"
                >
            </head>

            <body style="
                font-family: sans-serif;
                max-width: 600px;
                margin: 80px auto;
                padding: 0 20px;
                text-align: center;
            ">

                <h2>
                    ❌ Google authorization failed
                </h2>

                <p>
                    Please try connecting Google Calendar again.
                </p>

                <a href="/">
                    ← Back to EventScout
                </a>

            </body>
            </html>
            """,
            500,
        )



@app.route(
    "/search",
    methods=["POST"],
)
def search():

    request_text = request.form.get("request_text", "").strip()

    creds_json = session.get("credentials")

    if not creds_json and Path("user_credentials.json").exists():
        creds_json = Path(
            "user_credentials.json"
        ).read_text(
            encoding="utf-8"
        )

        session["credentials"] = creds_json

    if not creds_json:
        return redirect("/connect")

    try:

        result = run_pipeline_for_user(
            request_text,
            creds_json,
            preview_only=True,
        )

        events = result.get("events", [])
        message = result.get(
            "message",
            "No events found.",
        )

        return render_template_string("""
<!DOCTYPE html>
<html lang="en">
<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1.0"
>

<title>EventScout Results</title>

<style>

* {
    box-sizing: border-box;
}

body {
    margin: 0;
    font-family: Arial, sans-serif;
    background: #f8fafc;
    color: #0f172a;
}

.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 40px 20px;
}

h1 {
    margin-bottom: 8px;
}

.subtitle {
    color: #64748b;
    margin-bottom: 28px;
}

.table-wrap {
    background: white;
    border-radius: 16px;
    box-shadow: 0 8px 30px rgba(15, 23, 42, 0.08);
    overflow-x: auto;
}

table {
    width: 100%;
    border-collapse: collapse;
}

th,
td {
    padding: 16px;
    text-align: left;
    border-bottom: 1px solid #e2e8f0;
    vertical-align: middle;
}

th {
    background: #f1f5f9;
    font-size: 14px;
    white-space: nowrap;
}

.event-name {
    font-weight: 700;
    font-size: 16px;
    min-width: 220px;
}

.description {
    color: #64748b;
    margin-top: 6px;
    line-height: 1.4;
    max-width: 320px;
}

button {
    padding: 10px 16px;
    border: none;
    border-radius: 9px;
    background: #0f172a;
    color: white;
    font-weight: 600;
    cursor: pointer;
}

button:hover {
    opacity: 0.85;
}

a {
    color: #2563eb;
    text-decoration: none;
}

a:hover {
    text-decoration: underline;
}

.back {
    display: inline-block;
    margin-top: 24px;
    color: #475569;
}

</style>

</head>

<body>

<div class="container">

<h1>EventScout Results</h1>

<p class="subtitle">
{{ message }}
</p>

{% if events %}

<div class="table-wrap">

<table>

<thead>

<tr>
<th>#</th>
<th>Event</th>
<th>Date</th>
<th>Venue</th>
<th>Duration</th>
<th>Price</th>
<th>Event</th>
<th>Calendar</th>
</tr>

</thead>

<tbody>

{% for event in events %}

<tr>

<td>
{{ loop.index }}
</td>

<td>

<div class="event-name">
{{ event.name }}
</div>

{% if event.description %}

<div class="description">
{{ event.description }}
</div>

{% endif %}

</td>

<td>
{{ event.date or "Unknown" }}
</td>

<td>
{{ event.venue or "Unknown" }}
</td>

<td>

{% if event.duration_minutes %}
{{ event.duration_minutes }} min
{% else %}
Unknown
{% endif %}

</td>

<td>

{% if event.price is none %}
Unknown
{% elif event.price == 0 %}
Free
{% else %}
€{{ event.price }}
{% endif %}

</td>

<td>

{% if event.event_url %}

<a
    href="{{ event.event_url }}"
    target="_blank"
>
View
</a>

{% else %}

—

{% endif %}

</td>

<td>

<form
    action="/add-to-calendar"
    method="post"
>

<input
    type="hidden"
    name="name"
    value="{{ event.name }}"
>

<input
    type="hidden"
    name="date"
    value="{{ event.date or '' }}"
>

<input
    type="hidden"
    name="duration"
    value="{{ event.duration_minutes or 60 }}"
>

<input
    type="hidden"
    name="venue"
    value="{{ event.venue or '' }}"
>

<input
    type="hidden"
    name="description"
    value="{{ event.description or '' }}"
>

<button type="submit">
Add
</button>

</form>

</td>

</tr>

{% endfor %}

</tbody>

</table>

</div>

{% else %}

<div class="table-wrap">

<div
    style="
        padding:30px;
        text-align:center;
    "
>

<h2>
No events found
</h2>

<p>
{{ message }}
</p>

</div>

</div>

{% endif %}

<a
    class="back"
    href="/"
>
← Back to search
</a>

</div>

</body>
</html>
""",
            events=events,
            message=message,
        )

    except Exception as e:

        logger.error(
            "Search failed: %s",
            e,
        )

        return render_template_string("""
<div style="
    font-family:Arial,sans-serif;
    max-width:700px;
    margin:80px auto;
    text-align:center;
    padding:20px;
">

<h1>Search failed</h1>

<p>
{{ error }}
</p>

<p>
<a href="/">
← Back to search
</a>
</p>

</div>
""", error=str(e)), 500


@app.route(
    "/add-to-calendar",
    methods=["POST"],
)
def add_to_calendar():

    creds_json = session.get("credentials")

    if not creds_json:
        return redirect("/connect")

    try:

        creds = Credentials.from_authorized_user_info(
            json.loads(creds_json)
        )

        name = request.form.get(
            "name",
            "",
        )

        date = request.form.get(
            "date",
            "",
        )

        duration = int(
            request.form.get(
                "duration",
                "60",
            )
        )

        venue = request.form.get(
            "venue",
            "",
        )

        description = request.form.get(
            "description",
            "",
        )

        calendar_link = create_calendar_event(
            creds=creds,
            name=name,
            start_iso=date,
            duration_minutes=duration,
            venue=venue or None,
            description=description or None,
        )

        if not calendar_link:

            return (
                "Could not add the event to Google Calendar.",
                500,
            )

        return render_template_string("""
<div style="
    font-family:Arial,sans-serif;
    max-width:700px;
    margin:80px auto;
    text-align:center;
    padding:20px;
">

<h1>
Added to Google Calendar
</h1>

<h2>
{{ name }}
</h2>

<p>
{{ date }}
</p>

<p>
{{ venue }}
</p>

<p>

<a
    href="{{ calendar_link }}"
    target="_blank"
>
Open Google Calendar event
</a>

</p>

<p>

<a href="/">
Search for another event
</a>

</p>

</div>
""",
            name=name,
            date=date,
            venue=venue,
            calendar_link=calendar_link,
        )

    except Exception as e:

        logger.error(
            "Calendar creation failed: %s",
            e,
        )

        return (
            f"Calendar creation failed: {e}",
            500,
        )

if __name__ == "__main__":
    app.run(
        debug=True,
        port=5000,
    )

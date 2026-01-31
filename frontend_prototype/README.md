HTMX Frontend Prototype

This is a lightweight prototype of the Dashboard page rewritten with HTMX + Alpine + Tailwind.

Build & Run locally with Docker:

  docker build -t kilo/frontend-proto:local .
  docker run -p 8080:80 kilo/frontend-proto:local

Open http://localhost:8080 in your browser. The prototype fetches data from the gateway endpoints (e.g., http://localhost:8000/ai_brain/stats/dashboard). For metrics, the prototype uses the admin gateway proxy and requires a valid token.

Notes:
- This is a prototype that focuses on visual parity for the Dashboard. We can expand to other pages using the same approach.
- Replace the Tailwind CDN with a compiled CSS build if you need exact styling parity with the production frontend.

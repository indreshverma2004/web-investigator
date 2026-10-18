# OpenScope

OpenScope is a small local OSINT (open-source intelligence) investigator. It crawls a limited set of publicly accessible HTML pages on one website, extracts visible public signals, and shows the source page for each result. It does not log in, submit forms, or attempt to access private information.

## How it works

The Flask server validates the starting HTTP(S) URL, resolves its host and rejects non-public addresses. Each outgoing request is resolved again and the approved address set is pinned into the connection's DNS lookup. HTTPS certificates are verified against the operating system's native trust store. Redirects are followed manually: every target must resolve publicly and remain on the starting website's origin. The crawler honors `robots.txt`, applies an eight-second timeout, caps page bodies at 2 MB, waits briefly between pages, and fetches at most the selected number (1–30, default 20). Only HTML pages are parsed. Investigations run independently in memory and can be cancelled.

The parser reads visible text, page titles, and HTTP(S) links. It extracts email addresses (including `mailto:` links), domains, discovered URLs, and public IPv4 addresses. Hidden script/style content and form values are not parsed. Counts represent extraction occurrences; each entity includes its unique source pages. The graph contains pages, domains and emails, with links grounded in the crawled page evidence. Findings are observations, not claims of ownership or identity.

The JSON export contains the report, progress, page records, entities and graph. CSV includes entity type, value, occurrence count and source URLs. Data disappears when the server process stops.

## Privacy and responsible use

Use OpenScope only for public websites and research you are authorized to conduct. Respect site terms, robots.txt and applicable law. The app stores scan results only in process memory and does not persist them. Requests disclose the local machine's network address to the target site, as ordinary web requests do. Do not use this tool to harass, profile, or target people.

## Limitations

OpenScope is deliberately bounded and can miss content rendered by JavaScript, linked from non-crawlable routes, behind authentication, blocked by robots.txt, rate limits, or network controls. Extraction uses patterns and visible HTML text, so results may be incomplete or include false positives. DNS lookups are pinned for requests performed by OpenScope and redirects are rechecked; however, the implementation temporarily replaces Python's process-wide `socket.getaddrinfo` while a request is opened under a lock. This protects OpenScope's own concurrent requests, but a separate networking thread in the same Python process could observe that brief resolver override. Run the app as a dedicated local process and do not embed it in a multi-tenant server. The app cannot control routing performed by the host OS, VPN, proxy, or network. Environment proxies are disabled for crawler requests.

## Install and run (Windows PowerShell)

From this `openscope` directory:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Open the local URL printed by Flask (usually `http://127.0.0.1:5000`). Enter a public website URL such as the official NIT Raipur website, `https://nitrr.ac.in/`, choose a page limit, and start the investigation. Results vary with site availability and crawl policy; no NIT Raipur findings are built into the application.

## Tests

Tests use mocked HTTP responses and DNS data; they do not contact live websites.

```powershell
python -m pytest
```

## API

- `GET /api/health`
- `POST /api/investigations` with JSON `{"url":"https://example.org","max_pages":20}`
- `GET /api/investigations/<id>`
- `POST /api/investigations/<id>/cancel`
- `GET /api/investigations/<id>/export.json`
- `GET /api/investigations/<id>/export.csv`

The browser uses Cytoscape.js from a CDN. If it is unavailable, the graph area explains the issue and the evidence tables remain usable.

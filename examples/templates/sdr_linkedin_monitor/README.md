# SDR LinkedIn Monitor

**Use Case #58 — Sales Coach · Highest-Performing SDR**

Monitors LinkedIn 24/7 for hiring and role-change signals from senior engineering leaders at Series B+ companies, finds their corporate emails, and drafts highly personalized cold emails for SDR review — up to 50 per day.

---

## What It Does

1. **Campaign Intake** — Collects your ICP filters (target titles, company stage, trigger signals), daily quota, and the one-line pitch for your OSS framework.
2. **LinkedIn Signal Monitor** — Searches LinkedIn via Exa for "I'm hiring" and "just started a new role" posts from VP of Engineering and CTO titles at Series B+ companies.
3. **Corporate Email Lookup** — For each qualifying lead, finds their corporate email via web search (public company pages, Hunter.io results, profile data).
4. **Personalized Email Drafter** — Researches each company's recent product launch and drafts a short, personalized cold email: congratulates the lead, references the launch, softly pitches the framework.
5. **Email Queue Review** — Serves an HTML report with all drafted emails for your review. Nothing is sent automatically.

---

## Quickstart

### Prerequisites

- `ANTHROPIC_API_KEY` set (or preferred LLM provider key)
- Hive tools running (see top-level README)

### Run via TUI

```bash
cd /path/to/hive
hive tui
```

Then select **SDR LinkedIn Monitor** from the agent list.

### Run via CLI (headless)

```bash
cd /path/to/hive
PYTHONPATH=exports uv run python -m sdr_linkedin_monitor run
```

### Interactive shell

```bash
PYTHONPATH=exports uv run python -m sdr_linkedin_monitor shell
```

### Validate agent structure

```bash
PYTHONPATH=exports uv run python -m sdr_linkedin_monitor validate
```

### Show agent info

```bash
PYTHONPATH=exports uv run python -m sdr_linkedin_monitor info
```

---

## Targeting Defaults

| Parameter | Default |
|-----------|---------|
| Target titles | VP of Engineering, CTO, VP Engineering, Chief Technology Officer |
| Company stage | Series B, C, D, E, growth-stage |
| Trigger signals | "I'm hiring", "just started a new role", "excited to announce", "joining as", "new chapter" |
| Daily quota | 20 (max 50) |

All defaults can be adjusted at intake time.

---

## Output

The agent saves an `outreach_queue.html` file with:
- A summary table of all leads (name, title, company, email, signal type)
- Individual draft email cards with subject line, body, and personalization hook
- Source URLs for all research used

---

## Tools Used

| Tool | Purpose |
|------|---------|
| `exa_search` | LinkedIn signal discovery, email lookup, product launch research |
| `exa_get_contents` | Extract post content, contact pages, company blogs |
| `save_data` | Save draft JSON and HTML report |
| `append_data` | Build HTML report incrementally |
| `load_data` | Load existing drafts if needed |
| `serve_file_to_user` | Deliver the HTML queue to the user |

---

## Notes on LinkedIn Access

LinkedIn blocks direct scraping. This agent uses Exa search plus `linkedin.com`
targeting to surface public LinkedIn posts and then uses `exa_get_contents` to
extract the content needed for qualification.

## Notes on Email Lookup

No ZoomInfo API is bundled. The agent uses Exa search over public sources
(Hunter.io public results, company "About/Team" pages, LinkedIn profile data)
to find or infer corporate emails. Confidence levels are tracked: `verified`,
`inferred`, or `not_found`.

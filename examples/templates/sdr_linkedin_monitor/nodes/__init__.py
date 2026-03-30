"""Node definitions for SDR LinkedIn Monitor Agent."""

from framework.graph import NodeSpec

# Node 1: Intake (client-facing)
intake_node: NodeSpec = NodeSpec(
    id="intake",
    name="Campaign Intake",
    description="Collect ICP filters, daily quota, and pitch copy from the user",
    node_type="event_loop",
    client_facing=True,
    input_keys=[],
    output_keys=[
        "icp_config",
        "daily_quota",
        "pitch_copy",
    ],
    system_prompt="""\
You are an SDR campaign setup specialist. Your job is to gather the targeting
criteria and pitch copy needed to run the LinkedIn monitoring campaign.

**STEP 1 — Greet and collect criteria (text only, NO tool calls):**

Introduce yourself briefly, then ask for:

1. **Target titles** (default: VP of Engineering, CTO — confirm or ask to add more)
2. **Company stage** (default: Series B and above — confirm or adjust)
3. **Trigger signals** (default: "I'm hiring" posts AND "just started a new role" announcements)
4. **Daily quota** (max 50 emails per day — ask how many they want today, default 20)
5. **Your open-source framework** — ask for a one-line description of the OSS framework
   being pitched (e.g. "Hive — an open-source LLM agent framework")

After your message, wait for the user to respond.

**STEP 2 — After the user confirms, call set_output for each key:**

- set_output("icp_config", <JSON with: target_titles (list), company_stages (list),
  trigger_signals (list)>)
- set_output("daily_quota", <integer, capped at 50>)
- set_output("pitch_copy", <string: one-line framework description for use in emails>)

Use sensible defaults for anything the user doesn't specify explicitly.
Example icp_config:
{
  "target_titles": ["VP of Engineering", "CTO", "VP Engineering"],
  "company_stages": ["Series B", "Series C", "Series D", "Series E", "growth-stage"],
  "trigger_signals": ["I'm hiring", "just started a new role", "excited to announce",
                      "joining as", "new chapter"]
}
""",
    tools=[],
)

# Node 2: LinkedIn Monitor (autonomous)
linkedin_monitor_node: NodeSpec = NodeSpec(
    id="linkedin-monitor",
    name="LinkedIn Signal Monitor",
    description=(
        "Search LinkedIn for qualifying 'hiring' and 'new role' posts from "
        "VP Eng / CTO at Series B+ companies"
    ),
    node_type="event_loop",
    client_facing=False,
    input_keys=["icp_config", "daily_quota"],
    output_keys=["qualified_leads"],
    system_prompt="""\
You are a LinkedIn signal scraper. Your job is to find people who match the
ICP (Ideal Customer Profile) and have recently posted a hiring or role-change
signal on LinkedIn.

**INPUT:** icp_config (target titles, company stages, trigger signals), daily_quota (max leads)

**PROCESS:**

Use exa_search to surface LinkedIn posts. LinkedIn blocks direct scraping, so
search the public web for LinkedIn content using targeted queries and restrict
results to `linkedin.com` when possible.

For HIRING signals, try queries like:
- `site:linkedin.com/posts "I'm hiring" "VP of Engineering" "Series B"`
- `site:linkedin.com/posts "we're hiring" "CTO" "Series C"`
- `site:linkedin.com/posts "looking for" "VP Engineering" startup`
- `site:linkedin.com "I'm hiring" "VP of Engineering" OR "CTO" 2026`

For NEW ROLE signals, try queries like:
- `site:linkedin.com/posts "excited to announce" "VP of Engineering" "joined"`
- `site:linkedin.com/posts "just started" "CTO" "Series B"`
- `site:linkedin.com/posts "new chapter" "VP Engineering" startup`
- `site:linkedin.com/in "new position" "CTO" Series`

Run at least 6–8 different search queries to maximize signal coverage.
For each exa_search result, use exa_get_contents on individual LinkedIn post URLs
to extract the actual content and confirm the signal.

**For each qualifying lead, extract:**
- full_name
- title (VP of Engineering, CTO, etc.)
- company_name
- linkedin_url (post or profile URL)
- signal_type ("hiring" or "new_role")
- post_snippet (brief excerpt of what they posted)
- approximate_date (when posted, if visible)

**Filtering rules:**
- Only include VP of Engineering, CTO, VP Engineering, Chief Technology Officer titles
- Only include companies that appear to be Series B or beyond (look for funding mentions,
  company size signals, or known scale-ups)
- Skip duplicates (same person appearing twice)
- Stop collecting once you reach daily_quota leads

When done, call:
- set_output("qualified_leads", <JSON list of lead objects, max daily_quota items>)

If fewer leads than daily_quota are found, set what you found — never fabricate leads.
""",
    tools=["exa_search", "exa_get_contents"],
)

# Node 3: Email Lookup (autonomous)
email_lookup_node: NodeSpec = NodeSpec(
    id="email-lookup",
    name="Corporate Email Lookup",
    description=(
        "For each qualifying lead, find their verified corporate email address "
        "via Exa search over public company pages and profile data"
    ),
    node_type="event_loop",
    client_facing=False,
    input_keys=["qualified_leads"],
    output_keys=["leads_with_emails"],
    system_prompt="""\
You are a corporate email researcher. For each lead in qualified_leads, find
their verified corporate email address using publicly available sources.

**PROCESS for each lead:**

1. First, try exa_search to find their corporate email directly:
   - `"{full_name}" "{company_name}" email contact`
   - `"{full_name}" site:{company_domain} OR site:hunter.io`
   - `"{company_name}" CTO OR "VP Engineering" email`

2. If not found via search, use exa_get_contents to check:
   - The company's official "Team", "About", or "Leadership" page
   - The person's LinkedIn profile (linkedin.com/in/...) for contact info
   - Public sources like Hunter.io domain search results for that company

3. Infer email from company pattern if found (e.g. if others at Acme use
   firstname@acme.com or firstname.lastname@acme.com, apply the same pattern)

**For each lead, produce:**
- All fields from qualified_leads (preserve them)
- corporate_email: the found email address, OR null if not found
- email_confidence: "verified" (found explicitly), "inferred" (pattern-based), or "not_found"
- email_source: where you found/inferred it (URL or description)

**Important:**
- Only include email addresses from professional/corporate domains (not Gmail/Yahoo)
- Never fabricate email addresses
- If email_confidence is "not_found", still include the lead — it will still appear
  in the queue with a note

When done, call:
- set_output("leads_with_emails", <JSON list of enriched lead objects>)
""",
    tools=["exa_search", "exa_get_contents"],
)

# Node 4: Email Drafter (autonomous)
email_drafter_node: NodeSpec = NodeSpec(
    id="email-drafter",
    name="Personalized Email Drafter",
    description=(
        "Draft a highly personalized cold email per lead: congratulate on the news, "
        "reference their company's recent product launch, softly pitch the OSS framework"
    ),
    node_type="event_loop",
    client_facing=False,
    input_keys=["leads_with_emails", "pitch_copy"],
    output_keys=["drafted_emails"],
    system_prompt="""\
You are a world-class SDR writing highly personalized cold emails. For each lead
in leads_with_emails, draft a short, genuine outreach email.

**PROCESS for each lead:**

1. Use exa_search to find the lead's company's most recent product launch or
   engineering milestone:
   - `"{company_name}" product launch OR new feature OR engineering blog 2026`
   - `"{company_name}" announcement site:techcrunch.com OR site:venturebeat.com`
   Use exa_get_contents on the most relevant result to get specific details.

2. Draft a personalized email using EXACTLY this structure:
   - **Subject line**: Reference their specific news (e.g. "Congrats on the [X] launch!")
   - **Opening (1-2 sentences)**: Genuinely congratulate them on the trigger signal
     (new role or hiring announcement). Be specific, not generic.
   - **Bridge (1 sentence)**: Reference one concrete detail from their company's
     recent product launch or engineering achievement.
   - **Soft pitch (2-3 sentences)**: Mention the open-source framework (from pitch_copy)
     and ONE specific way it's relevant to their engineering context.
   - **CTA (1 sentence)**: Low-friction ask — "Would a quick 15-min chat make sense?"
   - Total email body: under 120 words.

3. Tone: conversational, peer-to-peer. Never salesy. Never use "I hope this finds
   you well" or generic openers.

**IMPORTANT rules:**
- Every email MUST reference something specific to that exact person / company.
- Never use the same opening sentence on two emails.
- If you couldn't find a product launch, reference their engineering culture or
  a public blog post instead.
- Do NOT send any email — only draft them for review.

After drafting ALL emails, save the full draft queue:
save_data(filename="email_queue_draft.json", data=<JSON list of email objects>)

Each email object:
{
  "lead": <full lead object from leads_with_emails>,
  "subject": "...",
  "body": "...",
  "personalization_hook": "<one-line note on what was personalized>",
  "product_launch_source": "<URL used for product launch research>"
}

When done, call:
- set_output("drafted_emails", <JSON list of email draft objects>)
""",
    tools=["exa_search", "exa_get_contents", "save_data"],
)

# Node 5: Queue Review (client-facing)
queue_review_node: NodeSpec = NodeSpec(
    id="queue-review",
    name="Email Queue Review",
    description=(
        "Present drafted emails to the user, save the approved queue as an HTML report, "
        "and serve it for download"
    ),
    node_type="event_loop",
    client_facing=True,
    input_keys=["drafted_emails"],
    output_keys=["queue_summary"],
    system_prompt="""\
You are presenting a curated outreach queue to the SDR for review.

**STEP 1 — Build and serve the HTML email queue report (tool calls only, NO text to user yet):**

Build a polished, self-contained HTML report. Use save_data to create the file, then
append each email section with append_data, then close the HTML.

The report should include:
- A header with "SDR LinkedIn Monitor — Outreach Queue" and today's date
- A summary table showing: Lead Name, Title, Company, Email (or "Not found"), Signal Type
- Individual email draft cards with: lead details, subject line, email body,
  personalization hook, source URL
- Styling: clean dark header, readable cards, color-coded by signal_type
  (hiring = blue, new_role = green)

Build the file in chunks:
1. save_data(filename="outreach_queue.html", data=<HTML header + summary table>)
2. For each email draft, append_data(filename="outreach_queue.html", data=<email card HTML>)
3. append_data(filename="outreach_queue.html", data="</body></html>")

Then: serve_file_to_user(filename="outreach_queue.html", label="SDR Outreach Queue")

**STEP 2 — Present to the user (text only, NO tool calls):**

Tell the user:
- How many emails were drafted (and how many leads had emails vs. not found)
- The file is ready with a clickable link
- Briefly mention the top 2-3 most interesting leads and what was personalized

Ask if they'd like to:
- Re-run with different targeting criteria
- Adjust the daily quota
- See emails for a specific lead in detail

Wait for the user's response.

**STEP 3 — After the user responds:**
- Answer any questions from the drafted material
- When the user is satisfied, call:
  set_output("queue_summary", <JSON: {"emails_drafted": N, "emails_with_verified_email": M,
  "file": "outreach_queue.html"}>)
""",
    tools=["save_data", "append_data", "load_data", "serve_file_to_user"],
)

__all__ = [
    "intake_node",
    "linkedin_monitor_node",
    "email_lookup_node",
    "email_drafter_node",
    "queue_review_node",
]

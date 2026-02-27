"""Node definitions for RSS-to-Twitter Agent."""

from framework.graph import NodeSpec


fetch_node = NodeSpec(
    id="fetch",
    name="Fetch RSS",
    description="Fetch and parse RSS articles",
    node_type="event_loop",
    client_facing=False,
    input_keys=["feed_url", "max_articles"],
    output_keys=["articles"],
    system_prompt="""\
You fetch RSS articles.

1. Call tool fetch_rss_data with optional feed_url and max_articles.
2. If tool returns no articles, set_output("articles", []).
3. Otherwise set_output("articles", <list of articles>). 
""",
    tools=["fetch_rss_data"],
)

process_node = NodeSpec(
    id="process",
    name="Summarize Articles",
    description="Summarize RSS articles into tweet-ready points",
    node_type="event_loop",
    client_facing=False,
    input_keys=["articles"],
    output_keys=["summaries"],
    system_prompt="""\
You summarize RSS articles.

1. If articles is empty, set_output("summaries", []).
2. Otherwise call summarize_articles_data with articles.
3. Set_output("summaries", <summaries list>). 
""",
    tools=["summarize_articles_data"],
)

generate_node = NodeSpec(
    id="generate",
    name="Generate Threads",
    description="Generate Twitter threads from summaries",
    node_type="event_loop",
    client_facing=False,
    input_keys=["summaries"],
    output_keys=["threads"],
    system_prompt="""\
You generate Twitter threads.

1. If summaries is empty, set_output("threads", []).
2. Otherwise call generate_threads_data with summaries.
3. Set_output("threads", <threads list>). 
""",
    tools=["generate_threads_data"],
)

approve_node = NodeSpec(
    id="approve",
    name="Approve Threads",
    description="Ask user whether to post generated threads",
    node_type="event_loop",
    client_facing=True,
    max_node_visits=1,
    input_keys=["threads"],
    output_keys=["should_post", "approved_threads"],
    system_prompt="""\
You are a thread approval checkpoint.

Show a compact preview of the generated threads and ask:
"Do you want to post these threads to Twitter now? (yes/no)"

If yes:
- set_output("should_post", true)
- set_output("approved_threads", threads)

If no:
- set_output("should_post", false)
- set_output("approved_threads", [])
""",
    tools=[],
)

post_node = NodeSpec(
    id="post",
    name="Post to Twitter",
    description="Post approved threads using Playwright",
    node_type="event_loop",
    client_facing=False,
    input_keys=["approved_threads", "twitter_credential_ref"],
    output_keys=["post_results"],
    system_prompt="""\
You post approved threads.

1. If approved_threads is empty, set_output("post_results", {"success": false, "error": "No approved threads"}).
2. Otherwise call post_to_twitter_data with approved_threads and twitter_credential_ref when available.
3. Set_output("post_results", <tool response>). 
""",
    tools=["post_to_twitter_data"],
)

complete_node = NodeSpec(
    id="complete",
    name="Complete",
    description="Finalize workflow output",
    node_type="event_loop",
    client_facing=False,
    input_keys=["threads", "post_results", "should_post"],
    output_keys=["workflow_status"],
    system_prompt="""\
You finalize run status.

Set workflow_status:
- "posted" if should_post is true and post_results.success is true
- "skipped" if should_post is false
- "failed" otherwise

Call set_output("workflow_status", <value>). 
""",
    tools=[],
)

__all__ = [
    "fetch_node",
    "process_node",
    "generate_node",
    "approve_node",
    "post_node",
    "complete_node",
]

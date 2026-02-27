# RSS-to-Twitter Agent (Modern Hive Template)

This template is the Hive v0.6-aligned version of RSS-to-Twitter automation.

## Structure

- `nodes/__init__.py`: `NodeSpec` definitions (`event_loop` nodes)
- `agent.py`: `Goal`, `EdgeSpec`, `GraphSpec`, `create_agent_runtime`
- `__main__.py`: `run`, `info`, `validate`
- `helpers.py`: RSS fetch, summarization/thread generation wrappers, Twitter posting helper

## Workflow

`fetch -> process -> generate -> approve (client-facing) -> post -> complete`

- Approval is explicit (`client_facing=True` on `approve` node).
- If rejected, flow routes directly to `complete` with `workflow_status=skipped`.

## Run

```bash
cd /Users/vasu/Desktop/hive
export PYTHONPATH=core:examples/templates

python -m rss_twitter_agent validate
python -m rss_twitter_agent info

# Safe deterministic run
python -m rss_twitter_agent run --mock --auto-approve

# Real LLM run (requires configured provider/model)
python -m rss_twitter_agent run --feed-url https://news.ycombinator.com/rss --max-articles 3

# Optional Hive v0.6 credential reference for Twitter session config
python -m rss_twitter_agent run --twitter-credential-ref twitter/default
```

## Notes

- This modern template coexists with your legacy implementation at `examples/template/rss_twitter_agent`.
- Legacy helper logic is reused via wrapper functions in `helpers.py`.
- Credential namespace (`{name}/{alias}`) is supported for Twitter session settings via:
  `--twitter-credential-ref twitter/default` or `TWITTER_CREDENTIAL_REF=twitter/default`.

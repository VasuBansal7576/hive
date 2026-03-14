# Contributing to hive-mcp-registry

## 5-Minute Quickstart

1. Fork the repository and clone your fork locally.
2. Copy `registry/_template/` to `registry/servers/<your-server>/`.
3. Update `manifest.json` with your real package, transport, credentials, and docs.
4. Add a sibling `README.md` that explains install, authentication, and a quick usage example.
5. Run:

```bash
python scripts/validate.py registry/servers/<your-server>/manifest.json
python scripts/build_index.py
```

6. Commit your changes and open a pull request.

## Manifest Reference

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `$schema` | `string` | No | Canonical schema URL for editor tooling and validation. |
| `name` | `string` | Yes | Registry identifier. Use lowercase letters, numbers, and hyphens only. |
| `display_name` | `string` | Yes | Human-friendly title shown in search results and UIs. |
| `version` | `string` | Yes | Server version in semver form, such as `1.2.0`. |
| `description` | `string` | Yes | Short summary of the server's purpose. |
| `author` | `object` | Yes | Original creator metadata with `name`, `github`, and `url`. |
| `maintainer` | `object` | Yes | Current maintainer metadata with `github` and `email`. |
| `repository` | `string` | Yes | Source repository URL. |
| `license` | `string` | Yes | License label or SPDX-like identifier. |
| `status` | `string` | Yes | One of `official`, `verified`, or `community`. |
| `docs_url` | `string` | No | Canonical documentation URL for install and auth setup. |
| `supported_os` | `string[]` | No | Supported OS values: `linux`, `macos`, `windows`. |
| `deprecated` | `boolean` | No | Whether the entry should no longer be installed. |
| `deprecated_by` | `string` | No | Registry name of the preferred replacement. |
| `transport` | `object` | Yes | Transport metadata with `supported` and `default`. |
| `install.pip` | `string \| null` | Yes | PyPI package name, or `null` if unavailable. |
| `install.docker` | `string \| null` | Yes | Docker image reference, or `null` if unavailable. |
| `install.npm` | `string \| null` | Yes | npm package name, or `null` if unavailable. |
| `stdio` | `object` | No | Launch config with `command` and `args`. |
| `http` | `object` | No | Launch config with `default_port`, `health_path`, `command`, and `args`. |
| `unix` | `object` | No | Launch config with `socket_template`, `command`, and `args`. |
| `sse` | `object` | No | Launch config with `url_template`, `command`, and `args`. |
| `tools` | `object[]` | Yes | Tool definitions with `name` and `description`. Tool names must be snake_case. |
| `credentials` | `object[]` | Yes | Credential definitions with `id`, `env_var`, `description`, optional `help_url`, and `required`. |
| `tags` | `string[]` | Yes | Search taxonomy tags. Every tag must come from the allowed list below. |
| `categories` | `string[]` | Yes | High-level category labels used by clients. |
| `mcp_protocol_version` | `string` | Yes | MCP protocol version date, such as `2024-11-05`. |
| `hive.min_version` | `string` | If `hive` present | Minimum Hive version supported. |
| `hive.max_version` | `string \| null` | If `hive` present | Maximum Hive version supported, or `null`. |
| `hive.profiles` | `string[]` | If `hive` present | Hive profiles where this server is a strong fit. |
| `hive.tool_namespace` | `string` | If `hive` present | Preferred Hive namespace prefix for tools. |
| `hive.example_agent` | `string` | If `hive` present | URL to an example Hive agent using the server. |

`_comment` fields are allowed anywhere in the manifest and are ignored by tooling. Use them sparingly to make templates clearer.

## Transport Examples

### stdio

Use stdio when the client launches the MCP server as a subprocess.

```json
{
  "transport": { "supported": ["stdio"], "default": "stdio" },
  "stdio": {
    "command": "uvx",
    "args": ["my-server", "--stdio"]
  }
}
```

### http

Use HTTP when the server exposes a local or remote web service and can report health.

```json
{
  "transport": { "supported": ["http"], "default": "http" },
  "http": {
    "default_port": 4010,
    "health_path": "/health",
    "command": "uvx",
    "args": ["my-server", "--http", "--port", "{port}"]
  }
}
```

### unix

Use Unix sockets for low-overhead local communication on Linux or macOS.

```json
{
  "transport": { "supported": ["unix"], "default": "unix" },
  "unix": {
    "socket_template": "/tmp/mcp-{name}.sock",
    "command": "uvx",
    "args": ["my-server", "--unix", "{socket_path}"]
  }
}
```

### sse

Use SSE when the server already exposes a long-lived stream endpoint.

```json
{
  "transport": { "supported": ["sse"], "default": "sse" },
  "sse": {
    "url_template": "http://localhost:{port}/sse",
    "command": "npx",
    "args": ["@scope/my-server", "--sse", "--port", "{port}"]
  }
}
```

## Tag Taxonomy

| Tag | Use when the server is primarily about... |
| --- | --- |
| `project-management` | Planning, task orchestration, boards, or delivery tracking |
| `communication` | Chat, messaging, notifications, or collaboration workflows |
| `crm` | Customer records, deal pipelines, or account management |
| `finance` | Accounting, budgets, billing, procurement, or payments |
| `developer-tools` | Engineering workflows, source control, build systems, or local tooling |
| `productivity` | General business operations and task execution |
| `data` | Data retrieval, transformation, enrichment, or warehousing |
| `atlassian` | Jira, Confluence, or Atlassian ecosystem integrations |
| `google` | Google Workspace or Google Cloud ecosystem integrations |
| `microsoft` | Microsoft 365, Azure, or Microsoft platform integrations |
| `aws` | Amazon Web Services infrastructure or data services |
| `github` | GitHub repositories, issues, or pull requests |
| `issue-tracking` | Tickets, bugs, defects, or incident queues |
| `calendar` | Scheduling, events, attendees, or meeting coordination |
| `email` | Mailboxes, drafts, sending, or inbox triage |
| `database` | Relational or document database access |
| `search` | Web search, enterprise search, or retrieval APIs |
| `ai` | LLM-adjacent workflows, model providers, or AI-native services |
| `analytics` | Reporting, dashboards, BI, or event analysis |
| `storage` | File storage, buckets, objects, or knowledge repositories |
| `monitoring` | Observability, incidents, uptime, or alerting |
| `security` | Security testing, auth, secrets, posture, or compliance |
| `ecommerce` | Orders, products, storefronts, or fulfillment |
| `hr` | Recruiting, people ops, interviews, or employee systems |
| `marketing` | Campaigns, content, attribution, or lead generation |

## CI Checks

The GitHub Action validates:

1. JSON syntax and schema compliance.
2. Registry naming rules and duplicate names.
3. PyPI package existence when `install.pip` is set.
4. snake_case tool names and UPPER_SNAKE_CASE credential env vars.
5. Allowed tag taxonomy usage.
6. Example manifests under `registry/_examples/`.

Common fixes:

- `✗ [SCHEMA]`: compare your manifest against `schema/manifest.schema.json`.
- `✗ [NAME FORMAT]`: rename `name` to lowercase letters, numbers, and hyphens only.
- `✗ [PYPI]`: publish the package first, correct the package name, or set `install.pip` to `null`.
- `✗ [TAGS]`: swap any unsupported tag for one from the taxonomy table above.
- `✗ [README]`: add a sibling `README.md` for real submissions under `registry/servers/`.

## Review Process

Maintainers aim to review straightforward submissions within 3-5 business days.

Reviewers look for:

- Accurate install instructions and transport metadata.
- Clear credential guidance and working docs.
- Tool descriptions that are specific enough for discovery UIs.
- Appropriate trust tier selection.

Trust tier promotion usually works like this:

- New third-party submissions start as `community`.
- Stable entries with reproducible install and auth steps can move to `verified`.
- `official` is reserved for Aden Hive-maintained or explicitly endorsed servers.

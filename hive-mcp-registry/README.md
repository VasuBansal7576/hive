# hive-mcp-registry

![CI](https://img.shields.io/badge/CI-validate.yml-lightgrey)
![License](https://img.shields.io/badge/license-Apache%202.0-blue)
![Servers](https://img.shields.io/badge/servers-0-lightgrey)

## What is this?

`hive-mcp-registry` is the community registry for MCP servers that work well with Hive agents. It provides a portable manifest format, trust metadata, validation tooling, and a generated index so users can discover, compare, and install compatible MCP servers without guessing at transport, credentials, or compatibility details.

## For Users — Discover & Install Servers

Use the registry from Hive CLI workflows:

```bash
hive mcp search github
hive mcp install jira
hive mcp list
```

Those commands consume the validated manifests in this repository and the generated `registry_index.json` file.

## For Contributors — Submit Your Server

1. Copy [`registry/_template/manifest.json`](registry/_template/manifest.json) into a new folder under `registry/servers/<your-server>/`.
2. Fill in the metadata, add a sibling `README.md`, and run `python scripts/validate.py registry/servers/<your-server>/manifest.json`.
3. Open a pull request and include enough docs for maintainers to verify installation, credentials, and trust tier.

Full contributor guidance lives in [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Registry Index

`registry_index.json` is the machine-readable export that clients can cache or mirror. Once hosted from the default branch, the canonical raw URL will be:

`https://raw.githubusercontent.com/aden-hive/hive-mcp-registry/main/registry_index.json`

The index contains the complete manifest payload for every server under `registry/servers/`, sorted alphabetically by name.

## Trust Tiers

| Tier | Meaning | Typical criteria |
| --- | --- | --- |
| `official` | Maintained by Aden Hive or an explicitly endorsed upstream owner | Actively maintained, documented, and tested by core maintainers |
| `verified` | Reviewed by maintainers and confirmed to install and authenticate successfully | Clear docs, stable metadata, working install path, and responsive maintainer |
| `community` | Contributor-submitted entry that passes schema and CI checks | Complete manifest, useful README, and no unresolved validation issues |

# Setup guide

This guide installs `notebooklm-skill` 1.3.x, authenticates a NotebookLM profile,
and configures the Claude Code Skill or MCP server.

## Requirements

- Python 3.10 or newer
- a Google account with access to NotebookLM
- Chromium for the interactive login flow
- `ffmpeg` and Poppler only when using `scripts/make_video.sh`

NotebookLM authentication is browser-based; no application API key is required.
Treat the saved browser state as a password because it contains session cookies.

## Install

### From a source checkout

```bash
git clone https://github.com/claude-world/notebooklm-skill.git
cd notebooklm-skill
./install.sh
```

The installer uses an isolated environment at
`${XDG_DATA_HOME:-~/.local/share}/notebooklm-skill/venv`, avoiding PEP 668 system
Python failures. It links commands to `${XDG_BIN_HOME:-~/.local/bin}`. Add that
directory to `PATH` if necessary.

Override locations with `NOTEBOOKLM_INSTALL_ROOT`, `XDG_BIN_HOME`, or
`NOTEBOOKLM_PYTHON`. The default install is independent of the checkout after it
finishes; developers can opt into an editable install with
`NOTEBOOKLM_INSTALL_EDITABLE=1`.

For a headless or staged install, set `NOTEBOOKLM_SKIP_BROWSER=1`,
`NOTEBOOKLM_SKIP_SKILL=1`, or `NOTEBOOKLM_SKIP_AUTH_CHECK=1`. Skipping Chromium means
browser-based setup will not work until `python -m playwright install chromium` is
run inside the installed environment.

### From PyPI

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install notebooklm-skill
python -m playwright install chromium
```

### With uvx

Run any command in an ephemeral environment:

```bash
uvx --from notebooklm-skill notebooklm-skill --help
uvx --from notebooklm-skill notebooklm-mcp --help
```

## Authenticate

Installed package:

```bash
notebooklm-auth setup
notebooklm-auth verify
```

Use the system Google Chrome when bundled Chromium is unsuitable:

```bash
notebooklm-auth setup --browser chrome --fresh
```

Zero-install upstream login:

```bash
uvx --from notebooklm-py notebooklm login
```

Use named profiles to keep accounts separate:

```bash
notebooklm-auth --profile work setup
notebooklm-auth --profile work verify
notebooklm-skill --profile work list
```

`NOTEBOOKLM_PROFILE=work` selects the same profile through the environment. Current
`notebooklm-py` versions normally store profiles below
`~/.notebooklm/profiles/<profile>/storage_state.json`. Never commit or share those
files.

To log out only the selected profile:

```bash
notebooklm-auth --profile work clear --yes
```

## Verify the CLI

```bash
notebooklm-skill list
notebooklm-skill create --title "Setup test" --text-sources "Hello NotebookLM" --strict
notebooklm-skill ask --notebook "Setup test" --query "What is this source about?"
notebooklm-skill delete --notebook "Setup test" --yes
```

Every command writes JSON to stdout. A nonzero exit code means the operation did not
fully satisfy its contract; source-level partial failures are also represented in the
JSON result.

## Install the Claude Code Skill

The source installer does this automatically. For PyPI or project-local setup:

```bash
# User scope: ~/.claude/skills/notebooklm-research/SKILL.md
notebooklm-install-skill

# Project scope: .claude/skills/notebooklm-research/SKILL.md
notebooklm-install-skill --scope project
```

Changed targets are not overwritten unless `--force` is supplied. Forced updates
create a timestamped backup first. The installer refuses symlink targets.

## Configure MCP

Add the repository's `.mcp.json` or equivalent client configuration:

```json
{
  "mcpServers": {
    "notebooklm": {
      "command": "uvx",
      "args": ["--from", "notebooklm-skill", "notebooklm-mcp"]
    }
  }
}
```

For a locally installed command, replace `command` with `notebooklm-mcp` and omit
`args`.

Restart the MCP client, then call `nlm_list`. Operational exceptions become MCP tool
errors instead of success-shaped error dictionaries. Notebook deletion requires
`confirm=true`.

HTTP mode is for local integration only:

```bash
notebooklm-mcp --http --host 127.0.0.1 --port 8765
```

Non-loopback binds are rejected. Do not bypass this without an authenticated TLS
reverse proxy and host-level access controls.

## Optional trend integration

`notebooklm-pipeline trend-to-content` and `nlm_trend_research` require a
`trend-pulse` executable:

```bash
export TREND_PULSE_CMD=/absolute/path/to/trend-pulse
notebooklm-pipeline trend-to-content --geo TW --count 5 --platform threads
```

The value is parsed as an executable plus arguments and is never passed to a shell.
The pipeline produces drafts; it does not publish them.

## Troubleshooting

### Authentication required or expired

```bash
notebooklm-auth verify
notebooklm-auth setup
```

Make sure the same `--profile` or `NOTEBOOKLM_PROFILE` is used for setup and the
failing command.

### Command not found after `./install.sh`

Add the command directory to your shell configuration:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

### Artifact generation timed out

The Google-side task may still be running. Inspect artifacts and download the exact
one when it appears:

```bash
notebooklm-skill list-artifacts --notebook NOTEBOOK_ID
notebooklm-skill download --notebook NOTEBOOK_ID --type slides \
  --artifact-id ARTIFACT_ID --output deck.pdf
```

### Output file exists

Choose another path or pass `--force` only when an overwrite is intentional. Symlink
destinations are always rejected.

### Browser is missing

Run this inside the environment where `notebooklm-skill` was installed:

```bash
python -m playwright install chromium
```

For defects, use the repository's issue templates. Report vulnerabilities through
the private channel described in [SECURITY.md](../SECURITY.md).

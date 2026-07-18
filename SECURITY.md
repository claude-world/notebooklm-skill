# Security policy

## Supported versions

Security fixes are provided for the latest released minor version.

| Version | Supported |
|---|---|
| 1.3.x | Yes |
| 1.2.x and older | No |

## Security model

`notebooklm-skill` controls a logged-in NotebookLM account and can read explicitly
supplied local files. Treat it as a local privileged tool.

- Browser state below `~/.notebooklm` contains Google session cookies. Never commit,
  log, attach, or share it.
- Prefer named profiles and least-privileged Google accounts for automation.
- `NOTEBOOKLM_AUTH_JSON`, when used by upstream tooling, is a secret equivalent to
  the stored browser state. Keep it in a secret manager, not `.env`.
- Downloads reject symlink targets and existing paths by default. Review any use of
  `--force`.
- Notebook deletion requires explicit confirmation (`--yes` in the CLI,
  `confirm=true` over MCP).
- The MCP HTTP transport accepts loopback hosts only. Do not expose it directly to a
  LAN or the public internet. Remote use requires an authenticated TLS reverse proxy
  and host-level access controls.
- MCP file-source and download arguments are local paths. Only grant MCP access to
  clients you trust with the current operating-system account.
- Keep `notebooklm-skill` and `notebooklm-py` current because NotebookLM's unofficial
  web API can change without notice.

## Reporting a vulnerability

Do not open a public issue for a suspected vulnerability. Use
[GitHub Private Vulnerability Reporting](https://github.com/claude-world/notebooklm-skill/security/advisories/new)
or email `security@claude-world.com`.

Include affected versions, reproduction steps, impact, and any suggested mitigation.
Do not include live session cookies or other credentials. We aim to acknowledge a
report within 48 hours.

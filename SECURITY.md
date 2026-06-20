# Security policy

Report vulnerabilities privately through GitHub's security advisory feature.
Do not open a public issue containing exploit details or credentials.

## Deployment requirements

- Keep `mnemo-core` behind a trusted reverse proxy.
- Use long random API and webhook secrets.
- Give the GitHub service account branch and pull-request permissions only.
- Require human approval through branch protection.
- Restrict `FRONTEND_ORIGIN` and URL source allow-lists.
- Persist and protect the SQLite state database.
- Terminate TLS at the proxy or ingress.

Mnemosyne stores API tokens only in process configuration. The web UI keeps its
token in browser session storage.

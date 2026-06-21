# Security policy

## Reporting a vulnerability

Report vulnerabilities privately through
[GitHub security advisories](https://github.com/pabooth/mnemosyne/security/advisories/new).
Do not open a public issue containing exploit details, credentials, private
documents, or generated confidential content.

## Supported versions

Only the latest released version receives security fixes.

## Deployment requirements

- Keep `mnemo-core` behind a trusted reverse proxy.
- Keep direct core and observability ports bound to loopback or an internal
  network.
- Use long random API and webhook secrets.
- Set a long random `GRAFANA_ADMIN_PASSWORD` before enabling observability.
- Give the GitHub service account branch and pull-request permissions only.
- Require human approval through branch protection.
- Restrict `FRONTEND_ORIGIN` and URL source allow-lists.
- Persist and protect the SQLite state database.
- Replace the root compatibility default with a dedicated `MNEMO_UID` and
  `MNEMO_GID`, and restrict the state directory to that identity.
- Terminate TLS at the proxy or ingress.

Mnemosyne stores API tokens only in process configuration. The web UI keeps its
token in browser session storage.

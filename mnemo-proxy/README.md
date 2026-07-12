# mnemo-proxy

`mnemo-proxy` is Mnemosyne's optional edge-routing component. It provides a
single HTTP entry point, routing `/` to `mnemo-ui` and `/api/`, `/mcp/`, and
`/health` to `mnemo-core`.

It contains no ingestion, authentication, publishing, or governance logic.
Production deployments should terminate TLS and enforce any site-level access
policy at an ingress in front of this container.

Build it from the repository root with:

```console
docker build -t mnemo-proxy:local mnemo-proxy
```

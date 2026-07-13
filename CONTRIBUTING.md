# Contributing

Open an issue before substantial changes so architecture and scope can be
agreed first.

Participation in this project is governed by the
[Code of Conduct](./CODE_OF_CONDUCT.md).
Maintainer releases follow [RELEASING.md](./RELEASING.md).

## Checks

```bash
cd mnemo-core
.venv/bin/pytest -q

cd ../mnemo-ui
npm test
npm run build

cd ..
MNEMO_HOME=/tmp docker compose config
```

Pull requests must preserve mandatory human review: no code path may merge
generated content or write directly to the protected knowledge-base branch.

New LLM providers must implement `LLMProvider` and include tests for factory
selection and valid structured output. Security-sensitive changes should
include negative tests.

With provider credentials configured, run the small prompt regression suite:

```bash
mnemo-evaluate --minimum-accuracy 0.75
mnemo-evaluate --version
```

This makes live provider calls and is intentionally not part of ordinary CI.

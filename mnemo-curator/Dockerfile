FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml ./
COPY README.md LICENSE ./
COPY mnemo_curator/ ./mnemo_curator/

RUN pip install .

CMD ["mnemo-curator", "scan"]

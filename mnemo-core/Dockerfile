FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml ./
COPY README.md LICENSE ./
COPY mnemo_core/ ./mnemo_core/

RUN pip install .

EXPOSE 7777

CMD ["python", "-m", "uvicorn", "mnemo_core.api.app:app", "--host", "0.0.0.0", "--port", "7777"]

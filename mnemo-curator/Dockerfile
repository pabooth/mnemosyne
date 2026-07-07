FROM python:3.12-slim@sha256:423ed6ab25b1921a477529254bfeeabf5855151dc2c3141699a1bfc852199fbf

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml ./
COPY README.md LICENSE ./
COPY mnemo_curator/ ./mnemo_curator/

RUN pip install .

RUN useradd --system --no-create-home --shell /usr/sbin/nologin mnemo-curator
USER mnemo-curator

CMD ["mnemo-curator", "scan"]

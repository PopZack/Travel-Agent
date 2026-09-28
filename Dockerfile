FROM python:3.12-slim

WORKDIR /app

# 装 uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml ./
COPY src ./src
COPY app ./app

RUN uv sync --no-dev

EXPOSE 8501
CMD ["uv", "run", "streamlit", "run", "app/streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]

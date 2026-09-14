ARG PYTHON_IMAGE=python:3.12-slim
FROM ${PYTHON_IMAGE}
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

RUN pip install --no-cache-dir uv==0.11.19
COPY pyproject.toml uv.lock README.md LICENSE ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src ./src
RUN uv sync --frozen --no-dev

EXPOSE 8000
CMD ["uvicorn", "researchforge.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]

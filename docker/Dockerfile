# Base Image for builder
FROM python:3.14.7-slim as builder

# Default env vars for python and uv
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Install uv from official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install system dependencies (add gcc here if you STILL want to compile orjson manually)
RUN apt-get update -y \
    && apt-get install -y --no-install-recommends curl ffmpeg libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Create directory for the app user
ENV USER=app
ENV HOME=/home/$USER
ENV APP_HOME=${HOME}/cerrrbot
ENV DATA_DIR_PATH=${HOME}/data

# Setup user and directories
RUN groupadd $USER \
    && useradd -m -g $USER $USER \
    && if ! getent group 101 > /dev/null; then groupadd -g 101 tgserver; fi \
    && usermod -aG 101 $USER \
    && mkdir -p $APP_HOME $DATA_DIR_PATH \
    && chown -R $USER:$USER $HOME

WORKDIR $APP_HOME

# Switch to non-root user
USER $USER

# Copy project files and lockfile
COPY --chown=$USER:$USER pyproject.toml uv.lock ./
COPY --chown=$USER:$USER app/ ./app/

# Sync dependencies using uv (creates .venv automatically)
RUN uv sync --frozen --no-dev --all-packages

# Add the virtual environment to PATH so python/celery commands work globally
ENV PATH="$APP_HOME/.venv/bin:$PATH"

CMD ["uv", "run", "-m", "app"]
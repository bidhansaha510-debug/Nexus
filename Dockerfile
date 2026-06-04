# ═══════════════════════════════════════════════════════════════
#  NEXUS AI — Dockerfile
#  Python 3.12.0 | Web mode (Flask + Ngrok)
# ═══════════════════════════════════════════════════════════════

FROM python:3.12.0-slim

# ── Metadata ──────────────────────────────────────────────────
LABEL maintainer="NEXUS AI"
LABEL description="NEXUS AI System — Containerised runtime"

# ── System dependencies ──────────────────────────────────────
# Build essentials for compiled Python packages (numpy, etc.)
# plus runtime libs for common requirements
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    git \
    curl \
    libffi-dev \
    libssl-dev \
    libportaudio2 \
    portaudio19-dev \
    libxml2-dev \
    libxslt1-dev \
    && rm -rf /var/lib/apt/lists/*

# ── Working directory ─────────────────────────────────────────
WORKDIR /app

# ── Install Python dependencies ──────────────────────────────
# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Create a cleaned requirements file:
#   - Remove stdlib modules (sqlite3, asyncio, ast) that can't be pip-installed
#   - Remove Windows-only packages (pywin32, wmi, pyautogui, etc.)
#   - Remove GUI packages (customtkinter, tkinter-tooltip, PySide6)
#   - Remove duplicate entries
RUN sed -e '/^sqlite3/d' \
        -e '/^asyncio/d' \
        -e '/^ast/d' \
        -e '/^pywin32/d' \
        -e '/^wmi/d' \
        -e '/^pyautogui/d' \
        -e '/^pygetwindow/d' \
        -e '/^keyboard/d' \
        -e '/^mouse/d' \
        -e '/^pynput/d' \
        -e '/^screeninfo/d' \
        -e '/^customtkinter/d' \
        -e '/^tkinter-tooltip/d' \
        -e '/^PySide6/d' \
        -e '/^pyttsx3/d' \
        -e '/^pyaudio/d' \
        -e '/^SpeechRecognition/d' \
        -e '/^matplotlib/d' \
        -e '/^plotly/d' \
        -e '/^pickle5/d' \
        requirements.txt > requirements_docker.txt \
    && pip install --no-cache-dir -r requirements_docker.txt \
    && rm requirements_docker.txt

# ── Copy application code ────────────────────────────────────
COPY . .

# ── Environment ──────────────────────────────────────────────
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV RENDER=true

# ── Expose the Flask web server port ─────────────────────────
EXPOSE 5000

# ── Health check ─────────────────────────────────────────────
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:${PORT:-5000}/ || exit 1

# ── Default entrypoint: Web mode ─────────────────────────────
CMD ["python", "main.py", "--web"]

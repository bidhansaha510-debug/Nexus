FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install cloudflared
RUN curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o /usr/local/bin/cloudflared \
    && chmod +x /usr/local/bin/cloudflared

# Copy requirements first (for Docker layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt || \
    pip install --no-cache-dir flask gunicorn requests beautifulsoup4 \
    transformers sentence-transformers chromadb nltk textblob \
    duckduckgo-search numpy networkx rich psutil edge-tts Pillow

# Copy project files
COPY . .

# Create data directories
RUN mkdir -p data/screenshots data/sessions data/self_rewriter/backups

# Expose port (Render expects a PORT env var)
EXPOSE 10000

# Start script
COPY start.sh .
RUN chmod +x start.sh
CMD ["./start.sh"]

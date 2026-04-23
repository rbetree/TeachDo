# Use a slim Python base to reduce image size.
FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    LC_ALL=C.UTF-8 \
    LANG=C.UTF-8 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
ARG PIP_INDEX_URL=https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple
RUN python -m pip install --no-cache-dir -r requirements.txt -i "${PIP_INDEX_URL}"

# Copy the rest of the application's code into the container at /app
COPY . .

# Create non-root user and ensure write permissions for mounted volumes
RUN groupadd -r appuser && useradd -r -g appuser appuser \
    && mkdir -p /app/var /app/logs \
    && chown -R appuser:appuser /app/var /app/logs
USER appuser

# Health check using the built-in healthz endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:6800/healthz', timeout=2).read()"

# Expose port 6800 to the outside world
EXPOSE 6800

# Command to run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "6800"]

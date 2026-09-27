# Production Dockerfile for Student Result Management System (SRMS)
FROM python:3.13-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir gunicorn==23.0.0

# Copy project files
COPY . /app/

# Create a non-root user and set permissions
RUN mkdir -p /app/static /app/media \
    && groupadd -r srms && useradd -r -g srms srms \
    && chown -R srms:srms /app

# Switch to the non-root user
USER srms

# Expose port
EXPOSE 8000

# Run gunicorn
CMD ["gunicorn", "StudentResultManagement.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]

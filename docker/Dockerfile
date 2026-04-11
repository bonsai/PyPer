# Dockerfile for PyPer Web API
FROM python:3.10-slim

WORKDIR /app

# Install Node.js for building LINE Mini App frontend
RUN apt-get update && apt-get install -y nodejs npm

# Install Python dependencies
COPY webapp/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY webapp/ .

# Build LINE Mini App frontend
COPY line-minigram/ /tmp/line-minigram/
WORKDIR /tmp/line-minigram
RUN npm install && npm run build

# Copy built frontend to static folder
RUN mkdir -p /app/static && cp -r build/* /app/static/

WORKDIR /app

# Expose port
EXPOSE 8080

# Run with gunicorn for production
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 main:app

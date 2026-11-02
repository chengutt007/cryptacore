FROM python:3.11-slim

WORKDIR /app

# Copy requirements first for better layer caching
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the backend code
COPY backend/ ./backend/

# Copy ML models and code
COPY ml/ ./ml/

# Set PYTHONPATH to include ml directory
ENV PYTHONPATH=/app:$PYTHONPATH

# Expose the port
EXPOSE 8000

# Change to backend directory and run the application
WORKDIR /app/backend
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

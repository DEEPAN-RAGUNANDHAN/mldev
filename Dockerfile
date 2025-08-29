# Use an official lightweight Python image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy files
COPY . /app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the default port (optional: FastAPI can run on dynamic ports)
# You can hardcode a default here or override using Docker run/env
EXPOSE 8080

# Run the app (using env variable from .env)
CMD ["python", "-m", "uvicorn", "app:app", "--reload", "--host", "0.0.0.0", "--port", "8080"]
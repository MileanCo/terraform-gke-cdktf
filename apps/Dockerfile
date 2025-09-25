FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set environment variables
ENV FLASK_APP=flask_app.py
ENV PYTHONUNBUFFERED=1

# Default port (can be overridden by .env file at runtime)
ENV PORT=5001

# Expose port dynamically based on PORT environment variable
EXPOSE $PORT

# Run the application
CMD ["python", "flask_app.py"]

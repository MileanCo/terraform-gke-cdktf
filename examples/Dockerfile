FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 5000

# Set environment variables
ENV FLASK_APP=sample_flask_app.py
ENV PYTHONUNBUFFERED=1

# Run the application
CMD ["python", "sample_flask_app.py"]

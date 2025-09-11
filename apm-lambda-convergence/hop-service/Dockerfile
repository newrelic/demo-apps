# Use the official Python 3.13 slim image as a base
FROM python:3.12-slim

# Set the working directory inside the container
WORKDIR /code

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Copy the application source code
COPY . .

# Expose the port the app runs on
EXPOSE 8001

# Start the application with the NR APM agent agent initialized
CMD ["newrelic-admin", "run-program", "gunicorn", "--workers", "4", "--bind", "0.0.0.0:8001", "main:app"]

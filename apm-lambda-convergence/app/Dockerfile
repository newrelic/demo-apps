# Use the official Python 3.13 slim image as a base
FROM python:3.13-slim

# Set the working directory inside the container
WORKDIR /code

# Copy the requirements file into the container
# This is done first to leverage Docker's layer caching.
# The dependencies will only be re-installed if this file changes.
COPY requirements.txt .

# Install the Python dependencies
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Copy the rest of the application source code (main.py, static/, templates/)
COPY . .

# Expose the port that Gunicorn will run on
EXPOSE 8000

# Specify the command to run the application using Gunicorn
# --workers 4: Spawns 4 worker processes to handle requests.
# --bind 0.0.0.0:8000: Binds to all network interfaces on port 8000.
# main:app: Tells Gunicorn to run the 'app' Flask object from the 'main.py' file.
CMD ["gunicorn", "--workers", "4", "--bind", "0.0.0.0:8000", "main:app"]

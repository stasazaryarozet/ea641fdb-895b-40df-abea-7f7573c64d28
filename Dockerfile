# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
# We will create a specific, minimal requirements.txt for the handler
RUN pip install --no-cache-dir Flask gunicorn

# Copy the form handler and wsgi entrypoint into the container
COPY form_handler.py .
COPY wsgi.py .

# Make port 8080 available to the world outside this container
EXPOSE 8080

# Define environment variable
ENV PORT 8080

# Run wsgi.py when the container launches
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "wsgi:app"] 
# Use the Python 3.10.4 version of the Docker base image
FROM python:3.10.4-bullseye

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Create a working directory
WORKDIR /usr/src/app

# Copy dependency list
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the app code and instance folder
COPY ./website ./website
COPY ./main.py .
COPY ./instance ./instance

# Make sure the instance folder (for SQLite DB) is writable
RUN chmod -R g+w ./instance
RUN mkdir -p /usr/src/app/website/static/images/products && \
    chmod -R g+w /usr/src/app/website/static/images/products


EXPOSE 5000

# Run the Flask app via main.py
#CMD ["python", "main.py"]

# Alternative: Run using Gunicorn (production)
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "main:app"]

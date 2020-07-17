# Use the official lightweight Python image.
# https://hub.docker.com/_/python
FROM python:3.7-slim

ARG DB_TYPE
ENV DB_TYPE=${DB_TYPE:-mysql}

WORKDIR /app

# First, install deps; they are likely to change less than
# app code, so this will optimize layer cache
COPY requirements.txt /app
RUN pip install -r requirements.txt

# Copy the rest of the application code
COPY . /app

CMD ["python","app.py"]
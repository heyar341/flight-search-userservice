FROM python:3.10.2-slim

WORKDIR /app

COPY requirements.txt .
RUN apt -y update && apt -y install git \
    && python -m pip install --upgrade pip \
    && python -m pip install --no-cache-dir -r requirements.txt

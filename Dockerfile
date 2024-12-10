FROM python:3.12-slim-bookworm

ENV PIP_DISABLE_PIP_VERSION_CHECK 1
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /raceEngineer

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .
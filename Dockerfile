FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgeos-dev libproj-dev gdal-bin libgdal-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8050

ENV ARIA_HOST=0.0.0.0

ENTRYPOINT ["./entrypoint.sh"]

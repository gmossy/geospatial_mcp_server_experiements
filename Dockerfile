FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (for GDAL/Rasterio if needed, though wheels usually suffice)
RUN apt-get update && apt-get install -y \
    gdal-bin \
    libgdal-dev \
    libexpat1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Expose ports for MCP Server (8000) and Gradio (7860)
EXPOSE 8000
EXPOSE 7860

# Start script
COPY start.sh .
RUN chmod +x start.sh

CMD ["./start.sh"]

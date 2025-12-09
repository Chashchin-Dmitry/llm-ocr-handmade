FROM python:3.11-slim

WORKDIR /app

# Install system dependencies including LibreOffice for DOC/DOCX conversion
RUN apt-get update && apt-get install -y \
    libmagic1 \
    poppler-utils \
    libreoffice-writer \
    libreoffice-common \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY backend/ ./backend/

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]

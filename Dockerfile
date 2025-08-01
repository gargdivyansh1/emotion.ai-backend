# Use Python 3.10 base image for TensorFlow 2.19.0 compatibility
FROM python:3.10-slim

# Environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install system dependencies for image processing, numpy, etc.
RUN apt-get update && apt-get install -y \
    build-essential \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copy entire project
COPY . .

# Expose the port (Render/other hosts use 10000)
EXPOSE 10000

# Run the FastAPI app using uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "10000"]

# Install system dependencies for OpenCV, DeepFace, and PostgreSQL
RUN apt-get update && apt-get install -y \
    # PostgreSQL dependencies
    libpq-dev \
    # Python build dependencies
    python3-dev \
    # OpenCV dependencies (for Haar cascades)
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    # DeepFace & TensorFlow dependencies
    libopenblas-dev \
    liblapack-dev \
    gfortran \
    # Video/Image processing (optional but recommended)
    ffmpeg \
    libsm6 \
    libxext6 \
    # Clean up to reduce image size
    && rm -rf /var/lib/apt/lists/*

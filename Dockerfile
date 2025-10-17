#FROM python:3.13-slim
FROM nvcr.io/nvidia/pytorch:25.05-py3

WORKDIR /app

COPY pyproject.toml uv.lock* /app/

RUN pip install uv

# Install dependencies into the venv
RUN uv sync

RUN apt-get update && \
    apt-get install -y \
    libmagic-dev \
    libgl1 \
    poppler-utils \
    tesseract-ocr \
    tesseract-ocr-spa \
    tesseract-ocr-eng

COPY . /app/

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
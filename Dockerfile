FROM python:3.13-slim

WORKDIR /app

COPY pyproject.toml uv.lock* /app/

RUN pip install uv

# Install dependencies into the venv
RUN uv sync

COPY . /app/

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"] 
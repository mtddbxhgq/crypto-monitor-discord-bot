FROM python:3.12-slim

WORKDIR /app

# Security: run as non-root user
RUN adduser --disabled-password --gecos "" botuser

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot.py .

RUN chown -R botuser:botuser /app
USER botuser

CMD ["python", "-u", "bot.py"]

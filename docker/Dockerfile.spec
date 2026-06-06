FROM python:3.11-slim

RUN pip install --no-cache-dir pyyaml

COPY docker/spec_validator.py /app/spec_validator.py

WORKDIR /app

CMD ["python", "spec_validator.py"]

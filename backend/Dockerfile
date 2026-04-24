FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY backend/requirements.txt backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy dataset and backend
COPY dataset/ dataset/
COPY backend/ backend/

# Train models
WORKDIR /app/backend
RUN python train_model.py

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

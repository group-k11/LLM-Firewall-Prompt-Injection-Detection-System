FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY backend/requirements.txt backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

# Pre-download the Sentence Transformer model weights at build time.
# This prevents a cold-start delay on the first user request and avoids
# runtime failures if the container has no outbound internet access.
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Copy dataset and backend source
COPY dataset/ dataset/
COPY backend/ backend/

# Train ML models (SVM + transformer classifier)
WORKDIR /app/backend
RUN python train_model.py

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

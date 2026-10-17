# Hugging Face Space (Docker SDK) / any container host. Not deployed: no HF_TOKEN available.
FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1 HF_HOME=/app/.cache/hf PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY citesure ./citesure
RUN pip install --extra-index-url https://download.pytorch.org/whl/cpu .
COPY config ./config
COPY data/corpus_manifest.yaml ./data/corpus_manifest.yaml
COPY scripts ./scripts
COPY static ./static
COPY eval ./eval
# Public NIST PDFs are downloaded at build time, the index is built at build time (no runtime ingest),
# and the embedding + re-rank models are cached into the image.
RUN python scripts/download_corpus.py && python -m citesure.ingest.cli all \
 && python -c "from sentence_transformers import CrossEncoder; CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')"
EXPOSE 7860
# ANTHROPIC_API_KEY, LLM_PROVIDER, LLM_MODEL are provided as Space secrets / env vars, never baked in.
CMD ["python", "-m", "uvicorn", "citesure.app:app", "--host", "0.0.0.0", "--port", "7860"]

# CiteSure demo image. Hugging Face Spaces (Docker SDK) compatible: listens on 7860, runs as uid 1000.
FROM python:3.11-slim

RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user PATH=/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 HF_HOME=/home/user/.cache/hf \
    TOKENIZERS_PARALLELISM=false
WORKDIR /home/user/app

# CPU-only torch wheel (much smaller than the default CUDA build).
RUN pip install torch --index-url https://download.pytorch.org/whl/cpu

COPY --chown=user pyproject.toml README.md LICENSE ./
COPY --chown=user citesure ./citesure
RUN pip install .

COPY --chown=user config ./config
COPY --chown=user data ./data
COPY --chown=user scripts ./scripts
COPY --chown=user static ./static
COPY --chown=user eval ./eval

# Build time: fetch the public NIST PDFs (skipped if already present in data/raw), build the index
# (downloads the embedding model into HF_HOME) and cache the cross-encoder re-ranker.
# No runtime ingest, nothing is written at runtime.
RUN python scripts/download_corpus.py && python -m citesure.ingest.cli all \
 && python -c "from sentence_transformers import CrossEncoder; CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')"

# Models are cached in the image: never reach out to the Hub at runtime; preload them at startup.
ENV HF_HUB_OFFLINE=1 CITESURE_WARMUP=1
EXPOSE 7860
# ANTHROPIC_API_KEY (secret), LLM_PROVIDER, LLM_MODEL, DEMO_DAILY_QUESTION_CAP come from the environment.
# --proxy-headers so per-IP limits see the real client behind the Spaces proxy.
CMD ["python", "-m", "uvicorn", "citesure.app:app", "--host", "0.0.0.0", "--port", "7860", "--proxy-headers", "--forwarded-allow-ips", "*"]

FROM python:3.12-slim
WORKDIR /app
COPY engine/pyproject.toml engine/pyproject.toml
COPY engine/corvo_engine engine/corvo_engine
ENV PYTHONPATH=/app/engine PYTHONUNBUFFERED=1
# A cada 10 min lê os feeds, passa pelo portão e envia o aprovado à API (memória de já vistos em /state).
CMD ["python", "-m", "corvo_engine.collect", "--interval", "600", "--state", "/state/seen.sqlite"]

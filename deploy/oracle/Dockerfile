FROM python:3.12-slim
WORKDIR /app
COPY engine/pyproject.toml engine/pyproject.toml
COPY engine/corvo_engine engine/corvo_engine
ENV PYTHONPATH=/app/engine PYTHONUNBUFFERED=1
COPY deploy/oracle/loop.sh /loop.sh
RUN chmod +x /loop.sh
# A cada 60 s publica o que houver na caixa de entrada (/inbox/*.jsonl) e move o arquivo para /state/done.
CMD ["/loop.sh"]

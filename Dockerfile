# Optional container. It exists to prove the point: the base image needs
# nothing added to it, because the program has no dependencies.
FROM python:3.12-slim
WORKDIR /app
COPY . .
# Generate once at build time so the image ships with a report already in it.
RUN python3 -m unittest discover -s tests -t . && python3 solana_pulse.py --out out --blocks 3
# Default: run forever, regenerating every 30 minutes.
ENTRYPOINT ["python3", "solana_pulse.py"]
CMD ["--interval", "30m", "--out", "out"]

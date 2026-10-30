FROM ubuntu:24.04
RUN apt-get update && apt-get install -y --no-install-recommends btrfs-progs && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY run.sh .
CMD ["bash", "run.sh"]

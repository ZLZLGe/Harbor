FROM python:3.11-slim

WORKDIR /root

RUN mkdir -p /root/workspace
COPY workspace/build_genome_assets.py /root/workspace/build_genome_assets.py
COPY workspace/genome_fixture.py /root/workspace/genome_fixture.py
COPY workspace/kmer_counter_baseline.py /root/workspace/kmer_counter_baseline.py
COPY skills /root/.codex/skills

RUN python -m pip install --no-cache-dir pytest==8.4.1
RUN python /root/workspace/build_genome_assets.py

CMD ["python", "--version"]

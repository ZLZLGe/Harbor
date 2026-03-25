FROM python:3.11-slim-bookworm

ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /root

RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice-calc

RUN pip install --no-cache-dir openpyxl==3.1.5 pytest==8.4.1

COPY bond-stress-template.xlsx /root/bond-stress-template.xlsx
COPY portfolio_holdings.csv /root/portfolio_holdings.csv
COPY coupon_calendar.csv /root/coupon_calendar.csv
COPY risk_free_curve.csv /root/risk_free_curve.csv
COPY recovery_assumptions.csv /root/recovery_assumptions.csv
COPY skills /root/.codex/skills

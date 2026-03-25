FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /root

RUN pip install --no-cache-dir \
    pypdf==5.4.0 \
    pytest==8.4.1

COPY skills /root/.codex/skills
COPY enrollment_builder /tmp/enrollment_builder

RUN mkdir -p /root/enrollment/forms \
    && cp /tmp/enrollment_builder/intake_profile.json /root/enrollment/intake_profile.json \
    && python3 /tmp/enrollment_builder/build_enrollment_form.py \
        /root/enrollment/forms/employee_enrollment_form \
    && rm -rf /tmp/enrollment_builder

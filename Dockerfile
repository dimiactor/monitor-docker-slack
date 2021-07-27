FROM python:latest

ENV SLACK_CHANNEL ""
ENV SLACK_TOKEN ""

USER root
WORKDIR /
ADD requirements.txt /requirements.txt

RUN pip install -r requirements.txt && \
# Verify docker image
    pip show requests-unixsocket | grep "0.1.5"

ADD monitor-docker-slack.py /monitor-docker-slack.py
ADD monitor-docker-slack.sh /monitor-docker-slack.sh

RUN chmod o+x /*.sh && chmod o+x /*.py

ENTRYPOINT ["/monitor-docker-slack.sh"]

FROM python:3.6-slim
ARG user
ARG password
ADD requirements.lock /
RUN pip install --upgrade --extra-index-url https://$user:$password@distribution.livetech.site -r /requirements.lock
ADD . /loko-orchestrator
ENV PYTHONPATH=$PYTHONPATH:/loko-orchestrator
WORKDIR /loko-orchestrator/loko_orchestrator/services
CMD python services.py

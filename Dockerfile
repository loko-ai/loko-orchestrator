FROM python:3.10-slim
ARG user
ARG password
ADD requirements.lock /
RUN pip install --upgrade --extra-index-url https://$user:$password@distribution.livetech.site -r /requirements.lock
ADD . /loko-orchestrator
ENV PYTHONPATH=$PYTHONPATH:/loko-orchestrator
WORKDIR /loko-orchestrator/loko_orchestrator/services
#RUN groupadd -r loko -g 1001 && useradd -u 1001 --no-log-init -r -g loko loko
#USER loko
CMD groupadd -r loko -g ${USER_GID} && useradd -u ${USER_UID} --no-log-init -r -g loko loko && su loko -c "python services.py"

FROM python:3.10-slim
RUN apt-get update && apt-get install -y git
RUN pip install pyarmor
ARG user
ARG password
ADD requirements.lock /
RUN pip install -r /requirements.lock
ADD . /loko-orchestrator
#WORKDIR /loko-orchestrator/loko_orchestrator/services
WORKDIR /loko-orchestrator/loko_orchestrator/services
# RUN pyarmor obfuscate --exact services.py
RUN mkdir /obfuscated
RUN mv services.py /obfuscated
WORKDIR /obfuscated
RUN pyarmor obfuscate services.py
RUN rm services.py
WORKDIR /obfuscated/dist
ENV PYTHONPATH=$PYTHONPATH:/loko-orchestrator
# RUN pyarmor obfuscate -O /dist loko_orchestrator/services/services.py
# RUN pyarmor obfuscate --src="." -r --output=/dist loko_orchestrator/services/services.py
# RUN rm -rf /loko-orchestrator
# WORKDIR /dist
# WORKDIR /loko-orchestrator/loko_orchestrator/services
# ENV PYTHONPATH=$PYTHONPATH:/dist

#CMD python services.py
#RUN groupadd -r loko -g 1001 && useradd -u 1001 --no-log-init -r -g loko loko
#USER loko
CMD groupadd -r loko -g ${USER_GID} && useradd -u ${USER_UID} --no-log-init -r -g loko loko && su loko -c "python services.py"

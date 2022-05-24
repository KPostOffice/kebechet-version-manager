FROM centos/python-38-centos7 AS base

# Setup env
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONFAULTHANDLER 1

FROM base AS python-deps

USER 0

RUN pip install pipenv

# Install python dependencies in /op/app-root/.venv
COPY controller/Pipfile .
COPY controller/Pipfile.lock .
# Need PIPENV_IGNORE_VIRTUALENVS because py38 is a venv in centos7
RUN mkdir .venv && PIPENV_IGNORE_VIRTUALENVS=1 PIPENV_VENV_IN_PROJECT=1 pipenv install --deploy

FROM base AS runtime

USER 0

COPY ./controller/app /opt/app-root/src/controller
# Remove symbolic link used for local dev and replace it with actual content
RUN rm /opt/app-root/src/controller/common
COPY ./common /opt/app-root/src/controller/common

COPY --from=python-deps /opt/app-root/src/.venv /opt/app-root/src/.venv

WORKDIR /opt/app-root/src/controller

CMD source /opt/app-root/src/.venv/bin/activate && flask run
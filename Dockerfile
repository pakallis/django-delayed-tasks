FROM python:3.9

ENV PYTHONFAULTHANDLER=1 \
  PYTHONUNBUFFERED=1 \
  PYTHONHASHSEED=random \
  PIP_NO_CACHE_DIR=1 \
  PIP_DISABLE_PIP_VERSION_CHECK=1 \
  PIP_DEFAULT_TIMEOUT=100 \
  POETRY_VERSION="1.2.0" \
  POETRY_HOME="/opt/poetry" \
  POETRY_NO_INTERACTION=1 \
  POETRY_VIRTUALENVS_IN_PROJECT=true \
  PYSETUP_PATH="/opt/pysetup" \
  VENV_PATH="/opt/pysetup/.venv"

ENV PATH="$POETRY_HOME/bin:$VENV_PATH/bin:$PATH"


RUN curl -sSL https://install.python-poetry.org | python3 -



WORKDIR $PYSETUP_PATH
COPY poetry.lock pyproject.toml $PYSETUP_PATH

RUN poetry install

WORKDIR /app/
COPY entrypoint.sh /app/
COPY . /app/
ENTRYPOINT ["/app/entrypoint.sh"]

FROM python:3.9-slim-buster

WORKDIR /app

RUN apt update && apt install jq -y
COPY ./Pipfile.lock ./Pipfile.lock
RUN jq -r '.default | to_entries[] | .key + .value.version ' Pipfile.lock > requirements.txt
RUN pip install -r requirements.txt \
    && rm -rf ~/.cache/pip \
    && cd /usr/local/lib/python3.9/site-packages/ \
    && rm -r **/__pycache__ \
    && rm -r *.dist-info \
    && rm -r **/tests

COPY ./ ./

ENTRYPOINT ["bash", "/app/entrypoint.sh"]
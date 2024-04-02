FROM python:3.11

WORKDIR /code

# copy only the requirements, this install step can take a while
# and requirements don't change as often as code, so doing it
# this way allows docker to cache the env
COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY ./app /code/app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]


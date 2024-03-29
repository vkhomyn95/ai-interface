FROM python:3.10

WORKDIR /usr/src

COPY requirements.txt requirements.txt

RUN python -m venv venv

RUN python -m pip install Flask

RUN python -m pip install mariadb

RUN venv/bin/pip3 install --no-cache-dir -r requirements.txt

COPY . ./

EXPOSE 5000

ENTRYPOINT ["python3", "-u", "app.py"]

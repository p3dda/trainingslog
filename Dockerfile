FROM debian:jessie
ENV PYTHONUNBUFFERED 1
RUN mkdir /code
WORKDIR /code
ADD requirements.txt /code/
RUN apt-get update && apt-get install -y \
    python \
    python-pip
RUN pip install -r requirements.txt
ADD . /code/

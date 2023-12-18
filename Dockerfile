FROM python:3.10-bullseye
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update
RUN apt-get -y install sudo
RUN apt-get install -y apt-transport-https ca-certificates dirmngr
RUN apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv 8919F6BD2B48D754
RUN echo "deb https://packages.clickhouse.com/deb stable main" | tee \
    /etc/apt/sources.list.d/clickhouse.list
RUN apt-get update

RUN apt-get install -y clickhouse-server
RUN service clickhouse-server start
RUN service clickhouse-server status

COPY . /app
WORKDIR /app

RUN pip install --upgrade pip
RUN pip install --upgrade setuptools
RUN pip install -r requirements.txt

CMD ["bash", "-c", "service clickhouse-server start && uvicorn main:app --host 0.0.0.0 --port 8080"]

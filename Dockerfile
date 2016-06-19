FROM ubuntu:latest

RUN apt update
RUN apt install python3.5 -y

COPY indexer/ indexer/

CMD /usr/bin/python3.5 -m indexer.main

FROM webrecorder/pywb

USER root
RUN pip install fakeredis redis

WORKDIR /app
RUN chown archivist /app

USER archivist

ADD *.py /app/
ADD uwsgi.ini /app/
ADD config.yaml /app/

RUN wb-manager init store

ENV REDIS_URL=redis://redis/0

CMD uwsgi uwsgi.ini


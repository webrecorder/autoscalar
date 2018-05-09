FROM webrecorder/pywb

USER root
RUN pip install fakeredis redis

#RUN mkdir /app && chown archivist /app

ENV CLIENT_REDIS_URL=redis://redis/0
ENV QUEUE_REDIS_URL=redis://redis/2

RUN mkdir -p /data/warcs

WORKDIR /data/warcs

ENV PYWB_CONFIG_FILE=/app/config.yaml

ADD config.yaml /app/

ADD *.py /app/
ADD uwsgi.ini /app/
ADD capture.ini /app/

ADD run.sh /app/

ADD ./templates/ /app/templates/
ADD ./static/ /app/static/

CMD /app/run.sh


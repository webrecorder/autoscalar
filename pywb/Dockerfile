FROM webrecorder/pywb

USER root
RUN pip install fakeredis redis

#RUN mkdir /app && chown archivist /app

ENV REDIS_URL=redis://redis/0

ADD *.py /app/
ADD uwsgi.ini /app/
ADD config.yaml /app/

RUN mkdir -p /data/warcs

#USER archivist

WORKDIR /data/warcs

ENV PYWB_CONFIG_FILE=/app/config.yaml

ADD run.sh /app/

ADD ./templates/ /app/templates/
ADD ./static/ /app/static/

CMD /app/run.sh


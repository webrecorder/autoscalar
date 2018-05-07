FROM python:3.5.3

RUN mkdir /app
WORKDIR /app

ADD requirements.txt /app
RUN pip install -r requirements.txt

ADD templates/ /app/templates/
ADD static/ /app/static/
ADD *.py /app/

ADD detect_media.js /app/scripts/detect_media.js

CMD python -u main.py


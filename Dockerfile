FROM python:3.12

RUN mkdir /code
COPY ./requirements.txt /code
WORKDIR /code

RUN pip install -r requirements.txt

RUN mkdir /start
COPY ./run.sh /start
RUN chmod +x /start/run.sh

RUN useradd web -s /bin/bash
USER web

CMD /start/run.sh

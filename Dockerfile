FROM alpine

WORKDIR /app
COPY ./main.py /app/

RUN apk --update --no-cache add curl ca-certificates python3 py3-pip build-base libffi-dev python3-dev \
    && pip3 install requests \
    && pip3 install oci 

ENTRYPOINT [ "python3", "main.py" ]



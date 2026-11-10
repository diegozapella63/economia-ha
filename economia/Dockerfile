ARG BUILD_FROM
FROM $BUILD_FROM

RUN apk add --no-cache python3

COPY app /app
# a versão fica só no config.yaml: o servidor lê daqui
COPY config.yaml /app/config.yaml
RUN chmod a+x /app/run.sh

CMD [ "/app/run.sh" ]

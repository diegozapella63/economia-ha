#!/bin/sh
# O s6-overlay da imagem base passa o ambiente limpo; with-contenv devolve o SUPERVISOR_TOKEN.
if [ -x /usr/bin/with-contenv ]; then
  exec /usr/bin/with-contenv python3 -u /app/server.py
fi
exec python3 -u /app/server.py

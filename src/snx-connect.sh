#!/bin/sh
# snx-connect.sh

# O Flatpak instala os seus ficheiros Python em /app/bin/
# O comando 'exec' substitui o processo do shell pelo processo do Python
exec python3 /app/src/snx-connect/main.py "$@"

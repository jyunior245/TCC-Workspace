#!/bin/sh

echo "Aguardando o banco de dados ficar pronto em db:5432..."

while ! nc -z db 5432; do
  sleep 1
done

echo "PostgreSQL está pronto! Iniciando aplicação Flask..."

exec "$@"

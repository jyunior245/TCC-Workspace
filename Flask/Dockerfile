FROM python:3-alpine3.19

WORKDIR /app

# Install system dependencies for psycopg2 and other tools
# postgresql-dev: required for pg_config to build psycopg2
# gcc, python3-dev, musl-dev: required for compiling C extensions
# linux-headers: often needed for python packages
RUN apk add --no-cache postgresql-dev gcc python3-dev musl-dev linux-headers

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

COPY wait-for-db.sh /wait-for-db.sh
RUN chmod +x /wait-for-db.sh

EXPOSE 5000

CMD ["/wait-for-db.sh", "python", "main.py"]

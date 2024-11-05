FROM python:3.12-slim

RUN apt update && apt install -y gcc libpq-dev ffmpeg libopencv-dev git

# Installation des dépendances
WORKDIR /r_and_d
COPY ./src/rd/pyproject.toml .
RUN pip3 install poetry==1.8.3 

RUN poetry install

# Copier le reste du code
COPY ./src/rd .
COPY .env .

# Exposer le port
EXPOSE 8002

# Lancer l'application FastAPI
CMD ["tail", "-f", "/dev/null"]
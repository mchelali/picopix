FROM python:3.12-slim

RUN apt update && apt install -y \
    gcc \
    libpq-dev \
    ffmpeg \
    libopencv-dev \
    git \
    curl \
    nano \
    vim \
    openssh-server \
    supervisor


# Configurer le serveur SSH
RUN mkdir /var/run/sshd && \
    echo 'PermitRootLogin yes' >> /etc/ssh/sshd_config && \
    echo 'PasswordAuthentication yes' >> /etc/ssh/sshd_config && \
    echo 'ChallengeResponseAuthentication no' >> /etc/ssh/sshd_config

# # Ajouter un utilisateur pour SSH
# RUN useradd -rm -d /home/ssh_user -s /bin/bash -u 1000 ssh_user && \
#     echo 'ssh_user:password' | chpasswd && \
#     mkdir -p /home/ssh_user/.ssh && \
#     chown -R ssh_user:ssh_user /home/ssh_user

# Configurer un mot de passe pour root
RUN echo 'root:rootpassword' | chpasswd

# Installer Poetry et configurer les environnements virtuels partagés
RUN pip3 install poetry==1.8.3 

# Installation des dépendances
WORKDIR /r_and_d
COPY ./src/rd/pyproject.toml .
COPY ./src/rd/poetry.toml .
# COPY ./src/rd/requirements.txt .

# RUN chown -R ssh_user:ssh_user /r_and_d
# RUN pip install -r requirements.txt
RUN poetry install

# Copier le reste du code
COPY ./src/rd .
COPY .env .

RUN poetry cache clear pypi --all

# Configurer supervisord pour gérer plusieurs processus
RUN mkdir -p /etc/supervisor/conf.d
COPY docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Exposer le port
EXPOSE 8002 22

# Lancer l'application FastAPI
# CMD ["tail", "-f", "/dev/null"]
# CMD ["poetry", "run", "mlflow", "server", "--host", "0.0.0.0", "--port", "8002"]

# Lancer supervisord pour gérer SSH et MLflow
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]

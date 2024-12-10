# Configuration Airflow 

## Créez une Connexion SSH dans Airflow
Dans l'interface Airflow :

1. Allez dans Admin > Connexions > + Ajouter une Connexion.
2. Remplissez les champs suivants :
   * **Conn ID** : `rd_host`.
   * **Conn Type** : `SSH`.
   * **Host** : `host.docker.internal` (si le conteneur est sur la même machine, sinon utilisez l'IP ou l'adresse du serveur Docker).
   * **Port** : `2222` (le port SSH mappé dans votre conteneur Docker).
   * **Login** : `ssh_user` (le nom d'utilisateur configuré dans le conteneur).
   * **Password** : `password` (le mot de passe configuré pour cet utilisateur).

Cliquez sur Save.
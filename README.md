# Picopix

Colorisation d'images est un probleme auquel est confrenté  la caumunauté de vision par ordinateur. Ce projet implémente 2 méthodes de l'état de l'art pour la résolution de cette problématiques avec un structure MLOps complète pour la gestion et maintenance de l'application et l'amélioration des modèles utilisés. 


## Structure du projet

```bash
.
├── Makefile                    <--- racourcie des commandes docker pour le lancemant des conteneur
├── README.md                   <--- Présentation du peojet
├── dataset
│   ├── README.md               <--- Présentation de la basse de données initiale
│   ├── dataset_preparation.sh  <--- Script de préparation de la base de donnée initiale 
├── docker                      <--- Dossier des fichier de configuration Docker
│   └── ....
├── docker-compose.dev.yaml     <--- Composition des dockers de dévellopement
├── docker-compose.yaml         <--- Composition des dockers de production
├── notebooks                   <--- dossier des notebooks de test et d'exploitation
├── references                  <--- dossier de documentation
└── src                 
    ├── api                     <--- API
    │   ├── README.md
    ├── rd                      <--- partie r&d du projet
    │   ├── README.md
    └── webapp                  <--- application web via Streamlit
    │   ├── README.md

```




## Utilisation
Pour lancer tous les conteneur en loacal, il vous suffit de clounner le répertoire et lancer les conteneurs. les commandes suivantes illustre ceci :

```bash
git clone git@github.com:mchelali/picopix.git
cd picopix/ 
make start
```

Pour stoper les conteneurs
```bash
make stop
```
from mlflow import MlflowClient
import mlflow
import boto3
from botocore.client import Config
import os
from pathlib import Path
from typing import Dict, Tuple
import torch
import hashlib
import io
import dotenv

dotenv.load_dotenv()

# Initialisation des clients MLflow et S3/MinIO
mlflow_client = MlflowClient(tracking_uri="http://r_and_d:8002")
s3_client = boto3.client(
    "s3",
    endpoint_url=os.environ.get("AWS_ENDPOINT_URL"),
    aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
    config=Config(signature_version="s3v4"),
)

bucket_name = "colorisation-models"

# Création du bucket dans MinIO si nécessaire
try:
    s3_client.create_bucket(Bucket=bucket_name)
    print(f"Bucket '{bucket_name}' créé avec succès.")
except s3_client.exceptions.BucketAlreadyOwnedByYou:
    print(f"Bucket '{bucket_name}' déjà existant.")


def upload_model_to_minio(
    model_name: str, best_models: Dict[str, Tuple[float, str]]
) -> None:
    """
    Télécharge le meilleur modèle depuis MLflow et upload tous les fichiers et sous-dossiers dans le bucket MinIO.

    Parameters:
        model_name (str): Le nom du modèle à télécharger et uploader.
        best_models (Dict[str, Tuple[float, str]]): Dictionnaire contenant les modèles avec
                                                    leurs pertes de validation et leurs ID d'exécution.

    Returns:
        None
    """
    print("============= ", model_name)
    try:
        # Téléchargement des artefacts du modèle
        model_path = mlflow_client.download_artifacts(
            best_models[model_name][1], model_name
        )
        model_path = Path(model_path)
        print("----------- ", model_path)

        if model_path.is_dir():
            # Parcours de tous les fichiers et sous-dossiers
            for file_path in model_path.rglob("*"):
                if file_path.is_file():  # Upload uniquement des fichiers
                    # Construire le chemin de destination en conservant la structure du dossier
                    relative_path = file_path.relative_to(model_path)
                    s3_key = f"{model_name}/{relative_path}"

                    # Upload vers MinIO
                    s3_client.upload_file(str(file_path), bucket_name, s3_key)
                    print(
                        f"{file_path} uploadé dans le bucket {bucket_name} sous la clé {s3_key}"
                    )
        else:
            # Si ce n'est pas un répertoire, uploader le fichier directement
            s3_client.upload_file(
                str(model_path), bucket_name, f"{model_name}_best_model.pth"
            )
            print(
                f"{model_path} uploadé dans le bucket {bucket_name} sous la clé {model_name}_best_model.pth"
            )

    except Exception as e:
        print(f"Erreur lors de l'upload de {model_name} : {e}")


def are_models_identical(model_path_1: str, model_path_2: str) -> bool:
    """
    Compare les poids de deux modèles PyTorch pour vérifier s'ils sont identiques.

    Parameters:
        model_path_1 (str): Chemin vers le premier modèle (state_dict).
        model_path_2 (str): Chemin vers le second modèle (state_dict).

    Returns:
        bool: True si les deux modèles sont identiques, False sinon.
    """
    # Charger les deux modèles
    state_dict_1 = torch.load(
        model_path_1, weights_only=False, map_location="cpu"
    ).state_dict()
    state_dict_2 = torch.load(model_path_2, weights_only=False, map_location="cpu")

    # Si les clés des deux state_dict sont différentes, ils ne sont pas identiques
    if state_dict_1.keys() != state_dict_2.keys():
        return False

    # Comparer les poids de chaque couche
    for key in state_dict_1.keys():
        if not torch.equal(state_dict_1[key], state_dict_2[key]):
            return False  # Une différence détectée

    return True  # Tous les poids sont identiques


def upload_model_to_minio2(
    model_name: str, best_models: Dict[str, Tuple[float, str]]
) -> None:
    """
    Télécharge le meilleur modèle depuis MLflow, le convertit en format PyTorch natif (state_dict),
    vérifie si le modèle a déjà été uploadé en comparant directement les poids,
    et upload les fichiers dans le bucket MinIO avec versionnement incrémental.

    Parameters:
        model_name (str): Le nom du modèle à télécharger et uploader.
        best_models (Dict[str, Tuple[float, str]]): Dictionnaire contenant les modèles avec
                                                    leurs pertes de validation et leurs ID d'exécution.

    Returns:
        None
    """
    print(f"============= Uploading model: {model_name} =============")
    try:
        # Récupération de l'ID d'exécution
        _, run_id = best_models[model_name]

        # Téléchargement du modèle depuis MLflow
        model_path = mlflow_client.download_artifacts(run_id, model_name)
        model_path = Path(f"{model_path}/generator/data/model.pth")

        if not model_path.exists():
            raise FileNotFoundError(f"Fichier {model_path} introuvable.")

        # Charger uniquement le state_dict du modèle actuel
        pytorch_model = torch.load(model_path, weights_only=False, map_location="cpu")

        state_dict = (
            pytorch_model.state_dict()
            if hasattr(pytorch_model, "state_dict")
            else pytorch_model
        )

        # Comparer le modèle actuel avec ceux déjà présents dans MinIO
        response = s3_client.list_objects_v2(
            Bucket=bucket_name, Prefix=f"{model_name}/"
        )

        if "Contents" in response:
            for obj in response["Contents"]:
                key = obj["Key"]
                if key.endswith(".pth"):
                    # Télécharger chaque modèle pour comparer
                    temp_file = f"/tmp/{key.replace('/', '_')}"
                    s3_client.download_file(bucket_name, key, temp_file)

                    # Vérifier si les modèles sont identiques
                    if are_models_identical(model_path, temp_file):
                        print(
                            f"Le modèle {model_name} est déjà présent dans le bucket. Upload ignoré."
                        )
                        Path(temp_file).unlink()
                        return

                    Path(temp_file).unlink()

        # Trouver le prochain index
        existing_versions = []
        for obj in response.get("Contents", []):
            key = obj["Key"]
            # Extraire l'indice du fichier (ex: my_model_v3.pth -> 3)
            if key.endswith(".pth"):
                parts = key.split("_v")
                if len(parts) > 1 and parts[-1].replace(".pth", "").isdigit():
                    existing_versions.append(int(parts[-1].replace(".pth", "")))

        next_version = max(existing_versions) + 1 if existing_versions else 1

        # Sauvegarder le modèle avec l'index incrémenté
        state_dict_path = f"{model_name}_v{next_version}.pth"
        torch.save(state_dict, state_dict_path)

        # Upload vers MinIO
        s3_key = f"{model_name}/{state_dict_path}"
        s3_client.upload_file(state_dict_path, bucket_name, s3_key)

        print(
            f"{state_dict_path} (PyTorch state_dict) uploadé dans le bucket {bucket_name} sous la clé {s3_key}"
        )

        # Nettoyer le fichier local après upload
        Path(state_dict_path).unlink()

    except Exception as e:
        print(f"Erreur lors de l'upload de {model_name} : {e}")


def find_best_models(experiment_id: str) -> Dict[str, Tuple[float, str]]:
    """
    Parcourt toutes les exécutions de l'expérience et sélectionne le meilleur modèle
    (celui avec la plus faible perte de validation) pour chaque type de modèle.

    Parameters:
        experiment_id (str): L'ID de l'expérience MLflow.

    Returns:
        Dict[str, Tuple[float, str]]: Un dictionnaire contenant les meilleurs modèles pour chaque type.
    """
    best_models = {}

    # Parcourir toutes les exécutions de l'expérience
    for run in mlflow_client.search_runs(experiment_id):
        model_name = run.data.tags.get("mlflow.runName", "").split("_")[0]
        test_error = run.data.metrics.get("test_error")  # Métirque de validation
        print(model_name, test_error)
        if test_error is not None:
            # Vérifier si ce modèle est meilleur que le précédent
            if model_name not in best_models or test_error < best_models[model_name][0]:
                best_models[model_name] = (test_error, run.info.run_id)

    return best_models


def register_best_models(best_models: Dict[str, Tuple[float, str]]) -> None:
    """
    Enregistre les meilleurs modèles dans le registre MLflow.

    Parameters:
        best_models (Dict[str, Tuple[float, str]]): Dictionnaire des meilleurs modèles à enregistrer.

    Returns:
        None
    """
    for model_name, (val_loss, best_run_id) in best_models.items():
        model_uri = f"runs:/{best_run_id}/{model_name}"
        try:
            # Créez ou mettez à jour le modèle dans le registre
            mlflow_client.create_registered_model(model_name)
        except mlflow.exceptions.RestException:
            pass  # Le modèle existe déjà

        mlflow_client.create_model_version(
            name=model_name, source=model_uri, run_id=best_run_id
        )
        print(f"Enregistré {model_name} avec loss {val_loss} (run ID: {best_run_id})")


if __name__ == "__main__":
    # Nom de l'expérience dans MLflow
    experiment_name = "Colorizator"

    # Obtenir l'ID de l'expérience
    experiment = mlflow_client.get_experiment_by_name(experiment_name)
    if experiment is None:
        raise ValueError(f"L'expérience '{experiment_name}' est introuvable.")
    experiment_id = experiment.experiment_id

    # Trouver et enregistrer les meilleurs modèles
    best_models = find_best_models(experiment_id)
    # register_best_models(best_models)

    # Uploader les meilleurs modèles vers MinIO
    for model_name in best_models.keys():
        upload_model_to_minio2(model_name, best_models)


import io
import cv2
import numpy as np
import requests
import torch
import torchvision.transforms as transforms
import torch.nn.functional as F
from typing import Optional
from skimage.color import lab2rgb

from model.colorizator import Net
from model.pix2pix import GeneratorUNet

from pixlibs.storage_boto3 import get_storage_client

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

bucket_name = "colorisation-models"
models_names = ["autoencoder", "pix2pix"]

models_names = {
    "autoencoder": Net(),
    "pix2pix": GeneratorUNet()
}

s3_client = get_storage_client()


def get_latest_model_uri(s3_client, model_name: str) -> Optional[str]:
    """
    Récupère l'URI de la dernière version d'un modèle dans un bucket MinIO.

    Parameters:
        model_name (str): Le nom du modèle.
        bucket_name (str): Le nom du bucket MinIO.

    Returns:
        Optional[str]: L'URI de la dernière version du modèle ou None si aucune version n'existe.
    """
    try:
        bucket = s3_client.Bucket(bucket_name)

        # Lister les objets sous le préfixe du modèle
        objects = bucket.objects.filter(Prefix=f"{model_name}/")
        model_files = []

        for obj in objects:
            if obj.key.endswith(".pth"):
                # Extraire l'indice de version (ex: my_model_v3.pth -> 3)
                parts = obj.key.split("_v")
                if len(parts) > 1 and parts[-1].replace(".pth", "").isdigit():
                    version = int(parts[-1].replace(".pth", ""))
                    model_files.append((version, obj.key))

        print(model_files)
        if not model_files:
            raise ValueError(f"Aucune version trouvée pour le modèle {model_name} dans le bucket {bucket_name}.")

        # Trouver la clé de la dernière version
        latest_version, latest_key = max(model_files, key=lambda x: x[0])

        # Construire l'URI du modèle
        # uri = f"{s3_client.meta.client.meta.endpoint_url}/{bucket_name}/{latest_key}"
        # print(f"URI du dernier modèle : {uri}")
        return latest_key

    except Exception as e:
        print(f"Erreur lors de la récupération de la dernière version du modèle {model_name}: {e}")
        raise

def get_presigned_url(s3_client, bucket_name, object_key, expiration=3600):
    """
    Génère un lien présigné pour un objet dans MinIO.
    
    Parameters:
        s3_client: Client S3 configuré.
        bucket_name (str): Nom du bucket MinIO.
        object_key (str): Chemin de l'objet dans le bucket.
        expiration (int): Durée de validité du lien présigné en secondes (par défaut : 1 heure).
    
    Returns:
        str: URL présigné permettant d'accéder à l'objet.
    """
    return s3_client.meta.client.generate_presigned_url(
        'get_object',
        Params={'Bucket': bucket_name, 'Key': object_key},
        ExpiresIn=expiration
    )


def infer_autoencoder(image: np.ndarray) -> np.ndarray:
    """
    Infers a colorized version of a grayscale image using a pre-trained autoencoder model.

    """
    def to_rgb(grayscale_input: torch.Tensor, ab_input: torch.Tensor) -> np.ndarray:
        """
        Converts grayscale and AB channels to an RGB image using the LAB color space.

        Parameters:
            grayscale_input (torch.Tensor): Grayscale channel, shape (1, H, W), values in range [0, 1].
            ab_input (torch.Tensor): AB channels, shape (2, H, W), values in range [-1, 1].

        Returns:
            np.ndarray: RGB image, values in range [0, 1].
        """
        # Combine grayscale and AB channels
        color_image = torch.cat((grayscale_input, ab_input), dim=0).numpy()
        color_image = color_image.transpose((1, 2, 0))  # Convert to H x W x C

        # Denormalize LAB channels
        color_image[:, :, 0] = color_image[:, :, 0] * 100  # L channel (0 to 100)
        color_image[:, :, 1:] = color_image[:, :, 1:] * 128  # AB channels (-128 to 128)

        # Convert LAB to RGB
        color_image = lab2rgb(color_image.astype(np.float64))
        return color_image

    
    # Validate input normalization
    if not (0 <= image.min() and image.max() <= 1):
        print("Input image values should be normalized to the range [0, 1].")
        image = image.astype(np.float16) / 255.

    # Resize and prepare the input image
    original_h, original_w = image.shape[:2]
    input_gray = cv2.resize(image, (256, 256))  # Resize to 256x256
    input_gray = torch.from_numpy(input_gray).unsqueeze(0).unsqueeze(0).float().to(device)  # Shape: (1, 1, 256, 256)

    # Perform inference
    with torch.no_grad():  # Disable gradient calculation
        output_ab = models_names["autoencoder"](input_gray)  # Shape: (1, 2, 256, 256)

    # Convert to RGB and resize to original dimensions
    colored_image = to_rgb(input_gray[0, 0].cpu(), output_ab[0].cpu())
    colored_image = cv2.resize(colored_image, (original_w, original_h))  # Resize to original dimensions
    colored_image = (colored_image * 255).astype(np.uint8)  # Scale to [0, 255] for visualization

    return colored_image


def infer_pix2pix(image: np.ndarray) -> np.ndarray:
    """
    Infers a colorized version of an image using a pre-trained Pix2Pix model.
    """
    # Validate input normalization
    if not (0 <= image.min() and image.max() <= 1):
        print("Input image values should be normalized to the range [0, 1].")
        image = image.astype(np.float16) / 255.

    # Ensure the input has 3 channels (if grayscale, repeat across channels)
    if image.ndim == 2:  # Grayscale image (H x W)
        image = np.stack([image] * 3, axis=-1)  # Convert to RGB (H x W x 3)

    if image.shape[-1] != 3:
        raise ValueError("Input image must have 3 channels (RGB).")

    # Get original dimensions
    original_h, original_w = image.shape[:2]

    # Define preprocessing pipeline
    preprocess = transforms.Compose(
        [
            transforms.ToPILImage(),  # Convert to PIL image
            transforms.Resize((256, 256)),  # Resize to 256x256
            transforms.ToTensor(),  # Convert to tensor
            transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5)),  # Normalize to [-1, 1]
        ]
    )

    # Apply preprocessing
    input_tensor = preprocess((image * 255).astype(np.uint8)).unsqueeze(0).to(device)  # Add batch dimension

    # Perform inference
    model.eval()  # Ensure the model is in evaluation mode
    with torch.no_grad():
        output_tensor = model(input_tensor)  # Output tensor, shape: (1, 3, 256, 256)

    # Post-process the output
    output_image = output_tensor.squeeze(0).cpu().numpy().transpose(1, 2, 0)  # Shape: (256, 256, 3)
    output_image = (output_image * 0.5 + 0.5)  # De-normalize to [0, 1]
    output_image = cv2.resize(output_image, (original_w, original_h))  # Resize to original dimensions
    output_image = (output_image * 255).astype(np.uint8)  # Scale to [0, 255] for visualization

    return output_image

for model_name, model in models_names.items():

    lastest_model = get_latest_model_uri(s3_client, model_name=model_name)

    print(bucket_name, lastest_model)

    # Générer un lien présigné
    presigned_url = get_presigned_url(s3_client, bucket_name, lastest_model)

    # Télécharger les poids en mémoire via le lien présigné
    response = requests.get(presigned_url, stream=True)
    if response.status_code == 200:
        # Charger les données dans un buffer
        buffer = io.BytesIO(response.content)
        
        # Charger les poids dans un dictionnaire d'état
        state_dict = torch.load(buffer, map_location="cpu", weights_only=False)
        
        # Charger les poids dans le modèle
        model.load_state_dict(state_dict)
        model.to(device)
        model.eval()
        print(f"Le modèle {model_name} a été chargé avec succès depuis {presigned_url}.")
    else:
        print(f"Impossible de télécharger le modèle {model_name}. Code HTTP : {response.status_code}")

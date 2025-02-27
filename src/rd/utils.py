import json
import os
import time
import torch
from torch.utils.data import Dataset
import numpy as np
from skimage.color import rgb2lab, rgb2gray, lab2rgb
from torchvision import datasets
import matplotlib.pyplot as plt
from typing import Dict, Optional
from PIL import Image


class Pix2pixDataset(Dataset):

    def __init__(self, root_dir, transforms=None, mode="train"):
        self.transform = transforms

        self.image_paths = [
            os.path.join(root, f)
            for root, dirs, files in os.walk(root_dir)
            for f in files
            if f.endswith(".jpg")
        ]

    def __getitem__(self, index):
        # Load and convert image to RGB
        image = Image.open(self.image_paths[index % len(self.image_paths)]).convert(
            "RGB"
        )

        # Convert image to NumPy array
        img_A = np.asarray(image)

        # Get grayscale version as img_B
        img_B = rgb2gray(img_A)

        # Convert grayscale image back to 3 channels by stacking
        img_B = np.stack([img_B] * 3, axis=-1)  # Shape (H, W, 3)

        # Apply transforms if available
        if self.transform:
            # Apply transforms and normalize to [-1, 1]
            img_A = self.transform(Image.fromarray(img_A)) * 2 - 1
            img_B = self.transform(
                Image.fromarray((img_B * 255).astype(np.uint8))
            )  * 2 - 1 # Rescale grayscale to 0-255, then normalize

        return img_B, img_A

    def __len__(self):
        return len(self.image_paths)


class LABColorDataset(Dataset):
    def __init__(self, root_dir: str, transform=None):
        """
        Initialize the LABColorDataset dataset.

        Args:
            root_dir (str): Directory containing images.
            transform: Optional torchvision transform to apply to each image.
        """
        self.root_dir = root_dir
        self.transform = transform
        # self.image_paths = [
        #     os.path.join(root_dir, f)
        #     for f in os.listdir(self.root_dir)
        #     if f.endswith((".png", ".jpg", ".jpeg"))
        # ]
        self.image_paths = [
            os.path.join(root, f)
            for root, dirs, files in os.walk(self.root_dir)
            for f in files
            if f.endswith(".jpg")
        ]

    def __len__(self) -> int:
        """Returns the total number of images."""
        return len(self.image_paths)

    def __getitem__(self, index: int):
        """
        Retrieve and process an image at the given index.

        Args:
            index (int): Index of the image to retrieve.

        Returns:
            Tuple[torch.Tensor, torch.Tensor]: Grayscale image tensor and "ab" channel tensor.
        """
        path = self.image_paths[index]  # Get the image path
        image = Image.open(path).convert("RGB")  # Load the image and ensure it's RGB

        if self.transform:
            image = self.transform(image)  # Apply transforms if provided

        # Convertir le tensor RGB en numpy pour LAB conversion
        image_np = image.permute(1, 2, 0).numpy()  # (H, W, C) pour skimage
        image_np = image_np * 255.0  # Remettre l'image dans la plage [0, 255]

        # Conversion en LAB
        img_lab = rgb2lab(image_np).astype(np.float32)

        # Normaliser chaque canal
        L = img_lab[:, :, 0] / 100.0  # Normalise L dans [0, 1]
        a = (img_lab[:, :, 1] + 128) / 255.0  # Normalise a dans [0, 1]
        b = (img_lab[:, :, 2] + 128) / 255.0  # Normalise b dans [0, 1]

        # Combine en tensors PyTorch
        input_L = torch.tensor(L).unsqueeze(0)  # Ajoute une dimension pour le canal (1, H, W)
        target_ab = torch.tensor(np.stack((a, b), axis=-1)).permute(2, 0, 1)  # (2, H, W)

        return input_L, target_ab


class AverageMeter:
    """
    Tracks and computes average, sum, and count of values over time.

    Useful for monitoring metrics like loss during training.
    """

    def __init__(self) -> None:
        """
        Initializes an AverageMeter instance and resets all counters.
        """
        self.reset()

    def reset(self) -> None:
        """
        Resets all tracked metrics to zero.
        """
        self.val: float = 0
        self.avg: float = 0
        self.sum: float = 0
        self.count: int = 0

    def update(self, val: float, n: int = 1) -> None:
        """
        Updates the tracked metrics with a new value.

        Args:
            val (float): The new value to add to the meter.
            n (int): The weight or number of occurrences for the new value (default is 1).
        """
        self.val = val
        self.sum += val * n
        self.count += n
        self.avg = self.sum / self.count


class Trainer:
    def __init__(self, device: torch.device) -> None:
        """
        Initializes the Trainer class.

        Args:
            device (torch.device): Device to be used for model and data (e.g., 'cpu' or 'cuda').
        """
        self.device: torch.device = device
        self.train_losses: list[float] = []
        self.val_losses: list[float] = []

    def train(
        self,
        train_loader: torch.utils.data.DataLoader,
        epoch: int,
        model: torch.nn.Module,
        criterion: torch.nn.Module,
        optimizer: torch.optim.Optimizer,
    ) -> None:
        """
        Trains the model for one epoch, logging losses and updating weights.

        Args:
            train_loader (torch.utils.data.DataLoader): DataLoader for the training set.
            epoch (int): Current epoch number.
            model (torch.nn.Module): Model to be trained.
            criterion (torch.nn.Module): Loss function.
            optimizer (torch.optim.Optimizer): Optimizer for model parameters.
            scheduler (Optional[torch.optim.lr_scheduler._LRScheduler]): Learning rate scheduler (optional).
        """
        print(f"Starting training epoch {epoch + 1}")
        model.train()
        batch_time, data_time, losses = AverageMeter(), AverageMeter(), AverageMeter()
        end = time.time()

        for i, (input_gray, input_ab) in enumerate(train_loader):
            input_gray, input_ab = input_gray.to(self.device), input_ab.to(self.device)
            data_time.update(time.time() - end)
            output_ab = model(input_gray)
            loss = criterion(output_ab, input_ab)
            losses.update(loss.item(), input_gray.size(0))

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            batch_time.update(time.time() - end)
            end = time.time()

            if i % 25 == 0:
                self._log_training(
                    epoch, i, len(train_loader), batch_time, data_time, losses
                )

        self.train_losses.append(losses.avg)
        print(f"Finished training epoch {epoch + 1}")

    def _log_training(
        self,
        epoch: int,
        batch_idx: int,
        num_batches: int,
        batch_time: AverageMeter,
        data_time: AverageMeter,
        losses: AverageMeter,
    ) -> None:
        """
        Logs training progress for a given batch.

        Args:
            epoch (int): Current epoch number.
            batch_idx (int): Current batch index.
            num_batches (int): Total number of batches in the epoch.
            batch_time (AverageMeter): AverageMeter for batch processing time.
            data_time (AverageMeter): AverageMeter for data loading time.
            losses (AverageMeter): AverageMeter for tracking losses.
        """
        print(
            f"Epoch: [{epoch + 1}][{batch_idx}/{num_batches}]\t"
            f"Time {batch_time.val:.3f} ({batch_time.avg:.3f})\t"
            f"Data {data_time.val:.3f} ({data_time.avg:.3f})\t"
            f"Loss {losses.val:.6f} ({losses.avg:.6f})\t"
        )

    def validate(
        self,
        val_loader: torch.utils.data.DataLoader,
        model: torch.nn.Module,
        criterion: torch.nn.Module,
    ) -> float:
        """
        Validates the model for one epoch, logging losses and optionally saving images.

        Args:
            val_loader (torch.utils.data.DataLoader): DataLoader for the validation set.
            epoch (int): Current epoch number.
            save_images (bool): Flag to save images during validation.
            model (torch.nn.Module): Model to be validated.
            criterion (torch.nn.Module): Loss function.

        Returns:
            float: Average validation loss for the epoch.
        """
        model.eval()
        batch_time, data_time, losses = AverageMeter(), AverageMeter(), AverageMeter()
        end = time.time()

        for i, (input_gray, input_ab) in enumerate(val_loader):
            data_time.update(time.time() - end)
            input_gray, input_ab = input_gray.to(self.device), input_ab.to(self.device)
            output_ab = model(input_gray)
            loss = criterion(output_ab, input_ab)
            losses.update(loss.item(), input_gray.size(0))
            batch_time.update(time.time() - end)
            end = time.time()

            if i % 25 == 0:
                self._log_validation(i, len(val_loader), batch_time, losses)

        self.val_losses.append(losses.avg)
        print("Finished validation.")
        return losses.avg

    def _log_validation(
        self,
        batch_idx: int,
        num_batches: int,
        batch_time: AverageMeter,
        losses: AverageMeter,
    ) -> None:
        """
        Logs validation progress for a given batch.

        Args:
            batch_idx (int): Current batch index.
            num_batches (int): Total number of batches in validation.
            batch_time (AverageMeter): AverageMeter for batch processing time.
            losses (AverageMeter): AverageMeter for tracking losses.
        """
        print(
            f"Validate: [{batch_idx}/{num_batches}]\t"
            f"Time {batch_time.val:.3f} ({batch_time.avg:.3f})\t"
            f"Loss {losses.val:.6f} ({losses.avg:.6f})\t"
        )

    def plot_losses(self, save_path_folder: Optional[str] = None) -> None:
        """
        Plots and optionally saves training and validation losses.

        Args:
            save_path (Optional[str]): Path to save the loss plot (optional).
        """
        epochs = range(1, len(self.train_losses) + 1)
        plt.figure(figsize=(10, 5))
        plt.plot(epochs, self.train_losses, label="Training Loss")
        plt.plot(epochs, self.val_losses, label="Validation Loss")
        plt.xlabel("Epochs")
        plt.ylabel("Loss")
        plt.legend()
        plt.title("Training and Validation Loss Over Epochs")

        if save_path_folder:
            plt.savefig(f"{save_path_folder}/losses.png")
        # plt.show()

        with open(f"{save_path_folder}/losses.json", "w") as fout:
            json.dump(
                {"train_losses": self.train_losses, "val_losses": self.val_losses},
                fout,
                indent=2,
            )

import numpy as np
import torch
import os
from model.colorizator import Net
import torch.nn as nn
import argparse
import torchvision.transforms as T
import cv2
import glob

from utils import ColorizeData, Trainer


def clean_train_imgs(folder_path):  # remove images with no color

    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        if os.path.isfile(file_path):
            image = cv2.imread(file_path)
            if image is not None:
                image_hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
                if image_hsv[:, :, 0].sum() == 0 and image_hsv[:, :, 1].sum() == 0:
                    os.remove(file_path)
                    print("Removed image: {}".format(file_path))


if __name__ == "__main__":
    # Parsing arguments from command line
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--image_dir",
        type=str,
        default="landscape_images/",
        help="Directory containing all images in the dataset",
    )
    parser.add_argument(
        "--epochs", type=int, default=100, help="Number of training epochs"
    )
    parser.add_argument(
        "--lr", type=float, default=1e-3, help="Learning rate for training"
    )
    parser.add_argument(
        "--weight_decay",
        type=float,
        default=1e-4,
        help="Weight decay value for Adam optimizer",
    )
    parser.add_argument(
        "--loss",
        type=str,
        default="mse",
        help="Choose between MAE or MSE Loss for training",
    )
    parser.add_argument(
        "--batch_size",
        type=int,
        default=16,
        help="Batch size for training and validation",
    )
    parser.add_argument(
        "--early_stop",
        type=int,
        default=10,
        help="Stop trainning if validation does not decrease at given times",
    )
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = Net().to(device)

    if args.loss == "mse":  # Initialize loss according to choice
        criterion = nn.MSELoss().to(device)
    else:
        criterion = nn.L1Loss().to(device)

    optimizer = torch.optim.Adam(
        model.parameters(), lr=args.lr, weight_decay=args.weight_decay
    )
    scheduler = torch.optim.lr_scheduler.StepLR(
        optimizer, step_size=5, gamma=0.5, verbose=False
    )
    # Training
    root_data = os.path.abspath(args.image_dir)

    train_transforms = T.Compose([T.RandomResizedCrop(224), T.RandomHorizontalFlip()])
    train_imagefolder = ColorizeData(f"{root_data}/train", train_transforms)
    train_loader = torch.utils.data.DataLoader(
        train_imagefolder, batch_size=args.batch_size, shuffle=True
    )

    # Validation
    val_transforms = T.Compose([T.Resize(256), T.CenterCrop(224)])
    val_imagefolder = ColorizeData(f"{root_data}/val", val_transforms)
    val_loader = torch.utils.data.DataLoader(
        val_imagefolder, batch_size=args.batch_size, shuffle=False
    )

    print("Image preprocessing completed!")
    trainner = Trainer(device)
    vald_loss = np.inf
    patience = 0
    # Train model
    for epoch in range(args.epochs):
        # Train for one epoch, then validate
        trainner.train(train_loader, epoch, model, criterion, optimizer)
        scheduler.step()
        with torch.no_grad():
            epoch_valid_loss = trainner.validate(val_loader, model, criterion)

        if epoch_valid_loss > vald_loss:
            print(f"---> Early stopping criterion {patience}/{args.early_stop}")
            patience += 1
        else:
            patience = 0
            vald_loss = epoch_valid_loss
            torch.save(model, "checkpoint/best_model.pth")
            trainner.plot_losses("checkpoint")

        if patience > args.early_stop:
            break

    torch.save(model, "checkpoint/last_model.pth")
    trainner.plot_losses("checkpoint")

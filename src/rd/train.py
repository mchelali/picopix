import numpy as np
import torch
import os
from model.colorizator import Net
import torch.nn as nn
import argparse
import torchvision.transforms as T
import cv2
import glob

from mlflow import MlflowClient
import mlflow

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
        default="dataset/",
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
        default=1e-3,
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

    dataset = os.path.dirname(args.image_dir).split(os.path.sep)[-1]

    # Define experiment name, run name and artifact_path name
    mlflow_experiment = mlflow.set_experiment("Colorizator")
    run_name = f"autoencoder_{dataset}"
    client = MlflowClient(tracking_uri=os.getenv("MLFLOW_TRACKING_URI"))

    if args.loss == "mse":  # Initialize loss according to choice
        criterion = nn.MSELoss().to(device)
    else:
        criterion = nn.L1Loss().to(device)

    optimizer = torch.optim.Adam(
        model.parameters(), lr=args.lr, weight_decay=args.weight_decay
    )
    scheduler = torch.optim.lr_scheduler.StepLR(
        optimizer, step_size=10, gamma=0.5, verbose=False
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

    # Store information in tracking server
    with mlflow.start_run(run_name=run_name) as run:
        # Train model
        for epoch in range(args.epochs):
            # Train for one epoch, then validate
            trainner.train(train_loader, epoch, model, criterion, optimizer)
            scheduler.step()
            with torch.no_grad():
                epoch_valid_loss = trainner.validate(val_loader, model, criterion)

            # Log train and validation losses with MLflow
            mlflow.log_metric("train_loss", trainner.train_losses[-1], step=epoch)
            mlflow.log_metric("val_loss", trainner.val_losses[-1], step=epoch)

            if epoch_valid_loss > vald_loss:
                print(f"---> Early stopping criterion {patience}/{args.early_stop}")
                patience += 1
            else:
                patience = 0
                vald_loss = epoch_valid_loss
                torch.save(model, "models/auto_encoder.pth")
                trainner.plot_losses("models")

            if patience > args.early_stop or epoch == args.epochs - 1:
                # save only the best model
                mlflow.pytorch.log_model(pytorch_model=model, artifact_path=run_name)
                break

        # torch.save(model, "models/auto_encoder_last_epoch.pth")
        trainner.plot_losses("models")

        params = {
            "dataset": dataset,
            "epochs": args.epochs,
            "patience": args.early_stop,
            "loss": args.loss,
            "batch_size": args.batch_size,
            "learning_rate": args.lr,
            "weight_decay": args.weight_decay,
        }

        mlflow.log_params(params)

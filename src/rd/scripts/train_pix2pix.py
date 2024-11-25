import argparse
import os
import numpy as np
import time
import datetime
import sys

import torchvision.transforms as transforms
from torchvision.utils import save_image
from torch.utils.data import DataLoader
from torchvision import datasets
from torch.autograd import Variable
import torch.nn as nn
import torch.nn.functional as F
import torch
from PIL import Image

from mlflow import MlflowClient
import mlflow

from utils import Pix2pixDataset
from model.pix2pix import GeneratorUNet, Discriminator, weights_init_normal

CLIENT = MlflowClient(tracking_uri="http://r_and_d:8002")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--image_dir",
        type=str,
        default="dataset/",
        help="Directory containing all images in the dataset",
    )
    parser.add_argument(
        "--epoch", type=int, default=0, help="epoch to start training from"
    )
    parser.add_argument(
        "--n_epochs", type=int, default=200, help="number of epochs of training"
    )
    parser.add_argument(
        "--batch_size", type=int, default=16, help="size of the batches"
    )
    parser.add_argument("--lr", type=float, default=0.0002, help="adam: learning rate")
    parser.add_argument(
        "--b1",
        type=float,
        default=0.5,
        help="adam: decay of first order momentum of gradient",
    )
    parser.add_argument(
        "--b2",
        type=float,
        default=0.999,
        help="adam: decay of first order momentum of gradient",
    )
    parser.add_argument(
        "--decay_epoch",
        type=int,
        default=100,
        help="epoch from which to start lr decay",
    )
    parser.add_argument(
        "--n_cpu",
        type=int,
        default=1,
        help="number of cpu threads to use during batch generation",
    )
    parser.add_argument(
        "--img_height", type=int, default=256, help="size of image height"
    )
    parser.add_argument(
        "--img_width", type=int, default=256, help="size of image width"
    )
    parser.add_argument(
        "--channels", type=int, default=3, help="number of image channels"
    )
    parser.add_argument(
        "--sample_interval",
        type=int,
        default=500,
        help="interval between sampling of images from generators",
    )
    parser.add_argument(
        "--models_interval",
        type=int,
        default=-1,
        help="interval between model modelss",
    )
    args = parser.parse_args()

    dataset = os.path.dirname(args.image_dir).split(os.path.sep)[-1]

    # Define experiment name, run name and artifact_path name
    mlflow_experiment = mlflow.set_experiment("Colorizator")
    run_name = f"pix2pix_{dataset}"
    artifact_path = "pix2pix"

    os.makedirs("models/", exist_ok=True)

    root_data = os.path.abspath(args.image_dir)

    cuda = True if torch.cuda.is_available() else False

    # Loss functions
    criterion_GAN = torch.nn.MSELoss()
    criterion_pixelwise = torch.nn.L1Loss()

    # Loss weight of L1 pixel-wise loss between translated image and real image
    lambda_pixel = 100

    # Calculate output of image discriminator (PatchGAN)
    patch = (1, args.img_height // 2**4, args.img_width // 2**4)

    # Initialize generator and discriminator
    generator = GeneratorUNet()
    discriminator = Discriminator()

    if cuda:
        generator = generator.cuda()
        discriminator = discriminator.cuda()
        criterion_GAN.cuda()
        criterion_pixelwise.cuda()

    if args.epoch != 0:
        # Load pretrained models
        generator.load_state_dict(torch.load("models/generator_%d.pth" % args.epoch))
        discriminator.load_state_dict(
            torch.load("models/discriminator_%d.pth" % args.epoch)
        )
    else:
        # Initialize weights
        generator.apply(weights_init_normal)
        discriminator.apply(weights_init_normal)

    # Optimizers
    optimizer_G = torch.optim.Adam(
        generator.parameters(), lr=args.lr, betas=(args.b1, args.b2)
    )
    optimizer_D = torch.optim.Adam(
        discriminator.parameters(), lr=args.lr, betas=(args.b1, args.b2)
    )

    # Configure dataloaders
    transforms_ = transforms.Compose(
        [
            transforms.Resize((args.img_height, args.img_width), Image.BICUBIC),
            transforms.ToTensor(),
            transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5)),
        ]
    )

    dataloader = DataLoader(
        Pix2pixDataset(f"{root_data}/train", transforms=transforms_),
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=args.n_cpu,
    )

    val_dataloader = DataLoader(
        Pix2pixDataset(f"{root_data}/val", transforms=transforms_),
        batch_size=10,
        shuffle=True,
        num_workers=1,
    )

    # Test
    test_dataloader = DataLoader(
        Pix2pixDataset(f"{root_data}/test", transforms=transforms_),
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=1,
    )

    # Tensor type
    Tensor = torch.cuda.FloatTensor if cuda else torch.FloatTensor

    def sample_images(batches_done):
        """Saves a generated sample from the validation set"""
        imgs = next(iter(val_dataloader))
        real_A = Variable(imgs[0].type(Tensor))
        real_B = Variable(imgs[1].type(Tensor))
        fake_B = generator(real_A)
        img_sample = torch.cat((real_A.data, fake_B.data, real_B.data), -2)
        os.makedirs("models/%s/" % "validation", exist_ok=True)
        save_image(
            img_sample,
            "models/%s/%s.png" % ("validation", batches_done),
            nrow=5,
            normalize=True,
        )

    # ----------
    #  Training
    # ----------

    prev_time = time.time()
    with mlflow.start_run(run_name=run_name) as run:
        for epoch in range(args.epoch, args.n_epochs):
            avg_loss_G = 0
            avg_loss_D = 0
            for i, (A, B) in enumerate(dataloader):

                # Model inputs
                real_A = Variable(A.type(Tensor))
                real_B = Variable(B.type(Tensor))

                # Adversarial ground truths
                valid = Variable(
                    Tensor(np.ones((real_A.size(0), *patch))), requires_grad=False
                )
                fake = Variable(
                    Tensor(np.zeros((real_A.size(0), *patch))), requires_grad=False
                )

                # ------------------
                #  Train Generators
                # ------------------

                optimizer_G.zero_grad()

                # GAN loss
                fake_B = generator(real_A)
                pred_fake = discriminator(fake_B, real_A)
                loss_GAN = criterion_GAN(pred_fake, valid)
                # Pixel-wise loss
                loss_pixel = criterion_pixelwise(fake_B, real_B)

                # Total loss
                loss_G = loss_GAN + lambda_pixel * loss_pixel
                avg_loss_G += loss_G.item()

                loss_G.backward()

                optimizer_G.step()

                # ---------------------
                #  Train Discriminator
                # ---------------------

                optimizer_D.zero_grad()

                # Real loss
                pred_real = discriminator(real_B, real_A)
                loss_real = criterion_GAN(pred_real, valid)

                # Fake loss
                pred_fake = discriminator(fake_B.detach(), real_A)
                loss_fake = criterion_GAN(pred_fake, fake)

                # Total loss
                loss_D = 0.5 * (loss_real + loss_fake)
                avg_loss_D += loss_D.item()

                loss_D.backward()
                optimizer_D.step()

                # --------------
                #  Log Progress
                # --------------

                # Determine approximate time left
                batches_done = epoch * len(dataloader) + i
                batches_left = args.n_epochs * len(dataloader) - batches_done
                time_left = datetime.timedelta(
                    seconds=batches_left * (time.time() - prev_time)
                )
                prev_time = time.time()

                # Print log
                sys.stdout.write(
                    "\r[Epoch %d/%d] [Batch %d/%d] [D loss: %f] [G loss: %f, pixel: %f, adv: %f] ETA: %s"
                    % (
                        epoch,
                        args.n_epochs,
                        i,
                        len(dataloader),
                        loss_D.item(),
                        loss_G.item(),
                        loss_pixel.item(),
                        loss_GAN.item(),
                        time_left,
                    )
                )

                # If at sample interval save image
                if batches_done % args.sample_interval == 0:
                    sample_images(batches_done)

        mlflow.log_metric("loss_G", avg_loss_G / len(dataloader), step=epoch)
        mlflow.log_metric("loss_D", avg_loss_D / len(dataloader), step=epoch)
        # if opt.models_interval != -1 and epoch % opt.models_interval == 0:
        # Save model modelss
        torch.save(
            generator.state_dict(),
            "models/generator.pth",
        )
        torch.save(
            discriminator.state_dict(),
            "models/discriminator.pth",
        )
        mlflow.pytorch.log_model(
            pytorch_model=generator,
            artifact_path=f"{artifact_path}/{run_name}_generator.pth",
        )
        mlflow.pytorch.log_model(
            pytorch_model=generator,
            artifact_path=f"{artifact_path}/{run_name}_discriminator.pth",
        )

        state_dict = torch.load("models/generator.pth", map_location="cpu")
        generator.load_state_dict(state_dict)
        if cuda:
            generator = generator.cuda()
        with torch.no_grad():
            test_error = 0
            for i, (A, B) in enumerate(test_dataloader):
                real_A = Variable(A.type(Tensor))
                real_B = Variable(B.type(Tensor))
                fake_B = generator(real_A)
                test_error += criterion_GAN(fake_B, real_B).item()

            test_error = test_error / len(test_dataloader)
        mlflow.log_metric("test_error", test_error)
        params = {
            "dataset": dataset,
            "epochs": args.n_epochs,
            "criterion_GAN": "MSELoss",
            "criterion_pixelwise": "L1Loss",
            "batch_size": args.batch_size,
            "learning_rate": args.lr,
        }
        mlflow.log_params(params)

import argparse
import torch
import torch.nn as nn
import matplotlib.pyplot as plt
from skimage.color import lab2rgb, rgb2gray
import numpy as np
import os
import cv2

from model.colorizator import Net


def to_rgb(grayscale_input, ab_input):
    # Show/save rgb image from grayscale and ab channels
    plt.clf()  # clear matplotlib
    color_image = torch.cat((grayscale_input, ab_input), 0).numpy()  # combine channels
    color_image = color_image.transpose((1, 2, 0))  # rescale for matplotlib
    color_image[:, :, 0:1] = color_image[:, :, 0:1] * 100
    color_image[:, :, 1:3] = color_image[:, :, 1:3] * 255 - 128
    color_image = lab2rgb(color_image.astype(np.float64))
    return color_image


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--model_path",
        default="checkpoint/best_model.pth",
        type=str,
        help="Path to the saved model",
    )

    parser.add_argument(
        "--image_path",
        type=str,
        help="Path to the grayscale test image",
    )

    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print("Beginning Inference")
    model = torch.load(args.model_path, weights_only=False).to(device)
    # model = Net()
    # state_dict = torch.load(
    #     args.model_path, map_location="cpu"
    # )  # Load the state dictionary
    # model.load_state_dict(state_dict)
    # model.to(device)
    input_gray = cv2.imread(args.image_path)
    w, h = input_gray.shape[0:2]
    input_gray = cv2.resize(input_gray, (256, 256))
    input_gray = rgb2gray(input_gray)
    input_gray = torch.from_numpy(input_gray).unsqueeze(0).float()
    input_gray = torch.unsqueeze(input_gray, dim=0).to(device)
    model.to(device)
    model.eval()
    output_ab = model(input_gray)
    colored_image = to_rgb(
        input_gray[0].cpu(),
        output_ab[0].detach().cpu(),
    )
    colored_image = cv2.resize(colored_image, (h, w))
    colored_image = (colored_image * 255).astype(np.uint8)
    plt.imsave(arr=colored_image, fname="checkpoint/inference_output.jpg")
    print("Colorized image saved at 'inference/inference_output.jpg'")

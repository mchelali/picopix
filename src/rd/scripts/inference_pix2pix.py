import argparse
import torch
import matplotlib.pyplot as plt
from skimage.color import rgb2gray
import numpy as np
import cv2

from model.pix2pix import GeneratorUNet


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
    generator = GeneratorUNet()

    print("Beginning Inference")
    state_dict = torch.load("models/generator.pth", map_location="cpu")
    generator.load_state_dict(state_dict)
    generator.to(device)

    input_gray = cv2.imread(args.image_path)
    w, h = input_gray.shape[0:2]
    input_gray = cv2.resize(input_gray, (256, 256))
    input_gray = rgb2gray(input_gray)
    input_gray = np.array([input_gray] * 3)
    input_gray = torch.from_numpy(input_gray).unsqueeze(0).float().to(device)

    colored_image = generator(input_gray)
    colored_image = colored_image.detach().cpu().numpy()[0].transpose(1, 2, 0)

    colored_image = cv2.resize(colored_image, (h, w))
    colored_image = (colored_image * 255).astype(np.uint8)

    plt.imsave(arr=colored_image, fname="models/pix2pix_output.jpg")
    print("Colorized image saved at 'models/pix2pix_output.jpg'")

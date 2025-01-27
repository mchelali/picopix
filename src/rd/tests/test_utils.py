import pytest
import torch
from torchvision import transforms

from utils import *


@pytest.fixture
def mock_dataset(tmp_path):
    # Create mock image dataset
    img_dir = tmp_path / "images"
    img_dir.mkdir()
    for i in range(3):
        Image.new("RGB", (64, 64), color=(i * 50, i * 50, i * 50)).save(
            img_dir / f"img_{i}.jpg"
        )
    return img_dir


def test_pix2pix_dataset_length(mock_dataset):
    dataset = Pix2pixDataset(root_dir=str(mock_dataset))
    assert len(dataset) == 3, "Dataset length mismatch"


def test_pix2pix_dataset_item(mock_dataset):
    transforms_ = transforms.Compose(
        [
            transforms.Resize((256, 256), Image.BICUBIC),
            transforms.ToTensor(),
        ]
    )
    dataset = Pix2pixDataset(root_dir=str(mock_dataset), transforms=transforms_)
    img_B, img_A = dataset[0]
    assert img_B.shape[0] == 3, "Grayscale image should have 3 channels"
    assert img_A.shape[0] == 3, "RGB image should have 3 channels"
    assert img_B.shape[1:] == img_A.shape[1:], "Image dimensions mismatch"


def test_lab_color_dataset_length(mock_dataset):
    dataset = LABColorDataset(root_dir=str(mock_dataset))
    assert len(dataset) == 3, "LAB dataset length mismatch"


def test_lab_color_dataset_item(mock_dataset):
    transform = transforms.Compose(
        [
            transforms.Resize((256, 256), Image.BICUBIC),
            transforms.ToTensor(),
        ]
    )
    dataset = LABColorDataset(root_dir=str(mock_dataset), transform=transform)
    img_gray, img_ab = dataset[0]
    assert img_gray.shape[0] == 1, "Grayscale image should have 1 channel"
    assert img_ab.shape[0] == 2, "AB channels should have 2 dimensions"
    assert img_gray.shape[1:] == img_ab.shape[1:], "Image dimensions mismatch"


def test_average_meter():
    meter = AverageMeter()
    meter.update(10, 2)
    meter.update(20, 3)
    assert meter.avg == pytest.approx(16, 0.1), "Average calculation is incorrect"
    assert meter.sum == 80, "Sum calculation is incorrect"
    assert meter.count == 5, "Count calculation is incorrect"

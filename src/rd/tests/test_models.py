import torch

from model.colorizator import Net
from model.pix2pix import GeneratorUNet, Discriminator


def test_autoencoder():
    input = torch.rand(2, 1, 256, 256)
    colorizator = Net()
    output = colorizator(input)
    assert len(output) == 2
    assert tuple(output.shape) == (2, 2, 256, 256)


def test_pix2pix():
    input = torch.rand(2, 3, 256, 256)

    gen = GeneratorUNet()
    disc = Discriminator()

    out_im = gen(input)

    assert tuple(out_im.shape) == (2, 3, 256, 256)

    pred_fake = disc(out_im, input)

    assert len(pred_fake) == 2

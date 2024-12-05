# Research & Developpement

This project contains scripts to train and evaluate a model designed to colorize a gray scale images.
In our case, we select two public GitHubs projects to train and evaluate our models. These Github projects are listed bellow: 
- [1] https://github.com/williamcfrancis/CNN-Image-Colorization-Pytorch
- [2] https://github.com/eriklindernoren/PyTorch-GAN/blob/master/implementations/pix2pix/pix2pix.py

The proposed model in [1] is the pix2pix model is a conditionnal GAN that can be trained to generate images according to the target images. In our case, it is trainned to generate color images.

The proposed model in[2] propose an autoencoder that is composed with ResNet34 to encode the gray image into a vector in lattent space and reversed ResNet34 to upscale the vector into original spatiale size and generate a color image. 

## Model

# Color space

The RGB-to-LAB color space conversion involves several steps because LAB is device-independent and based on the human visual system, unlike the RGB color space. Here’s a breakdown of the transformation:

## RGB -> LAB

Certainly! Here are the RGB-to-LAB conversion formulas in Markdown format:

### Step 1: RGB to XYZ Conversion

1. **Normalize** RGB values to the range $[0, 1]$:
   - For RGB values in $[0, 255]$, divide by 255.

2. **Apply gamma correction** to linearize RGB:
$$
   R = \begin{cases} 
        \frac{R}{12.92}, & \text{if } R \leq 0.04045 \\ 
        \left(\frac{R + 0.055}{1.055}\right)^{2.4}, & \text{if } R > 0.04045 
       \end{cases}
$$
$$
   G = \begin{cases} 
        \frac{G}{12.92}, & \text{if } G \leq 0.04045 \\ 
        \left(\frac{G + 0.055}{1.055}\right)^{2.4}, & \text{if } G > 0.04045 
       \end{cases}
$$
$$
   B = \begin{cases} 
        \frac{B}{12.92}, & \text{if } B \leq 0.04045 \\ 
        \left(\frac{B + 0.055}{1.055}\right)^{2.4}, & \text{if } B > 0.04045 
       \end{cases}

$$
1. **Convert linear RGB to XYZ** using the following matrix transformation:

   $$
   \begin{bmatrix} X \\ Y \\ Z \end{bmatrix} = 
   \begin{bmatrix} 
       0.4124564 & 0.3575761 & 0.1804375 \\ 
       0.2126729 & 0.7151522 & 0.0721750 \\ 
       0.0193339 & 0.1191920 & 0.9503041 
   \end{bmatrix} 
   \begin{bmatrix} R \\ G \\ B \end{bmatrix}
   $$

### Step 2: XYZ to LAB Conversion

The LAB color space is calculated from XYZ values with respect to a reference white point, typically $D65$, where:
- $X_n = 95.047$
- $Y_n = 100.0
- $Z_n = 108.883$

1. **Normalize $X$, $Y$, and $Z$ with the reference white:**

   $
   x = \frac{X}{X_n}, \quad y = \frac{Y}{Y_n}, \quad z = \frac{Z}{Z_n}
   $

2. **Apply the following non-linear transformation:**

   $
   f(t) = \begin{cases} 
           t^{\frac{1}{3}}, & \text{if } t > 0.008856 \\ 
           7.787t + \frac{16}{116}, & \text{if } t \leq 0.008856 
          \end{cases}
   $

3. **Calculate the LAB components:**

   $
   L = 116 \cdot f(y) - 16
   $

   $
   a = 500 \cdot (f(x) - f(y))
   $

   $
   b = 200 \cdot (f(y) - f(z))
   $

In this LAB representation:
- $L$ is in the range $[0, 100]$,
- $a$ and $b$ generally range from $[-128, 127]$.

## LAB -> RGB 

To convert from LAB to RGB, we need to reverse the transformations from LAB to XYZ and then from XYZ to RGB. Here are the formulas for each step:

### Step 1: LAB to XYZ Conversion

Given LAB values:
- $ L $ (lightness), typically in the range $[0, 100]$
- $ a $ (green-red), typically in the range $[-128, 127]$
- $ b $ (blue-yellow), typically in the range $[-128, 127]$

1. **Calculate intermediate values**:
   $
   y = \frac{L + 16}{116}
   $
   $
   x = a / 500 + y
   $
   $
   z = y - b / 200
   $

2. **Adjust values to the XYZ scale**:
   $
   X = \begin{cases} 
       X_n \cdot x^3, & \text{if } x > 0.206893 \\
       X_n \cdot \frac{x - 16 / 116}{7.787}, & \text{if } x \leq 0.206893 
       \end{cases}
   $
   
   $
   Y = \begin{cases} 
       Y_n \cdot y^3, & \text{if } y > 0.206893 \\
       Y_n \cdot \frac{y - 16 / 116}{7.787}, & \text{if } y \leq 0.206893 
       \end{cases}
   $
   
   $
   Z = \begin{cases} 
       Z_n \cdot z^3, & \text{if } z > 0.206893 \\
       Z_n \cdot \frac{z - 16 / 116}{7.787}, & \text{if } z \leq 0.206893 
       \end{cases}
   $

   Here, $ X_n = 95.047 $, $ Y_n = 100.0 $, and $ Z_n = 108.883 $ (for the D65 reference white).

### Step 2: XYZ to RGB Conversion

1. **Convert XYZ to linear RGB** using the following matrix transformation:

   $
   \begin{bmatrix} R \\ G \\ B \end{bmatrix} = 
   \begin{bmatrix} 
       3.2404542 & -1.5371385 & -0.4985314 \\ 
       -0.9692660 & 1.8760108 & 0.0415560 \\ 
       0.0556434 & -0.2040259 & 1.0572252 
   \end{bmatrix} 
   \begin{bmatrix} X \\ Y \\ Z \end{bmatrix}
   $

2. **Apply gamma correction** to convert linear RGB values to sRGB:

   For each of $ R $, $ G $, and $ B $:

   $
   R = \begin{cases} 
       12.92 \cdot R, & \text{if } R \leq 0.0031308 \\ 
       1.055 \cdot R^{\frac{1}{2.4}} - 0.055, & \text{if } R > 0.0031308 
       \end{cases}
   $

   $
   G = \begin{cases} 
       12.92 \cdot G, & \text{if } G \leq 0.0031308 \\ 
       1.055 \cdot G^{\frac{1}{2.4}} - 0.055, & \text{if } G > 0.0031308 
       \end{cases}
   $

   $
   B = \begin{cases} 
       12.92 \cdot B, & \text{if } B \leq 0.0031308 \\ 
       1.055 \cdot B^{\frac{1}{2.4}} - 0.055, & \text{if } B > 0.0031308 
       \end{cases}
   $

3. **Convert to RGB scale** (if needed):
   - Scale $ R $, $ G $, and $ B $ from $[0, 1]$ to $[0, 255]$ by multiplying by 255.

This completes the transformation from LAB to RGB. Note that you may need to clamp the RGB values to the range $[0, 255]$ at the end to ensure valid color values.


# Usage

to train autoencoder, please run the following command

```bash
poetry run python -m scripts.train_autoencoder --image_dir dataset/coco_dataset/ --epochs 2 --batch_size 4
```


TO train pix2pix model, please run the following command

```bash
poetry run python -m scripts.train_pix2pix --image_dir dataset/coco_dataset/ --n_epochs 2 --batch_size 4
```

To register the model and upload the best ones to MinIO bucket 

```bash
python -i  -m scripts.register_best_model
```
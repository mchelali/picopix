# Dataset Presentation

The PicoPix project aims to colorize images, and to train a model for this purpose, we need a dataset rich in diverse images and contexts. There are multiple datasets available, but we selected [MSCOCO](https://cocodataset.org/#download) (Microsoft Common Objects in Context) due to its extensive variety of scenes, objects, and categories, which make it ideal for learning colorization patterns across many real-world contexts.

MSCOCO is a large-scale dataset that contains over **330,000 images**, divided into different subsets for **training**, **validation**, and **test** purposes. The dataset includes a diverse set of everyday scenes containing various objects and categories, making it one of the most widely used datasets for visual tasks such as object detection, segmentation, and, in our case, image colorization.

In our project, due to the extensive quantity of data and the computational resources required, we’ll focus on the **validation set** only. This subset provides sufficient images for training and testing while keeping the data manageable.

## Dataset Splits

The MSCOCO dataset is organized into three main sets:
1. **Training Set**: The largest subset, containing around 118,000 images, designed for model training.
2. **Validation Set**: Contains around 5,000 images and is typically used for validating model performance.
3. **Test Set**: Also with around 41,000 images, this subset is used for final testing and model evaluation on unseen data.

While these subsets offer a complete setup for deep learning training workflows, for the PicoPix project, using only the validation set allows us to strike a balance between data availability and resource constraints.

## Download Instructions

To use the MSCOCO dataset as provided by Microsoft, download the images and annotations by running the following command:

```bash
python prepare_mscoco_dataset.py
```

This script will download, extract, and organize the dataset into train, validation, and test sets, allowing for an easy setup if you decide to work with the full dataset.
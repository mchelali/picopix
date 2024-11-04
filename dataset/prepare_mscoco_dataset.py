import os
import zipfile
import requests
import random
from shutil import move
from pycocotools.coco import COCO
import json

# Define categories that represent natural elements
NATURAL_CATEGORIES = ["person", "car", "sky", "animal", "bird", "dog", "cat", "plant"]

# Define the COCO 2017 dataset URLs
COCO_URLS = {
    "train": "http://images.cocodataset.org/zips/train2017.zip",
    "val": "http://images.cocodataset.org/zips/val2017.zip",
    "annotations": "http://images.cocodataset.org/annotations/annotations_trainval2017.zip",
}

# Directories for downloading and organizing dataset
BASE_DIR = "./coco_dataset"
TRAIN_DIR = os.path.join(BASE_DIR, "train")
VAL_DIR = os.path.join(BASE_DIR, "val")
TEST_DIR = os.path.join(BASE_DIR, "test")
ANNOTATIONS_DIR = os.path.join(BASE_DIR, "annotations")

# Create required directories if not exist
os.makedirs(BASE_DIR, exist_ok=True)
os.makedirs(TRAIN_DIR, exist_ok=True)
os.makedirs(VAL_DIR, exist_ok=True)
os.makedirs(TEST_DIR, exist_ok=True)
os.makedirs(ANNOTATIONS_DIR, exist_ok=True)


# Function to download and extract a zip file
def download(url):
    zip_path = os.path.join(BASE_DIR, url.split("/")[-1])
    if not os.path.exists(zip_path):
        print(f"Downloading {url}...")
        response = requests.get(url, stream=True)
        with open(zip_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)
    else:
        print(f"{zip_path} already exists. Skipping download.")
    return zip_path


def split_train_vald(zip_path, train_dir, val_dir, img_ids_filter):
    with zipfile.ZipFile(zip_path, "r") as zip_file:
        # Get a list of all image files in the ZIP archive
        # Filter files by natural image IDs and get image files
        file_list = [
            f
            for f in zip_file.namelist()
            if f.endswith(".jpg")
            # and int(os.path.basename(f).split(".")[0]) in img_ids_filter
        ]

        # Shuffle the list to ensure random distribution
        random.shuffle(file_list)

        # Calculate split index (e.g., 80% train, 20% validation)
        split_index = int(0.2 * len(file_list))
        train_files = file_list[:split_index]
        val_files = file_list[split_index : split_index + split_index]

        # Extract training files
        print("Extracting training files...")
        for file_name in train_files:
            # Extract each file into the training directory
            zip_file.extract(file_name, train_dir)

        # Extract validation files
        print("Extracting validation files...")
        for file_name in val_files:
            # Extract each file into the validation directory
            zip_file.extract(file_name, val_dir)

    return train_dir, val_dir


def extract_zip(zip_path, outputfolder):
    # # Extract the zip file
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        print(f"Extracting {zip_path}...")
        zip_ref.extractall(outputfolder)

    return outputfolder


def get_nb_file(folder):
    images = [
        os.path.join(root, f)
        for root, dirs, files in os.walk(folder)
        for f in files
        if f.endswith(".jpg")
    ]
    return len(images)


# Download the training, validation, and annotations files
train_zip = download(COCO_URLS["train"])
test_zip = download(COCO_URLS["val"])
annot_zip = download(COCO_URLS["annotations"])

test_folder = extract_zip(test_zip, TEST_DIR)
annotations_folder = extract_zip(annot_zip, ANNOTATIONS_DIR)

annotations_path = os.path.join(ANNOTATIONS_DIR, "annotations/instances_train2017.json")
# Load COCO annotations
coco = COCO(annotations_path)

# Get category IDs for natural elements
cat_ids = coco.getCatIds(catNms=NATURAL_CATEGORIES)

# Get image IDs that contain any of these categories
natural_img_ids = set(coco.getImgIds(catIds=cat_ids))

print("Moving files to train, val, and test directories...")
train_folder, val_folder = split_train_vald(
    train_zip, TRAIN_DIR, VAL_DIR, natural_img_ids
)

print("Data split completed.")
print(
    f"Training images: {get_nb_file(train_folder)}, Validation images: {get_nb_file(val_folder)} , Test images: {get_nb_file(test_folder)}"
)

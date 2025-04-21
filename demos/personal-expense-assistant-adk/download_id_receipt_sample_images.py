from datasets import load_dataset
import os

# Using mousserlane/id_receipt_dataset dataset
ds = load_dataset("mousserlane/id_receipt_dataset")

# Directory to save images
output_dir = "receipt_samples"
os.makedirs(output_dir, exist_ok=True)

for idx, item in enumerate(ds["train"]):
    image = item["image"]
    # The image is a PIL Image object; save it as a PNG file
    image_path = os.path.join(output_dir, f"{idx}.png")
    image.save(image_path)

print("All images have been saved to the receipt_samples directory.")

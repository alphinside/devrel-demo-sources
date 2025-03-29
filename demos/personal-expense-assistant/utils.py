from google.cloud import storage
from settings import get_settings
import base64
import tempfile
from pathlib import Path

SETTINGS = get_settings()

GCS_BUCKET_CLIENT = storage.Client(project=SETTINGS.GCLOUD_PROJECT_ID).get_bucket(
    "personal-expense-assistant-receipts"
)
# Create a temporary directory for caching if it doesn't exist
IMAGE_CACHE_DIR = Path(tempfile.gettempdir()) / "personal-expense-assistant-cache"
IMAGE_CACHE_DIR.mkdir(parents=True, exist_ok=True)


def store_image_in_gcs(image_data: bytes, image_hash: str) -> None:
    """
    Stores image data in Google Cloud Storage.

    Args:
        image_data: Raw binary image data
        image_hash: Generated hash identifier for the image

    Returns:
        None
    """
    try:
        # Format filename and create blob object
        blob_name = f"{image_hash}.jpg"
        blob = GCS_BUCKET_CLIENT.blob(blob_name)

        # Check if blob already exists to avoid redundant uploads
        if blob.exists():
            print(f"Image {image_hash}.jpg already exists in GCS, skipping upload")
            return

        # Create a new blob and upload the JPEG data
        blob.upload_from_string(image_data, content_type="image/jpeg")
        print(f"Successfully uploaded image {image_hash}.jpg to GCS")
    except Exception as e:
        print(f"Error storing image in GCS: {e}")


def download_image_from_gcs(image_hash: str) -> str | None:
    """
    Downloads an image from Google Cloud Storage and returns it as base64 encoded string.
    Uses local caching to avoid redundant downloads.

    Args:
        image_hash: The hash identifier of the image to download

    Returns:
        str | None: Base64 encoded image data, or None if download fails
    """
    try:
        # Define the local cache file path
        local_cache_path = IMAGE_CACHE_DIR / f"{image_hash}.jpg"

        # Check if the file exists in local cache
        if local_cache_path.exists():
            print(f"Using cached image {image_hash}.jpg from local storage")
            with open(local_cache_path, "rb") as f:
                image_data = f.read()
        else:
            # If not in cache, download from GCS
            # Construct the blob name with jpg extension
            blob_name = f"{image_hash}.jpg"
            blob = GCS_BUCKET_CLIENT.blob(blob_name)

            # Check if blob exists
            if not blob.exists():
                print(f"Image {blob_name} does not exist in GCS")
                return None

            # Download the blob as bytes and save to local cache
            image_data = blob.download_as_bytes()
            with open(local_cache_path, "wb") as f:
                f.write(image_data)

            print(f"Downloaded and cached image {image_hash}.jpg")

        return base64.b64encode(image_data).decode("utf-8")
    except Exception as e:
        print(f"Error downloading image from GCS: {e}")
        return None

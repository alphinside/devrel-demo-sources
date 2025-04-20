from google.cloud import storage
from settings import get_settings
import base64
import tempfile
from pathlib import Path
import re

SETTINGS = get_settings()

GCS_BUCKET_CLIENT = storage.Client(project=SETTINGS.GCLOUD_PROJECT_ID).get_bucket(
    SETTINGS.STORAGE_BUCKET_NAME
)
# Create a temporary directory for caching if it doesn't exist
IMAGE_CACHE_DIR = Path(tempfile.gettempdir()) / "personal-expense-assistant-cache"
IMAGE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
STORED_IMAGE_NAME_FORMAT = "{image_hash_id}.webp"


def store_image_in_gcs(image_data: bytes, image_hash_id: str) -> None:
    """
    Stores image data in Google Cloud Storage.

    Args:
        image_data: Raw binary image data (standardized as WebP)
        image_hash_id: Hash identifier of the image

    Returns:
        None
    """
    try:
        # Format filename and create blob object
        blob = GCS_BUCKET_CLIENT.blob(
            STORED_IMAGE_NAME_FORMAT.format(image_hash_id=image_hash_id)
        )

        # Check if blob already exists to avoid redundant uploads
        if blob.exists():
            print(f"Image {image_hash_id} already exists in GCS, skipping upload")
            return

        # Create a new blob and upload the image data with WebP mime type
        blob.upload_from_string(image_data, content_type="image/webp")
        print(f"Successfully uploaded image {image_hash_id} to GCS")
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
        image_file_name = STORED_IMAGE_NAME_FORMAT.format(image_hash_id=image_hash)

        # Define the local cache file path
        local_cache_path = IMAGE_CACHE_DIR / image_file_name

        # Check if the file exists in local cache
        if local_cache_path.exists():
            print(f"Using cached image {image_file_name} from local storage")
            with open(local_cache_path, "rb") as f:
                image_data = f.read()
        else:
            # If not in cache, download from GCS
            blob = GCS_BUCKET_CLIENT.blob(image_file_name)

            # Check if blob exists
            if not blob.exists():
                print(f"Image {image_file_name} does not exist in GCS")
                return None

            # Download the blob as bytes and save to local cache
            image_data = blob.download_as_bytes()
            with open(local_cache_path, "wb") as f:
                f.write(image_data)

            print(f"Downloaded and cached image {image_file_name}")

        return base64.b64encode(image_data).decode("utf-8")
    except Exception as e:
        print(f"Error downloading image from GCS: {e}")
        return None

def sanitize_image_id(image_id: str) -> str:
    """Sanitize image ID by removing any leading/trailing whitespace."""
    if image_id.startswith("[IMAGE-"):
        image_id = image_id.split("ID ")[1].split("]")[0]
        
    return image_id.strip()

def extract_attachment_ids_from_response(response_text: str) -> list[str]:
    """Extract image hash IDs from <attachments> tags in the response.

    Args:
        response_text: The response text from the LLM.

    Returns:
        list[str]: List of image hash IDs.
    """
    # Look for <attachments> tag
    pattern = r"<attachments>([^<]+)</attachments>"

    match = re.search(pattern, response_text)
    if match:
        content = match.group(1).strip()

        # Split by commas and strip whitespace
        hash_ids = [sanitize_image_id(hash_id.strip()) for hash_id in content.split(",")]
        return [hash_id for hash_id in hash_ids if hash_id]  # Filter out empty strings

    return []

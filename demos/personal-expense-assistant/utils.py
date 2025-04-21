from google.cloud import storage
from settings import get_settings
import base64
import tempfile
from pathlib import Path
import re
from schema import ChatRequest
from google.genai import types
import hashlib

SETTINGS = get_settings()

GCS_BUCKET_CLIENT = storage.Client(project=SETTINGS.GCLOUD_PROJECT_ID).get_bucket(
    SETTINGS.STORAGE_BUCKET_NAME
)
# Create a temporary directory for caching if it doesn't exist
IMAGE_CACHE_DIR = Path(tempfile.gettempdir()) / "personal-expense-assistant-cache"
IMAGE_CACHE_DIR.mkdir(parents=True, exist_ok=True)


def format_user_request_to_adk_content(request: ChatRequest) -> types.Content:
    """Format a user request into ADK Content format.

    Args:
        request: The chat request object containing text and optional files

    Returns:
        types.Content: The formatted content for ADK
    """
    # Create a list to hold parts
    parts = []

    # Handle image files if present
    for data in request.files:
        # Process the image and convert to string placeholder
        image_data = base64.b64decode(data.serialized_image)
        # Store in Google Cloud Storage
        image_hash_id, gs_uri = store_image_in_gcs(image_data, data.mime_type)

        # Add gs:// URI to parts
        parts.append(
            types.Part(
                file_data=types.FileData(file_uri=gs_uri, mime_type=data.mime_type)
            )
        )

        # Add image placeholder identifier
        placeholder = f"[IMAGE-ID {image_hash_id}]"
        parts.append(types.Part(text=placeholder))

    # Handle if user didn't specify text input
    if not request.text:
        request.text = " "

    parts.append(types.Part(text=request.text))

    # Create and return the Content object
    return types.Content(role="user", parts=parts)


def store_image_in_gcs(image_data: bytes, mime_type: str) -> tuple[str, str]:
    """
    Generate a unique hash ID for image data and store it in Google Cloud Storage.

    Args:
        image_data: Raw binary image data (standardized as WebP)
        mime_type: MIME type of the image

    Returns:
        tuple[str, str]: A tuple containing the hash identifier of the image and the gs:// URI
    """
    try:
        # Generate a unique hash ID for the image
        hasher = hashlib.sha256(image_data)
        image_hash_id = hasher.hexdigest()[:12]

        # Create blob object
        blob = GCS_BUCKET_CLIENT.blob(image_hash_id)

        # Get URI formats for the blob
        gs_uri = f"gs://{SETTINGS.STORAGE_BUCKET_NAME}/{image_hash_id}"

        # Check if blob already exists to avoid redundant uploads
        if blob.exists():
            print(f"Image {image_hash_id} already exists in GCS, skipping upload")
            return image_hash_id, gs_uri

        # Upload the image data
        blob.upload_from_string(image_data, content_type=mime_type)
        print(f"Successfully uploaded image {image_hash_id} to GCS")

        return image_hash_id, gs_uri
    except Exception as e:
        raise Exception(f"Error storing image in GCS: {e}")


def download_image_from_gcs(image_hash: str) -> tuple[str, str] | None:
    """
    Downloads an image from Google Cloud Storage and returns it as base64 encoded string with its MIME type.
    Uses local caching to avoid redundant downloads.

    Args:
        image_hash: The hash identifier of the image to download

    Returns:
        tuple[str, str] | None: A tuple containing (base64_encoded_data, mime_type), or None if download fails
    """
    try:
        # Define the local cache file path and metadata path
        local_cache_path = IMAGE_CACHE_DIR / image_hash
        local_metadata_path = IMAGE_CACHE_DIR / f"{image_hash}.metadata"
        mime_type = "image/jpeg"  # Default mime type if not found

        # Check if the file exists in local cache
        if local_cache_path.exists() and local_metadata_path.exists():
            print(f"Using cached image {image_hash} from local storage")
            with open(local_cache_path, "rb") as f:
                image_data = f.read()
            with open(local_metadata_path, "r") as f:
                mime_type = f.read().strip()
        else:
            # If not in cache, download from GCS
            blob = GCS_BUCKET_CLIENT.blob(image_hash)
            blob.reload()  # Ensure we have the latest metadata

            # Check if blob exists
            if not blob.exists():
                print(f"Image {image_hash} does not exist in GCS")
                return None

            # Download the blob as bytes and save to local cache
            image_data = blob.download_as_bytes()
            with open(local_cache_path, "wb") as f:
                f.write(image_data)

            # Get and save the mime type metadata
            mime_type = blob.content_type or mime_type
            with open(local_metadata_path, "w") as f:
                f.write(mime_type)

            print(f"Downloaded and cached image {image_hash} with type {mime_type}")

        return base64.b64encode(image_data).decode("utf-8"), mime_type
    except Exception as e:
        print(f"Error downloading image from GCS: {e}")
        return None


def sanitize_image_id(image_id: str) -> str:
    """Sanitize image ID by removing any leading/trailing whitespace."""
    if image_id.startswith("[IMAGE-"):
        image_id = image_id.split("ID ")[1].split("]")[0]

    return image_id.strip()


def extract_attachment_ids_and_sanitize_response(
    response_text: str,
) -> tuple[str, list[str]]:
    """Extract image hash IDs from <attachments> tags and remove those tags from the response.

    Args:
        response_text: The response text from the LLM.

    Returns:
        tuple[str, list[str]]: A tuple containing the sanitized response text and list of image hash IDs.
    """
    # Look for <attachments> tag
    pattern = r"<attachments>([^<]+)</attachments>"

    # Find all occurrences of the pattern
    matches = re.findall(pattern, response_text)
    all_attachments_hash_ids = []

    for match in matches:
        content = match.strip()

        # Split by commas and strip whitespace
        hash_ids = [
            sanitize_image_id(hash_id.strip()) for hash_id in content.split(",")
        ]
        all_attachments_hash_ids.extend(
            [hash_id for hash_id in hash_ids if hash_id]
        )  # Filter out empty strings

    # Remove all <attachments> tags from the response
    sanitized_text = re.sub(pattern, "", response_text)

    return sanitized_text, all_attachments_hash_ids


def extract_thinking_process(response_text: str) -> tuple[str, str]:
    """Extract thinking process from response text and sanitize the response.

    Args:
        response_text: The response text from the LLM.

    Returns:
        tuple[str, str]: A tuple containing the sanitized response text and extracted thinking process.
    """
    # Look for content between <thinking> and </thinking>
    pattern = r"<thinking>(.+?)</thinking>"

    # Search for the pattern
    match = re.search(pattern, response_text, re.DOTALL)
    thinking_process = ""

    if match:
        thinking_process = match.group(1).strip()

    # Remove the thinking process from the response
    sanitized_text = re.sub(pattern, "", response_text, flags=re.DOTALL)

    return sanitized_text, thinking_process

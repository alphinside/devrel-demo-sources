from google.cloud import storage
from settings import get_settings
import base64
from schema import ChatRequest, ImageData
from google.genai import types
import hashlib
from google.adk.artifacts import GcsArtifactService
import logger


SETTINGS = get_settings()

GCS_BUCKET_CLIENT = storage.Client(project=SETTINGS.GCLOUD_PROJECT_ID).get_bucket(
    SETTINGS.STORAGE_BUCKET_NAME
)


def store_uploaded_image_as_artifact(
    artifact_service: GcsArtifactService,
    app_name: str,
    user_id: str,
    session_id: str,
    image_data: ImageData,
) -> tuple[str, bytes]:
    """
    Store an uploaded image as an artifact in Google Cloud Storage.

    Args:
        artifact_service: The artifact service to use for storing artifacts
        app_name: The name of the application
        user_id: The ID of the user
        session_id: The ID of the session
        image_data: The image data to store

    Returns:
        tuple[str, bytes]: A tuple containing the image hash ID and the image byte
    """

    # Decode the base64 image data and use it to generate a hash id
    image_byte = base64.b64decode(image_data.serialized_image)
    hasher = hashlib.sha256(image_byte)
    image_hash_id = hasher.hexdigest()[:12]

    artifact_versions = artifact_service.list_versions(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id,
        filename=image_hash_id,
    )
    if artifact_versions:
        logger.info(f"Image {image_hash_id} already exists in GCS, skipping upload")

        return image_hash_id, image_byte

    artifact_service.save_artifact(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id,
        filename=image_hash_id,
        artifact=types.Part(
            inline_data=types.Blob(mime_type=image_data.mime_type, data=image_byte)
        ),
    )

    return image_hash_id, image_byte


def download_image_from_gcs(
    artifact_service: GcsArtifactService,
    app_name: str,
    user_id: str,
    session_id: str,
    image_hash: str,
) -> tuple[str, str] | None:
    """
    Downloads an image artifact from Google Cloud Storage and
    returns it as base64 encoded string with its MIME type.
    Uses local caching to avoid redundant downloads.

    Args:
        artifact_service: The artifact service to use for downloading artifacts
        app_name: The name of the application
        user_id: The ID of the user
        session_id: The ID of the session
        image_hash: The hash identifier of the image to download

    Returns:
        tuple[str, str] | None: A tuple containing (base64_encoded_data, mime_type), or None if download fails
    """
    try:
        artifact = artifact_service.load_artifact(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id,
            filename=image_hash,
        )
        if not artifact:
            logger.info(f"Image {image_hash} does not exist in GCS Artifact Service")
            return None

        # Get the blob and mime type
        image_data = artifact.inline_data.data
        mime_type = artifact.inline_data.mime_type

        logger.info(f"Downloaded image {image_hash} with type {mime_type}")

        return base64.b64encode(image_data).decode("utf-8"), mime_type
    except Exception as e:
        logger.error(f"Error downloading image from GCS: {e}")
        return None


def format_user_request_to_adk_content_and_store_artifacts(
    request: ChatRequest, app_name: str, artifact_service: GcsArtifactService
) -> types.Content:
    """Format a user request into ADK Content format.

    Args:
        request: The chat request object containing text and optional files
        app_name: The name of the application
        artifact_service: The artifact service to use for storing artifacts

    Returns:
        types.Content: The formatted content for ADK
    """
    # Create a list to hold parts
    parts = []

    # Handle image files if present
    for data in request.files:
        # Process the image and add string placeholder

        image_hash_id, image_byte = store_uploaded_image_as_artifact(
            artifact_service=artifact_service,
            app_name=app_name,
            user_id=request.user_id,
            session_id=request.session_id,
            image_data=data,
        )

        # Add inline data part
        parts.append(
            types.Part(
                inline_data=types.Blob(mime_type=data.mime_type, data=image_byte)
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


def sanitize_image_id(image_id: str) -> str:
    """Sanitize image ID by removing any leading/trailing whitespace."""
    if image_id.startswith("[IMAGE-"):
        image_id = image_id.split("ID ")[1].split("]")[0]

    return image_id.strip()

from langchain_google_genai import GoogleGenerativeAIEmbeddings
import firebase_admin
from firebase_admin import firestore
from firebase_admin import credentials
from langchain_google_firestore import FirestoreVectorStore
import typer
from google.cloud import storage
from google.oauth2 import service_account
import vertexai
from vertexai.vision_models import Image, MultiModalEmbeddingModel
from google.cloud.firestore_v1.vector import Vector

from settings import get_settings, IMAGE_EMBEDDING_DIMENSION, IMAGE_EMBEDDING_FIELD_NAME

app = typer.Typer()
settings = get_settings()
BUCKET_NAME = "genai-l200-training"
IMAGE_PREFIX = "images/"
PDF_PREFIX = "documents/"

sa_credentials = service_account.Credentials.from_service_account_file(
    settings.CLOUDRUN_SERVICE_ACCOUNT_KEY,
)

vertexai.init(
    project=settings.VERTEX_PROJECT_ID,
    location=settings.VERTEX_LOCATION,
    credentials=sa_credentials,
)


def initialize_firebase() -> tuple[FirestoreVectorStore, firestore.CollectionReference]:
    """Initialize Firebase and create vector store instances.

    This function sets up the Firebase client and creates vector store instances
    for both document and image embeddings using Google's Generative AI.

    Returns:
        tuple[FirestoreVectorStore, firestore.CollectionReference]: A tuple containing:
            - FirestoreVectorStore instance for document embeddings
            - Firestore collection reference for image embeddings
    """
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/text-embedding-004", google_api_key=settings.GEMINI_API_KEY
    )

    cred = credentials.Certificate(settings.CLOUDRUN_SERVICE_ACCOUNT_KEY)
    firebase_app = firebase_admin.initialize_app(cred)
    firestore_db = firestore.client(app=firebase_app)

    docs_vector_store = FirestoreVectorStore(
        collection=settings.DOCS_COLLECTION_NAME,
        embedding_service=embeddings,
        client=firestore_db,
    )

    image_collection = firestore_db.collection(settings.IMAGE_COLLECTION_NAME)
    multimodal_embeddings = MultiModalEmbeddingModel.from_pretrained(
        "multimodalembedding@001"
    )

    return docs_vector_store, image_collection, multimodal_embeddings


def convert_and_store_image_embedding(
    collection: firestore.CollectionReference,
    image_path: str,
    multimodal_embeddings: MultiModalEmbeddingModel,
):
    """Store image embedding in Firestore.

    Args:
        collection: Firestore collection reference
        image_path: Path to the image in GCS
        multimodal_embeddings: MultiModalEmbeddingModel instance
    """

    # Generate image embedding
    embeddings = multimodal_embeddings.get_embeddings(
        image=Image.load_from_file(f"gs://{BUCKET_NAME}/{image_path}"),
        dimension=IMAGE_EMBEDDING_DIMENSION,
    )

    collection.add(
        {
            "image_path": image_path,
            IMAGE_EMBEDDING_FIELD_NAME: Vector(embeddings.image_embedding),
            "created_at": firestore.SERVER_TIMESTAMP,
        }
    )


@app.command()
def ingest_images_and_pdf_data(
    batch_size: int = typer.Option(
        10, help="Number of documents to process in each batch"
    ),
) -> None:
    """Ingest images and document data into Firebase.

    This command processes images and documents, generates embeddings,
    and stores them in Firebase for vector search capabilities.

    Args:
        batch_size: Number of documents to process in each batch (default: 10)
    """
    try:
        docs_vector_store, image_collection, multimodal_embeddings = (
            initialize_firebase()
        )

        # Process images
        # images_files = list_genai_l200_images_files()

        # # Index image embedding
        # for image_file in tqdm(images_files, desc="Processing images"):

        #     convert_and_store_image_embedding(
        #         collection=image_collection,
        #         image_path=image_file,
        #         multimodal_embeddings=multimodal_embeddings,
        #     )

        print("\nCompleted processing all images!")

        # Create vector search index
        print("\nCreating vector search index...")
        import subprocess

        vector_config = f'{{"dimension":{IMAGE_EMBEDDING_DIMENSION},"flat":{{}}}}'
        field_config = (
            f"field-path={IMAGE_EMBEDDING_FIELD_NAME},vector-config={vector_config}"
        )

        gcloud_cmd = [
            "gcloud",
            "firestore",
            "indexes",
            "composite",
            "create",
            f"--collection-group={settings.IMAGE_COLLECTION_NAME}",
            "--query-scope=COLLECTION",
            f"--field-config={field_config}",
            "--database=(default)",
        ]

        try:
            subprocess.run(gcloud_cmd, check=True)
            print("Vector search index created successfully!")
        except subprocess.CalledProcessError as e:
            print(f"Warning: Failed to create vector search index: {e}")

    except Exception as e:
        typer.echo(f"Error processing files: {str(e)}", err=True)
        raise typer.Exit(1)


def list_genai_l200_images_files():
    """List all image files in the Google Cloud Storage bucket.

    Returns:
        List[str]: List of image file names in the bucket
    """
    try:
        # Initialize GCS client
        storage_client = storage.Client(credentials=sa_credentials)
        bucket = storage_client.bucket(BUCKET_NAME)

        # List all blobs/files in the bucket and get their names
        blobs = bucket.list_blobs(prefix=IMAGE_PREFIX)
        return [blob.name for blob in blobs if blob.name.split("/")[-1]]

    except Exception as e:
        print(f"Error listing files: {str(e)}")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()

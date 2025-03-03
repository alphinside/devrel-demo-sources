from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
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
from tqdm import tqdm
from typing import List, Tuple
import subprocess
import io
from PyPDF2 import PdfReader
from langchain_core.documents import Document

from settings import (
    get_settings,
    IMAGE_EMBEDDING_DIMENSION,
    PDF_EMBEDDING_DIMENSION,
    EMBEDDING_FIELD_NAME,
    BUCKET_NAME,
    IMAGE_PREFIX,
    PDF_PREFIX,
)

app = typer.Typer()
settings = get_settings()

sa_credentials = service_account.Credentials.from_service_account_file(
    settings.CLOUDRUN_SERVICE_ACCOUNT_KEY,
)

vertexai.init(
    project=settings.VERTEX_PROJECT_ID,
    location=settings.VERTEX_LOCATION,
    credentials=sa_credentials,
)


def initialize_firebase() -> Tuple[
    FirestoreVectorStore, firestore.CollectionReference, MultiModalEmbeddingModel
]:
    """Initialize Firebase and create instances for vector search.

    Sets up Firebase client and creates necessary instances for both document
    and image vector search capabilities:
    1. Document vector store using Gemini text embeddings
    2. Image collection for storing multimodal embeddings
    3. Pre-trained multimodal embedding model

    Returns:
        Tuple containing:
        - FirestoreVectorStore: Vector store for document embeddings
        - firestore.CollectionReference: Collection for image embeddings
        - MultiModalEmbeddingModel: Model for generating image embeddings

    Raises:
        firebase_admin.exceptions.FirebaseError: If Firebase initialization fails
        google.api_core.exceptions.GoogleAPIError: If model initialization fails
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
) -> None:
    """Generate and store embedding for a single image in Firestore.

    Args:
        collection: Firestore collection reference for storing embeddings
        image_path: Path to the image in GCS bucket (without bucket name)
        multimodal_embeddings: Pre-trained model for generating image embeddings

    Raises:
        Exception: If there's an error generating embeddings or storing in Firestore
    """

    # Generate image embedding
    full_path = f"gs://{BUCKET_NAME}/{image_path}"
    embeddings = multimodal_embeddings.get_embeddings(
        image=Image.load_from_file(full_path),
        dimension=IMAGE_EMBEDDING_DIMENSION,
    )

    collection.add(
        {
            "image_path": full_path,
            EMBEDDING_FIELD_NAME: Vector(embeddings.image_embedding),
            "created_at": firestore.SERVER_TIMESTAMP,
        }
    )


def create_vector_search_index(collection_name: str, embedding_dimension: int) -> bool:
    """Create a vector search index for a Firestore collection.

    Creates a composite index that enables vector similarity search
    over the embedding field in the specified collection.

    Args:
        collection_name: Name of the collection to create index for
        embedding_dimension: Dimension of the embedding vector

    Returns:
        bool: True if index creation was successful, False otherwise

    Raises:
        subprocess.CalledProcessError: If the gcloud command fails
    """
    vector_config = f'{{"dimension":{embedding_dimension},"flat":{{}}}}'
    field_config = f"field-path={EMBEDDING_FIELD_NAME},vector-config={vector_config}"

    gcloud_cmd = [
        "gcloud",
        "firestore",
        "indexes",
        "composite",
        "create",
        f"--collection-group={collection_name}",
        "--query-scope=COLLECTION",
        f"--field-config={field_config}",
        "--database=(default)",
    ]

    try:
        subprocess.run(gcloud_cmd, check=True)
        typer.echo(
            f"Vector search index created successfully for collection: {collection_name}"
        )
        return True
    except subprocess.CalledProcessError as e:
        typer.echo(f"Warning: Failed to create vector search index: {e}")
        return False


@app.command()
def ingest_data() -> None:
    """Ingest both images and document data into Firebase.

    This command orchestrates the complete ingestion pipeline:
    1. Initializes Firebase and required models
    2. Processes images: generates embeddings and stores in image collection
    3. Processes PDFs: extracts text, splits into chunks, and stores in document collection
    4. Creates vector search indexes for both collections

    Raises:
        typer.Exit: If there's an error during any stage of the ingestion process
    """

    docs_vector_store, image_collection, multimodal_embeddings = initialize_firebase()

    ingest_images_data(image_collection, multimodal_embeddings)
    ingest_pdf_data(docs_vector_store)


def ingest_images_data(
    image_collection: firestore.CollectionReference,
    multimodal_embeddings: MultiModalEmbeddingModel,
) -> None:
    """Process and store image embeddings in Firebase.

    For each image in the GCS bucket:
    1. Generates embeddings using the multimodal model
    2. Stores embeddings and metadata in Firestore
    3. Creates a vector search index for the collection

    Args:
        image_collection: Firestore collection for storing image embeddings
        multimodal_embeddings: Pre-trained model for generating image embeddings

    Raises:
        typer.Exit: If there's an error processing images or creating the index
    """
    try:
        # Process images
        images_files = list_genai_l200_files(IMAGE_PREFIX)

        # Index image embedding
        for image_file in tqdm(images_files, desc="Processing images"):
            convert_and_store_image_embedding(
                collection=image_collection,
                image_path=image_file,
                multimodal_embeddings=multimodal_embeddings,
            )

        typer.echo("\nCompleted processing all images!")

        # Create vector search index
        typer.echo("\nCreating vector search index for image collection...")
        create_vector_search_index(
            settings.IMAGE_COLLECTION_NAME, IMAGE_EMBEDDING_DIMENSION
        )

    except Exception as e:
        typer.echo(f"Error processing files: {str(e)}", err=True)
        raise typer.Exit(1)


def list_genai_l200_files(prefix: str) -> List[str]:
    """List files from a specific prefix in the GCS bucket.

    Args:
        prefix: Directory prefix to list files from (e.g., 'images/' or 'documents/')

    Returns:
        List[str]: List of file paths relative to the bucket root,
                  excluding empty directory markers

    Raises:
        typer.Exit: If there's an error accessing the GCS bucket or listing files
    """
    try:
        # Initialize GCS client
        storage_client = storage.Client(credentials=sa_credentials)
        bucket = storage_client.bucket(BUCKET_NAME)

        # List all blobs/files in the bucket and get their names
        blobs = bucket.list_blobs(prefix=prefix)
        return [blob.name for blob in blobs if blob.name.split("/")[-1]]

    except Exception as e:
        typer.echo(f"Error listing files: {str(e)}")
        raise typer.Exit(1)


def read_pdf_from_gcs(bucket_name: str, pdf_path: str) -> str:
    """Read and extract text content from a PDF stored in GCS.

    Downloads the PDF content to memory and extracts text from all pages
    without saving to disk.

    Args:
        bucket_name: Name of the GCS bucket
        pdf_path: Path to the PDF file in the bucket

    Returns:
        str: Concatenated text content from all pages of the PDF

    Raises:
        Exception: If there's an error downloading, reading, or processing the PDF
    """
    try:
        # Initialize GCS client and get the blob
        storage_client = storage.Client(credentials=sa_credentials)
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(pdf_path)

        # Download PDF content to memory
        pdf_content = blob.download_as_bytes()

        # Create PDF reader object
        pdf_file = io.BytesIO(pdf_content)
        pdf_reader = PdfReader(pdf_file)

        # Extract text from all pages
        text_content = []
        for page in pdf_reader.pages:
            text_content.append(page.extract_text())

        return "\n".join(text_content)

    except Exception as e:
        raise Exception(f"Error reading PDF {pdf_path}: {str(e)}")


def ingest_pdf_data(
    docs_vector_store: FirestoreVectorStore,
) -> None:
    """Process and store PDF content in Firebase.

    For each PDF in the GCS bucket:
    1. Extracts text content
    2. Splits text into smaller chunks for better embedding
    3. Generates embeddings for each chunk
    4. Stores in Firestore with metadata
    5. Creates a vector search index

    Args:
        docs_vector_store: FirestoreVectorStore for document embeddings

    Raises:
        typer.Exit: If there's an error processing PDFs or creating the index
    """
    try:
        # Initialize text splitter
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=300,
            chunk_overlap=100,
            length_function=len,
            separators=["\n\n", "\n", " ", ""],
        )

        # Get list of PDF files
        pdf_files = list_genai_l200_files(PDF_PREFIX)

        # Process each PDF
        for pdf_file in tqdm(pdf_files, desc="Processing PDFs"):
            # Extract text content
            text_content = read_pdf_from_gcs(BUCKET_NAME, pdf_file)

            # Split text into chunks
            texts = text_splitter.split_text(text_content)

            # Create documents with metadata for each chunk
            documents = []
            for text_chunk in texts:
                doc = Document(
                    page_content=text_chunk,
                    metadata={
                        "bucket_path": f"gs://{BUCKET_NAME}/{pdf_file}",
                    },
                )
                documents.append(doc)

            # Add to vector store in batches
            docs_vector_store.add_documents(documents)
            typer.echo(f"\nProcessed {pdf_file}: {len(texts)} chunks created")

        typer.echo("\nCompleted processing all PDFs!")

        # Create vector search index
        typer.echo("\nCreating vector search index for document collection...")
        create_vector_search_index(
            settings.DOCS_COLLECTION_NAME, PDF_EMBEDDING_DIMENSION
        )

    except Exception as e:
        typer.echo(f"Error processing PDF files: {str(e)}", err=True)
        raise typer.Exit(1)


if __name__ == "__main__":
    app()

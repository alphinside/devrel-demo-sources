from langchain_google_genai import GoogleGenerativeAIEmbeddings
import firebase_admin
from firebase_admin import firestore
from firebase_admin import credentials
from langchain_google_firestore import FirestoreVectorStore
from langchain_core.documents import Document
from tqdm import tqdm
import typer
from typing import List
from pathlib import Path

from settings import get_settings

app = typer.Typer()


def initialize_firebase() -> tuple[firestore.Client, FirestoreVectorStore]:
    """Initialize Firebase and create vector store instance.

    This function sets up the Firebase client and creates a vector store instance
    using Google's Generative AI embeddings.

    Returns:
        tuple[firestore.Client, FirestoreVectorStore]: A tuple containing:
            - Firestore client instance
            - FirestoreVectorStore instance configured with Gemini embeddings
    """
    settings = get_settings()

    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/text-embedding-004", google_api_key=settings.GEMINI_API_KEY
    )

    cred = credentials.Certificate(settings.CLOUDRUN_SERVICE_ACCOUNT_KEY)
    firebase_app = firebase_admin.initialize_app(cred)
    db = firestore.client(app=firebase_app)

    vector_store = FirestoreVectorStore(
        collection=settings.COLLECTION_NAME, embedding_service=embeddings, client=db
    )

    return db, vector_store


def process_ndjson_batch(
    vector_store: FirestoreVectorStore, batch: List[Document], batch_size: int = 10
) -> None:
    """Process a batch of documents and add them to the vector store.

    Args:
        vector_store: The vector store instance to add documents to
        batch: List of Document objects to be processed
        batch_size: Size of each batch for processing (default: 10)
    """
    if len(batch) >= batch_size:
        vector_store.add_documents(documents=batch)
        batch.clear()


@app.command()
def ingest_hotels_data(
    input_file: Path = typer.Argument(
        "hotel_data.ndjson", help="Path to the NDJSON file containing hotel data"
    ),
    batch_size: int = typer.Option(
        10, help="Number of documents to process in each batch"
    ),
) -> None:
    """Ingest hotel data from NDJSON file into Firebase vector store.

    This command reads hotel data from an NDJSON file and stores it in Firebase
    using vector embeddings for semantic search capabilities.

    Args:
        input_file: Path to the NDJSON file containing hotel data.
            Optional, default is 'hotel_data.ndjson'
        batch_size: Number of documents to process in each batch (default: 10)

    Raises:
        FileNotFoundError: If the input file doesn't exist
        typer.Exit: If there's an error processing the file
    """
    try:
        _, vector_store = initialize_firebase()

        if not input_file.exists():
            typer.echo(f"Error: File {input_file} not found", err=True)
            raise typer.Exit(1)

        batches: List[Document] = []
        with open(input_file, "r") as file:
            for line in tqdm(file, desc="Processing hotels"):
                hotel_data = line.strip()
                doc = Document(page_content=hotel_data)
                batches.append(doc)

                process_ndjson_batch(vector_store, batches, batch_size)

        # Process remaining documents
        if batches:
            vector_store.add_documents(documents=batches)

        typer.echo(f"Successfully processed hotel data from {input_file}")

    except Exception as e:
        typer.echo(f"Error processing file: {str(e)}", err=True)
        raise typer.Exit(1)


if __name__ == "__main__":
    app()

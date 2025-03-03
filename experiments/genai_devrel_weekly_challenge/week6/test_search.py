from index import initialize_firebase
import typer
from firebase_admin import firestore
from google.cloud.firestore_v1.base_vector_query import DistanceMeasure
from google.cloud.firestore_v1.vector import Vector
from vertexai.vision_models import MultiModalEmbeddingModel
from settings import IMAGE_EMBEDDING_DIMENSION, EMBEDDING_FIELD_NAME
from typing import List
from langchain_core.documents import Document

app = typer.Typer()


def search_firestore_collection(
    image_collection: firestore.CollectionReference,
    multimodal_embeddings: MultiModalEmbeddingModel,
    query: str,
    limit: int,
) -> List[str]:
    """Search for images in Firestore using semantic similarity.

    Generates text embeddings from the query and performs vector similarity search
    against the image embeddings stored in Firestore.

    Args:
        image_collection: Firestore collection containing image embeddings
        multimodal_embeddings: Model for generating query embeddings
        query: Natural language query to search for images
        limit: Maximum number of results to return

    Returns:
        List[str]: List of GCS paths to the most relevant images

    Raises:
        google.api_core.exceptions.GoogleAPIError: If embedding generation fails
        google.cloud.exceptions.NotFound: If collection doesn't exist
    """
    embeddings = multimodal_embeddings.get_embeddings(
        contextual_text=query,
        dimension=IMAGE_EMBEDDING_DIMENSION,
    )
    # Requires a single-field vector index
    query_result = image_collection.find_nearest(
        vector_field=EMBEDDING_FIELD_NAME,
        query_vector=Vector(embeddings.text_embedding),
        distance_measure=DistanceMeasure.COSINE,
        limit=limit,
    )

    return [doc.to_dict()["image_path"] for doc in query_result.stream()]


@app.command()
def search_query(
    query: str = typer.Argument(..., help="Search query for finding relevant content"),
    limit: int = typer.Option(5, help="Maximum number of results to return"),
) -> None:
    """Search for images and documents using semantic similarity.

    Performs a semantic search over both image and document collections using
    the provided query. For images, it uses multimodal embeddings to find visually
    similar content. For documents, it uses text embeddings to find relevant text chunks.

    Args:
        query: Natural language query to search for content
        limit: Maximum number of results to return per collection (default: 5)

    Examples:
        $ python test_search.py "modern office building with glass walls"
        $ python test_search.py "document about sustainability" --limit 10

    Raises:
        typer.Exit: If there's an error during search execution
    """
    try:
        docs_vector_store, image_collection, multimodal_embeddings = (
            initialize_firebase()
        )

        # Perform the image search
        image_search_results = search_firestore_collection(
            image_collection, multimodal_embeddings, query, limit
        )

        # Perform the pdf search
        pdf_results: List[Document] = docs_vector_store.similarity_search(
            query, k=limit
        )

        # Display image results
        typer.echo(
            f"\nFound {len(image_search_results)} image search results for: '{query}'\n"
        )
        for image_path in image_search_results:
            typer.echo("-" * 30)
            typer.echo(image_path)

        # Display document results
        typer.echo(f"\nFound {len(pdf_results)} pdf search results for: '{query}'\n")
        for result in pdf_results:
            typer.echo("-" * 30)
            typer.echo(result.page_content)

    except Exception as e:
        import traceback

        typer.echo(
            f"Error performing search: {str(e)}\n{traceback.format_exc()}", err=True
        )
        raise typer.Exit(1)


if __name__ == "__main__":
    app()

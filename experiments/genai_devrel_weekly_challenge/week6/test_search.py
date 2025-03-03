from index import initialize_firebase
import typer
from firebase_admin import firestore
from google.cloud.firestore_v1.base_vector_query import DistanceMeasure
from google.cloud.firestore_v1.vector import Vector
from vertexai.vision_models import MultiModalEmbeddingModel
from settings import IMAGE_EMBEDDING_DIMENSION, IMAGE_EMBEDDING_FIELD_NAME

app = typer.Typer()


def search_firestore_collection(
    image_collection: firestore.CollectionReference,
    multimodal_embeddings: MultiModalEmbeddingModel,
    query: str,
    limit: int,
):
    embeddings = multimodal_embeddings.get_embeddings(
        contextual_text=query,
        dimension=IMAGE_EMBEDDING_DIMENSION,
    )
    # Requires a single-field vector index
    query_result = image_collection.find_nearest(
        vector_field=IMAGE_EMBEDDING_FIELD_NAME,
        query_vector=Vector(embeddings.text_embedding),
        distance_measure=DistanceMeasure.COSINE,
        limit=limit,
    )

    return [doc.to_dict()["image_path"] for doc in query_result.stream()]


@app.command()
def search_query(
    query: str = typer.Argument(..., help="Search query for finding hotels"),
    limit: int = typer.Option(5, help="Maximum number of results to return"),
) -> None:
    """Search for hotels using semantic similarity.

    This command performs a semantic search over the hotel database using
    the provided query and returns the most relevant results.

    Args:
        query: Natural language query to search for hotels
        limit: Maximum number of results to return (default: 5)

    Example:
        $ python test_search.py "luxury hotels with pool in bali"
        $ python test_search.py "cheap hostels in bangkok" --limit 10
    """
    try:
        docs_vector_store, image_collection, multimodal_embeddings = (
            initialize_firebase()
        )

        # Perform the search
        image_search_results = search_firestore_collection(
            image_collection, multimodal_embeddings, query, limit
        )

        # if not results:
        #     typer.echo("No results found.")
        #     return

        # Display results
        typer.echo(f"\nFound {len(image_search_results)} results for: '{query}'\n")

        for image_path in image_search_results:
            typer.echo(image_path)

    except Exception as e:
        import traceback

        typer.echo(
            f"Error performing search: {str(e)}\n{traceback.format_exc()}", err=True
        )
        raise typer.Exit(1)


if __name__ == "__main__":
    app()

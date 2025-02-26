from index import initialize_firebase
import typer
import json
from langchain_core.documents import Document

app = typer.Typer()


def format_search_result(doc: Document) -> str:
    """Format the search result for display.

    Args:
        doc: Document containing hotel data

    Returns:
        str: Formatted string representation of the result
    """
    try:
        # Parse the JSON content from page_content
        hotel_data = json.loads(doc.page_content)
        return (
            f"\nHotel: {hotel_data.get('hotel_name', 'N/A')}\n"
            f"Address: {hotel_data.get('hotel_address', 'N/A')}\n"
            f"Description: {hotel_data.get('hotel_description', 'N/A')}\n"
            f"Nearby: {hotel_data.get('nearest_attractions', 'N/A')}\n"
            f"{'-' * 80}"
        )
    except json.JSONDecodeError:
        return f"Error parsing result: {doc.page_content}"


@app.command()
def search_hotels(
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
        _, vector_store = initialize_firebase()

        # Perform the search
        results = vector_store.similarity_search(query, k=limit)

        if not results:
            typer.echo("No results found.")
            return

        # Display results
        typer.echo(f"\nFound {len(results)} results for: '{query}'\n")

        for doc in results:
            typer.echo(format_search_result(doc))

    except Exception as e:
        import traceback

        typer.echo(
            f"Error performing search: {str(e)}\n{traceback.format_exc()}", err=True
        )
        raise typer.Exit(1)


if __name__ == "__main__":
    app()

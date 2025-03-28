import datetime
from google.cloud import firestore
from google.cloud.firestore_v1.vector import Vector
from google.cloud.firestore_v1 import FieldFilter
from google.cloud.firestore_v1.base_query import And
from google.cloud.firestore_v1.base_vector_query import DistanceMeasure
from settings import get_settings
from google import genai
from smolagents import tool

SETTINGS = get_settings()
DB_CLIENT = firestore.Client(
    project=SETTINGS.GCLOUD_PROJECT_ID
)  # Will use "(default)" database
COLLECTION = DB_CLIENT.collection("personal-expense-assistant-receipts")
GENAI_CLIENT = genai.Client(
    vertexai=True, location=SETTINGS.GCLOUD_LOCATION, project=SETTINGS.GCLOUD_PROJECT_ID
)
EMBEDDING_DIMENSION = 768
EMBEDDING_FIELD_NAME = "embedding"
INVALID_ITEMS_FORMAT_ERR = """
Invalid items format. Must be a list of dictionaries with 'name', 'price', and 'quantity' keys."
"""


@tool
def store_receipt_data(
    image_id: str,
    store_name: str,
    transaction_time: datetime.datetime,
    total_amount: float,
    items: list[dict[str, str]],
    currency: str = "IDR",
) -> str:
    """
    This is a tool that stores receipt data in a database.

    Args:
        image_id: The unique identifier of the image. For example IMAGE-POSITION 0-ID 12345,
                  the ID of the image is 12345.
        store_name: The name of the store.
        transaction_time: The time of purchase in UTC
        total_amount: The total amount spent.
        items: A list of items purchased with their prices. Items object must have the following keys:
            - name: The name of the item.
            - price: The price of the item.
            - quantity: The quantity of the item. Optional, default to 1.

            E.g.:
            [
                {
                    "name": "Item 1",
                    "price": 10000,
                    "quantity": 2
                },
                {
                    "name": "Item 2",
                    "price": 20000
                }
            ]
        currency: The currency of the transaction, can be derived from the store location.
            If unsure, default is "IDR".
    """
    try:
        # In case of it provide full image placeholder, extract the id string
        if image_id.startswith("[IMAGE-"):
            image_id = image_id.split("ID ")[1].split("]")[0]

        # Check if the receipt already exists
        doc = get_receipt_data_by_image_id(image_id)

        if doc:
            return f"Receipt with ID {image_id} already exists"

        # Validate transaction time
        if not isinstance(transaction_time, datetime.datetime):
            raise ValueError(
                "Invalid transaction time format. Must be datetime object."
            )

        # Validate items format
        if not isinstance(items, list):
            raise ValueError(INVALID_ITEMS_FORMAT_ERR)

        for item in items:
            if not isinstance(item, dict) or "name" not in item or "price" not in item:
                raise ValueError(INVALID_ITEMS_FORMAT_ERR)

            if "quantity" not in item:
                item["quantity"] = 1

        # Create a combined text from all receipt information for better embedding
        receipt_full_info = f"""
        Store: {store_name}
        Transaction Time: {transaction_time}
        Amount: {total_amount}
        Currency: {currency}
        Items: {items}
        """

        result = GENAI_CLIENT.models.embed_content(
            model="text-embedding-004", contents=receipt_full_info
        )

        embedding = result.embeddings[0].values

        doc = {
            "receipt_id": image_id,
            "store_name": store_name,
            "transaction_time": transaction_time,
            "total_amount": total_amount,
            "currency": currency,
            "items": items,
            EMBEDDING_FIELD_NAME: Vector(embedding),
        }

        COLLECTION.add(doc)

        return f"Receipt stored successfully with ID: {image_id}"
    except Exception as e:
        return f"Failed to store receipt: {str(e)}"


@tool
def search_receipts_by_metadata_filter(
    start_time: datetime.datetime,
    end_time: datetime.datetime,
    min_total_amount: float = None,
    max_total_amount: float = None,
) -> list:
    """
    Filter receipts by metadata within a specific time range and optionally by amount.

    Args:
        start_time: The start datetime for the filter (inclusive) - REQUIRED
        end_time: The end datetime for the filter (inclusive) - REQUIRED
        min_total_amount: The minimum total amount for the filter (inclusive) - OPTIONAL
        max_total_amount: The maximum total amount for the filter (inclusive) - OPTIONAL

    Returns:
        A list of receipt data matching all applied filters
    """
    try:
        # Start with the base collection reference
        query = COLLECTION

        # Convert datetime objects to ISO format strings for Firestore compatibility
        start_time_str = start_time.isoformat() + "Z"  # Add Z for UTC timezone
        end_time_str = end_time.isoformat() + "Z"  # Add Z for UTC timezone

        # Build the composite query by properly chaining conditions
        filters = [
            FieldFilter("transaction_time", ">=", start_time_str),
            FieldFilter("transaction_time", "<=", end_time_str),
        ]

        # Add optional filters
        if min_total_amount is not None:
            filters.append(FieldFilter("total_amount", ">=", min_total_amount))

        if max_total_amount is not None:
            filters.append(FieldFilter("total_amount", "<=", max_total_amount))

        # Apply the filters
        composite_filter = And(filters=filters)
        query = query.where(filter=composite_filter)

        # Execute the query and collect results
        receipts = []
        for doc in query.stream():
            data = doc.to_dict()
            data.pop(
                EMBEDDING_FIELD_NAME, None
            )  # Remove embedding as it's not needed for display
            receipts.append(data)

        return receipts
    except Exception as e:
        return f"Error filtering receipts: {str(e)}"


@tool
def search_relevant_receipts_by_natural_language_query(
    query: str, limit: int = 5
) -> list:
    """
    Search for receipts with content most similar to the query. Results from this tool are
    not final, they are only suggestions. Need additional verification and check with the user
    query to confirm the results.

    Args:
        query: The search text (e.g., "coffee", "dinner", "groceries")
        limit: Maximum number of results to return (default: 5)

    Returns:
        A list of most relevant receipt data matching the query, need to be processed further
    """
    try:
        # Generate embedding for the query text
        result = GENAI_CLIENT.models.embed_content(
            model="text-embedding-004", contents=query
        )
        query_embedding = result.embeddings[0].values

        vector_query = COLLECTION.find_nearest(
            vector_field=EMBEDDING_FIELD_NAME,
            query_vector=Vector(query_embedding),
            distance_measure=DistanceMeasure.EUCLIDEAN,
            limit=5,
        )

        # Execute the query and collect results
        receipts = []
        for doc in vector_query.stream():
            data = doc.to_dict()
            data.pop(
                EMBEDDING_FIELD_NAME, None
            )  # Remove embedding as it's not needed for display
            receipts.append(data)

        return receipts
    except Exception as e:
        return f"Error searching receipts: {str(e)}"


def get_receipt_data_by_image_id(image_id: str) -> dict:
    """
    Retrieve receipt data from the database using the image_id.

    Args:
        image_id: The unique identifier of the receipt image. For example, if the placeholder is
                [IMAGE-ID 12345] or [IMAGE-POSITION 0-ID 12345], the ID to use is 12345.

    Returns:
        A dictionary containing the receipt data or an error message if not found.
        With the following keys:
            - receipt_id: The unique identifier of the receipt image.
            - store_name: The name of the store.
            - transaction_time: The time of purchase in UTC.
            - total_amount: The total amount spent.
            - receipt_description: A detailed description of the receipt contains the items.
    """
    try:
        # Query the receipts collection for documents with matching receipt_id (image_id)
        query = COLLECTION.where(
            filter=FieldFilter("receipt_id", "==", image_id)
        ).limit(1)
        docs = list(query.stream())

        if not docs:
            return {}

        # Get the first matching document
        doc_data = docs[0].to_dict()
        doc_data.pop(EMBEDDING_FIELD_NAME, None)

        return doc_data
    except Exception as e:
        return f"Error retrieving receipt: {str(e)}"

import datetime
from google.cloud import firestore
from google.cloud.firestore_v1.vector import Vector
from settings import get_settings
from google import genai
from smolagents import tool

SETTINGS = get_settings()
DB_CLIENT = firestore.Client(
    project=SETTINGS.GCLOUD_PROJECT_ID
)  # Will use "(default)" database
COLLECTION = DB_CLIENT.collection("receipts")
GENAI_CLIENT = genai.Client(
    vertexai=True, location=SETTINGS.GCLOUD_LOCATION, project=SETTINGS.GCLOUD_PROJECT_ID
)
EMBEDDING_DIMENSION = 768


@tool
def store_receipt_data(
    image_id: str,
    store_name: str,
    transaction_time: datetime.datetime,
    total_amount: float,
    currency: str,
    receipt_description: str,
) -> str:
    """
    This is a tool that stores receipt data in a database.

    Args:
        image_id: The unique identifier of the image. For example IMAGE-POSITION 0-ID 12345,
                  the ID of the image is 12345.
        store_name: The name of the store.
        transaction_time: The time of purchase in UTC
        total_amount: The total amount spent.
        currency: The currency of the transaction. If not explicitly provided, derive from the transaction country location.
        receipt_description: A detailed description of the receipt
    """
    try:
        # Create a combined text from all receipt information for better embedding
        receipt_full_info = f"""
        Store: {store_name}
        Transaction Time: {transaction_time}
        Amount: {total_amount} {currency}
        Description: {receipt_description}
        """

        result = GENAI_CLIENT.models.embed_content(
            model="text-embedding-004", contents=receipt_full_info
        )

        embedding = result.embeddings[0].values

        doc = {
            "name": image_id,
            "store_name": store_name,
            "transaction_time": transaction_time,
            "total_amount": total_amount,
            "currency": currency,
            "receipt_description": receipt_description,
            "embedding": Vector(embedding),
        }

        COLLECTION.add(doc)

        return f"Receipt stored successfully with ID: {image_id}"
    except Exception as e:
        return f"Failed to store receipt: {str(e)}"

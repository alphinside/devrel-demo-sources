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

        # In case of it provide full image placeholder, extract the id string
        if image_id.startswith("[IMAGE-"):
            image_id = image_id.split("ID ")[1].split("]")[0]

        doc = {
            "receipt_id": image_id,
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


@tool
def get_receipt_data(image_id: str) -> str:
    """
    Retrieve receipt data from the database using the image_id.

    Args:
        image_id: The unique identifier of the receipt image. For example, if the placeholder is
                [IMAGE-ID 12345] or [IMAGE-POSITION 0-ID 12345], the ID to use is 12345.

    Returns:
        A formatted string containing the receipt data or an error message if not found.
    """
    try:
        # Query the receipts collection for documents with matching receipt_id (image_id)
        query = COLLECTION.where("receipt_id", "==", image_id).limit(1)
        docs = list(query.stream())

        if not docs:
            return f"No receipt found with ID: {image_id}"

        # Get the first matching document
        doc_data = docs[0].to_dict()

        # Format the receipt data
        formatted_data = f"""
        Receipt ID: {image_id}
        Store: {doc_data.get("store_name", "N/A")}
        Date: {doc_data.get("transaction_time", "N/A")}
        Amount: {doc_data.get("total_amount", "N/A")} {doc_data.get("currency", "N/A")}
        Description: {doc_data.get("receipt_description", "N/A")}
        """

        return formatted_data
    except Exception as e:
        return f"Error retrieving receipt: {str(e)}"

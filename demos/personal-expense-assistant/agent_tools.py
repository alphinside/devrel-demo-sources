import datetime
from smolagents import tool


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
        currency: The currency of the transaction.
        receipt_description: A detailed description of the receipt
    """
    print(
        f"Image ID: {image_id}, Store name: {store_name}, Transaction time: {transaction_time}, Total amount: {total_amount}, Currency: {currency}, Receipt description: {receipt_description}"
    )
    return f"Receipt stored successfully with ID: {image_id}"


# CLI Command

- Create bucket

    ```
    gsutil mb -l us-central1 gs://personal-expense-assistant-receipts
    ```

- Create Firestore Vector Index

    ```
    gcloud firestore indexes composite create \
        --collection-group="personal-expense-assistant-receipts" \
        --query-scope=COLLECTION \
        --field-config field-path="embedding",vector-config='{"dimension":"768", "flat": "{}"}' \
        --database="(default)"
    ```

- Create Firestore Index for Composite Search

    - Search of transaction time and total amount

        ```
        gcloud firestore indexes composite create \
            --collection-group=personal-expense-assistant-receipts \
            --field-config field-path=total_amount,order=ASCENDING \
            --field-config field-path=transaction_time,order=ASCENDING \
            --field-config field-path=__name__,order=ASCENDING \
            --database="(default)"
        ```
# Personal Expense Assistant Agent using Smolagents, Gemini, and Firestore

This project contains demo code to deploy a personal assistant capable to extract and store personal invoices and receipts, store it in databases, and provide search capabilities. It built as two services, frontend using Gradio and backend services using FastAPI. It utilize Smolagent as the agent framework, Gemini as the language model, Firestore as the database, and Google Cloud Storage as the storage.  

## Prerequisites

- Enable the following APIs
    - Gemini API
    - Firestore API
    - Google Cloud Storage API
    - Cloud Build API

- Prepare a Google Cloud Storage bucket

    ```
    gsutil mb -l us-central1 gs://personal-expense-assistant-receipts
    ```

- Create a Firestore default database

## CLI Commands

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
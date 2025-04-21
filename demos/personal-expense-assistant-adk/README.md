# Personal Expense Assistant Agent using Google ADK, Gemini 2.5 Flash, and Firestore

This project contains demo code to deploy a personal assistant capable to extract and store personal invoices and receipts, store it in databases, and provide search capabilities. It built as two services, frontend using Gradio and backend services using FastAPI. It utilize Google ADK as the agent framework, Gemini 2.5 Flash as the language model, Firestore as the database, and Google Cloud Storage as the storage. It also display how we can leverage Gemini 2.5 Flash thinking process in the UI

## Prerequisites

- If you are executing this project from your personal IDE, Login to Gcloud using CLI with the following command :

    ```shell
    gcloud auth application-default login
    ```

- Prepare a Google Cloud Storage bucket

    ```shell
    gsutil mb -l us-central1 gs://personal-expense-assistant-receipts
    ```

- Create Firestore database `(default)` with security rules - open ( for 30 days ) and region us-central1

- Enable the following APIs

    ```shell
    gcloud services enable aiplatform.googleapis.com \
                           firestore.googleapis.com \
                           run.googleapis.com \
                           cloudbuild.googleapis.com \
                           cloudresourcemanager.googleapis.com
    ```

- Install [uv](https://docs.astral.sh/uv/getting-started/installation/) and prepare the python env

    ```shell
    uv sync --frozen
    ```

- Create Firestore Vector Index

    ```shell
    gcloud firestore indexes composite create \
        --collection-group="personal-expense-assistant-receipts" \
        --query-scope=COLLECTION \
        --field-config field-path="embedding",vector-config='{"dimension":"768", "flat": "{}"}' \
        --database="(default)"
    ```

- Create Firestore Index for Composite Search of transaction time and total amount

    ```shell
    gcloud firestore indexes composite create \
        --collection-group=personal-expense-assistant-receipts \
        --field-config field-path=total_amount,order=ASCENDING \
        --field-config field-path=transaction_time,order=ASCENDING \
        --field-config field-path=__name__,order=ASCENDING \
        --database="(default)"
    ```

- Copy the `settings.yaml.example` to `settings.yaml` and update the value accordingly. Only mandatory to update the following values:
  - `GCLOUD_PROJECT_ID` : Your GCP Project ID

## Running Locally

- Run the backend service

    ```shell
    uv run backend.py
    ```

    If successful, you should see the following output ( the backend service will run on port 8081 ):

    ```shell
    INFO:     Started server process [4572]
    INFO:     Waiting for application startup.
    INFO:     Application startup complete.
    INFO:     Uvicorn running on http://0.0.0.0:8081 (Press CTRL+C to quit)
    ```

- Run the frontend service

    ```shell
    uv run frontend.py
    ```

    If successful, you should see the following output ( the frontend service will run on port 8080 ):

    ```shell
    * Running on local URL:  http://0.0.0.0:8080

    To create a public link, set `share=True` in `launch()`.
    ```

Now you can access the web application on the browser

## Deploying to Cloud Run

To deploy to Cloud Run

```shell
gcloud run deploy personal-expense-assistant \
--source . \
--port=8080 \
--allow-unauthenticated \
--env-vars-file=settings.yaml \
--memory 1024Mi
```

If successful, you should see the following output:

```shell
Deployed revision: personal-expense-assistant-00001
```

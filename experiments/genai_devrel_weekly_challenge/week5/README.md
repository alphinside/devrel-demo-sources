# GenAI DevRel Weekly Challenge Week 3

Key points:

- Prepare dataset for Gemini Fine Tuning
- Finetune Gemini
- Deploy Finetuned Gemini to Endpoint
- Connect app to finetuned endpoint

Before running this script, please ensure the previous requirements in [week2 docs](../week2/README.md) are met

## Adding Permission to Service Account

Gemini Finetuned model will be deployed in the VertexAI Endpoints, hence we need to add the following permission to the previously enabled service account

- Vertex AI User

## Prepare Dataset for Fine Tuning

- Run `sample_and_format_dataset.py`, it will output formatted JSONL data under `output_path` directory
- Upload the resulting JSONL to GCS

## Run Finetuning Jobs

- Follow instructions at https://cloud.google.com/vertex-ai/generative-ai/docs/models/gemini-use-supervised-tuning#console

## Test the Deployed Finetuned Model

- See the model in tuning jobs table https://console.cloud.google.com/vertex-ai/studio/tuning and click Test

## Find the Model and Deployment in Model Registry and Online Predictions

- Check here https://console.cloud.google.com/vertex-ai/models for the model registry
- Check here https://console.cloud.google.com/vertex-ai/online-prediction/endpoints for the model deploymenyt. The endpoint resource address format is `projects/{PROJECT_ID}/locations/{LOCATIONS}/endpoints/{ENDPOINT_ID}`

## Run the App

- Set the `GEMINI_FINETUNED_URI` in `settings.yaml` and run the app

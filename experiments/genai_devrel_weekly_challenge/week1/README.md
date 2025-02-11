# GenAI DevRel Weekly Challenge Week 1

Key points:

- Deploy Gemma
- Create Chat Interface
- Connect Database for Chat Memory Management
- Deploy Chat Interface

## Chatbot Web App with Gradio and Ollama-Gemma 2 on Cloud Run

In this example, we will deploy ollama service on the cloudrun as the backend, and then deploy a service which act as the frontend using gradio, also on cloudrun

### 1. Deploy Ollama Backend on Cloud Run

Change working directory to `./ollama-cloudrun-deploy` and see this [README.md](ollama-cloudrun-deploy/README.md)

### 2. Create Database Instance

- Enable the following API:

  - Cloud SQL Admin API
- Go to [Cloud SQL](https://console.cloud.google.com/sql) and create a new database instance in with PostgreSQL database, recommended using the following specifications:

  - Enterprise edition
  - Edition preset : Sandbox
  - Zonal availability : Single zone
  - Name it as you want
- Set permission for created ollama cloud run service account (the one created in the `Deploy Ollama Backend` step), add the following permissions:

  - `Cloud SQL Admin`
  - `Cloud Run Invoker`

### 2. Deploy Gradio App

Change back working directory to example root directory `devrel-demos/ai-ml/gemma-ollama-app-streamlit`

- Set permission for created ollama cloud run service account (the one created in the `Deploy Ollama Backend` step), add the following permissions, See [this docs](https://cloud.google.com/iam/docs/manage-access-service-accounts) on how to do it:

  - `Cloud Run Invoker`
- Put the service account key (json file) in the working directory and rename it to `cloudrun-sa.json`. IMPORTANT NOTES: this is only for tutorial purpose, as it is not secure. The best way is to use [gcloud secret manager](https://cloud.google.com/secret-manager/docs)
- Copy `settings.yaml.example` to `settings.yaml` and change the value respective to your ollama deployment
  - `OLLAMA_SERVICE_URL` key denotes the ollama cloudrun service URL. E.g. `https://ollama-gemma-gpu-xxxxxxxx.us-central1.run.app`
  - `CLOUDRUN_SERVICE_ACCOUNT_KEY` key denotes the service account key (json file). For this example, we rename the key file `cloudrun-sa.json` and put it in this example directory
  - `CHAT_HISTORY_DB_URI` key denotes the connection string to the postgresql database. E.g. `postgresql://postgres:postgres@127.0.0.1:5432/postgres?sslmode=disable`
  - `DB_CONNECTION_NAME` key denotes the connection name for the cloud sql proxy,which consists of project id, region and instance name provided in the following string format: `project:region:instance_name`
- Run cloud run deploy, if Dockerfile present in the working directory it will build using it

    ```console
    gcloud beta run deploy gradio-app --source . --allow-unauthenticated --port 7860 --env-vars-file settings.yaml
    ```

    Notes that we set `--allow-unauthenticated` so that we can access the web page without any authentication.

### 3. Connect to the Chatbot Gradio App

After successful deployment, it we can access it on the shown Service URL. E.g

```console
https://gradio-app-xxxxxxxxx.us-central1.run.app
```

### 4. Cleaning Up

After you finished your experiments, don't forget to clean all resources:

1. Artifact Registry -> Clean the pushed image
2. Service Account -> Clean the created service account for cloudrun
3. Cloud SQL -> Clean the created database instance
4. Cloud Run -> Clean the deployed services, ollama backend and streamlit frontend

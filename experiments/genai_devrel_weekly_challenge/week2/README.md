# GenAI DevRel Weekly Challenge Week 2

Key points:

- Connect the Chat Interface App to Gemini
- Create Prompt Version Management

Before running this script, please ensure the previous requirements in [week1 docs](../week1/README.md) are met

## Connecting to Gemini

- Go to [Google AI Studio](https://aistudio.google.com/apikey) and create API KEY
- Fill the `GEMINI_API_KEY` in `settings.yaml` (copy and rename the `settings.yaml.example` to `settings.yaml` if you haven't done yet) with the created API KEY

## Prompt Version Management

- Ensure you run the `cloud-sql-proxy.sh` to connect to the Postgre Cloud SQL instance
- If you want to add new prompt version, create new file under migrations directory, e.g. `migrations/003_add_new_prompt.sql`
- Run the migrations by running `migrate.py`

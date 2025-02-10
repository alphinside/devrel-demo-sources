#!/bin/bash

if [ ! -f cloud-sql-proxy ]; then
    curl -o cloud-sql-proxy https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.14.3/cloud-sql-proxy.linux.amd64
    chmod +x cloud-sql-proxy
else
    echo "cloud-sql-proxy already exists, skipping download"
fi

# Use GCLOUD_CREDENTIALS env var if set, otherwise default to cloudrun-sa.json
CREDENTIALS_FILE=${GCLOUD_CREDENTIALS:-cloudrun-sa.json}

./cloud-sql-proxy ${DB_CONNECTION_NAME} --credentials-file ${CREDENTIALS_FILE}

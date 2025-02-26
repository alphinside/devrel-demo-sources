#!/bin/bash
#
# Copyright 2025 Google LLC
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#   https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

if [ ! -f cloud-sql-proxy ]; then
    curl -o cloud-sql-proxy https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.14.3/cloud-sql-proxy.linux.amd64
    chmod +x cloud-sql-proxy
else
    echo "cloud-sql-proxy already exists, skipping download"
fi

# Use GCLOUD_CREDENTIALS env var if set, otherwise default to cloudrun-sa.json
CREDENTIALS_FILE=${GCLOUD_CREDENTIALS:-cloudrun-sa.json}

./cloud-sql-proxy ${DB_CONNECTION_NAME} --credentials-file ${CREDENTIALS_FILE}

"""
Copyright 2025 Google LLC

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import os
import psycopg
from settings import get_settings


def run_migrations():
    """Run all SQL migrations in the migrations directory."""
    settings = get_settings()

    # Connect to the database
    with psycopg.connect(settings.CHAT_HISTORY_DB_URI) as conn:
        # Enable autocommit mode
        conn.autocommit = True

        try:
            # Create migrations table if it doesn't exist
            with conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS migrations (
                        id SERIAL PRIMARY KEY,
                        filename VARCHAR(255) NOT NULL,
                        applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(filename)
                    )
                """)

                # Get list of applied migrations
                cursor.execute("SELECT filename FROM migrations")
                applied_migrations = {row[0] for row in cursor.fetchall()}

                # Get all migration files
                migration_dir = os.path.join(os.path.dirname(__file__), "migrations")
                migration_files = sorted(
                    [f for f in os.listdir(migration_dir) if f.endswith(".sql")]
                )

                # Apply new migrations
                for filename in migration_files:
                    if filename not in applied_migrations:
                        print(f"Applying migration: {filename}")

                        # Read and execute migration file
                        with open(os.path.join(migration_dir, filename), "r") as f:
                            sql = f.read()
                            cursor.execute(sql)

                        # Record migration as applied
                        cursor.execute(
                            "INSERT INTO migrations (filename) VALUES (%s)", (filename,)
                        )
                        print(f"Successfully applied migration: {filename}")

        except Exception as e:
            print(f"Error during migration: {e}")
            raise


if __name__ == "__main__":
    run_migrations()

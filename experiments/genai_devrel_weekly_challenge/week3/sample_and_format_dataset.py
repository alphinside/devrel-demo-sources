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

import typer
from datasets import load_dataset
import json
from pathlib import Path
from tqdm import tqdm
from datasets.arrow_dataset import Dataset

app = typer.Typer()


@app.command()
def main(
    train_samples: int = typer.Option(
        500, help="Number of training samples to extract."
    ),
    val_samples: int = typer.Option(
        100, help="Number of validation samples to extract."
    ),
    output_path: str = typer.Option(
        "converted_data", help="Path to save the processed data."
    ),
):
    """
    Downloads the OpenAssistant Guanaco dataset, samples a subset of the training and validation sets,
    formats the data into a JSONL format suitable for fine-tuning, and saves the processed data to disk.
    """
    output_path = Path(output_path)
    output_path.mkdir(exist_ok=True)
    ds = load_dataset("timdettmers/openassistant-guanaco")
    train_ds: Dataset = ds["train"]
    eval_ds: Dataset = ds["test"]

    if train_samples:
        train_ds = train_ds.select(range(train_samples))
    if val_samples:
        eval_ds = eval_ds.select(range(val_samples))

    def format_example(example: dict) -> dict:
        """
        Formats a single example from the dataset into the format expected for fine-tuning.

        Args:
            example (dict): A dictionary containing the 'text' field with the conversation.

        Returns:
            dict: A dictionary with a 'contents' key, where the value is a list of dictionaries,
                  each with 'role' and 'parts' keys.
        """
        contents = []
        text = example["text"]

        turn_splits = text.split("###")

        for split in turn_splits:
            role = None

            if split.strip().startswith("Human:"):
                role = "user"
                content = split.replace("Human:", "").strip()
            elif split.strip().startswith("Assistant:"):
                role = "model"
                content = split.replace("Assistant:", "").strip()

            if role:
                contents.append({"role": role, "parts": [{"text": content}]})

        return {"contents": contents}

    train_data = f"{output_path}/train.jsonl"
    val_data = f"{output_path}/val.jsonl"

    with open(train_data, "w") as f:
        for example in tqdm(train_ds, desc="Processing train data"):
            data = format_example(example)
            f.write(json.dumps(data) + "\n")

    with open(val_data, "w") as f:
        for example in tqdm(eval_ds, desc="Processing val data"):
            data = format_example(example)
            f.write(json.dumps(data) + "\n")


if __name__ == "__main__":
    app()

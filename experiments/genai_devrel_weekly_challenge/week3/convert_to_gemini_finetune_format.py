import typer
from datasets import load_dataset
import json
from pathlib import Path
from tqdm import tqdm

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
    output_path = Path(output_path)
    output_path.mkdir(exist_ok=True)
    ds = load_dataset("timdettmers/openassistant-guanaco")
    train_ds = ds["train"]
    eval_ds = ds["test"]

    if train_samples:
        train_ds = train_ds.select(range(train_samples))
    if val_samples:
        eval_ds = eval_ds.select(range(val_samples))

    def format_example(example):
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

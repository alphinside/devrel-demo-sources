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

import vertexai
from vertexai.preview.vision_models import ImageGenerationModel, ImageGenerationResponse
from typing import Iterator
from vertexai.generative_models import GenerativeModel, Part, Image


def generate_bouquet_image(output_file: str, prompt: str) -> ImageGenerationResponse:
    """Generate an AI-powered image based on a text description.

    This function uses Vertex AI's Image Generation model to create an image
    based on the provided text prompt. The generated image is saved to the
    specified output file.

    Args:
        output_file (str): The local file path where the generated image will be saved.
        prompt (str): A text description of the image to be generated.

    Returns:
        ImageGenerationResponse: The response object containing the generated image
            and associated metadata.
    """
    model = ImageGenerationModel.from_pretrained("imagegeneration@002")

    images = model.generate_images(
        prompt=prompt,
        number_of_images=1,
        seed=1,
        add_watermark=False,
    )

    images[0].save(location=output_file)

    return images


def analyze_bouquet_image(image_path: str) -> Iterator[str]:
    """Analyze an image and generate birthday wishes using Gemini Pro Vision.

    This function takes an image file, processes it using the Gemini Pro Vision model,
    and generates creative birthday wishes based on the content of the image.

    Args:
        image_path (str): The local file path to the image to be analyzed.

    Yields:
        str: Chunks of generated birthday wishes text, streamed as they are produced.
    """
    model = GenerativeModel("gemini-pro-vision")
    prompt = [
        Part.from_image(Image.load_from_file(image_path)),
        "Generate exciting birthday wishes based on the image provided",
    ]
    responses = model.generate_content(prompt)
    return responses.text


if __name__ == "__main__":
    PROJECT_ID = "your-project-id"
    REGION_ID = "your-location"
    OUTPUT_IMAGE = "image.jpeg"

    vertexai.init(project=PROJECT_ID, location=REGION_ID)

    generate_bouquet_image(
        output_file=OUTPUT_IMAGE,
        prompt="Create an image containing a bouquet of 2 sunflowers and 3 roses",
    )

    print(analyze_bouquet_image(OUTPUT_IMAGE))

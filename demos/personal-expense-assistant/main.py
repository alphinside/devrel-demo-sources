from smolagents import LiteLLMModel, CodeAgent
import litellm

litellm.vertex_project = "alvin-exploratory-2"  # Your Project ID
litellm.vertex_location = "us-central1"  # proj location


def main():
    from PIL import Image

    # Load an image file
    image_path = "dinner_page-0001.jpg"  # Replace with your actual image path
    image = Image.open(image_path)

    model = LiteLLMModel(model_id="vertex_ai/gemini-2.0-flash-001", temperature=0)

    agent = CodeAgent(tools=[], model=model)

    result = agent.run(
        "describe the image",
        images=[image],
    )
    print(result)


if __name__ == "__main__":
    main()

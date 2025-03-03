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

import json
from typing import Dict, List, Any
from tqdm import tqdm
from deepeval import assert_test

from graph import GraphManager
from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCaseParams, LLMTestCase
from settings import get_settings

from pydantic import BaseModel
import instructor
from litellm import completion

from deepeval.models import DeepEvalBaseLLM
from deepeval.dataset import EvaluationDataset
import pytest


settings = get_settings()
graph_manager = GraphManager(use_memory=False)


def load_raw_test_cases(test_file: str) -> List[Dict[str, Any]]:
    """Load test cases from a JSON file.

    Args:
        test_file: Path to the JSON file containing test cases

    Returns:
        List of test cases as dictionaries
    """
    try:
        with open(test_file, "r") as f:
            test_cases = json.load(f)
        print(f"Successfully loaded {len(test_cases)} test cases from {test_file}")
        return test_cases
    except FileNotFoundError:
        print(f"Error: Test file {test_file} not found")
        return []
    except json.JSONDecodeError:
        print(f"Error: Test file {test_file} is not valid JSON")
        return []


def load_test_cases():
    raw_test_cases = load_raw_test_cases("test_cases.json")
    test_cases = []
    for test_case in tqdm(raw_test_cases):
        question = test_case["question"]
        reference_output = test_case["answer"]

        updated_graph = graph_manager.graph.invoke({"messages": question})
        actual_output = updated_graph["messages"][-1].content

        test_case = LLMTestCase(
            input=question,
            actual_output=actual_output,
            expected_output=reference_output,
        )
        test_cases.append(test_case)

    return test_cases


class CustomGeminiFlash(DeepEvalBaseLLM):
    def __init__(self):
        self.instructor_client = instructor.from_litellm(completion)

    def load_model(self):
        return self.instructor_client

    def generate(self, prompt: str, schema: BaseModel) -> BaseModel:
        resp = self.instructor_client.chat.completions.create(
            model="gemini/gemini-2.0-flash",
            api_key=settings.GEMINI_API_KEY,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            response_model=schema,
        )

        return resp

    async def a_generate(self, prompt: str, schema: BaseModel) -> BaseModel:
        return self.generate(prompt, schema)

    def get_model_name(self):
        return "Gemini 2.0 Flash"


dataset = EvaluationDataset(test_cases=load_test_cases())
correctness_metric = GEval(
    name="Correctness",
    criteria="Determine whether the actual output is factually correct based on the expected output.",
    evaluation_steps=[
        "Check whether the facts in 'actual output' contradicts any facts in 'expected output'",
        "You should also heavily penalize omission of detail",
        "Vague language, or contradicting OPINIONS, are OK",
    ],
    evaluation_params=[
        LLMTestCaseParams.INPUT,
        LLMTestCaseParams.ACTUAL_OUTPUT,
        LLMTestCaseParams.EXPECTED_OUTPUT,
    ],
    model=CustomGeminiFlash(),
    threshold=0.5,
)


@pytest.mark.parametrize(
    "test_case",
    dataset,
)
def test_correctness(test_case: LLMTestCase) -> None:
    assert_test(test_case, [correctness_metric])

from graph import GraphManager
from deepeval.metrics import ToolCorrectnessMetric
from deepeval.test_case import LLMTestCase, ToolCall
import pytest


graph_manager = GraphManager(use_memory=False)


@pytest.mark.parametrize(
    "test_case,expected_tool_names",
    [
        ("how's weather in Jakarta?", ["get_weather_tool"]),
        ("hello", []),
    ],
)
def test_toolusage(test_case: str, expected_tool_names: list[str]) -> None:
    updated_graph = graph_manager.graph.invoke({"messages": test_case})

    test_case = LLMTestCase(
        input=test_case,
        actual_output=updated_graph["messages"][-1].content,
        tools_called=[
            ToolCall(name=tool_name)
            for tool_name in updated_graph["latest_func_call_name"]
        ],
        expected_tools=[ToolCall(name=tool_name) for tool_name in expected_tool_names],
    )
    metric = ToolCorrectnessMetric()
    metric.measure(test_case)

from types import SimpleNamespace as NS

from brain.providers.ollama_provider import OllamaProvider


def _resp(content=None, calls=None):
    return NS(id="r", choices=[NS(message=NS(content=content, tool_calls=calls))])


def test_ollama_tool_loop_runs_tool_then_returns_final_text():
    provider = OllamaProvider()
    call = NS(id="c1", function=NS(name="add", arguments='{"a": 2, "b": 3}'))
    replies = iter([_resp(calls=[call]), _resp(content="The answer is 5")])
    seen = []
    provider.client = NS(chat=NS(completions=NS(create=lambda **kw: seen.append(kw["messages"][-1]["role"]) or next(replies))))

    result = provider.think_with_tools(
        "sys", "what is 2+3?", tools=[{"type": "function", "function": {"name": "add"}}],
        tool_executor=lambda name, args: {"success": True, "sum": args["a"] + args["b"]},
    )

    assert result.response == "The answer is 5"
    assert seen == ["user", "tool"]

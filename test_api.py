"""Run this first: confirms your key, endpoint and tool calling all work."""
import os, json
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(base_url="https://api.meta.ai/v1", api_key=os.environ["MODEL_API_KEY"])
MODEL = "muse-spark-1.3"

r = client.chat.completions.create(
    model=MODEL, messages=[{"role": "user", "content": "Reply with the single word: ready"}])
print("1) basic call:", r.choices[0].message.content)
print("   usage:", r.usage)

tools = [{"type": "function", "function": {
    "name": "add", "description": "Add two numbers.",
    "parameters": {"type": "object", "properties": {
        "a": {"type": "number"}, "b": {"type": "number"}}, "required": ["a", "b"]}}}]
r = client.chat.completions.create(
    model=MODEL, tools=tools,
    messages=[{"role": "user", "content": "Use the add tool to add 19 and 23."}])
calls = r.choices[0].message.tool_calls or []
print("2) tool calling:", "WORKS" if calls else "no tool call returned",
      [(c.function.name, c.function.arguments) for c in calls])

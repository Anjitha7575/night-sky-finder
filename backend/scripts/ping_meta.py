"""Smallest possible Muse Spark call, using /v1/responses. Checks the key works.

Run from backend/:  python scripts/ping_meta.py
"""
import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(base_url="https://api.meta.ai/v1", api_key=os.getenv("META_API_KEY"))
resp = client.responses.create(
    model=os.getenv("META_MODEL", "muse-spark-1.3"),
    input="Reply with one word: ok",
)
print("reply:", resp.output_text)
print("usage:", resp.usage)

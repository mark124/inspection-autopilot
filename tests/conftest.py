"""Force stub mode for the whole suite.

app/qwen.py auto-loads a repo-root .env (setdefault), so a developer with a
real key would otherwise run the tests against the live API. Setting the key
to an empty string here wins over the autoload and keeps tests offline,
deterministic, and free.
"""
import os

os.environ["DASHSCOPE_API_KEY"] = ""

import os
import yaml

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def load(name):
    with open(os.path.join(ROOT, "config", f"{name}.yaml"), encoding="utf-8") as f:
        return yaml.safe_load(f)

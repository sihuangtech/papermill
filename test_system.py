import os
import json
import logging
import yaml
import sys

# Ensure the parent directory is in the path so we can import src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.orchestrator import Orchestrator

def test_initialization():
    try:
        # Create a dummy config if not exists for testing
        if not os.path.exists("config.yaml"):
            with open("config.yaml", "w") as f:
                f.write("research_directions: []\n")

        orchestrator = Orchestrator("config.yaml")
        print("Orchestrator initialized successfully.")
        return orchestrator
    except Exception as e:
        print(f"Initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    test_initialization()

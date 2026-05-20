from executor import run_pipeline
import json

if __name__ == "__main__":
    result = run_pipeline("Show me all customers")
    print(json.dumps(result, indent=2))

import os
import sys


def load_env_from_integration_tests():
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if not os.path.isfile(env_path):
        print(f"ERROR: .env file not found at {env_path}")
        sys.exit(1)
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ[key.strip()] = value.strip()


# Load .env before any other imports
load_env_from_integration_tests()

from multiagent_firewall.orchestrator import GuardOrchestrator


def main():
    if len(sys.argv) < 2:
        print('Usage: python run_orchestrator.py "Your text here"')
        sys.exit(1)
    text = sys.argv[1]
    orchestrator = GuardOrchestrator()
    result = orchestrator.run(text=text)
    for key, value in result.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()

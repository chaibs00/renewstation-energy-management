import sys
from pathlib import Path

# Make the `renewstation` package importable when running pytest from pipelines/
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

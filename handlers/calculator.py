import math
import random
from typing import Any, Dict


def calculate(python_expression: str) -> Dict[str, Any]:
    """Evaluate a python expression with math and random modules available."""
    safe_globals: Dict[str, Any] = {"__builtins__": {}, "math": math, "random": random}
    result = eval(python_expression, safe_globals)
    return {"success": True, "result": result}

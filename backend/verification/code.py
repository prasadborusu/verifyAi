"""
Sandboxed Code Execution & Verification Module.
Validates code safety via AST inspection and executes within an isolated Python environment.
Compares actual output against expected test cases.
"""

import ast
import sys
import io
import time
import logging
from typing import Dict, Any, List, Optional, Tuple
from backend.models.schemas import VerificationCheck

logger = logging.getLogger("verification_code")

FORBIDDEN_MODULES = {
    "os", "sys", "subprocess", "socket", "shutil", "builtins",
    "posix", "nt", "pty", "commands", "importlib", "requests", "urllib", "http"
}

FORBIDDEN_CALLS = {
    "eval", "exec", "__import__", "open", "breakpoint", "compile", "globals", "locals"
}


class CodeSafetyVisitor(ast.NodeVisitor):
    """AST visitor to detect forbidden imports and system calls."""

    def __init__(self):
        self.violations: List[str] = []

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            root_mod = alias.name.split(".")[0]
            if root_mod in FORBIDDEN_MODULES:
                self.violations.append(f"Forbidden module import: '{alias.name}'")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module:
            root_mod = node.module.split(".")[0]
            if root_mod in FORBIDDEN_MODULES:
                self.violations.append(f"Forbidden from-import: '{node.module}'")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        if isinstance(node.func, ast.Name):
            if node.func.id in FORBIDDEN_CALLS:
                self.violations.append(f"Forbidden function invocation: '{node.func.id}()'")
        self.generic_visit(node)


def inspect_code_safety(code_str: str) -> Tuple[bool, List[str]]:
    """Inspects code syntax and AST for safety violations."""
    try:
        tree = ast.parse(code_str)
        visitor = CodeSafetyVisitor()
        visitor.visit(tree)
        return len(visitor.violations) == 0, visitor.violations
    except SyntaxError as se:
        return False, [f"Syntax error in code: {se}"]
    except Exception as e:
        return False, [f"AST parse error: {e}"]


def execute_sandboxed_code(
    code_str: str,
    inputs: Optional[Dict[str, Any]] = None,
    timeout_seconds: float = 2.0,
) -> Dict[str, Any]:
    """
    Executes Python code in a restricted execution namespace with captured stdout.
    """
    is_safe, violations = inspect_code_safety(code_str)
    if not is_safe:
        return {
            "success": False,
            "error": f"Security violation: {', '.join(violations)}",
            "stdout": "",
            "return_value": None,
        }

    # Safe builtins
    safe_builtins = {
        "abs": abs, "round": round, "min": min, "max": max, "sum": sum,
        "len": len, "range": range, "int": int, "float": float, "str": str,
        "bool": bool, "list": list, "dict": dict, "set": set, "tuple": tuple,
        "print": print, "enumerate": enumerate, "zip": zip,
    }

    import math
    safe_globals = {
        "__builtins__": safe_builtins,
        "math": math,
    }

    # Include user inputs in local namespace
    local_ns = dict(inputs or {})

    # Capture stdout
    old_stdout = sys.stdout
    redirected_output = io.StringIO()
    sys.stdout = redirected_output

    start_time = time.time()
    try:
        exec(code_str, safe_globals, local_ns)
        output_str = redirected_output.getvalue().strip()
        elapsed = time.time() - start_time

        # Extract result or default output variable
        result_val = local_ns.get("result", local_ns.get("output", None))
        if result_val is None and output_str:
            # Try to parse stdout as number/string
            result_val = output_str

        return {
            "success": True,
            "error": None,
            "stdout": output_str,
            "return_value": result_val,
            "execution_time_sec": round(elapsed, 4),
            "locals": {k: v for k, v in local_ns.items() if not k.startswith("_")},
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Execution error: {str(e)}",
            "stdout": redirected_output.getvalue().strip(),
            "return_value": None,
        }
    finally:
        sys.stdout = old_stdout


def verify_code_execution(
    code_str: str,
    inputs: Optional[Dict[str, Any]] = None,
    expected_output: Optional[Any] = None,
) -> VerificationCheck:
    """Verifies that generated code executes safely and yields expected result."""
    exec_res = execute_sandboxed_code(code_str, inputs)
    if not exec_res["success"]:
        return VerificationCheck(
            check_name="Sandboxed Code Execution Check",
            check_type="code",
            passed=False,
            details=f"Code execution failed: {exec_res['error']}",
            expected=expected_output,
            actual=None,
        )

    actual_val = exec_res["return_value"]
    if expected_output is not None:
        passed = str(actual_val) == str(expected_output)
        details = (
            f"Code executed successfully. Expected: {expected_output}, Got: {actual_val}. "
            f"{'Output matched.' if passed else 'Output mismatch!'}"
        )
    else:
        passed = True
        details = f"Code executed safely without errors. Result: {actual_val}"

    return VerificationCheck(
        check_name="Sandboxed Code Execution Check",
        check_type="code",
        passed=passed,
        details=details,
        expected=expected_output,
        actual=actual_val,
    )

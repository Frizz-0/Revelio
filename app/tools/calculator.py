"""Small deterministic arithmetic evaluator used by the Revelio agent."""

import ast
import math
import operator
import re


_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def calculate(expression: str) -> int | float:
    """Evaluate numeric arithmetic without exposing Python's eval()."""
    if len(expression) > 256:
        raise ValueError("Expression is too long.")
    try:
        tree = ast.parse(expression.replace("^", "**"), mode="eval")
        result = _evaluate(tree.body)
    except (SyntaxError, TypeError, ZeroDivisionError, OverflowError) as exc:
        raise ValueError(f"Invalid arithmetic expression: {exc}") from exc
    if isinstance(result, float) and not math.isfinite(result):
        raise ValueError("Result is not finite.")
    return result


def _evaluate(node: ast.AST) -> int | float:
    if isinstance(node, ast.Constant) and type(node.value) in (int, float):
        return node.value
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPERATORS:
        return _OPERATORS[type(node.op)](_evaluate(node.operand))
    if isinstance(node, ast.BinOp) and type(node.op) in _OPERATORS:
        left, right = _evaluate(node.left), _evaluate(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 100:
            raise ValueError("Exponent is too large.")
        result = _OPERATORS[type(node.op)](left, right)
        if abs(result) > 10**100:
            raise ValueError("Result is too large.")
        return result
    raise ValueError("Only numeric arithmetic expressions are supported.")


def expression_from_goal(goal: str) -> str | None:
    """Extract a standalone arithmetic request for zero-LLM execution."""
    text = goal.strip().lower().replace("×", "*").replace("÷", "/").replace("−", "-")
    text = re.sub(r"(?<=\d)\s*x\s*(?=\d)", "*", text)
    text = re.sub(
        r"^(what(?:\s+is|'s|s)?|calculate|compute|evaluate|solve)\s+",
        "",
        text,
    )
    text = text.rstrip(" ?=.")
    text = text.replace(",", "")
    percent = re.fullmatch(r"([+-]?\d+(?:\.\d+)?)\s*%\s+of\s+([+-]?\d+(?:\.\d+)?)", text)
    if percent:
        return f"({percent.group(1)} / 100) * {percent.group(2)}"
    if re.fullmatch(r"[\d\s()+\-*/%.^]+", text) and re.search(r"[+\-*/%^]", text):
        return text
    return None


def goal_requires_calculator(goal: str) -> bool:
    """Catch explicit calculation requests in mixed research tasks too."""
    return expression_from_goal(goal) is not None or bool(
        re.search(
            r"\b(calculate|compute|arithmetic|add|plus|multiply|times|divide|minus|subtract|sum|total|percent)\b",
            goal,
            re.I,
        )
    )

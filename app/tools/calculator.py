def calculate(expression: str):
    try:
        return eval(
            expression,
            {"__builtins__": {}},
            {}
        )
    except Exception as e:
        raise ValueError(f"Invalid expression: {e}")
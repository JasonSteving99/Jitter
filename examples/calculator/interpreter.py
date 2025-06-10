from calculator import tokenizer


def interpret(program_tokens: list[tokenizer.LPar | tokenizer.RPar | tokenizer.Integer | tokenizer.Float | tokenizer.PlusOp | tokenizer.MinusOp | tokenizer.MulOp | tokenizer.DivOp | tokenizer.PowOp]) -> float:
    """Interpret the program tokens eagerly left-to-right not honoring operator precedence other than parentheses.

    The implementation will use the functions in @calculator.operations to implement this logic."""
    raise NotImplementedError("Still need to implement this!")
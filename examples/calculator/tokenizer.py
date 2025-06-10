from dataclasses import dataclass


@dataclass(frozen=True)
class Integer:
    val: int

@dataclass(frozen=True)
class Float:
    val: float

@dataclass(frozen=True)
class PlusOp:
    pass

@dataclass(frozen=True)
class MinusOp:
    pass

@dataclass(frozen=True)
class MulOp:
    pass

@dataclass(frozen=True)
class DivOp:
    pass

@dataclass(frozen=True)
class PowOp:
    pass

@dataclass(frozen=True)
class LPar:
    pass

@dataclass(frozen=True)
class RPar:
    pass


def tokenize(input_string: str) -> list[LPar | RPar | Integer | Float | PlusOp | MinusOp | MulOp | DivOp | PowOp]:
    """
    Tokenizes an input arithmetic expression string into a list of token objects.

    This function parses the input string character by character, identifying numbers
    (integers and floats), operators (+, -, *, /, ^), and parentheses.
    It skips whitespace and raises a ValueError for unexpected characters.

    Makes use of all the dataclasses in @calculator.tokenizer
    """
    raise NotImplementedError("Tokenization not yet implemented")
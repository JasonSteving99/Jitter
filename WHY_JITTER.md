# Why Does Jitter Exist?

Jitter is fundamentally an experiment in what a __programming language__ might look like if designed with an LLM-based development cycle in mind? Yes, Jitter is currently Python-lib-shaped, but this is largely just a hack to rush experimentally to the heart of the question of whether (or, how useful it would be for) a hypothetical language could leverage its wealth of knowledge of your program to squeeze every last drop out of LLM coding capabilities before even resorting to making our LLMs "agentic".

# Mental Model Building vs Prompt Engineering: Spot the Difference

When I reflect on what it is I'm doing when I'm zoomed into a program and investigating what it would take to add a new function to solve a problem, it seems to boil down to the following:

1. Understand the context in which this function should be called
   
    This essentially boils down to reading the existing function from which the new function will be called to understand what data will be in scope at that time, and understand what's going to be done with the result once it's produced. 

    If I focus in on a single caller, it may even be useful to know __how the program will even arrive at that place__ by tracing an example call chain up the stack a bit (there would likely be more than one of these in a complex codebase, but even tracing through a single path generally suffices to give me the contextual understanding I need).

2. Understand the types passed into the function

    To implement the body of this new function I'll need to know what data I'm going to be working with. I'd need to check the type definitions of all args. This may involve recursively diving into arbitrarily nested types referenced by complex structured types.

3. Understand the return type

    Similarly, I'd need to know what I'm supposed to be returning to callers. I'd need to dive into the type definition to understand the shape of the data I should be returning.

4. Explore the codebase to find which other functions to use

    This is the most open-ended part of the entire process. Here, I'll need to explore the codebase, potentially falling back on my existing memroy of the codebase's architecture to direct my search for existing functionality that I can leverage to implement this new functionality. The end result of this search though is simply a mental list of available functions that will be useful to me.

    It's worth noting that understanding these functions may recursively involve repeating steps 2 & 3 to understand the types going in/out.

## **__Building__** the Mental Model is Hard & Interesting; **__Using__** the Mental Model is Boring
Great! Now that I've done the above, I'm done researching and I have all my __mise en place__, I've arguably already done 100% of the hard part, **the rest is essentially just manual labor**. 

It's worth admitting that, as a professional software developer, 99.99% of the time the for-loops, if-statements and function calls in the body of this function I've been researching will be **TRIVIAL** to implement once I've done the hard work of understanding the context in which those for-loops, if-statements and function calls need to live.

## So, How Was This Different Than Prompt Engineering?

**It wasn't!**

The entire discovery process I described above completely boils down to collecting a set of facts and loading them into my working memory. Is the only difference between this and prompt engineering the fact that I didn't bother to write it down? I'd argue.... yes! That's literally the only difference. 

The programming process that we've all been following day in and day out for years is literally just prompt engineering in the mental scratch space of our short term memory.

## Aside - "Functional Programming" Design Principles

One thing that was taken for granted above, was just how much of the stated simplicity in the above mental model building activity was the result of the functions described explicitly not referencing anything outside of the explicitly passed arguments. Arguably, the entire reason that so many engineers so passionately advocate for functional programming is simply the fact that it limits the size of the context window that they need to be able to load into their head in order to confidently/correctly implement functions. 

In a non-functional world, in the best case you follow all of the same steps above, but just add more steps to the list in looking for things like data that might be mutating out from underneath you unexpectedly when calling other functions, or looking for state that you'll need to manage that's implicitly defined outside the scope of explicit arguments or return values. In the worst case, you end up needing to understand complex temporal invariants on the "correct" order to call certain methods to correctly use fickle, mutable, stateful objects that merge state and functionality. Hope you have a really large working memory, you might make this work.

# Jitter Automates Prompt Engineering

If the difference between mental model building and prompt engineering is just whether or not you write it down, then Jitter is attempting to bridge that gap by simply automatically collecting the context and writing it down for you.

The theory that Jitter is exploring, is that this context that used to live solely in a developer's head, can be gainfully leveraged to add some automated assistance to the **boring part** of filling in the body of a function once the relevant context is all discovered.

## Example Automated Context Discovery

Let's just work through an example of Jitter in action, to see what context it automatically discovers in the implementation of a function. Let's take the [example calculator program](https://github.com/JasonSteving99/Jitter/tree/main/examples/calculator) and break down the context that Jitter automatically collects when coming across the unimplemented [`interpret` function](https://github.com/JasonSteving99/Jitter/blob/f211f4650017b3bc060bfdaf22d986b64c1a26ee/examples/calculator/interpreter.py#L4):

```python
from calculator import tokenizer


def interpret(program_tokens: list[tokenizer.LPar | tokenizer.RPar | tokenizer.Integer | tokenizer.Float | tokenizer.PlusOp | tokenizer.MinusOp | tokenizer.MulOp | tokenizer.DivOp | tokenizer.PowOp]) -> float:
    """Interpret the program tokens eagerly left-to-right not honoring operator precedence other than parentheses.

    The implementation will use the functions in @calculator.operations to implement this logic."""
    raise NotImplementedError("Still need to implement this!")
```

There's so much rich context here just **waiting** to be extracted! Here's the context that Jitter produces for this function (remember, this is a great example of **why programming is both hard and time consuming**, this massive chunk of text - almost 200 lines! - below is the **MINIMUM** amount of context you'd need to load into your short term memory to implement this function yourself!):

```
TARGET FUNCTION TO IMPLEMENT:
Function name: interpret
Function signature: interpret(program_tokens: list[calculator.tokenizer.LPar | calculator.tokenizer.RPar | calculator.tokenizer.Integer | calculator.tokenizer.Float | calculator.tokenizer.PlusOp | calculator.tokenizer.MinusOp | calculator.tokenizer.MulOp | calculator.tokenizer.DivOp | calculator.tokenizer.PowOp]) -> float
Function docstring: Interpret the program tokens eagerly left-to-right not honoring operator precedence other than parentheses.

The implementation will use the functions in @calculator.operations to implement this logic.


TYPE DEFINITIONS:
The following custom types are used by this function (arguments, return type, or referenced functions):

--- LPar (from /Users/jasonsteving/Projects/PLJam/examples/calculator/tokenizer.py:32-35) ---

@dataclass(frozen=True)
class LPar:
    pass

--- RPar (from /Users/jasonsteving/Projects/PLJam/examples/calculator/tokenizer.py:36-39) ---

@dataclass(frozen=True)
class RPar:
    pass

--- Integer (from /Users/jasonsteving/Projects/PLJam/examples/calculator/tokenizer.py:4-7) ---
from calculator import tokenizer
@dataclass(frozen=True)
class Integer:
    val: int

--- Float (from /Users/jasonsteving/Projects/PLJam/examples/calculator/tokenizer.py:8-11) ---

@dataclass(frozen=True)
class Float:
    val: float

--- PlusOp (from /Users/jasonsteving/Projects/PLJam/examples/calculator/tokenizer.py:12-15) ---

@dataclass(frozen=True)
class PlusOp:
    pass

--- MinusOp (from /Users/jasonsteving/Projects/PLJam/examples/calculator/tokenizer.py:16-19) ---

@dataclass(frozen=True)
class MinusOp:
    pass

--- MulOp (from /Users/jasonsteving/Projects/PLJam/examples/calculator/tokenizer.py:20-23) ---

@dataclass(frozen=True)
class MulOp:
    pass

--- DivOp (from /Users/jasonsteving/Projects/PLJam/examples/calculator/tokenizer.py:24-27) ---

@dataclass(frozen=True)
class DivOp:
    pass

--- PowOp (from /Users/jasonsteving/Projects/PLJam/examples/calculator/tokenizer.py:28-31) ---

@dataclass(frozen=True)
class PowOp:
    pass



REFERENCED DEPENDENCIES:
The function's implementation plan references these modules/functions that should be used in the implementation.
IMPORTANT: Do NOT include import statements for these modules in your implementation - the module imports will be automatically added to the file (access members via the module).

--- @calculator.operations (module from /Users/jasonsteving/Projects/PLJam/examples/calculator/operations.py) - Use as: operations ---
"""
Basic Calculator Library

A simple calculator that provides basic arithmetic operations.
All functions currently raise NotImplementedError and need implementation.
"""

def add(a, b):
    """
    Add numbers together.

    Args:
        a (float): The first number
        b (float): The second number

    Returns:
        float: The sum of a and b
    """
    raise NotImplementedError("Addition operation not yet implemented")


def subtract(a, b):
    """
    Subtract the second number from the first number.

    Args:
        a (float): The number to subtract from
        b (float): The number to subtract

    Returns:
        float: The difference of a and b (a - b)
    """
    raise NotImplementedError("Subtraction operation not yet implemented")


def multiply(a, b):
    """
    Multiply two numbers together.

    Args:
        a (float): The first number
        b (float): The second number

    Returns:
        float: The product of a and b
    """
    raise NotImplementedError("Multiplication operation not yet implemented")


def divide(a, b):
    """
    Divide the first number by the second number.

    Args:
        a (float): The dividend (number to be divided)
        b (float): The divisor (number to divide by)

    Returns:
        float: The quotient of a and b (a / b)

    Raises:
        ZeroDivisionError: If b is zero
    """
    raise NotImplementedError("Division operation not yet implemented")


def power(base, exponent):
    """
    Raise a number to the power of another number.

    Args:
        base (float): The base number
        exponent (float): The exponent

    Returns:
        float: base raised to the power of exponent
    """
    raise NotImplementedError("Power operation not yet implemented")


def square_root(n):
    """
    Calculate the square root of a number.

    Args:
        n (float): The number to find the square root of

    Returns:
        float: The square root of n

    Raises:
        ValueError: If n is negative
    """
    raise NotImplementedError("Square root operation not yet implemented")



CALL STACK CONTEXT:
Here are the functions in the call stack that led to interpret being called (showing last 1 of 1):

--- Call Stack Level 1: /Users/jasonsteving/Projects/PLJam/examples/calculator/test.py:4-16 ---
def test():
    """This will compute the basic arithmetic formula: (5 + 3) * 2 - 4 / 2 = 14

    For the implementation, we'll first make the formula a string, and then parse it using
    @calculator.tokenizer::tokenize and then @calculator.interpreter to interpret the evaluation of the tokens.

    Print out the result before returning it.
    """
    formula_string = "(5 + 3) * 2 - 4 / 2"
    tokens = tokenizer.tokenize(formula_string)
    result = interpreter.interpret(tokens)
    print(result)
    return result
```

Jitter just automatically wrote down every last bit of context that our development discovery process described above listed! Jitter collected all type definitions that the arguments and return types transtively reference. It collected the full call stack that led down to the function that's being implemented. And it collected even the context of functions that will need to be used in the body of the implementation by parsing out the forward @-reference to `@calculator.tokenizer`.

All of this is the __MINIMUM__ amount of context necessary to understand how to implement this function. Seeing it written down like this, personally, I'm **amazed** that we're able to write even simple programs like this little calculator example! I'm repeating myself now, but truly, to me this is why programming is hard - there's just **so much context to collect to do ANYTHING**.

## Keep the Human in the Driver Seat via @-references

One thing that may not be __immediately__ obvious on your first read, is that the context for which functions should be used in the internal implementation of the function was dictated by a human who typed out the docstring in the unimplemented function body. The `@calculator.tokenizer` string is the result of a human still taking the time to do research to discover what's going to be useful in the implementation. This isn't a bug, this is BY DESIGN. The most reliable approach to doing that sort of forward planning in a codebase of arbitrary complexity, is to allow a human to leverage their experience and long term memory of the architecture of the codebase to direct the planning for this function's implementation. In simple cases an "agentic" LLM system may also be used to discover and write out this @-reference, but the main design intention here is to make sure that this type of system is open to having a human in the driver's seat.

## Passing this Context to an LLM

Jitter is a fantastic example of how a language might make use of all of the information available to it, both statically and at runtime, to help us collect all of this information in one place. And naturally, now that we have all the context in one place, it's worth at least attempting to get a first stab at the boring part by passing all this curated context to an LLM to build out this function body for us. 

While this is still hotly debatedd, for many of us, it's completely uncontroversial to claim that an LLM might be capable of successfully writing a **single function** given all of this context. 

We haven't asked the LLM to discover this context itself, we're not expecting the LLM to intuit the fact that this function should even exist, we've simply handed it the context necessary to come to the conclusion that we could come to ourselves to solve a very minimal, isolated problem. 

# A Programming Language Could do a Much Better Job Than Jitter

To close the loop on all this, let's bring things back around to the fact that Jitter is an experiment. Jitter is a neat demonstration that inspecting a program to collect the necessary context for implementing functions can be largely automated so that we can squeeze more out of LLMs without even diving into "agentic" solutions. 

But Jitter is limited. It currently hacks this functionality into Python programs at runtime, by forcing the user to raise a `NotImplementedError` and then inspecting the stack trace of the raised Exception. But, this is obviously extremely brittle; among many more issues, most obviously, even a single `try: ... except Exception: ...` and the whole thing falls apart. 

I've made Jitter as hopefully a call to action to programming language designers/developers out there to try thinking about this sort of LLM-assisted development cycle in your language! Your compiler/interpreter has access to SO much rich information, that could be put to incredibly valuable use, and it probably wouldn't take __that much__ effort. And there are so many different angles for you to come at this from, I mean, a static analysis tool could acquire much of this information at the click of a button. 

I hope to encourage exploring how concrete language tooling can still be leveraged in a more explainable way than generalist "agentic" coding tools where we cross our fingers and hope the "agent" walks the right parts of our codebase to get all the information necessary. Remember, when that fancy "agentic" LLM tool is exploring your codebase, all it's doing is just trying to fill its context window with this information that I've shown Jitter collecting in the example system prompt above.
# Jitter

Jitter is an experiment in what it would look like to work in a programming language that enables you to interactively 
lay down the train tracks in front of you as you're going. 

Instead of figuring out everything in advance and running it later, just litter your program with 
`NotImplementedError`s or call functions that don't even exist yet, and instead of letting your program crash, Jitter 
will handle these cases at runtime by allowing you to implement the function just in time. So, rather than these 
situations being the end of the road leading to some uncrecoverable crash, you can just lay down some more track in 
front of you and keep on keepin on!

## CoRecursive Programming Language Jam Submission
 
This project is my submission to a 2 week (1 week planning - 1 week implementation) programming language jam hosted in the CoRecursive Slack Community. Don't expect this to be a fully fledged, bulletproof project. 

# Design
## Before

If you have functions like:
```python
def foo():
  print("In foo")
  bar()

def bar():
  print("In bar")
  raise NotImplementedError("Oh no, this function's not implemented yet!")
```
and a program like this:
```python
if __name__ == "__main__":
  foo()
```
normally, you'd run into a crash, something like:
```bash
In foo
In bar
Traceback (most recent call last):
  File "/Users/jasonsteving/Projects/PLJam/ex.py", line 10, in <module>
    foo()
  File "/Users/jasonsteving/Projects/PLJam/ex.py", line 3, in foo
    bar()
  File "/Users/jasonsteving/Projects/PLJam/ex.py", line 7, in bar
    raise NotImplementedError("Oh no, this function's not implemented yet!")
NotImplementedError: Oh no, this function's not implemented yet!
```
:(
## After
With Jitter, you can simply wrap your program like:
```python
if __name__ == "__main__":
  with Jitter():
    foo()
```
and now, any time a `NotImplementedError` is reached, Jitter will automatically handle the error, pausing execution and asking you for a (re-)implementation of the offending function (potentially using LLM code-generation). Then, once you've given it the valid implementation, Jitter will edit the source code in place to replace the bad implementation with your new implementation, and then by way of stack inspection, Jitter will literally resume your program from where it left off, but this time using the new given implementation. 

This idea is repeatable within a given session, so you can incrementally build out your program, laying one more piece of track in front of you at a time so that the program **never** dies just because something wasn't yet implemented yet.

## Stretch Goal Idea
In the future, I may extend this to handle `NameError`, e.g:
```bash
  File "/Users/jasonsteving/Projects/PLJam/ex.py", line 2, in foo
    bar()
    ^^^
NameError: name 'bar' is not defined
```
to give you a chance to implement the non-existent function and keep going.

# Install Using UV

Install Jitter using the below command:
```
$ uv add jitter-llm --optional cli
```

If you don't want to be able to autogenerate scaffolding for programs that can be implemented via Jitter, drop the `--optional cli` args.

### Auto-Generate Scaffolding for Programs to Try Out Jitter
The fastest way to get started with Jitter and get a feel for it is to run something like:
```
$ mkdir -p "sample/text_box_repl"
$ uv run jitter --output_dir "sample/text_box_repl" --desc "A repl that echoes but allows users to choose the shape of the boxes"
```

Claude Code will then go off and generate the scaffolding for the program you described, leaving all the implementations as `raise NotImplementedError("...")` so you can implement the detailed behavior using Jitter. Btw, you may ask yourself "why not just have Claude Code go and implement the full implementation for me then? Why use Jitter at all?"...I encourage you to try out both! Try just giving Claude Code the exact same one liner prompt directly, letting it run in auto-accept-edits mode, and see if it produces something you're happy with! In my experience I've actually been surprised that Jitter actually seems to do a better job of building out the program more efficiently than Claude Code on its own, but hey, this is all an experiment.

# Take Advantage of Jitter Executing at Program Runtime

Right now, the fact that Jitter executes as part of the runtime of your program is honestly only useful insofar as that's the easiest way to get access to the call chains to populate the LLM context window with how/why/when the unimplemented function is getting called. But, realistically, that could be done with sufficiently advanced static analysis (which would be sick, if this were a builtin feature of a compiler as opposed to just an add-on library). But, I want Jitter to have a reason to exist in its current form, and I think that will need to come down to taking advantage of information that ONLY EXISTS AT RUNTIME. 

## Add Actual Args to LLM Context

The simplest example of unique information that Jitter has access to as a part of the runtime, is the **actual data passed into the unimplemented function**. By inspecting the callstack, Jitter has the ability to give the LLM **perfect** understanding of exactly how it's being called, rather than forcing it to just rely broadly and generically on the type signature. Type signatures are useful, but explicit examples are even better, so we should absolutely be capturing the actual runtime argument data and passing that to the LLM context.

## Run the Replacement Implementation Over the Original Args and Ask Whether Result is Valid

Now an even more advanced thing that I can do is automatically call the replacement implementation with the captured original arguments and show the output (or error if the generated impl was invalid) to the user to ask them if this is what they'd expect. By doing this BEFORE accepting the re-implementation and rerunning the callstack we open the door to a rich interactive implementation loop, giving the human and potentially LLM users very rich information to make use of to re-implement the function properly before committing and moving on.
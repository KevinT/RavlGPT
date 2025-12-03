# Example: Simple Loop Tree

Demonstrates multi-LLM support with two child loops that playfully compete.

## Quick Start

Run directly - the system will clone a local copy for you, you will find it in `./ravl_loops/simple_loop_tree`:

```bash
ravl ravl.examples.example_2_nested_loops
```

## Run Individual Loops

```bash

# Start the parent loop (which will start the child loops)
ravl simple_loop_tree

# Start the Anthropic child loop only
ravl simple_loop_tree.simple_loop_anthropic

# Start the OpenAI child loop only
ravl simple_loop_tree.simple_loop_openai
```

## View Learning

Learning artifacts are stored in your local clone at:

```
ravl_loops/simple_loop_tree/learnings/
```

You can change this for all three loops from the parent's `ravl.toml`, or set it differently in each of the child loop's config files.

## Requirements

You'll need API keys configured:
- `ANTHROPIC_API_KEY` for the Anthropic loop
- `OPENAI_API_KEY` for the OpenAI loop

Set these in your `.env` file or environment.

## Additional useful commands

```
ravl LOOP_NAME	--show-config				# Show what config settings the loop will use
ravl LOOP_NAME	--show-execution			# Show the execution steps as it runs
ravl --loop-health LOOP_NAME 				# Diagnose the health of your loop
ravl --execution-health LOOP_NAME --focus "Why is this taking so long?"		# Diagnose any issues the framework is having executing the loop
ravl --list	simple							# Show all available loops with "simple" in their name
ravl --help									# Usage, Commands and Loop options help
```
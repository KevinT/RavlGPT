# This file is maintained by a human, do not change it
-----

# Pattern: English->Code->English loop development
## USED WHEN
Markdown loop imperative + learning approach not converging on a good solution
	- loop isn't learning enough context
	- loop too slow / token hungry for what it is doing
	- problem is large for simple codegen
	- feeling of "if this was just code it would work by now"

-----

## Pattern: Get it working in code, generalise it to md
Switch to doing it in code (but keep the md loop). 

1. Build working ravl using AI repl + code
2. Generalise it into a markdown->codegen capability
3. Refactor md loop to depend on generated code
4. Move code into .ravl fx if it could extend all ravls

## Examples
1. markdown proving complex for data + metadata ingestion from google workspace because it uses the google workspace API which is quite complex.

-----

## ANTI-pattern: Allow AI code agent too much freedom to make changes for a specific feature which then end up making assumptions and breaking other features, or we go around in circles in fixing mode and never quite capture ground
## Resolutions
Get a simple system that works and keep it working by iteratively improving it:
1. Including VISION.md in context when adding new features
2. Take smaller steps towards a bigger goal that the agent is aware of
3. Work backwards from solving a real world problem rather than just "adding framework capabilities that will definitely be useful"
4.1 Design mode before implementation, always
4.2 Read the designs that will be implemented and understand what they are, even if you're confident the agent is heading in the right direction - otherwise it will get there without you

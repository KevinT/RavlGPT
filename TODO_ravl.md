# This file is maintained by a human, do not change it

name of the ants in terry pratchett?

----- BUSY

strategy_coherence delegated loop
./ravl --execution-health fde_facts failing

----- TODO -----

# Tidy First

- remove ability to name a ravl in the config - the folder name is the ravl name, otherwise there's confusion

- Additional learning clean up 
	- the /logs folder could go under /history and be called /terminal-log or something like that

- "Fetching document 5/6: https://docs.google.com/spreadsheets/d"
	- Should rather use the document name, if it has it.

- move common/mixins/LLMMixin to common/llm/. and remove the mixins folder

- synthesize_domain_learnings.md and synthesize_run.md seem very similar but I can see code usages of both. What's correct?

- ask generated code to include print statements for the domain specific actoins it is taking

# General Features
## PIONEER
- See if I can convert python fde source loop into markdown loop
	provide a loop archetype in md loop config
	create a loop archetype in .ravl
		list of code files to keep in context when generating executable code for md ravls
	when md loop runs with an archetype it adds those source code files to the context as available functionality to use (needs to fit in context window)
	- Deleted fde_operating_strategy_google_md is worth relooking at, could an agent write a ravl_loop.md version of the python implementation version that got the same results (was called fde_operating_strategy_google_py at time of deletion)?

## SETTLE
- Improve detection for custom code generation
	- print(f"  [•] Custom code required - complex operations in loop spec", file=sys.stderr)

- Context gathering capability
	- automatically send an email to someone to get more context and add it to the reply
	- forward an email to an address that automatically adds it to the org-context? not sure this is a ravl feature...idea source = chris's weekly tech email
	- slack / commands
		- /I command
		 	- "/I would like to know XYZ"
		 	- "/I would like to add context BLAH"

- Allow some prompt text to be include in a health check
	- "why is blah not blah?"

- Add https://langfuse.com/self-hosting to have observability + optimisation of LLM calls, which is a key feature of the ravl approach, so better visibility and optimisation there would be helpful. There is a free self hosted MIT open source option. It does add architectural complexity though - do this when ready to step away from current code + text simplicity/iteration speed/context containing

- turn the release_notes ravl into one that can be delegated to in any project

- ravl framework version numbers in the loop learning outputs so that health checkers have the context of when the fx changed
	- consider using the SHA hash of the HEAD of the ravl git repo as the version, so we don't need to manually increment anything?

- "Fetching document" could give document name instead of URL, would be more helpful

## SCALE
- Make ravl framework portable between LLMs - currently only built using anthropic, but tried to keep coupling + direct dependency low
	- support opencode
	- support codex
	- support google gemini
	- Add per-ravl model selection support to markdown ravls


# Sand Specific



- SIESe RAVLs
	SOURCE
	INGEST
	- Clickup integration
	- FAC and PAC?
	- weekly reports
		- https://docs.google.com/presentation/d/1VPQ1dZMhkImtLv5_g3I1giAKekZz31tFNh3okmG4kgw/edit?slide=id.g38c112459d8_0_0#slide=id.g38c112459d8_0_0
	ENRICH
	SERVE
	- Sand Partner recommender

- test guardian template on compliance docs

- build up org context graph from operational data sources
	+ PEOPLE
		+ Google workspace
		+ HiBob
		+ ?
	+ CLIENTS
		+ ?
	+ INITIATIVES / CVL
		+ ?

- PAC and FAC based guidance

- https://capability-demo.energy.sandtech.app/ as a source


# This file is maintained by a human, do not change it

----- BUSY

allow loops to create new loops themselves, by calling "ravl --new ..."

----- TODO -----

# Tidy First

--new is not working since the switch from / to . namespaces

- Additional learning clean up 
	- the /logs folder could go under /history and be called /terminal-log or something like that

- move common/mixins/LLMMixin to common/llm/. and remove the mixins folder

- synthesize_domain_learnings.md and synthesize_run.md seem very similar but I can see code usages of both. What's correct?

- ask generated code to include print statements for the domain specific actions it is taking

# General Features
## PIONEER

- Get learning notes from Notion into my personal context?

## SETTLE
- ravl --list xyz should do --namespaces-only by default
- these are effectively doing the same thing on different files, they could be turned into a library loop and parameterise
	frontier_delivery.context_inference.infer_employee_efforts
	sand_organisation.context_inference.infer_employee_efforts
- If REFLECT detects there has been multiple recent failures and no success, switch --show-execution on to help the user find the issue (they might not know about the flag)
- enable the ability to switch off learning from siblings, children and parents independently in ravl.yml
- Add funtionality to have #> ignored by ravl fx so people can add comments to ravl_loop.md that aren't used by fx
- Known unkowns listing
	- During learn stage write known_unknowns.json to loop and execution learning
	- If there are answers in those files, use them in reflect stage (could be added by human or another loop)
	- Allow for perspective-based answers - human thinks answer is X, self_healing_loop thinks Y

- Context gathering capability
	- automatically send an email to someone to get more context and add it to the reply
	- forward an email to an address that automatically adds it to the org-context? not sure this is a ravl feature...idea source = chris's weekly tech email
	- slack / commands
		- /I command
		 	- "/I would like to know XYZ"
		 	- "/I would like to add context BLAH"

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


# ACT

People should be able to look at the change log and see what updates have been made to the content from the front end. They should not see git or deployment or background changes, only the semantically meaningful content updates.

- Look at ./.ravl/docs/RELEASE_NOTES.md, if it exists
- Look at the git commit history of the ravl submodule
- Identify all meaningful content updates that have been made since changelog.md was last updated
- Also check if any of the very recent updates should have updated text based on recent changes rather than a new section being added
- Use an LLM call to collate a list of changes, focussing on the problem statement/value/outcome not implementation details - make it nice and human readable
- Update the RELEASE_NOTES.md, keeping the same structure and format that is there and putting newer items at the top

# VERIFY
- RELEASE_NOTES.md exists in the `./.ravl/docs/` folder
- The notes are focussed on things that users of the framework would be interested in knowing, not minor fixes and refactorings
- There should be no implementation details in the release notes just information on new capabilities added to the framework
	- Eg - There should be no notes like "clean up" or "Fix .env file parsing to strip shell-style quotes", these are implementation details
- The latest notes are at the top

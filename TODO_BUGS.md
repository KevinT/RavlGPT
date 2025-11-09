- claude ravl agent never seems to invoke.

- Real-time output streaming for generated code (print statements visible during execution, better UX for long-running operations)

- it looks like loops are being flagged as failing even when they pass - check the verifications system

- read_parent_model and read_sibling_model are incorrect, they use parent.parent mechanism to find learning
	- parent_model_path = self.model_path.parent.parent.parent / 'learnings' / 'model.yml'

- ravl protocol not being provided to loop enhancer:
	- protocol_file = self.loop_dir.parent.parent.parent / '.ravl' / 'docs' / 'RAVL_PROTOCOL.md'

- Fix github action error in sand-strategy project- https://github.com/Sand-EnterpriseAI/sand-strategy/actions/runs/18549268840/job/52873503259

- does the parameter passing from ravl.yml into ravl_loop.md work?

- ravl health doesn't understand delegated loops

- `_merged_config.yml` is being written to the loop directory itself - that could be read only and it's deleted afterwards so lost. Should it not be rather in /learning and retained?

- possible bug in invalidating generated code if the ravl_loop.md has changed
	- that loop could be delegating to another loop that has changed, but code only checks caller, not down delegation path. Would need to change loop to force a regeneration, or fix fx code

- empty ravl template has wrong content

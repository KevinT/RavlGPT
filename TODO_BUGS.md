# IMPORTANT: THIS FILE IS MAINTAINED BY A HUMAN. IGNORE IT.

----------------
Venv needs recreation: venv has incompatible Python 3.14.0: Python 3.14.0 has compatibility issues (use 3.9-3.13)
----------------
- rugby_tips_1 is failing but still running the cached code
----------------
- claude ravl agent in .claude of DigitalTerrain never seems to invoke.
----------------
- ravl protocol not being provided to loop enhancer:
	- protocol_file = self.loop_dir.parent.parent.parent / '.ravl' / 'docs' / 'RAVL_PROTOCOL.md'
----------------
- Fix github action error in sand-strategy project- https://github.com/Sand-EnterpriseAI/sand-strategy/actions/runs/18549268840/job/52873503259
----------------
- ravl health doesn't understand delegated loops
----------------
- `_merged_config.yml` is being written to the loop directory itself - that could be read only and it's deleted afterwards so lost. Should it not be rather in /learning and retained?
----------------
- possible bug in invalidating generated code if the ravl_loop.md has changed
	- that loop could be delegating to another loop that has changed, but code only checks caller, not down delegation path. Would need to change loop to force a regeneration, or fix fx code
----------------
-    • Fetching document 8/8: Healthcare Radar
      ⚠️  Could not fetch edit history: Missing required parameter "fileId"
      ✓ Saved: healthcare-radar.md (13717 bytes)
      ✓ Metadata: healthcare-radar.metadata.jsonl (appended)

----------------
ravl --list emplo
[✗] ⚠️  ⚠️  NAME COLLISIONS DETECTED

The following loop names are ambiguous (multiple loops share the same name):
You must use full paths to run these loops.

Loop name: 'infer_employee_efforts' (2 instances)
  → ravl_loops/frontier_delivery/ravl_loops/context_inference/ravl_loops/infer_employee_efforts
  → ravl_loops/sand_organisation/ravl_loops/context_inference/ravl_loops/infer_employee_efforts

To run a colliding loop, use its full path:
  ./ravl ravl_loops/frontier_delivery/ravl_loops/context_inference/ravl_loops/infer_employee_efforts
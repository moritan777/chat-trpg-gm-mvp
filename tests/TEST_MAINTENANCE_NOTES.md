# Automated test maintenance notes

## Updated

- `test_companion_banter.py`
  - Replaced old Niko prompt assertions with the current association-axis definition.
  - Replaced old Garan prompt assertions with the current action-axis definition.
  - Added regression assertions that the giant-squid example and cliff-climbing fixation do not return.
  - Aligned turn output contract with one utterance per companion per turn.
  - Removed brittle prompt-size limits.
- `test_scenario_intent_layer.py`
  - Replaced exact confidence equality with a semantic threshold.
  - Renamed an ambiguous test whose old name claimed dice behavior it did not verify.
- `test_generic_skill_actions.py`
  - Replaced fixed output offsets with relative-order checks.
- `test_object_location_scope.py`
  - Added a regression test for duplicate aliases where the first global candidate is not visible.
- `test_arrival_npc_description.py`
  - Added an arrival case with no NPCs.
- `test_game_structure.py`
  - Added checks for required `Game` public methods.
- `test_action_skill_checks.py`
  - Reviewed and retained. It already covers current routing guards and five-rank checks.
- `test_opening_geography.py`
  - Reviewed and retained as a Lighthouse scenario regression test.

## Expected implementation mismatches exposed by the refreshed tests

The current engine prompt shown in recent logs still contains two obsolete statements:

1. The topic-derivation example beginning with `巨大イカ→沈没船`.
2. `同じ人物の短い再応答もよい` in the history/line-count section.

The refreshed tests intentionally reject both because they conflict with the current prompt policy:

- avoid a concrete giant-squid association anchor;
- each companion speaks at most once per turn.

Remove those two obsolete prompt fragments in `fixed_truth_ai_gm_mvp.py` before expecting the complete suite to pass.

## Validation performed here

- All eight Python files passed `python -m py_compile`.
- Runtime tests were not executed because `fixed_truth_ai_gm_mvp.py` and the authored Lighthouse scenario were not available in this workspace.

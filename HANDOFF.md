# sge-to-slurm Handoff

## Current status (brief)

- Core converter behavior is in place and documented in `README.md`.
- SCC module packaging exists via `module_installation/` and the `sgeconvert` modulefile.
- Basic automated tests exist, but they are limited by the small set of real SCC job-script examples used so far.

## What should happen next

The highest-value next step is broader real-world testing against SCC-specific SGE scripts.

- Team members should run representative scripts through `sge-to-slurm` and inspect outputs.
- Focus on translation quality for SCC patterns (resources, queues, parallel environments, array jobs, and common shell usage patterns).
- Capture cases where generated Slurm output is incomplete, incorrect, or requires manual edits.
- Add each gap as either:
  - a converter improvement (code change), or
  - a configuration/mapping update (site config rules), or
  - an explicit documented limitation.

## Why this is the priority

This tool improves fastest through exposure to diverse real job scripts. Initial testing covered only a limited set of examples, so practical team usage is the best way to close parity gaps between SCC SGE usage and expected Slurm output.

## Suggested working loop

1. Collect a batch of real SCC SGE scripts (including edge cases).
2. Convert with `sge-to-slurm` and review warnings/errors plus output scripts.
3. Validate output behavior in Slurm (or with domain expert review where runtime validation is not yet possible).
4. Log findings and classify by severity/frequency.
5. Implement fixes, update tests with new fixtures, and repeat.

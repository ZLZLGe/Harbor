# MAPK14 Lead Triage Notes

The primary target is MAPK14 / p38-alpha. Only records for this target should drive potency ranking; off-target kinase activity is useful context but should not rescue a MAPK14-inactive compound.

Normalize all activity values to nM before ranking. Exact IC50, Ki, and Kd records are considered direct biochemical potency evidence. EC50 records are acceptable backup evidence but should receive less weight than direct biochemical records. Values reported as `<` or `<=` are upper bounds and should be treated as potent-but-censored evidence. Values reported as `>` or `>=` are lower bounds and should not be averaged as if they were exact activity values.

For this stage, the team wants a shortlist that favors oral-like molecules with measured potency, avoids hard safety exclusions, and preserves series diversity. Reactive covalent probes may remain in the audit trail, but they should not be marked as `advance` unless there is a compelling non-reactive rationale.

Known nuisance patterns for this packet include Michael acceptor acrylamides, catechol/polyphenol assay interference, coumarin anticoagulant liability, highly lipophilic alkyl tails, and duplicate salt forms of the same parent compound.

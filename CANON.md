# OMEGA FINALIZATION ENGINE SPINE v17

Status: NOT SEALED
Execution chain present through EVT-010.
Six required receipts materially present and linked. Self-test evidence upgraded through EVT-010 / R-SELFTEST-001. Seal decision remains honestly NOT_SEALED (PATCHABLE, not PASS).
Purpose: Minimal stable spine for the OMEGA Finalization Engine after Phase 1 authority cleanup and normalized Phase 2 claim instantiation.

## Root files
- `CANON.md` = human-facing governing canon and current truth
- `AUTHORITY_LEDGER.json` = machine-readable authority graph, buckets, supersession, contradictions, and promotion constraints
- `CLAIM_REGISTER.json` = normalized Phase 2 claim register for live canon candidates only
- `LINEAGE.json` = hash lineage and compact bundle provenance only
- `SEAL.json` = seal admissibility rules, receipt templates, and current seal-event boundary
- `SOURCE_INDEX.json` = excluded source artifacts with hashes, kept outside the compact root to prevent bloat
- `LOGBOOK.jsonl` = append-only updates, completed phases, next legal triggers, and future audit entries

## Anti-bloat rule
Keep files as minimal as possible to prevent bloating. Anything that can exist in a single file should do so.

## Invariant Definitions — I1 through I7

The following invariants define the structural and functional requirements for any candidate seeking seal admissibility. These are the canonical predicates against which receipts are evaluated.

- **I1 — Candidate Identity**  
  The candidate file is present in the archive and its SHA-256 hash is recorded and verifiable against a known hash value.

- **I2 — Self-Containment**  
  The candidate has no unresolved external dependencies at the level being evaluated. All declared dependencies are either absent under a self-contained claim or explicitly present and ledgered in the archive.

- **I3 — Version Integrity**  
  A version identifier is explicitly present in the candidate record and is consistent across all archive surfaces that reference the candidate.

- **I4 — Defect Detectability**  
  A corrupted or mutated copy of the candidate produces a detectable failure. The canonical candidate itself is not modified during this check.

- **I5 — Temporal Stability**  
  Repeated probing of the candidate across time does not produce structural drift. Output structure remains consistent across separated probe runs.

- **I6 — Schema Conformance**  
  The candidate matches the expected archive schema and required field structure defined by `CANON.md`, `AUTHORITY_LEDGER.json`, `CLAIM_REGISTER.json`, `SEAL.json`, and `RECEIPTS.json`.

- **I7 — Structural Reproducibility**  
  A fixed input applied to the candidate produces the same output structure across independent runs, differing only in timestamp fields.

## Evaluation Ceiling Rule

- **PATCHABLE**  
  Artifact-surface checks, including ledger inspection, hash comparison, structural probes, and receipt-surface validation, can produce at most `PATCHABLE`.

- **PASS**  
  `PASS` requires verified cold-boot runtime execution at the level claimed.


## Receipt State vs History

`EXECUTION_LEDGER.jsonl` and `LOGBOOK.jsonl` are the append-only historical truth surfaces for execution and rebuild chronology.

`RECEIPTS.json` is the canonical receipt-state container. It holds the current receipt state view used for seal evaluation.

Beginning with v17, `RECEIPTS.json` also contains an append-only `receipt_history` ledger. New receipt revisions must be appended there with explicit version lineage. The `receipts` array remains the current canonical receipt-state view.

### Receipt Revision Rule

- Do not silently replace a receipt without preserving revision lineage.
- Every revised receipt must carry:
  - `receipt_version`
  - `receipt_revision_id`
  - `supersedes_revision_id`
  - `receipt_state`
- `receipt_history` is append-only.
- `receipts` may change only as the current-state projection of the latest receipt revisions.
- Historical receipt revisions before v17 may be incomplete because earlier builds used current-state replacement without a dedicated receipt-history ledger. This is a known legacy boundary, not a sealed surface.


## HARD ANTI-BLOAT RULE
This rule is binding for this build and every future build the engine seals or audits.

- Every build must prevent bloating.
- Every update must prevent bloating.
- Every zip should contain no more than 10 root files maximum if possible.
- Always update and merge what can be merged into a single file without breaking load-bearing structure.
- Do not add a new root file unless it carries unique governing force that cannot be safely merged into an existing root file.
- Prefer strengthening an existing root file over spawning a sibling file.
- Any proposed expansion must justify why merge is impossible or unsafe.

This is not a style preference. It is a regression-prevention rule.


## Current truth
Phase 1 is complete.
Authority lives in `AUTHORITY_LEDGER.json`.
Phase 2 claim instantiation exists in `CLAIM_REGISTER.json` and is normalized.
The archive now contains an append-only `LOGBOOK.jsonl` for everything it audits after creation as well.

## A-010 distinction (governing vs promotion)
A-010 currently holds the governing slot in the authority graph for live governance runtime in its lineage.
That is why its `authority_level` is `governing`.
This does **not** mean it is fully promoted, fully receipted, or sealed.
`promotion_ready = false` means external promotion and seal conditions are still unmet until required receipts exist.

## What changed in this rebuild
- added `LOGBOOK.jsonl` as the append-only audit/update spine for future runs
- updated `CLAIM_REGISTER.json` to normalized claim form
- merged claim-linked contradiction resolution into `AUTHORITY_LEDGER.json`
- retained `LINEAGE.json` only for hash lineage / provenance
- kept `SEAL.json` as the seal-rule root
- kept `SOURCE_INDEX.json` instead of embedding bulky sources
- did not add `EXECUTION_LEDGER.jsonl`, `RECEIPTS.json`, or `REGRESSION_RULES.json` yet, because empty rooms pretending to be machinery are still empty rooms

## Honesty boundary
This archive is not sealed.
It does not prove the corpus is fully verified.
It preserves the current authority graph, contradiction resolutions, claim register, seal rules, source lineage, and append-only progress log well enough to continue without authority, claim, or phase amnesia.

## Stable root meaning
This archive now covers seven load-bearing root functions:
1. canon
2. authority ledger
3. claim register
4. lineage
5. seal rules
6. source index
7. append-only logbook

## What remains missing for the true Finalization Engine
The compact spine still does not include:
- `EXECUTION_LEDGER.jsonl`
- `RECEIPTS.json`
- `REGRESSION_RULES.json`
Those should only be added when they are materially instantiated.

## Next legal rebuild triggers
Do not rebuild this compact spine again unless one of these becomes true:
1. `EXECUTION_LEDGER.jsonl` is instantiated
2. `RECEIPTS.json` becomes real
3. `SEAL.json` materially changes
4. the authority graph or claim register changes in a way that affects governing force, bucket assignment, contradiction resolution, or promotion blocking
5. `LOGBOOK.jsonl` reveals a new completed phase that introduces a new load-bearing root file

## Current bundle-level truth
- A-003 = canonical constitution/spec only
- A-005 = canonical executed reference runtime only
- A-010 = only live governance runtime in the NAS lineage, while still not promotion-ready
- A-011/NAS = fossil / historical input only
- A-006 = wrapper / fusion header only
- A-013 and A-014 = candidate-only, not sealed

## Rule carried forward
“Live Canon Candidate” means eligible for further audit and possible promotion, not currently governing unless separately granted governing force.


## Memory root
The archive includes `MEMORY.json` as the minimal canonical memory vault. It stores only durable, load-bearing audit memory that future seal audits must not have to reconstruct from surrounding chat context. It is portable to future audited builds, but must remain minimal.


## Execution-state note
The execution spine now exists but remains minimally instantiated. Starter events are present in `EXECUTION_LEDGER.jsonl`. `RECEIPTS.json` exists as the canonical append-only receipt container with an empty `receipts` array. No receipt-backed seal attempt has occurred. One real receipt now exists: R-SELFTEST-001 with PATCHABLE status only; no seal decision is admissible.


## Current execution-bearing truth
The archive now contains the full six-receipt chain and matching execution events through seal-decision evaluation.
The result is still NOT SEALED because all receipts remain PATCHABLE rather than PASS.
This is an honest, receipted non-seal state, not a failure and not a bluff.

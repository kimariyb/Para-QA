# Experiment status v1

## Frozen offline pilot

- Run ID: `pilot-offline-v1`
- QAC generation mode: deterministic dry run; no external LLM call
- Source corpus: 20 cleaned papers sampled from the 644-paper internal-development corpus
- QAC records after deterministic QC and deduplication: 474
- Document-disjoint split: train 326, dev 51, test 97
- Deterministic provenance validation: 474/474 records valid
- Test robustness fixtures: 358 (numeric 67, entity 97, distractor 97, unanswerable 97)

## Retrieval baseline

The reportable offline retrieval baseline indexes `outputs/pilot_qac/evidence_corpus_all.jsonl`, built directly from all 644 cleaned papers. The corpus contains 19,641 heading-aware evidence units and is independent of the QAC subset used as queries.

| Split | Queries | Corpus units | Recall@1 | Recall@3 | Recall@5 | MRR | nDCG |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| pilot test | 97 | 19,641 | 0.784 | 0.928 | 0.928 | 0.849 | 0.883 |

Artifacts:

- `outputs/pilot_qac/qac_report.json`
- `outputs/pilot_qac/qac_test_stress.jsonl`
- `outputs/pilot_qac/evidence_corpus_all.jsonl`
- `outputs/pilot_qac/bm25_test_full_literature_corpus.json`

## Claim boundary

These results establish only that a deterministic lexical retrieval baseline can recover source-linked evidence units for a dry-run silver QAC pilot. They do **not** establish the paper's central claim that evidence-grounded RAG outperforms a general LLM: that requires frozen real-LLM QAC generation and verification, controlled B0--B3/P1--P3 system runs, and judge results from an independent model.

## Next gated execution

Before any external-model run, record the generator, verifier, judge and answer-model identifiers; endpoint versions; decoding settings; run seed; API budget; and the date of corpus freeze. Use independent generator and verifier/judge model families where possible. Preserve every raw response, retry, rejection reason and cost log.

`scripts/preflight_experiment.py` implements this gate without making a network
call. The current local preflight report is intentionally `ready: false`: the
independent verifier, answer-model credential, and independent judge endpoint
have not yet been registered. This is a configuration gate, not a failed model
experiment; no external request was sent.

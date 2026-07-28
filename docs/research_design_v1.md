# Research Design v1

## Study

**Evidence-Grounded Retrieval-Augmented Generation for Navigating the
Interdisciplinary Literature of Parahydrogen-Induced Hyperpolarization NMR**

This project evaluates whether an evidence-grounded RAG system improves over
generic closed-book LLMs and generic RAG on interdisciplinary PHIP/SABRE
literature. It evaluates support by the frozen literature corpus, not chemical
advice or independent chemical truth.

## Research Questions

| ID | Question | Confirmatory outcome |
| --- | --- | --- |
| RQ1 | Does Chem-NMR-aware retrieval improve evidence retrieval? | Higher Evidence Recall@k, MRR, and nDCG than generic retrieval. |
| RQ2 | Does evidence-constrained generation improve answer traceability? | Higher citation precision, support rate, numeric/unit exact-match rate, and correct abstention rate. |
| RQ3 | Does the proposed system generalize across PHIP/SABRE disciplines? | Higher macro-average performance across the taxonomy below. |
| RQ4 | Are findings robust to automated-evaluation failure modes? | Stable system ranking across judges and controlled stress sets. |

## Scope and Corpus

- Include English, full-text PHIP/SABRE papers that are openly accessible or
  otherwise lawful to process and redistribute as required by the release.
- Freeze the DOI list, access date, license, source URL, raw-file SHA-256, and
  cleaned-text SHA-256 before QAC generation.
- Exclude papers without a reproducible source, duplicate versions, and text
  that fails the documented parser quality checks.
- Assign one or more corpus labels: catalysis and reaction mechanisms; NMR
  methods and pulse sequences; nuclear-spin physics and polarization transfer;
  molecular design and materials; biological, metabolic, and imaging
  applications.

All cleaned papers may be used for internal development and retrieval
experiments. Corpus selection remains a release gate: if rights allow only
metadata but not text redistribution, the dataset must not release the
corresponding context span.

## Silver QAC Protocol

QAC records are generated and audited by LLM-assisted code only. They are
**silver labels**, not expert-validated gold labels. Each record must include:

```text
id, question, answer, context, evidence_unit_ids, evidence_offsets,
doc_id, doi, section, qtype, difficulty, discipline_tags, answerability,
generator_model, verifier_models, prompt_hash, source_hash, split
```

The generation model, RAG generator, and judge models must be separate.
Every retained item must pass all of the following gates:

1. Evidence offsets resolve exactly against the frozen cleaned text.
2. Rule checks pass for schema, self-contained wording, source identifiers,
   numeric values, units, and language.
3. An independent verifier judges every answer claim as entailed by the cited
   evidence.
4. An independent answerer, restricted to the evidence, produces a consistent
   answer.
5. Exact, near-duplicate, and cross-split leakage checks pass.

Split source documents before generating questions. Test questions and their
source documents may be indexed at inference time, but may not be used for
prompt, threshold, or retrieval-model selection. Reserve a chronological
held-out slice for temporal robustness reporting.

## Systems

All systems use the same frozen corpus, query set, generator budget, and answer
format.

| ID | System |
| --- | --- |
| B0 | Closed-book general-purpose LLM. |
| B1 | BM25 retrieval with fixed-length chunks. |
| B2 | Dense retrieval with fixed-length chunks. |
| B3 | Generic hybrid retrieval with reciprocal-rank fusion. |
| P1 | Section-aware chunking plus hybrid retrieval. |
| P2 | P1 plus evidence-linked Chem-NMR metadata filtering or reranking. |
| P3 | P2 plus reranking, evidence-constrained generation, and citation verification. |

Chem-NMR metadata covers isotope/nucleus, substrate, catalyst, solvent,
temperature, field strength, pressure, concentration, enhancement factor, and
reaction or polarization conditions. Every extracted attribute requires a
source span and confidence record.

## Evaluation

Primary retrieval metrics:

- Evidence Recall@1, @3, and @5
- MRR and nDCG over reference source evidence units
- DOI and section hit rate
- Macro-average by discipline and question type

Primary answer metrics:

- Evidence-supported claim rate
- Citation precision and recall
- Numeric and unit exact-match accuracy
- Correct abstention on unanswerable questions
- Judge agreement, disagreement, and abstention rate

RAGAS metrics are secondary diagnostics only. All reported metrics include
micro and macro averages plus 95% bootstrap confidence intervals. Use McNemar
tests for paired binary outcomes and paired permutation or Wilcoxon tests for
continuous per-question measures, with Holm correction for multiple tests.

## Controlled Stress Sets

Construct automatically labelled perturbations from verified source items:

- numeric or unit changes;
- temperature, solvent, catalyst, substrate, or nucleus substitutions;
- negated causal or conditional statements;
- lexically similar but unsupported distractor evidence;
- unanswerable questions.

The expected answer for each stress item must be determined by the source and
the transformation rule, not by a judge model. Evaluate judges with answer
order swaps, hidden system names, answer-length perturbations, and replacement
of one judge model family.

## Reproducibility and Limitations

Version and archive prompts, model identifiers, parameters, seeds, retrieval
settings, raw outputs, latency, cost, errors, input hashes, and result tables.
Release code, configurations, data cards, stress sets, and scripts through
persistent repositories with DOIs.

The paper must state that it measures literature-evidence fidelity and
retrieval reliability under automated silver evaluation. It does not establish
expert agreement, laboratory validity, or the safety of experimental advice.

## Delivery Gates

1. **Corpus gate:** rights manifest and interdisciplinary taxonomy frozen.
2. **Schema gate:** QAC and provenance schemas validated on local fixtures.
3. **System gate:** B0-B3 and P1-P3 run from one reproducible interface.
4. **Pilot gate:** 20 documents complete without schema, leakage, or metric
   failures; model cost and error rate are recorded.
5. **Study gate:** protocol, models, prompts, and thresholds frozen before the
   full run.
6. **Release gate:** data, code, raw results, and manuscript tables are
   reproducible from tagged artifacts.

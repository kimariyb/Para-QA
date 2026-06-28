# Para-QA

Para-QA is a research-oriented data construction and evaluation pipeline for question answering over parahydrogen hyperpolarization literature, especially PHIP and SABRE papers. The project converts papers into Markdown, cleans literature text, generates Question-Answer-Context (QAC) examples through Dify workflows, and evaluates retrieval-augmented generation (RAG) performance with RAGAS.

The repository is intended for researchers who need a reproducible workflow for building domain-specific QA benchmarks and comparing RAG configurations on specialized chemistry and NMR literature.

## Table of Contents

- [Key Features](#key-features)
- [Tech Stack](#tech-stack)
- [Repository Structure](#repository-structure)
- [Pipeline Overview](#pipeline-overview)
- [Prerequisites](#prerequisites)
- [Setup](#setup)
- [Environment Variables](#environment-variables)
- [Usage](#usage)
- [Data and Outputs](#data-and-outputs)
- [Available Commands](#available-commands)
- [Development Notes](#development-notes)
- [Troubleshooting](#troubleshooting)
- [License](#license)

## Key Features

- Batch document parsing with MinerU for PDF, Office, image, and related scientific document formats.
- Markdown preprocessing that removes trailing reference, funding, author information, acknowledgements, and other noisy metadata sections.
- QAC dataset creation for PHIP and SABRE literature, with each example containing a question, a concise answer, and supporting context.
- Dify API clients for file upload, workflow execution, workflow log recovery, and RAG chat evaluation.
- RAGAS-based evaluation for answer quality and retrieval quality across different chunk sizes.
- Saved intermediate artifacts, raw API logs, result CSV files, and publication-ready metric visualizations.

## Tech Stack

| Area | Tools |
| --- | --- |
| Language | Python 3.10+ |
| Interactive workflow | Jupyter Notebook / JupyterLab |
| Document parsing | MinerU |
| Workflow and RAG service | Dify |
| Data processing | pandas, numpy |
| API access | requests, httpx |
| RAG evaluation | RAGAS, LangChain |
| Visualization | matplotlib, seaborn, wordcloud |

## Repository Structure

```text
.
|-- data/
|   |-- markdown/              # Markdown files extracted from source papers
|   `-- qac/                   # Selected paper subset used for QAC generation
|-- logs/
|   |-- 128/                   # Raw RAG API response logs for chunk size 128
|   |-- 256/
|   |-- 512/
|   |-- 1024/
|   `-- 2048/
|-- outputs/
|   |-- qac_dataset.jsonl      # Full QAC dataset
|   |-- qac_dataset_test.jsonl # Evaluation subset
|   |-- papers_tag.jsonl       # Paper metadata and method tags
|   |-- sampled_papers_100.csv # Sampled paper list
|   `-- *.pdf                  # Distribution plots, word clouds, and metrics plots
|-- results/
|   `-- qac_results_*.csv      # RAGAS evaluation results
|-- scripts/
|   |-- mineru_batch.py        # Batch parser for MinerU
|   |-- preprocess_markdown.py # Markdown cleaning CLI
|   `-- create_qac_jsonl.py    # JSONL merge and filtering CLI
|-- utils/
|   |-- dify.py                # Dify API client wrappers
|   |-- parser.py              # Markdown cleaning utilities
|   `-- __init__.py
|-- generate_qac_dataset.ipynb # QAC generation and dataset preparation
|-- evaluate_qac_dataset.ipynb # RAG evaluation workflow
|-- requirements.txt           # Python dependency list
|-- .env.example               # Example API configuration
|-- LICENSE
`-- README.md
```

## Pipeline Overview

```text
Source papers
  -> MinerU batch parsing
  -> raw Markdown files
  -> Markdown preprocessing
  -> selected QAC source files
  -> Dify QAC workflow
  -> QAC JSONL dataset
  -> Dify RAG chat API
  -> RAGAS evaluation
  -> logs, CSV results, and summary figures
```

The core benchmark format is JSONL. Each line is one independent QAC record:

```json
{
  "question": "What is the first step in the pulse sequences for PHIP experiments?",
  "answer": "The first step is to convert two-spin order into longitudinal magnetization or into I1y if an ROE is used.",
  "context": "The text discusses the use of NMR spectroscopy and PHIP for structural investigations..."
}
```

## Prerequisites

- Python 3.10 or newer.
- A virtual environment manager such as `venv`, `conda`, `uv`, or `micromamba`.
- MinerU and its model/runtime dependencies if you need to parse raw documents.
- A running Dify instance and API keys if you need to regenerate QAC data or evaluate a Dify RAG application.
- JupyterLab or another notebook runner for the two notebook-based workflows.

Existing derived artifacts are included in the repository, so you can inspect generated data, logs, results, and figures without connecting to Dify or MinerU.

## Setup

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it on macOS or Linux:

```bash
source .venv/bin/activate
```

Activate it on Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create a local environment file:

```bash
cp .env.example .env
```

Fill in `.env` with the Dify endpoints and API keys for your own deployment before running API-backed workflows.

## Environment Variables

| Variable | Required For | Description |
| --- | --- | --- |
| `DIFY_QAC_API_KEY` | QAC generation | API key for the Dify workflow that generates QAC records. |
| `DIFY_UPLOAD_FILE_URL` | QAC generation | Dify file upload endpoint, usually ending with `/v1/files/upload`. |
| `DIFY_WORKFLOW_RUN_URL` | QAC generation | Dify workflow execution endpoint, usually ending with `/v1/workflows/run`. |
| `DIFY_WORKFLOW_LOG_URL` | QAC recovery | Dify workflow logs endpoint, usually ending with `/v1/workflows/logs`. |
| `DIFY_RAG_API_KEY` | RAG evaluation | API key for the Dify chat or RAG application being evaluated. |
| `DIFY_RAG_CHAT_URL` | RAG evaluation | Dify chat endpoint, usually ending with `/v1/chat-messages`. |
| `DIFY_USER` | All Dify requests | Stable user identifier sent with API requests. |

Do not commit real API keys. Keep secrets in `.env`, your shell environment, or a local secret manager.

## Usage

### 1. Parse Papers with MinerU

Place raw source documents in a local directory such as `pdfs/`, then run:

```bash
python scripts/mineru_batch.py --input ./pdfs --output ./mineru --backend hybrid-auto-engine --lang en
```

Common options:

| Option | Description |
| --- | --- |
| `--input` | Source file or directory to parse. |
| `--output` | Root directory for MinerU outputs. |
| `--api-url` | Existing MinerU API server URL. If omitted, the script attempts to start a local server. |
| `--backend` | MinerU parsing backend. |
| `--method` | PDF parsing mode: `auto`, `txt`, or `ocr`. |
| `--lang` | Document language passed to MinerU. |
| `--formula false` | Disable formula parsing. |
| `--table false` | Disable table parsing. |
| `--image-analysis false` | Disable image and chart analysis. |

The batch script processes files sequentially. A failed file is logged and does not stop the rest of the batch.

### 2. Clean Markdown Files

Run Markdown preprocessing:

```bash
python scripts/preprocess_markdown.py --input data/markdown --output data/cleaned
```

The cleaner stops when it reaches headings that usually mark non-content sections, including references, supporting information, acknowledgements, conflict-of-interest statements, funding statements, author contributions, and data availability sections.

### 3. Generate the QAC Dataset

Open the QAC generation notebook:

```bash
jupyter lab generate_qac_dataset.ipynb
```

This notebook is used to:

1. Tag papers by method or topic.
2. Select the document subset used for QAC construction.
3. Upload selected Markdown files to Dify.
4. Run the Dify workflow that generates QAC records.
5. Save generated records as JSONL.

If you already have multiple JSONL shards from Dify, merge and filter them with:

```bash
python scripts/create_qac_jsonl.py --input qac_jsonls --output outputs/qac_dataset.jsonl --overwrite
```

The merge script removes empty lines, malformed JSON lines, records containing `NaN` or `None` markers, and records containing Chinese characters in nested values.

### 4. Evaluate RAG Performance

Open the evaluation notebook:

```bash
jupyter lab evaluate_qac_dataset.ipynb
```

The evaluation notebook:

1. Loads `outputs/qac_dataset_test.jsonl`.
2. Sends each question to the configured Dify RAG application.
3. Saves raw API responses under `logs/<chunk_size>/`.
4. Extracts retrieved contexts from Dify metadata.
5. Builds RAGAS `SingleTurnSample` records.
6. Computes answer and retrieval metrics.
7. Writes result CSV files under `results/`.
8. Generates summary visualizations under `outputs/`.

## Data and Outputs

| Path | Description |
| --- | --- |
| `data/markdown/` | Markdown files parsed from the original literature corpus. |
| `data/qac/` | Selected Markdown files used as source material for QAC generation. |
| `outputs/papers_tag.jsonl` | Paper-level metadata and method labels. |
| `outputs/qac_dataset.jsonl` | Full generated QAC dataset. |
| `outputs/qac_dataset_test.jsonl` | Test subset used by the evaluation notebook. |
| `outputs/sampled_papers_100.csv` | Sampled paper metadata for inspection or analysis. |
| `outputs/method_distribution.pdf` | Distribution of paper methods or labels. |
| `outputs/sampled_distribution.pdf` | Distribution plot for the sampled subset. |
| `outputs/title_wordcloud.pdf` | Word cloud generated from paper titles. |
| `outputs/evaluation_metrics.pdf` | Summary plot comparing evaluation metrics. |
| `logs/<chunk_size>/` | Per-question raw Dify responses for each evaluated chunk size. |
| `results/qac_results_128.csv` | RAGAS results for chunk size 128. |
| `results/qac_results_256.csv` | RAGAS results for chunk size 256. |
| `results/qac_results_512.csv` | RAGAS results for chunk size 512. |
| `results/qac_results_1024.csv` | RAGAS results for chunk size 1024. |
| `results/qac_results_2048.csv` | RAGAS results for chunk size 2048. |
| `results/qac_results_llm.csv` | LLM-only or non-retrieval baseline results. |

## Available Commands

| Command | Description |
| --- | --- |
| `python scripts/mineru_batch.py --help` | Show MinerU batch parsing options. |
| `python scripts/preprocess_markdown.py --help` | Show Markdown preprocessing options. |
| `python scripts/create_qac_jsonl.py --help` | Show QAC JSONL merge options. |
| `python -m compileall scripts utils` | Check Python syntax for scripts and utility modules. |
| `jupyter lab generate_qac_dataset.ipynb` | Open the QAC generation workflow. |
| `jupyter lab evaluate_qac_dataset.ipynb` | Open the RAG evaluation workflow. |

## Development Notes

- Run scripts from the repository root so relative paths such as `data/markdown` and `outputs/qac_dataset.jsonl` resolve correctly.
- `utils.dify` contains lightweight wrappers for Dify upload, workflow, log, and chat endpoints.
- `utils.parser.MarkdownProcessor` contains the Markdown section-truncation logic.
- Notebooks may still contain local endpoint examples or experiment-specific constants. Replace those values with your own environment variables before rerunning API calls.
- The project stores research artifacts directly in `outputs/`, `results/`, and `logs/` so that experiments can be inspected after execution.

## Troubleshooting

### `ModuleNotFoundError`

Install the Python dependencies in the active environment:

```bash
pip install -r requirements.txt
```

### MinerU is not installed

Install the MinerU dependency and required model/runtime assets before running `scripts/mineru_batch.py`. You can still inspect existing Markdown and output files without MinerU.

### Dify returns `401` or `403`

Check that the API key matches the Dify application and endpoint being called. The QAC workflow key and the RAG chat key may be different.

### Dify connection errors

Verify that the endpoint host, port, and path are reachable from the machine running the notebook or script. Private network addresses require the same network or a VPN.

### Empty or incomplete QAC output

Check the Dify workflow logs first, then inspect intermediate JSONL shards. The merge script intentionally filters malformed records, `NaN` / `None` markers, and records containing Chinese characters.

### Unexpected evaluation scores

Inspect the raw response file in `logs/<chunk_size>/` for the affected question. The saved API response contains the answer and retrieved context metadata used to build the RAGAS sample.

## License

This project is licensed under the terms of the repository [LICENSE](LICENSE).

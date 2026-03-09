# Prompt Refiner
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Ollama](https://img.shields.io/badge/Ollama-required-000000)


[![DOI](https://img.shields.io/badge/DOI-10.5281%2Fzenodo.18926768-blue?logo=doi)](https://doi.org/10.5281/zenodo.18926768)


Prompt Refiner is a lightweight Python CLI tool that rewrites your raw prompts into clearer, structured prompts using a local LLM through Ollama.

## Requirements

- Python 3.10+
- Ollama installed and available on PATH

## Installation

```bash
pip install git+https://github.com/SharuPaul/prompt-refiner.git
```

## Ollama Setup

Prompt Refiner uses Ollama to run local models.

1. Install Ollama: https://ollama.com
2. Verify installation:

```bash
ollama --version
```

3. Optional manual model pull:

```bash
ollama pull phi3:mini
```

Behavior notes:
- If Ollama is not running, Prompt Refiner tries to start it.
- If the requested model is not available, Prompt Refiner tries to pull it.

## Example Models

You can use any model pulled in your Ollama instance. Refiner output quality depends on the model used. 

Common examples:

- `phi3:mini` (default)
- `llama3.2`
- `gemma2:2b`
- `gemma3:1b`

List currently pulled models:

```bash
prompt-refiner --list-models
```

## Usage

Basic prompt refinement:

```bash
prompt-refiner "write a code block for a calculator"
```

All available command options:

```bash
prompt-refiner --help
```

```text
prompt-refiner [prompt] [--model MODEL] [--ollama-url URL] [--timeout SECONDS] [--list-models]
```

- `prompt`: Raw prompt text. Optional. If omitted, input is read from stdin.
- `--model`: Ollama model name. Default: `phi3:mini`.
- `--ollama-url`: Ollama base URL. Default: `http://localhost:11434`.
- `--timeout`: HTTP timeout in seconds. Default: `60`.
- `--list-models`: List installed Ollama models and exit.

## Additional Usage examples

Use a specific model:

```bash
prompt-refiner --model llama3.2 "Help me write code for an RNA-seq pipeline"
```

Use a model from Hugging Face:

```bash
prompt-refiner --model hf.co/bartowski/SmolLM2-1.7B-Instruct-GGUF:Q4_K_M  "what is huggingface?"
```

Read prompt text from stdin:

```bash
echo "Write a paragraph on spatial transcriptomics" | prompt-refiner
```

Use a custom Ollama URL:

```bash
prompt-refiner --ollama-url http://localhost:11434 "improve this prompt"
```

Set request timeout:

```bash
prompt-refiner --timeout 90 "improve this prompt"
```

## Citation 

DOI: https://doi.org/10.5281/zenodo.18926768

## Practical Notes

From manual testing:

- Very small models tend to answer the prompt instead of refining it
- Refiner works with the models listed in the `Example Models` section
- If output quality drops, switch to one of the listed models or a larger model

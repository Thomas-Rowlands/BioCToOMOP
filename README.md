# BioC-To-OMOP

This repository contains the Python pipeline used to annotate BioC publications, including supplementary material, and import them into OMOP CDM using in-built ETL rules.

## Installation

The UV Python package manager was used for this project, utilising a pyproject.toml file that can be used to install dependencies.

```bash
# install package dependencies
uv sync
```

## MedCAT Models

MedCAT models are publicly available, see download instructions here: https://github.com/CogStack/cogstack-nlp/blob/main/medcat-v2/README.md 

## Configuration

To configure OMOP default concept IDs, such as the "NLP derived" measurement type or "Clinical document" type, the `.env` file located in the *scripts* folder should be modified according to your OMOP CDM installation.

The CogStack MedCAT model is used within this demonstration, with the model file path specified within the `.env` file.

## Usage

The main entry point for executing the pipeline is the run_python.py script located in the "scripts" folder. Configurable options are located in the adjacent .env file, such as DB connection, NLP model parameters and OMOP fallback concepts.

```bash
uv run scripts/run_pipeline.py
```
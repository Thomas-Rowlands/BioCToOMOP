# BioC-To-OMOP
This repository contains the Python pipeline used to annotate BioC publications, including supplementary material, and import them into OMOP CDM using in-built ETL rules.

## Installation
The UV Python package manager was used for this project, utilising a pyproject.toml file that can be used to install dependencies.
```
# install package dependencies
uv sync
```

## Usage
The main entry point for executing the pipeline is the run_python.py script located in the "scripts" folder. Configurable options are located in the adjacent .env file, such as DB connection, NLP model parameters and OMOP fallback concepts.
```
python scripts/run_pipeline.py
```
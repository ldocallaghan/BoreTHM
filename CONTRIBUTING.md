# Contributing to BoreTHM

Report a problem through [GitHub issues](https://github.com/ldocallaghan/BoreTHM/issues). Include the command or a small Python example, the BoreTHM and Python versions, and the complete output or traceback. Describe what you expected and what happened. Remove private site data before posting.

For changes beyond a fix, open an issue to discuss the scope before starting work. Explain the use case and the evidence needed to assess the change.

## Development setup

Clone the repository and create an environment as described in the [README](README.md#reproduce-the-reference-calculations). Use Python 3.14.4 and install the locked dependencies, then the editable package:

```sh
python -m pip install -r requirements-lock.txt
python -m pip install --no-deps -e .
python -m pytest
```

The default test run excludes the physical regressions marked `slow`. Build the water-property cache before running those:

```sh
borethm-water-table
python -m pytest -m slow
```

Set `OPENBLAS_NUM_THREADS=1`, `OMP_NUM_THREADS=1` and `MKL_NUM_THREADS=1` before starting Python. Run tests in one process. Slow regressions can take several hours. The [release checklist](docs/maintenance/release-checklist.md) records release validation.

## Changes and review

Describe the problem and how you checked the change in the pull request. Results in `results/` and goldens in `tests/golden/` change only with a documented reason and review of the numerical differences. A failing regression needs investigation before updating its expected values.

After changing public docstrings, regenerate the [API page](docs/api.md) with `python tools/build_api_docs.py`. Check documentation links with `python tools/check_links.py`.

Code contributions are under [Apache 2.0](LICENSE); documentation contributions are under [CC BY 4.0](LICENSE-docs). Third-party data retain their source licences and attribution. Include sources for new data and scientific inputs.

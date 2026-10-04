# DLVS-Wave v2 forecast pipeline

Maintained forecast code lives in `src/`. Start with the
[English operator guide](docs/FORECAST_PIPELINE_GUIDE.md) and the
[implementation audit](docs/FORECAST_RULES_AUDIT.md).

```bash
bash commands/forecast.sh --help
bash commands/forecast.sh check --config configs/world_nested_production.json
bash commands/forecast.sh run --config configs/region_single_example.json --label region
```

Use `configs/region_nested_example.json` for a regional recursive study or
`configs/world_nested_production.json` for worldwide L0-L4. Example dates are
fixed and must be changed explicitly for a new forecast issue.

Install `requirements-forecast.txt` in the repository's `.venv`, or select an
interpreter with `DLVS_PYTHON`. Execution requires raw inputs or access to USGS
and JPL. Study outputs are written under `studies_output/` and excluded from Git.

The World energy engine and separate causal Japan energy engine have different
training/refit/infill/bitwise contracts. The guide and audit identify those
differences explicitly; a standalone launcher does not make them equivalent.

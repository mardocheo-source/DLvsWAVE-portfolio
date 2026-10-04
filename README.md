# DLvsWAVE — Fixed Feature Banks and Scientific Data Pipelines

**Experimental research software and technical portfolio. Not intended for real-world deployment or operational earthquake forecasting.**

This Python project compares **fixed feature banks with learned readouts** against **end-to-end neural networks**, and applies related tooling to exploratory scientific time-series workflows. It shows the complete software path from acquiring and treating scientific data to organising model comparisons and auditing their outputs.

## What I contributed

My contribution represented in this repository is the integration of scientific-data acquisition, preprocessing, model-comparison tooling and research workflows:

- A command-line benchmark with synthetic tasks, configurable representations/readouts, neural presets, seed controls and persisted experiment metrics.
- USGS earthquake-catalog and NASA/JPL Horizons acquisition, with request/caching contracts and processing of timestamps, coordinates and numeric fields.
- Multi-stage exploratory time-series pipelines, candidate comparisons, report generation and temporal/source-integrity audit code.

These are software and research-engineering contributions. They do not establish a new physical earthquake mechanism or an operational prediction system.

## Start here: representative code

| Capability | Files to inspect |
| --- | --- |
| Fixed representations and model comparison | [feature_banks.py](feature_banks.py), [benchmark.py](benchmark.py), [deep_nets.py](deep_nets.py) |
| CLI and synthetic data | [cli.py](cli.py), [tasks.py](tasks.py) |
| Scientific acquisition and receipts | [production_inputs.py](DLVS-Wave-v2/src/production_inputs.py), [Horizons fetcher](DLVS-Wave-v2/src/horizons.py) |
| Cleaning, extraction and alignment | [event extraction](extract_earthquake_events.py), [daily aggregation](aggregate_nasadb_daily_master.py), [JPL alignment](research_pipeline/scientific/derive_aligned_jpl_master.py) |
| Forecast pipeline structure and audits | [operator guide](DLVS-Wave-v2/docs/FORECAST_PIPELINE_GUIDE.md), [rules audit](DLVS-Wave-v2/docs/FORECAST_RULES_AUDIT.md), [temporal availability audit](DLVS-Wave-v2/src/audit_energy_temporal_availability.py) |
| Example results and their scope | [verified synthetic summary](docs/portfolio-smoke-results.json), [historical results](docs/PORTFOLIO_HISTORICAL_RESULTS.md) |

## Sources, acquisition and treatment

The maintained acquisition code requests earthquake catalogs through the **USGS FDSN Event API** and ephemerides through **NASA/JPL Horizons** via Astroquery. Catalog requests are divided into bounded time slices; the code checks response caps and stores URLs, acquisition timestamps, row counts and SHA256 receipts. Horizons acquisition specifies bodies, epochs and observer coordinates, with pacing/retry and cached-input checks.

Processing includes parsing and normalising timestamps, converting numeric fields, handling missing values, deduplicating event IDs, normalising longitude and aligning event/ephemeris tables. The catalog loader creates weekly date buckets; other scripts provide daily aggregation and compact event extraction. These are different transformations for different workflows, not one universally validated preprocessing recipe.

[Data sources, acquisition files, attribution and exclusions](docs/PORTFOLIO_DATA_SOURCES.md) document the exact scope. Real scientific datasets, cached downloads, model packages and historical experiment databases are not bundled in this portfolio edition. Acquisition code remains available to demonstrate the work.

## Fixed feature banks versus deep learning

```text
Fixed representation:  x → φ(x) → trained readout → y
End-to-end model:      x → learned neural layers → y
```

Feature banks include Chebyshev polynomials, random/prime Fourier features, Morlet wavelets, random projection and passthrough. The fixed representation is not learned end to end, although preprocessing can be fitted from training data: for example, ChebyshevBank stores training-set feature ranges. Readouts include Ridge and other configured estimators. DeepNet learns neural layers through PyTorch.

The benchmark records test error, parameter counts and additional diagnostic metrics. Comparisons depend on data, feature settings, optimisation budget and hardware; this portfolio does not claim that either model family always wins. CSV/time-series workflows have separate controls and are not validated by the synthetic example.

## Installation

The checked example ran on Python **3.12.3**, NumPy **2.3.5**, SciPy **1.17.1**, scikit-learn **1.8.0** and PyTorch **2.11.0**, using CPU. From the repository root:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install 'torch==2.11.0' --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements.txt
```

The root requirements contain lower bounds rather than a complete environment lock; exact metrics can vary with installed versions. The execution command was verified in the existing runtime with the versions above, not in a newly provisioned environment. Advanced acquisition/forecast modules have additional dependencies listed in [requirements-forecast.txt](DLVS-Wave-v2/requirements-forecast.txt), and require separately provisioned inputs. GPU/XPU installation and extended workflows were not exercised in this preparation. Some legacy tests and replay commands assume archived study files or separately provisioned inputs; the complete legacy test suite is not certified for this stripped-data edition. The synthetic command below is the checked entry point.

## One quick, verified example

This reproduces an existing `friedman1` synthetic benchmark path with a deliberately small CPU budget:

```bash
mkdir -p outputs
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
python cli.py train --task friedman1 \
  --banks chebyshev --readouts ridge --deep-presets small \
  --deep-device cpu --seeds 1 --n-train 128 --n-test 128 \
  --max-iter 10 --jobs 1 --db outputs/portfolio-smoke.db
```

Checked successfully in approximately **25 seconds**. `--seeds 1` selects one seed (0), and the noise setting was the default 0. No scientific-data download or private input is needed. The database is a generated local output and is ignored by Git.

| Verified execution | Test MSE | Parameters |
| --- | ---: | ---: |
| Chebyshev + Ridge | 2.487930 | 46 |
| DeepNet small | 19.021879 | 737 |

The CLI also emits an automatically derived inverted-prediction diagnostic; it is recorded separately in the [machine-readable summary](docs/portfolio-smoke-results.json), not treated as another independently trained model. Ten neural epochs and one seed make this an **execution smoke check**, not a tuned or statistically conclusive comparison. Hardware-sensitive inference timings are deliberately omitted from the table.

## Existing results: verified versus historical

- **Verified here:** the single small synthetic command above, including its recorded test metrics and parameter counts.
- **Historical:** previous README values for a 500-sample, three-seed `friedman1` comparison are preserved in [historical results](docs/PORTFOLIO_HISTORICAL_RESULTS.md). Those runs were not repeated, and their original databases/models remain private. They must not be compared directly with the 128-sample smoke check.
- **Exploratory scientific workflows:** existing seismic pipeline and audit code is provided for inspection. No new seismic training, full replay or operational validation was performed for this portfolio preparation.

## Limits, especially seismic forecasting

Earthquakes are rare events; retrospective pattern fitting, selected event windows, multiple model searches, spatial aggregation and catalog revisions can produce misleading apparent skill. A high internal score is not a calibrated probability, an alarm threshold or proof of forecasting ability. Astronomical covariates are exploratory and do not establish causal earthquake mechanisms.

The code contains chronological/cutoff and temporal-availability checks, but their presence does not certify every historical run. In particular, the catalog loader identifies a later-retrieved historical catalog filtered by occurrence time, **not an archived as-of publication snapshot**. Out-of-time and out-of-region evaluation, selection bias, leakage and calibration remain important unresolved interpretation limits. Internal module names containing “production” describe pipeline organisation; they do not imply deployment validation.

**Do not use these outputs for public warnings, emergency response, safety decisions or operational earthquake predictions.**

## Attribution, reuse and citation

[Attribution and reuse](docs/PORTFOLIO_REUSE.md) explain that the original tree has no repository-wide software license; this preparation does not assign one to project or third-party content. Data-source rights are separate, and unverified redistribution assets are excluded.

Prepared citation template for the intended GitHub destination (repository creation/upload is pending explicit approval; this URL is not yet available):

> mardocheo-source. *DLvsWAVE — Fixed Feature Banks and Scientific Data Pipelines*. GitHub. Version `portfolio-2026-10-04`. https://github.com/mardocheo-source/DLvsWAVE-portfolio/tree/portfolio-2026-10-04

The local version tag identifies this prepared source snapshot. Once the private repository and tag are uploaded, the reference above becomes usable; until then, do not cite the intended URL in applications. This is not a DOI or a claim of peer-reviewed publication.

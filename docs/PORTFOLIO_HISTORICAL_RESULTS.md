# Historical results retained for context

The following section is transcribed from the original README in the source checkout at `e2d5cb4d008dc20bde92a19ce04183ba0fa3364e`. It documents previously reported work; the underlying historical runs were not re-executed in this preparation and the numbers are not independently verified here. Original databases, models and private research outputs remain in the private archive.

The newly checked small synthetic execution is documented separately in `portfolio-smoke-results.json`. Different sample sizes and training budgets make the two sets of numbers incomparable.

### Previously reported benchmark results

The following values were recorded in the earlier README for `friedman1`, with 500 samples and three seeds. They are historical example results, not a newly reproduced benchmark.

| Model | MSE | Parameters | Inference (μs) |
| --- | --- | --- | --- |
| Chebyshev + Ridge | **1.83** | **46** | 0.3 |
| Random Fourier + Ridge | 2.63 | 65 | 0.2 |
| Morlet + Ridge | 2.20 | 161 | 0.7 |
| DeepNet small | 6.27 | 737 | 1.0 |
| DeepNet default | 6.19 | 865 | 1.8 |
| DeepNet deep | 5.85 | 27,649 | 3.3 |

In this example, Chebyshev + Ridge has approximately 3.2× lower MSE and 600× fewer parameters than DeepNet deep. This result is specific to the dataset, training budget, and configuration. A 500-sample setting favors sample-efficient methods; larger training sets, such as `--n-train 5000` to `50000`, may change the comparison. Inference timings also depend on hardware and measurement conditions.


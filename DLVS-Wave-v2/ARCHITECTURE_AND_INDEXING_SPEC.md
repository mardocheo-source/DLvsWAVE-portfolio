# DLVS-Wave v2.0 - Architecture, Historical Indexing & Anti-Data-Leakage Specification

This document details the architectural specifications for **Historical & Future Indexing**, **Anti-Data-Leakage Protocols**, **Isolated Bit-Packing Partitioning**, and **Resampling Safety Locks** in the DLVS-Wave v2.0 framework.

---

## 1. Shifted Historical & Future Indexing System

### 1.1 Concept & Naming Convention
A master record at date $T$ is augmented with horizontal "twin" features shifted across time offsets $\Delta t$:
$$\text{Feature}(T, \Delta t) = \text{Feature}(T + \Delta t)$$

Canonical hierarchical naming standard:
`[prefisso]_[corpo/gruppo]_[metrica]_[aggregazione]_shift_[direzione][valore][unita]`

* **Direction Markers**:
  - `m`: Minus / Past (Lag, e.g., $\Delta t = -7\text{ days} \rightarrow \text{_shift_m7d}$)
  - `p`: Plus / Future (Lead, e.g., $\Delta t = +14\text{ days} \rightarrow \text{_shift_p14d}$)
* **Examples**:
  - `astro_moon_dist_shift_m7d`: Distance to Moon 7 days prior to current record.
  - `astro_sun_dec_shift_p14d`: Declination of Sun 14 days into the future.
  - `seis_core_magnitude_shift_m30d`: Maximum earthquake magnitude recorded 30 days prior.

---

## 2. Strict Causal Anti-Data-Leakage Protocol

```
┌────────────────────────────────────────────────────────────────────────┐
│                   CAUSAL ANTI-DATA-LEAKAGE BOUNDARY                    │
├──────────────────────────────┬─────────────────────────────────────────┤
│ CELESTIAL EPHEMERIDES (Astro)│ SEISMIC EVENTS (USGS)                   │
├──────────────────────────────┼─────────────────────────────────────────┤
│ • Past Shifts (-N days): OK  │ • Past Shifts (-N days): OK (Lag Feats) │
│ • Future Shifts (+N days): OK│ • Future Shifts (+N days): STRICT LOCK! │
│ (Orbits are deterministic    │ (Future seismic data must NEVER be      │
│ and known indefinitely)      │  used in predictive feature sets)       │
└──────────────────────────────┴─────────────────────────────────────────┘
```

1. **Astro Shifts**:
   - Ephemerides are deterministic and calculated forward in time. Both past ($-\Delta t$) and future ($+\Delta t$) shifts are strictly valid for feature engineering.
2. **Seismic Shifts**:
   - **Predictive Rule**: For any training, feature selection, or forecasting, **only past seismic shifts ($-\Delta t$) are allowed**.
   - **Target / Ground Truth**: Future seismic occurrences ($+\Delta t$) are exclusively generated as target labels or retroactive evaluation criteria, explicitly quarantined from feature sets.
3. **Audit Manifest (`master_anti_leakage_audit.md`)**:
   - Every generated master produces an audit log detailing every shift direction, step size, and an explicit compliance check confirming zero future seismic leakage in feature matrices.

---

## 3. Strict Bit-Packing Isolation by Family

To ensure feature selection algorithms (e.g. Optuna) and machine learning models can cleanly discriminate individual parameter groups without cross-family pollution:

1. **Untouched Seismic Core**:
   - `date`, `time`, `seis_core_id`, `seis_core_latitude`, `seis_core_longitude`, `seis_core_depth`, `seis_core_magnitude` remain in original raw uncompressed format (`float64`, `int64`, `str`).
2. **Isolated Astro Bitfield Containers (`packed_astro_container_*`)**:
   - Astro features (base ephemerides + past/future astro shifts) are discretized into 2-bit quantiles ($q_0, q_1, q_2, q_3$) and packed 8-at-a-time into `uint16` containers.
   - **Zero Seismic Contamination**: Under no circumstance may a seismic field be packed into an astro container.
3. **Dedicated Seismic Lag Containers (`packed_seis_lag_container_*`)**:
   - Historical seismic lag features, if compressed, are packed exclusively into separate, dedicated containers.

---

## 4. Resampling Safety Lock & Scale Inheritance

### 4.1 Safety Lock
* **Rule**: It is **strictly prohibited to resample or vertically aggregate an already bit-packed dataset**.
* **Enforcement**: The temporal summarizer will inspect column headers. If any `packed_*` columns are detected, it throws:
  `ValueError("Cannot resample a bit-packed dataset. Resampling must be executed strictly on the uncompressed raw master!")`

### 4.2 Configuration Schema (`master_schema_config.json`)
The configuration of all shifts and features is stored in a structured JSON schema:
```json
{
  "temporal_resolution": "1d",
  "shift_parameters": {
    "astro": {
      "min_step": -5,
      "max_step": 5,
      "step_days": 7,
      "generated_shifts": [-35, -28, -21, -14, -7, 7, 14, 21, 28, 35]
    },
    "seismic": {
      "min_step": -5,
      "max_step": 0,
      "step_days": 7,
      "generated_shifts": [-35, -28, -21, -14, -7]
    }
  },
  "safety_lock": {
    "allow_future_seismic": false,
    "leakage_warning_emitted": false
  }
}
```

When reserializing or aggregating at a new window resolution (e.g. 7-day, 14-day, or 30-day windows), the pipeline loads this schema to **dynamically recalculate the shifted historical indices directly on the new temporal scale**, preserving feature richness across any temporal resolution.

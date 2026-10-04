# DLVS-Wave v2.0 Master Manifest & Decodification Report: Master 1D

> **Generated at**: `2026-08-27 14:11:36 UTC`  
> **Chronological Timeline**: `2024-01-01` to `2024-05-01` (`122` time steps)

## 1. Dataset Dimensions & Compression Summary

| Dimension | Raw Uncompressed | Quantized Bit-Packed (2-Bit / 16-Bit) | Reduction Ratio |
| :--- | :--- | :--- | :--- |
| **Feature Columns** | `1115` columns | `153` columns | **7.97x fewer fields** |
| **Record Count** | `122` rows | `122` rows | 1:1 Synchronized |
| **Storage Size** | `1,176,165 bytes` | `107,462 bytes` | **90.86% space saved** |
| **Container Type** | `Float64` | `uint16` (`2` bits/field, `4` quantiles) | Compact Binary |

## 2. Preserved Seismic Features (In Chiaro / Uncompressed)

All seismic parameters (core 3D coordinates + magnitude and historical lag shifts) are preserved uncompressed as leading columns immediately following `date` for instant inspection:

- **`seis_core_magnitude`**
- **`seis_core_latitude`**
- **`seis_core_longitude`**
- **`seis_core_depth`**
- **`seis_core_magnitude_shift_m35d`**
- **`seis_core_depth_shift_m35d`**
- **`seis_core_magnitude_shift_m28d`**
- **`seis_core_depth_shift_m28d`**
- **`seis_core_magnitude_shift_m21d`**
- **`seis_core_depth_shift_m21d`**
- **`seis_core_magnitude_shift_m14d`**
- **`seis_core_depth_shift_m14d`**
- **`seis_core_magnitude_shift_m7d`**
- **`seis_core_depth_shift_m7d`**

## 3. Tracked Astronomical Bodies & Feature Groups Catalog

| Prefix / Body Group | Fields Count | Sample Features Included |
| :--- | :--- | :--- |
| **`astro_jupiter`** | 165 | `icrf`, `icrf`, `app`, `app`, ... (+161 more) |
| **`astro_mars`** | 165 | `icrf`, `icrf`, `app`, `app`, ... (+161 more) |
| **`astro_mercury`** | 165 | `icrf`, `icrf`, `app`, `app`, ... (+161 more) |
| **`astro_moon`** | 165 | `icrf`, `icrf`, `app`, `app`, ... (+161 more) |
| **`astro_saturn`** | 165 | `icrf`, `icrf`, `app`, `app`, ... (+161 more) |
| **`astro_sun`** | 110 | `icrf`, `icrf`, `app`, `app`, ... (+106 more) |
| **`astro_venus`** | 165 | `icrf`, `icrf`, `app`, `app`, ... (+161 more) |

## 4. Container Decodification Matrix & Quantile Codebook

This matrix allows 100% exact decompression of packed integer fields into their discrete quantile bins `[0, 1, 2, 3]`.

### Container: `packed_astro_container_000` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_ra_icrf` | `28.217` | `300.68` | `331.36` |
| `Bits 2-3` | `>> 2` | `astro_sun_dec_icrf` | `-17.603` | `-7.4188` | `4.4185` |
| `Bits 4-5` | `>> 4` | `astro_sun_ra_app` | `28.534` | `301.03` | `331.68` |
| `Bits 6-7` | `>> 6` | `astro_sun_dec_app` | `-17.515` | `-7.2938` | `4.5489` |
| `Bits 8-9` | `>> 8` | `astro_sun_azim` | `124.01` | `131.05` | `137.32` |
| `Bits 10-11` | `>> 10` | `astro_sun_elev` | `21.725` | `30.259` | `40.842` |
| `Bits 12-13` | `>> 12` | `astro_sun_app_mag` | `-26.775` | `-26.762` | `-26.744` |
| `Bits 14-15` | `>> 14` | `astro_sun_dist` | `0.98511` | `0.99093` | `0.99914` |

### Container: `packed_astro_container_001` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_dist_rate` | `0.010555` | `0.1954` | `0.24971` |
| `Bits 2-3` | `>> 2` | `astro_sun_illum_frac` | `20.217` | `58.052` | `86.48` |
| `Bits 4-5` | `>> 4` | `astro_moon_ra_icrf` | `105.76` | `185.14` | `260.05` |
| `Bits 6-7` | `>> 6` | `astro_moon_dec_icrf` | `-21.655` | `-2.4566` | `17.65` |
| `Bits 8-9` | `>> 8` | `astro_moon_ra_app` | `106.14` | `185.45` | `260.43` |
| `Bits 10-11` | `>> 10` | `astro_moon_dec_app` | `-21.606` | `-2.4578` | `17.698` |
| `Bits 12-13` | `>> 12` | `astro_moon_azim` | `85.425` | `196.34` | `265.08` |
| `Bits 14-15` | `>> 14` | `astro_moon_elev` | `-22.724` | `-2.6985` | `18.337` |

### Container: `packed_astro_container_002` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_app_mag` | `-11.544` | `-10.429` | `-8.5288` |
| `Bits 2-3` | `>> 2` | `astro_moon_surf_bright` | `4.3143` | `4.9805` | `5.747` |
| `Bits 4-5` | `>> 4` | `astro_moon_dist` | `0.0024678` | `0.0026026` | `0.002695` |
| `Bits 6-7` | `>> 6` | `astro_moon_dist_rate` | `-0.18727` | `0.021597` | `0.22057` |
| `Bits 8-9` | `>> 8` | `astro_moon_helio_dist` | `0.98549` | `0.99143` | `0.99956` |
| `Bits 10-11` | `>> 10` | `astro_moon_helio_dist_rate` | `-0.338` | `0.3245` | `0.96295` |
| `Bits 12-13` | `>> 12` | `astro_moon_phase_angle` | `43.142` | `80.731` | `126.56` |
| `Bits 14-15` | `>> 14` | `astro_moon_elong` | `53.33` | `99.12` | `136.75` |

### Container: `packed_astro_container_003` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_illum_frac` | `20.217` | `58.052` | `86.48` |
| `Bits 2-3` | `>> 2` | `astro_mars_ra_icrf` | `290.65` | `314.97` | `337.96` |
| `Bits 4-5` | `>> 4` | `astro_mars_dec_icrf` | `-22.81` | `-17.942` | `-10.267` |
| `Bits 6-7` | `>> 6` | `astro_mars_ra_app` | `290.19` | `314.52` | `337.54` |
| `Bits 8-9` | `>> 8` | `astro_mars_dec_app` | `-22.764` | `-17.848` | `-10.144` |
| `Bits 10-11` | `>> 10` | `astro_mars_azim` | `159.65` | `163.93` | `170.37` |
| `Bits 12-13` | `>> 12` | `astro_mars_elev` | `25.733` | `31.835` | `40.62` |
| `Bits 14-15` | `>> 14` | `astro_mars_app_mag` | `1.1833` | `1.2635` | `1.3075` |

### Container: `packed_astro_container_004` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_surf_bright` | `4.0553` | `4.096` | `4.125` |
| `Bits 2-3` | `>> 2` | `astro_mars_dist` | `2.0913` | `2.2079` | `2.3218` |
| `Bits 4-5` | `>> 4` | `astro_mars_dist_rate` | `-6.7116` | `-6.615` | `-6.3895` |
| `Bits 6-7` | `>> 6` | `astro_mars_helio_dist` | `1.3916` | `1.4131` | `1.4439` |
| `Bits 8-9` | `>> 8` | `astro_mars_helio_dist_rate` | `-1.9663` | `-1.5261` | `-0.91255` |
| `Bits 10-11` | `>> 10` | `astro_mars_phase_angle` | `14.021` | `19.291` | `24.132` |
| `Bits 12-13` | `>> 12` | `astro_mars_elong` | `20.8` | `28.106` | `34.709` |
| `Bits 14-15` | `>> 14` | `astro_mars_illum_frac` | `20.217` | `58.052` | `86.48` |

### Container: `packed_astro_container_005` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_ra_icrf` | `34.881` | `38.933` | `44.745` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_dec_icrf` | `12.826` | `14.278` | `16.113` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_ra_app` | `35.206` | `39.26` | `45.077` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_dec_app` | `12.937` | `14.382` | `16.209` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_azim` | `58.02` | `74.153` | `87.092` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_elev` | `-16.051` | `3.2775` | `22.811` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_app_mag` | `-2.3533` | `-2.1755` | `-2.0635` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_surf_bright` | `5.3342` | `5.3575` | `5.368` |

### Container: `packed_astro_container_006` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_dist` | `4.9556` | `5.4184` | `5.7802` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_dist_rate` | `16.323` | `23.928` | `26.798` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_helio_dist` | `4.9909` | `4.9973` | `5.0041` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_helio_dist_rate` | `0.3553` | `0.37993` | `0.40356` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_phase_angle` | `6.7091` | `9.8892` | `11.037` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_elong` | `35.802` | `60.013` | `86.368` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_illum_frac` | `20.217` | `58.052` | `86.48` |
| `Bits 14-15` | `>> 14` | `astro_saturn_ra_icrf` | `338.41` | `341.82` | `345.2` |

### Container: `packed_astro_container_007` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_dec_icrf` | `-10.799` | `-9.455` | `-8.1257` |
| `Bits 2-3` | `>> 2` | `astro_saturn_ra_app` | `338.72` | `342.13` | `345.51` |
| `Bits 4-5` | `>> 4` | `astro_saturn_dec_app` | `-10.678` | `-9.3306` | `-7.9982` |
| `Bits 6-7` | `>> 6` | `astro_saturn_azim` | `113.22` | `133.07` | `161.47` |
| `Bits 8-9` | `>> 8` | `astro_saturn_elev` | `10.75` | `29.014` | `41.494` |
| `Bits 10-11` | `>> 10` | `astro_saturn_app_mag` | `0.98025` | `0.991` | `1.0555` |
| `Bits 12-13` | `>> 12` | `astro_saturn_surf_bright` | `6.6913` | `6.717` | `6.7722` |
| `Bits 14-15` | `>> 14` | `astro_saturn_dist` | `10.454` | `10.594` | `10.681` |

### Container: `packed_astro_container_008` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_dist_rate` | `-13.638` | `-1.0169` | `11.997` |
| `Bits 2-3` | `>> 2` | `astro_saturn_helio_dist` | `9.7119` | `9.7206` | `9.7293` |
| `Bits 4-5` | `>> 4` | `astro_saturn_helio_dist_rate` | `-0.49952` | `-0.49626` | `-0.49286` |
| `Bits 6-7` | `>> 6` | `astro_saturn_phase_angle` | `1.3722` | `2.6561` | `3.8076` |
| `Bits 8-9` | `>> 8` | `astro_saturn_elong` | `13.58` | `27.008` | `40.404` |
| `Bits 10-11` | `>> 10` | `astro_saturn_illum_frac` | `20.217` | `58.052` | `86.48` |
| `Bits 12-13` | `>> 12` | `astro_mercury_ra_icrf` | `18.658` | `264.9` | `307.98` |
| `Bits 14-15` | `>> 14` | `astro_mercury_dec_icrf` | `-20.978` | `-8.2307` | `7.1979` |

### Container: `packed_astro_container_009` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mercury_ra_app` | `18.969` | `265.25` | `308.32` |
| `Bits 2-3` | `>> 2` | `astro_mercury_dec_app` | `-20.987` | `-8.1041` | `7.3266` |
| `Bits 4-5` | `>> 4` | `astro_mercury_azim` | `117.27` | `140.58` | `156.96` |
| `Bits 6-7` | `>> 6` | `astro_mercury_elev` | `26.37` | `28.729` | `37.491` |
| `Bits 8-9` | `>> 8` | `astro_mercury_app_mag` | `-0.8365` | `-0.256` | `1.01` |
| `Bits 10-11` | `>> 10` | `astro_mercury_surf_bright` | `2.356` | `3.0005` | `3.9118` |
| `Bits 12-13` | `>> 12` | `astro_mercury_dist` | `0.73127` | `1.0879` | `1.3166` |
| `Bits 14-15` | `>> 14` | `astro_mercury_dist_rate` | `-22.785` | `4.0088` | `19.992` |

### Container: `packed_astro_container_010` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mercury_helio_dist` | `0.35669` | `0.41338` | `0.45325` |
| `Bits 2-3` | `>> 2` | `astro_mercury_helio_dist_rate` | `-4.3038` | `3.2116` | `8.2808` |
| `Bits 4-5` | `>> 4` | `astro_mercury_phase_angle` | `31.495` | `64.725` | `121.67` |
| `Bits 6-7` | `>> 6` | `astro_mercury_elong` | `8.7512` | `15.696` | `19.961` |
| `Bits 8-9` | `>> 8` | `astro_mercury_illum_frac` | `20.217` | `58.052` | `86.48` |
| `Bits 10-11` | `>> 10` | `astro_venus_ra_icrf` | `244.71` | `284.49` | `323.48` |
| `Bits 12-13` | `>> 12` | `astro_venus_dec_icrf` | `-21.203` | `-16.495` | `-3.6454` |
| `Bits 14-15` | `>> 14` | `astro_venus_ra_app` | `245.05` | `284.85` | `323.8` |

### Container: `packed_astro_container_011` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_dec_app` | `-21.171` | `-16.396` | `-3.5137` |
| `Bits 2-3` | `>> 2` | `astro_venus_azim` | `146.75` | `159.45` | `171.02` |
| `Bits 4-5` | `>> 4` | `astro_venus_elev` | `29.426` | `32.464` | `42.292` |
| `Bits 6-7` | `>> 6` | `astro_venus_app_mag` | `-3.9453` | `-3.8925` | `-3.879` |
| `Bits 8-9` | `>> 8` | `astro_venus_surf_bright` | `0.8775` | `0.971` | `1.0702` |
| `Bits 10-11` | `>> 10` | `astro_venus_dist` | `1.3583` | `1.5059` | `1.6219` |
| `Bits 12-13` | `>> 12` | `astro_venus_dist_rate` | `5.5133` | `7.4854` | `9.2542` |
| `Bits 14-15` | `>> 14` | `astro_venus_helio_dist` | `0.72438` | `0.72656` | `0.72778` |

### Container: `packed_astro_container_012` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_helio_dist_rate` | `-0.075854` | `0.11508` | `0.21465` |
| `Bits 2-3` | `>> 2` | `astro_venus_phase_angle` | `23.698` | `34.075` | `44.682` |
| `Bits 4-5` | `>> 4` | `astro_venus_elong` | `17.026` | `24.29` | `31.133` |
| `Bits 6-7` | `>> 6` | `astro_venus_illum_frac` | `20.217` | `58.052` | `86.48` |
| `Bits 8-9` | `>> 8` | `astro_sun_ra_icrf_shift_m35d` | `296.4` | `318.8` | `339.71` |
| `Bits 10-11` | `>> 10` | `astro_sun_dec_icrf_shift_m35d` | `-19.799` | `-13.709` | `-5.883` |
| `Bits 12-13` | `>> 12` | `astro_sun_ra_app_shift_m35d` | `296.75` | `319.13` | `340.02` |
| `Bits 14-15` | `>> 14` | `astro_sun_dec_app_shift_m35d` | `-19.727` | `-13.602` | `-5.7555` |

### Container: `packed_astro_container_013` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_azim_shift_m35d` | `130.18` | `134.73` | `139.02` |
| `Bits 2-3` | `>> 2` | `astro_sun_elev_shift_m35d` | `20.118` | `24.841` | `31.621` |
| `Bits 4-5` | `>> 4` | `astro_sun_app_mag_shift_m35d` | `-26.777` | `-26.77` | `-26.76` |
| `Bits 6-7` | `>> 6` | `astro_sun_dist_shift_m35d` | `0.98412` | `0.98718` | `0.99195` |
| `Bits 8-9` | `>> 8` | `astro_sun_dist_rate_shift_m35d` | `-0.071703` | `0.08048` | `0.21328` |
| `Bits 10-11` | `>> 10` | `astro_sun_illum_frac_shift_m35d` | `17.846` | `54.473` | `85.652` |
| `Bits 12-13` | `>> 12` | `astro_moon_ra_icrf_shift_m35d` | `100.3` | `176.1` | `249.72` |
| `Bits 14-15` | `>> 14` | `astro_moon_dec_icrf_shift_m35d` | `-18.113` | `0.98323` | `18.694` |

### Container: `packed_astro_container_014` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_ra_app_shift_m35d` | `100.68` | `176.41` | `250.08` |
| `Bits 2-3` | `>> 2` | `astro_moon_dec_app_shift_m35d` | `-18.219` | `1.1146` | `18.588` |
| `Bits 4-5` | `>> 4` | `astro_moon_azim_shift_m35d` | `87.558` | `190.58` | `274.3` |
| `Bits 6-7` | `>> 6` | `astro_moon_elev_shift_m35d` | `-20.546` | `-1.6464` | `17.815` |
| `Bits 8-9` | `>> 8` | `astro_moon_app_mag_shift_m35d` | `-11.497` | `-10.334` | `-8.3295` |
| `Bits 10-11` | `>> 10` | `astro_moon_surf_bright_shift_m35d` | `4.3445` | `5.049` | `5.7615` |
| `Bits 12-13` | `>> 12` | `astro_moon_dist_shift_m35d` | `0.002463` | `0.0026038` | `0.0026955` |
| `Bits 14-15` | `>> 14` | `astro_moon_dist_rate_shift_m35d` | `-0.20649` | `0.011808` | `0.21954` |

### Container: `packed_astro_container_015` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_helio_dist_shift_m35d` | `0.98444` | `0.98715` | `0.99198` |
| `Bits 2-3` | `>> 2` | `astro_moon_helio_dist_rate_shift_m35d` | `-0.36663` | `0.3406` | `0.9608` |
| `Bits 4-5` | `>> 4` | `astro_moon_phase_angle_shift_m35d` | `44.498` | `84.867` | `130.03` |
| `Bits 6-7` | `>> 6` | `astro_moon_elong_shift_m35d` | `49.859` | `94.984` | `135.39` |
| `Bits 8-9` | `>> 8` | `astro_moon_illum_frac_shift_m35d` | `17.846` | `54.473` | `85.652` |
| `Bits 10-11` | `>> 10` | `astro_mars_ra_icrf_shift_m35d` | `284.3` | `301.84` | `318.87` |
| `Bits 12-13` | `>> 12` | `astro_mars_dec_icrf_shift_m35d` | `-23.543` | `-21.177` | `-17.06` |
| `Bits 14-15` | `>> 14` | `astro_mars_ra_app_shift_m35d` | `284.65` | `302.19` | `319.2` |

### Container: `packed_astro_container_016` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_dec_app_shift_m35d` | `-23.513` | `-21.109` | `-16.962` |
| `Bits 2-3` | `>> 2` | `astro_mars_azim_shift_m35d` | `158.5` | `161.33` | `164.61` |
| `Bits 4-5` | `>> 4` | `astro_mars_elev_shift_m35d` | `24.615` | `27.895` | `32.875` |
| `Bits 6-7` | `>> 6` | `astro_mars_app_mag_shift_m35d` | `1.2575` | `1.29` | `1.325` |
| `Bits 8-9` | `>> 8` | `astro_mars_surf_bright_shift_m35d` | `4.0555` | `4.094` | `4.1115` |
| `Bits 10-11` | `>> 10` | `astro_mars_dist_shift_m35d` | `2.1925` | `2.2746` | `2.353` |
| `Bits 12-13` | `>> 12` | `astro_mars_dist_rate_shift_m35d` | `-6.7328` | `-6.6279` | `-6.1897` |
| `Bits 14-15` | `>> 14` | `astro_mars_helio_dist_shift_m35d` | `1.4097` | `1.43` | `1.4541` |

### Container: `packed_astro_container_017` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_helio_dist_rate_shift_m35d` | `-2.0569` | `-1.8043` | `-1.4539` |
| `Bits 2-3` | `>> 2` | `astro_mars_phase_angle_shift_m35d` | `12.431` | `16.29` | `19.957` |
| `Bits 4-5` | `>> 4` | `astro_mars_elong_shift_m35d` | `18.546` | `23.974` | `29.016` |
| `Bits 6-7` | `>> 6` | `astro_mars_illum_frac_shift_m35d` | `17.846` | `54.473` | `85.652` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_ra_icrf_shift_m35d` | `34.15` | `36.324` | `39.617` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_dec_icrf_shift_m35d` | `12.535` | `13.366` | `14.507` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_ra_app_shift_m35d` | `34.474` | `36.649` | `39.945` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_dec_app_shift_m35d` | `12.647` | `13.474` | `14.61` |

### Container: `packed_astro_container_018` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_azim_shift_m35d` | `52.082` | `65.485` | `75.962` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_elev_shift_m35d` | `-21.315` | `-8.0288` | `5.8756` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_app_mag_shift_m35d` | `-2.417` | `-2.27` | `-2.157` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_surf_bright_shift_m35d` | `5.3555` | `5.364` | `5.37` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_dist_shift_m35d` | `4.8148` | `5.1581` | `5.4735` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_dist_rate_shift_m35d` | `23.114` | `25.977` | `27.201` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_helio_dist_shift_m35d` | `4.9891` | `4.9935` | `4.9982` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_helio_dist_rate_shift_m35d` | `0.34765` | `0.36502` | `0.38329` |

### Container: `packed_astro_container_019` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_phase_angle_shift_m35d` | `9.5485` | `10.697` | `11.2` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_elong_shift_m35d` | `56.703` | `74.948` | `94.489` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_illum_frac_shift_m35d` | `17.846` | `54.473` | `85.652` |
| `Bits 6-7` | `>> 6` | `astro_saturn_ra_icrf_shift_m35d` | `337.49` | `339.82` | `342.28` |
| `Bits 8-9` | `>> 8` | `astro_saturn_dec_icrf_shift_m35d` | `-11.162` | `-10.244` | `-9.274` |
| `Bits 10-11` | `>> 10` | `astro_saturn_ra_app_shift_m35d` | `337.8` | `340.13` | `342.59` |
| `Bits 12-13` | `>> 12` | `astro_saturn_dec_app_shift_m35d` | `-11.041` | `-10.121` | `-9.149` |
| `Bits 14-15` | `>> 14` | `astro_saturn_azim_shift_m35d` | `108.37` | `120.85` | `136.24` |

### Container: `packed_astro_container_020` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_elev_shift_m35d` | `4.8907` | `18.894` | `31.097` |
| `Bits 2-3` | `>> 2` | `astro_saturn_app_mag_shift_m35d` | `0.974` | `0.987` | `0.991` |
| `Bits 4-5` | `>> 4` | `astro_saturn_surf_bright_shift_m35d` | `6.682` | `6.704` | `6.7195` |
| `Bits 6-7` | `>> 6` | `astro_saturn_dist_shift_m35d` | `10.538` | `10.651` | `10.696` |
| `Bits 8-9` | `>> 8` | `astro_saturn_dist_rate_shift_m35d` | `-2.7648` | `6.6224` | `15.424` |
| `Bits 10-11` | `>> 10` | `astro_saturn_helio_dist_shift_m35d` | `9.7195` | `9.7256` | `9.7318` |
| `Bits 12-13` | `>> 12` | `astro_saturn_helio_dist_rate_shift_m35d` | `-0.49688` | `-0.49411` | `-0.49178` |
| `Bits 14-15` | `>> 14` | `astro_saturn_phase_angle_shift_m35d` | `0.9979` | `1.9443` | `3.1996` |

### Container: `packed_astro_container_021` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_elong_shift_m35d` | `9.8385` | `19.479` | `33.468` |
| `Bits 2-3` | `>> 2` | `astro_saturn_illum_frac_shift_m35d` | `17.846` | `54.473` | `85.652` |
| `Bits 4-5` | `>> 4` | `astro_mercury_ra_icrf_shift_m35d` | `262.17` | `287.51` | `322.63` |
| `Bits 6-7` | `>> 6` | `astro_mercury_dec_icrf_shift_m35d` | `-21.902` | `-19.066` | `-4.8425` |
| `Bits 8-9` | `>> 8` | `astro_mercury_ra_app_shift_m35d` | `262.52` | `287.86` | `322.95` |
| `Bits 10-11` | `>> 10` | `astro_mercury_dec_app_shift_m35d` | `-21.872` | `-18.974` | `-4.7123` |
| `Bits 12-13` | `>> 12` | `astro_mercury_azim_shift_m35d` | `124.36` | `147.52` | `160.79` |
| `Bits 14-15` | `>> 14` | `astro_mercury_elev_shift_m35d` | `25.762` | `27.514` | `28.953` |

### Container: `packed_astro_container_022` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mercury_app_mag_shift_m35d` | `-1.1725` | `-0.486` | `-0.237` |
| `Bits 2-3` | `>> 2` | `astro_mercury_surf_bright_shift_m35d` | `2.0705` | `2.689` | `3.0615` |
| `Bits 4-5` | `>> 4` | `astro_mercury_dist_shift_m35d` | `1.0484` | `1.239` | `1.3535` |
| `Bits 6-7` | `>> 6` | `astro_mercury_dist_rate_shift_m35d` | `-20.17` | `7.0203` | `24.402` |
| `Bits 8-9` | `>> 8` | `astro_mercury_helio_dist_shift_m35d` | `0.3436` | `0.40452` | `0.44999` |
| `Bits 10-11` | `>> 10` | `astro_mercury_helio_dist_rate_shift_m35d` | `-6.8235` | `-0.13809` | `6.5724` |
| `Bits 12-13` | `>> 12` | `astro_mercury_phase_angle_shift_m35d` | `23.823` | `43.287` | `70.396` |
| `Bits 14-15` | `>> 14` | `astro_mercury_elong_shift_m35d` | `9.3678` | `16.552` | `20.669` |

### Container: `packed_astro_container_023` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mercury_illum_frac_shift_m35d` | `17.846` | `54.473` | `85.652` |
| `Bits 2-3` | `>> 2` | `astro_venus_ra_icrf_shift_m35d` | `268.49` | `297.07` | `324.4` |
| `Bits 4-5` | `>> 4` | `astro_venus_dec_icrf_shift_m35d` | `-21.825` | `-19.935` | `-15.086` |
| `Bits 6-7` | `>> 6` | `astro_venus_ra_app_shift_m35d` | `268.85` | `297.42` | `324.72` |
| `Bits 8-9` | `>> 8` | `astro_venus_dec_app_shift_m35d` | `-21.814` | `-19.979` | `-14.98` |
| `Bits 10-11` | `>> 10` | `astro_venus_azim_shift_m35d` | `157.87` | `166.23` | `174.2` |
| `Bits 12-13` | `>> 12` | `astro_venus_elev_shift_m35d` | `28.88` | `30.431` | `33.406` |
| `Bits 14-15` | `>> 14` | `astro_venus_app_mag_shift_m35d` | `-3.9675` | `-3.918` | `-3.8885` |

### Container: `packed_astro_container_024` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_surf_bright_shift_m35d` | `0.9585` | `1.028` | `1.1` |
| `Bits 2-3` | `>> 2` | `astro_venus_dist_shift_m35d` | `1.3101` | `1.4241` | `1.5231` |
| `Bits 4-5` | `>> 4` | `astro_venus_dist_rate_shift_m35d` | `7.2366` | `8.5022` | `9.7323` |
| `Bits 6-7` | `>> 6` | `astro_venus_helio_dist_shift_m35d` | `0.72319` | `0.72597` | `0.72782` |
| `Bits 8-9` | `>> 8` | `astro_venus_helio_dist_rate_shift_m35d` | `0.091608` | `0.19431` | `0.22514` |
| `Bits 10-11` | `>> 10` | `astro_venus_phase_angle_shift_m35d` | `32.703` | `40.145` | `47.883` |
| `Bits 12-13` | `>> 12` | `astro_venus_elong_shift_m35d` | `23.353` | `28.301` | `33.03` |
| `Bits 14-15` | `>> 14` | `astro_venus_illum_frac_shift_m35d` | `17.846` | `54.473` | `85.652` |

### Container: `packed_astro_container_025` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_ra_icrf_shift_m28d` | `290.72` | `315.26` | `338.05` |
| `Bits 2-3` | `>> 2` | `astro_sun_dec_icrf_shift_m28d` | `-19.395` | `-12.523` | `-3.8352` |
| `Bits 4-5` | `>> 4` | `astro_sun_ra_app_shift_m28d` | `291.07` | `315.59` | `338.37` |
| `Bits 6-7` | `>> 6` | `astro_sun_dec_app_shift_m28d` | `-19.32` | `-12.411` | `-3.7052` |
| `Bits 8-9` | `>> 8` | `astro_sun_azim_shift_m28d` | `129.02` | `134.01` | `138.69` |
| `Bits 10-11` | `>> 10` | `astro_sun_elev_shift_m28d` | `20.401` | `25.835` | `33.45` |
| `Bits 12-13` | `>> 12` | `astro_sun_app_mag_shift_m28d` | `-26.777` | `-26.768` | `-26.757` |
| `Bits 14-15` | `>> 14` | `astro_sun_dist_shift_m28d` | `0.98428` | `0.98784` | `0.99333` |

### Container: `packed_astro_container_026` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_dist_rate_shift_m28d` | `-0.054741` | `0.098637` | `0.2222` |
| `Bits 2-3` | `>> 2` | `astro_sun_illum_frac_shift_m28d` | `21.207` | `58.052` | `86.094` |
| `Bits 4-5` | `>> 4` | `astro_moon_ra_icrf_shift_m28d` | `106.73` | `185.14` | `255.05` |
| `Bits 6-7` | `>> 6` | `astro_moon_dec_icrf_shift_m28d` | `-21.655` | `-2.4566` | `17.334` |
| `Bits 8-9` | `>> 8` | `astro_moon_ra_app_shift_m28d` | `107.1` | `185.45` | `255.42` |
| `Bits 10-11` | `>> 10` | `astro_moon_dec_app_shift_m28d` | `-21.606` | `-2.4578` | `17.381` |
| `Bits 12-13` | `>> 12` | `astro_moon_azim_shift_m28d` | `94.842` | `206.17` | `270.06` |
| `Bits 14-15` | `>> 14` | `astro_moon_elev_shift_m28d` | `-20.581` | `-1.6968` | `16.094` |

### Container: `packed_astro_container_027` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_app_mag_shift_m28d` | `-11.534` | `-10.424` | `-8.5758` |
| `Bits 2-3` | `>> 2` | `astro_moon_surf_bright_shift_m28d` | `4.3298` | `5.0015` | `5.7237` |
| `Bits 4-5` | `>> 4` | `astro_moon_dist_shift_m28d` | `0.0024766` | `0.0026044` | `0.0026949` |
| `Bits 6-7` | `>> 6` | `astro_moon_dist_rate_shift_m28d` | `-0.18727` | `0.060255` | `0.2499` |
| `Bits 8-9` | `>> 8` | `astro_moon_helio_dist_shift_m28d` | `0.9846` | `0.98779` | `0.99245` |
| `Bits 10-11` | `>> 10` | `astro_moon_helio_dist_rate_shift_m28d` | `-0.40195` | `0.20012` | `0.94199` |
| `Bits 12-13` | `>> 12` | `astro_moon_phase_angle_shift_m28d` | `43.775` | `80.731` | `125.17` |
| `Bits 14-15` | `>> 14` | `astro_moon_elong_shift_m28d` | `54.715` | `99.12` | `136.12` |

### Container: `packed_astro_container_028` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_illum_frac_shift_m28d` | `21.207` | `58.052` | `86.094` |
| `Bits 2-3` | `>> 2` | `astro_mars_ra_icrf_shift_m28d` | `285.73` | `304.66` | `322.92` |
| `Bits 4-5` | `>> 4` | `astro_mars_dec_icrf_shift_m28d` | `-23.423` | `-20.616` | `-15.832` |
| `Bits 6-7` | `>> 6` | `astro_mars_ra_app_shift_m28d` | `286.09` | `305` | `323.25` |
| `Bits 8-9` | `>> 8` | `astro_mars_dec_app_shift_m28d` | `-23.389` | `-20.543` | `-15.728` |
| `Bits 10-11` | `>> 10` | `astro_mars_azim_shift_m28d` | `158.73` | `161.81` | `165.57` |
| `Bits 12-13` | `>> 12` | `astro_mars_elev_shift_m28d` | `24.815` | `28.598` | `34.308` |
| `Bits 14-15` | `>> 14` | `astro_mars_app_mag_shift_m28d` | `1.2455` | `1.2845` | `1.321` |

### Container: `packed_astro_container_029` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_surf_bright_shift_m28d` | `4.0563` | `4.096` | `4.1137` |
| `Bits 2-3` | `>> 2` | `astro_mars_dist_shift_m28d` | `2.1722` | `2.2614` | `2.3469` |
| `Bits 4-5` | `>> 4` | `astro_mars_dist_rate_shift_m28d` | `-6.7295` | `-6.6604` | `-6.2331` |
| `Bits 6-7` | `>> 6` | `astro_mars_helio_dist_shift_m28d` | `1.4054` | `1.4264` | `1.452` |
| `Bits 8-9` | `>> 8` | `astro_mars_helio_dist_rate_shift_m28d` | `-2.0401` | `-1.7537` | `-1.3548` |
| `Bits 10-11` | `>> 10` | `astro_mars_phase_angle_shift_m28d` | `12.751` | `16.901` | `20.821` |
| `Bits 12-13` | `>> 12` | `astro_mars_elong_shift_m28d` | `19.002` | `24.822` | `30.193` |
| `Bits 14-15` | `>> 14` | `astro_mars_illum_frac_shift_m28d` | `21.207` | `58.052` | `86.094` |

### Container: `packed_astro_container_030` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_ra_icrf_shift_m28d` | `34.278` | `36.792` | `40.559` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_dec_icrf_shift_m28d` | `12.588` | `13.534` | `14.816` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_ra_app_shift_m28d` | `34.602` | `37.117` | `40.887` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_dec_app_shift_m28d` | `12.699` | `13.642` | `14.918` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_azim_shift_m28d` | `53.333` | `67.339` | `78.27` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_elev_shift_m28d` | `-20.284` | `-5.7838` | `9.2834` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_app_mag_shift_m28d` | `-2.404` | `-2.249` | `-2.135` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_surf_bright_shift_m28d` | `5.3513` | `5.363` | `5.3697` |

### Container: `packed_astro_container_031` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_dist_shift_m28d` | `4.8429` | `5.2122` | `5.5429` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_dist_rate_shift_m28d` | `21.936` | `25.683` | `27.128` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_helio_dist_shift_m28d` | `4.9895` | `4.9943` | `4.9994` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_helio_dist_rate_shift_m28d` | `0.34867` | `0.36913` | `0.38726` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_phase_angle_shift_m28d` | `9.0593` | `10.573` | `11.169` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_elong_shift_m28d` | `52.413` | `71.896` | `92.845` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_illum_frac_shift_m28d` | `21.207` | `58.052` | `86.094` |
| `Bits 14-15` | `>> 14` | `astro_saturn_ra_icrf_shift_m28d` | `337.67` | `340.22` | `342.88` |

### Container: `packed_astro_container_032` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_dec_icrf_shift_m28d` | `-11.091` | `-10.087` | `-9.0374` |
| `Bits 2-3` | `>> 2` | `astro_saturn_ra_app_shift_m28d` | `337.98` | `340.53` | `343.19` |
| `Bits 4-5` | `>> 4` | `astro_saturn_dec_app_shift_m28d` | `-10.97` | `-9.9643` | `-8.912` |
| `Bits 6-7` | `>> 6` | `astro_saturn_azim_shift_m28d` | `109.32` | `123.11` | `140.65` |
| `Bits 8-9` | `>> 8` | `astro_saturn_elev_shift_m28d` | `6.0776` | `21.029` | `33.666` |
| `Bits 10-11` | `>> 10` | `astro_saturn_app_mag_shift_m28d` | `0.97525` | `0.988` | `1.006` |
| `Bits 12-13` | `>> 12` | `astro_saturn_surf_bright_shift_m28d` | `6.6843` | `6.7065` | `6.723` |
| `Bits 14-15` | `>> 14` | `astro_saturn_dist_shift_m28d` | `10.553` | `10.641` | `10.693` |

### Container: `packed_astro_container_033` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_dist_rate_shift_m28d` | `-5.0543` | `5.1006` | `14.756` |
| `Bits 2-3` | `>> 2` | `astro_saturn_helio_dist_shift_m28d` | `9.718` | `9.7246` | `9.7313` |
| `Bits 4-5` | `>> 4` | `astro_saturn_helio_dist_rate_shift_m28d` | `-0.49731` | `-0.49474` | `-0.49191` |
| `Bits 6-7` | `>> 6` | `astro_saturn_phase_angle_shift_m28d` | `1.0823` | `2.0773` | `3.0652` |
| `Bits 8-9` | `>> 8` | `astro_saturn_elong_shift_m28d` | `10.679` | `20.815` | `31.881` |
| `Bits 10-11` | `>> 10` | `astro_saturn_illum_frac_shift_m28d` | `21.207` | `58.052` | `86.094` |
| `Bits 12-13` | `>> 12` | `astro_mercury_ra_icrf_shift_m28d` | `83.134` | `282.24` | `319.67` |
| `Bits 14-15` | `>> 14` | `astro_mercury_dec_icrf_shift_m28d` | `-21.713` | `-17.457` | `-0.07721` |

### Container: `packed_astro_container_034` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mercury_ra_app_shift_m28d` | `83.458` | `282.6` | `320` |
| `Bits 2-3` | `>> 2` | `astro_mercury_dec_app_shift_m28d` | `-21.703` | `-17.356` | `0.054748` |
| `Bits 4-5` | `>> 4` | `astro_mercury_azim_shift_m28d` | `117.42` | `144.42` | `160.11` |
| `Bits 6-7` | `>> 6` | `astro_mercury_elev_shift_m28d` | `25.885` | `27.845` | `29.923` |
| `Bits 8-9` | `>> 8` | `astro_mercury_app_mag_shift_m28d` | `-1.096` | `-0.404` | `-0.1995` |
| `Bits 10-11` | `>> 10` | `astro_mercury_surf_bright_shift_m28d` | `2.1277` | `2.773` | `3.133` |
| `Bits 12-13` | `>> 12` | `astro_mercury_dist_shift_m28d` | `0.98695` | `1.2159` | `1.3465` |
| `Bits 14-15` | `>> 14` | `astro_mercury_dist_rate_shift_m28d` | `-31.143` | `3.9914` | `22.895` |

### Container: `packed_astro_container_035` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mercury_helio_dist_shift_m28d` | `0.34315` | `0.39481` | `0.44733` |
| `Bits 2-3` | `>> 2` | `astro_mercury_helio_dist_rate_shift_m28d` | `-6.4991` | `1.07` | `7.8891` |
| `Bits 4-5` | `>> 4` | `astro_mercury_phase_angle_shift_m28d` | `25.044` | `47.317` | `79.344` |
| `Bits 6-7` | `>> 6` | `astro_mercury_elong_shift_m28d` | `9.9238` | `16.542` | `20.095` |
| `Bits 8-9` | `>> 8` | `astro_mercury_illum_frac_shift_m28d` | `21.207` | `58.052` | `86.094` |
| `Bits 10-11` | `>> 10` | `astro_venus_ra_icrf_shift_m28d` | `270.82` | `301.64` | `330.77` |
| `Bits 12-13` | `>> 12` | `astro_venus_dec_icrf_shift_m28d` | `-21.708` | `-19.522` | `-13.068` |
| `Bits 14-15` | `>> 14` | `astro_venus_ra_app_shift_m28d` | `271.17` | `301.99` | `331.09` |

### Container: `packed_astro_container_036` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_dec_app_shift_m28d` | `-21.715` | `-19.513` | `-12.954` |
| `Bits 2-3` | `>> 2` | `astro_venus_azim_shift_m28d` | `155.77` | `164.89` | `173.57` |
| `Bits 4-5` | `>> 4` | `astro_venus_elev_shift_m28d` | `28.959` | `30.828` | `34.962` |
| `Bits 6-7` | `>> 6` | `astro_venus_app_mag_shift_m28d` | `-3.9632` | `-3.912` | `-3.8832` |
| `Bits 8-9` | `>> 8` | `astro_venus_surf_bright_shift_m28d` | `0.94175` | `1.0165` | `1.0942` |
| `Bits 10-11` | `>> 10` | `astro_venus_dist_shift_m28d` | `1.3199` | `1.4413` | `1.5449` |
| `Bits 12-13` | `>> 12` | `astro_venus_dist_rate_shift_m28d` | `6.8961` | `8.299` | `9.639` |
| `Bits 14-15` | `>> 14` | `astro_venus_helio_dist_shift_m28d` | `0.72343` | `0.72636` | `0.72794` |

### Container: `packed_astro_container_037` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_helio_dist_rate_shift_m28d` | `0.059174` | `0.18452` | `0.22339` |
| `Bits 2-3` | `>> 2` | `astro_venus_phase_angle_shift_m28d` | `30.907` | `38.92` | `47.236` |
| `Bits 4-5` | `>> 4` | `astro_venus_elong_shift_m28d` | `22.114` | `27.511` | `32.654` |
| `Bits 6-7` | `>> 6` | `astro_venus_illum_frac_shift_m28d` | `21.207` | `58.052` | `86.094` |
| `Bits 8-9` | `>> 8` | `astro_sun_ra_icrf_shift_m21d` | `284.98` | `311.67` | `336.39` |
| `Bits 10-11` | `>> 10` | `astro_sun_dec_icrf_shift_m21d` | `-18.974` | `-11.296` | `-1.7658` |
| `Bits 12-13` | `>> 12` | `astro_sun_ra_app_shift_m21d` | `285.33` | `312.01` | `336.71` |
| `Bits 14-15` | `>> 14` | `astro_sun_dec_app_shift_m21d` | `-18.895` | `-11.18` | `-1.6343` |

### Container: `packed_astro_container_038` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_azim_shift_m21d` | `127.82` | `133.28` | `138.35` |
| `Bits 2-3` | `>> 2` | `astro_sun_elev_shift_m21d` | `20.703` | `26.878` | `35.307` |
| `Bits 4-5` | `>> 4` | `astro_sun_app_mag_shift_m21d` | `-26.776` | `-26.767` | `-26.754` |
| `Bits 6-7` | `>> 6` | `astro_sun_dist_shift_m21d` | `0.98446` | `0.98853` | `0.99472` |
| `Bits 8-9` | `>> 8` | `astro_sun_dist_rate_shift_m21d` | `-0.037618` | `0.1219` | `0.22916` |
| `Bits 10-11` | `>> 10` | `astro_sun_illum_frac_shift_m21d` | `16.495` | `51.795` | `84.524` |
| `Bits 12-13` | `>> 12` | `astro_moon_ra_icrf_shift_m21d` | `101.88` | `186.53` | `266.31` |
| `Bits 14-15` | `>> 14` | `astro_moon_dec_icrf_shift_m21d` | `-20.916` | `-2.7234` | `15.4` |

### Container: `packed_astro_container_039` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_ra_app_shift_m21d` | `102.26` | `186.84` | `266.7` |
| `Bits 2-3` | `>> 2` | `astro_moon_dec_app_shift_m21d` | `-21.013` | `-2.8576` | `15.51` |
| `Bits 4-5` | `>> 4` | `astro_moon_azim_shift_m21d` | `100.1` | `194.78` | `264.57` |
| `Bits 6-7` | `>> 6` | `astro_moon_elev_shift_m21d` | `-19.679` | `-0.79875` | `20.165` |
| `Bits 8-9` | `>> 8` | `astro_moon_app_mag_shift_m21d` | `-11.379` | `-10.151` | `-8.209` |
| `Bits 10-11` | `>> 10` | `astro_moon_surf_bright_shift_m21d` | `4.374` | `5.099` | `5.819` |
| `Bits 12-13` | `>> 12` | `astro_moon_dist_shift_m21d` | `0.0024523` | `0.0025871` | `0.0026895` |
| `Bits 14-15` | `>> 14` | `astro_moon_dist_rate_shift_m21d` | `-0.1893` | `0.013928` | `0.22085` |

### Container: `packed_astro_container_040` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_helio_dist_shift_m21d` | `0.98483` | `0.99025` | `0.99413` |
| `Bits 2-3` | `>> 2` | `astro_moon_helio_dist_rate_shift_m21d` | `-0.36665` | `0.18776` | `0.86393` |
| `Bits 4-5` | `>> 4` | `astro_moon_phase_angle_shift_m21d` | `46.328` | `87.943` | `132.07` |
| `Bits 6-7` | `>> 6` | `astro_moon_elong_shift_m21d` | `47.824` | `91.901` | `133.56` |
| `Bits 8-9` | `>> 8` | `astro_moon_illum_frac_shift_m21d` | `16.495` | `51.795` | `84.524` |
| `Bits 10-11` | `>> 10` | `astro_mars_ra_icrf_shift_m21d` | `287.17` | `307.46` | `326.93` |
| `Bits 12-13` | `>> 12` | `astro_mars_dec_icrf_shift_m21d` | `-23.29` | `-20.012` | `-14.532` |
| `Bits 14-15` | `>> 14` | `astro_mars_ra_app_shift_m21d` | `287.53` | `307.8` | `327.25` |

### Container: `packed_astro_container_041` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_dec_app_shift_m21d` | `-23.253` | `-19.933` | `-14.422` |
| `Bits 2-3` | `>> 2` | `astro_mars_azim_shift_m21d` | `158.96` | `162.31` | `166.61` |
| `Bits 4-5` | `>> 4` | `astro_mars_elev_shift_m21d` | `25.026` | `29.344` | `35.809` |
| `Bits 6-7` | `>> 6` | `astro_mars_app_mag_shift_m21d` | `1.23` | `1.282` | `1.319` |
| `Bits 8-9` | `>> 8` | `astro_mars_surf_bright_shift_m21d` | `4.055` | `4.093` | `4.112` |
| `Bits 10-11` | `>> 10` | `astro_mars_dist_shift_m21d` | `2.1519` | `2.2481` | `2.3407` |
| `Bits 12-13` | `>> 12` | `astro_mars_dist_rate_shift_m21d` | `-6.7243` | `-6.6508` | `-6.2744` |
| `Bits 14-15` | `>> 14` | `astro_mars_helio_dist_shift_m21d` | `1.4015` | `1.4229` | `1.45` |

### Container: `packed_astro_container_042` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_helio_dist_rate_shift_m21d` | `-2.0227` | `-1.7006` | `-1.2507` |
| `Bits 2-3` | `>> 2` | `astro_mars_phase_angle_shift_m21d` | `13.07` | `17.507` | `21.671` |
| `Bits 4-5` | `>> 4` | `astro_mars_elong_shift_m21d` | `19.456` | `25.658` | `31.35` |
| `Bits 6-7` | `>> 6` | `astro_mars_illum_frac_shift_m21d` | `16.495` | `51.795` | `84.524` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_ra_icrf_shift_m21d` | `34.416` | `37.288` | `41.546` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_dec_icrf_shift_m21d` | `12.643` | `13.71` | `15.133` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_ra_app_shift_m21d` | `34.74` | `37.614` | `41.875` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_dec_app_shift_m21d` | `12.754` | `13.818` | `15.234` |

### Container: `packed_astro_container_043` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_azim_shift_m21d` | `54.551` | `69.127` | `80.519` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_elev_shift_m21d` | `-19.242` | `-3.528` | `12.684` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_app_mag_shift_m21d` | `-2.391` | `-2.229` | `-2.114` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_surf_bright_shift_m21d` | `5.347` | `5.362` | `5.369` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_dist_shift_m21d` | `4.8711` | `5.2655` | `5.6086` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_dist_rate_shift_m21d` | `20.643` | `25.428` | `27.052` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_helio_dist_shift_m21d` | `4.9898` | `4.995` | `5.0005` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_helio_dist_rate_shift_m21d` | `0.3502` | `0.3718` | `0.3908` |

### Container: `packed_astro_container_044` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_phase_angle_shift_m21d` | `8.5263` | `10.447` | `11.133` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_elong_shift_m21d` | `48.181` | `68.878` | `91.211` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_illum_frac_shift_m21d` | `16.495` | `51.795` | `84.524` |
| `Bits 6-7` | `>> 6` | `astro_saturn_ra_icrf_shift_m21d` | `337.85` | `340.61` | `343.47` |
| `Bits 8-9` | `>> 8` | `astro_saturn_dec_icrf_shift_m21d` | `-11.019` | `-9.9301` | `-8.8033` |
| `Bits 10-11` | `>> 10` | `astro_saturn_ra_app_shift_m21d` | `338.16` | `340.93` | `343.78` |
| `Bits 12-13` | `>> 12` | `astro_saturn_dec_app_shift_m21d` | `-10.898` | `-9.8066` | `-8.6773` |
| `Bits 14-15` | `>> 14` | `astro_saturn_azim_shift_m21d` | `110.28` | `125.45` | `145.37` |

### Container: `packed_astro_container_045` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_elev_shift_m21d` | `7.2574` | `23.115` | `36.023` |
| `Bits 2-3` | `>> 2` | `astro_saturn_app_mag_shift_m21d` | `0.976` | `0.989` | `1.022` |
| `Bits 4-5` | `>> 4` | `astro_saturn_surf_bright_shift_m21d` | `6.687` | `6.709` | `6.726` |
| `Bits 6-7` | `>> 6` | `astro_saturn_dist_shift_m21d` | `10.533` | `10.631` | `10.691` |
| `Bits 8-9` | `>> 8` | `astro_saturn_dist_rate_shift_m21d` | `-7.3018` | `3.5742` | `14.079` |
| `Bits 10-11` | `>> 10` | `astro_saturn_helio_dist_shift_m21d` | `9.7165` | `9.7236` | `9.7308` |
| `Bits 12-13` | `>> 12` | `astro_saturn_helio_dist_rate_shift_m21d` | `-0.49772` | `-0.49524` | `-0.49216` |
| `Bits 14-15` | `>> 14` | `astro_saturn_phase_angle_shift_m21d` | `1.1667` | `2.2094` | `3.2377` |

### Container: `packed_astro_container_046` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_elong_shift_m21d` | `11.527` | `22.198` | `33.439` |
| `Bits 2-3` | `>> 2` | `astro_saturn_illum_frac_shift_m21d` | `16.495` | `51.795` | `84.524` |
| `Bits 4-5` | `>> 4` | `astro_mercury_ra_icrf_shift_m21d` | `23.305` | `277.22` | `316.73` |
| `Bits 6-7` | `>> 6` | `astro_mercury_dec_icrf_shift_m21d` | `-21.548` | `-15.57` | `4.6969` |
| `Bits 8-9` | `>> 8` | `astro_mercury_ra_app_shift_m21d` | `23.621` | `277.58` | `317.06` |
| `Bits 10-11` | `>> 10` | `astro_mercury_dec_app_shift_m21d` | `-21.558` | `-15.461` | `4.8276` |
| `Bits 12-13` | `>> 12` | `astro_mercury_azim_shift_m21d` | `113.21` | `141.08` | `159.48` |
| `Bits 14-15` | `>> 14` | `astro_mercury_elev_shift_m21d` | `26.015` | `28.153` | `30.907` |

### Container: `packed_astro_container_047` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mercury_app_mag_shift_m21d` | `-1.024` | `-0.358` | `-0.121` |
| `Bits 2-3` | `>> 2` | `astro_mercury_surf_bright_shift_m21d` | `2.179` | `2.841` | `3.205` |
| `Bits 4-5` | `>> 4` | `astro_mercury_dist_shift_m21d` | `0.92227` | `1.1849` | `1.3401` |
| `Bits 6-7` | `>> 6` | `astro_mercury_dist_rate_shift_m21d` | `-29.241` | `0.65834` | `21.413` |
| `Bits 8-9` | `>> 8` | `astro_mercury_helio_dist_shift_m21d` | `0.34788` | `0.39381` | `0.44449` |
| `Bits 10-11` | `>> 10` | `astro_mercury_helio_dist_rate_shift_m21d` | `-5.8264` | `2.2708` | `8.9063` |
| `Bits 12-13` | `>> 12` | `astro_mercury_phase_angle_shift_m21d` | `27.267` | `51.66` | `89.217` |
| `Bits 14-15` | `>> 14` | `astro_mercury_elong_shift_m21d` | `9.0403` | `15.745` | `19.715` |

### Container: `packed_astro_container_048` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mercury_illum_frac_shift_m21d` | `16.495` | `51.795` | `84.524` |
| `Bits 2-3` | `>> 2` | `astro_venus_ra_icrf_shift_m21d` | `265.17` | `298.38` | `329.87` |
| `Bits 4-5` | `>> 4` | `astro_venus_dec_icrf_shift_m21d` | `-21.582` | `-19.065` | `-10.887` |
| `Bits 6-7` | `>> 6` | `astro_venus_ra_app_shift_m21d` | `265.53` | `298.73` | `330.19` |
| `Bits 8-9` | `>> 8` | `astro_venus_dec_app_shift_m21d` | `-21.61` | `-19.031` | `-10.766` |
| `Bits 10-11` | `>> 10` | `astro_venus_azim_shift_m21d` | `153.63` | `163.54` | `172.94` |
| `Bits 12-13` | `>> 12` | `astro_venus_elev_shift_m21d` | `29.043` | `31.256` | `36.66` |
| `Bits 14-15` | `>> 14` | `astro_venus_app_mag_shift_m21d` | `-3.958` | `-3.906` | `-3.88` |

### Container: `packed_astro_container_049` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_surf_bright_shift_m21d` | `0.925` | `1.005` | `1.088` |
| `Bits 2-3` | `>> 2` | `astro_venus_dist_shift_m21d` | `1.3296` | `1.458` | `1.5657` |
| `Bits 4-5` | `>> 4` | `astro_venus_dist_rate_shift_m21d` | `6.5548` | `8.099` | `9.5447` |
| `Bits 6-7` | `>> 6` | `astro_venus_helio_dist_shift_m21d` | `0.72367` | `0.72672` | `0.7279` |
| `Bits 8-9` | `>> 8` | `astro_venus_helio_dist_rate_shift_m21d` | `0.02551` | `0.16938` | `0.22152` |
| `Bits 10-11` | `>> 10` | `astro_venus_phase_angle_shift_m21d` | `29.112` | `37.701` | `46.593` |
| `Bits 12-13` | `>> 12` | `astro_venus_elong_shift_m21d` | `20.863` | `26.714` | `32.277` |
| `Bits 14-15` | `>> 14` | `astro_venus_illum_frac_shift_m21d` | `16.495` | `51.795` | `84.524` |

### Container: `packed_astro_container_050` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_ra_icrf_shift_m14d` | `24.961` | `308.05` | `334.73` |
| `Bits 2-3` | `>> 2` | `astro_sun_dec_icrf_shift_m14d` | `-18.534` | `-10.033` | `0.30908` |
| `Bits 4-5` | `>> 4` | `astro_sun_ra_app_shift_m14d` | `25.276` | `308.39` | `335.04` |
| `Bits 6-7` | `>> 6` | `astro_sun_dec_app_shift_m14d` | `-18.452` | `-9.9136` | `0.44117` |
| `Bits 8-9` | `>> 8` | `astro_sun_azim_shift_m14d` | `126.6` | `132.54` | `138.01` |
| `Bits 10-11` | `>> 10` | `astro_sun_elev_shift_m14d` | `21.026` | `27.968` | `37.172` |
| `Bits 12-13` | `>> 12` | `astro_sun_app_mag_shift_m14d` | `-26.776` | `-26.765` | `-26.751` |
| `Bits 14-15` | `>> 14` | `astro_sun_dist_shift_m14d` | `0.98466` | `0.98928` | `0.99615` |

### Container: `packed_astro_container_051` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_dist_rate_shift_m14d` | `-0.020806` | `0.14782` | `0.24579` |
| `Bits 2-3` | `>> 2` | `astro_sun_illum_frac_shift_m14d` | `16.156` | `49.482` | `82.502` |
| `Bits 4-5` | `>> 4` | `astro_moon_ra_icrf_shift_m14d` | `93.413` | `177.77` | `257.17` |
| `Bits 6-7` | `>> 6` | `astro_moon_dec_icrf_shift_m14d` | `-19.522` | `0.53304` | `19.518` |
| `Bits 8-9` | `>> 8` | `astro_moon_ra_app_shift_m14d` | `93.792` | `178.08` | `257.55` |
| `Bits 10-11` | `>> 10` | `astro_moon_dec_app_shift_m14d` | `-19.466` | `0.53041` | `19.607` |
| `Bits 12-13` | `>> 12` | `astro_moon_azim_shift_m14d` | `84.157` | `182.5` | `261.45` |
| `Bits 14-15` | `>> 14` | `astro_moon_elev_shift_m14d` | `-19.675` | `0.30764` | `20.196` |

### Container: `packed_astro_container_052` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_app_mag_shift_m14d` | `-11.345` | `-10.125` | `-8.1575` |
| `Bits 2-3` | `>> 2` | `astro_moon_surf_bright_shift_m14d` | `4.421` | `5.172` | `5.8533` |
| `Bits 4-5` | `>> 4` | `astro_moon_dist_shift_m14d` | `0.0024559` | `0.002582` | `0.002685` |
| `Bits 6-7` | `>> 6` | `astro_moon_dist_rate_shift_m14d` | `-0.20923` | `-0.0039246` | `0.21861` |
| `Bits 8-9` | `>> 8` | `astro_moon_helio_dist_shift_m14d` | `0.98492` | `0.99075` | `0.99811` |
| `Bits 10-11` | `>> 10` | `astro_moon_helio_dist_rate_shift_m14d` | `-0.35369` | `0.3245` | `0.97676` |
| `Bits 12-13` | `>> 12` | `astro_moon_phase_angle_shift_m14d` | `49.448` | `90.594` | `132.6` |
| `Bits 14-15` | `>> 14` | `astro_moon_elong_shift_m14d` | `47.293` | `89.255` | `130.43` |

### Container: `packed_astro_container_053` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_illum_frac_shift_m14d` | `16.156` | `49.482` | `82.502` |
| `Bits 2-3` | `>> 2` | `astro_mars_ra_icrf_shift_m14d` | `288.61` | `310.24` | `330.89` |
| `Bits 4-5` | `>> 4` | `astro_mars_dec_icrf_shift_m14d` | `-23.142` | `-19.363` | `-13.165` |
| `Bits 6-7` | `>> 6` | `astro_mars_ra_app_shift_m14d` | `288.96` | `310.58` | `331.21` |
| `Bits 8-9` | `>> 8` | `astro_mars_dec_app_shift_m14d` | `-23.102` | `-19.279` | `-13.051` |
| `Bits 10-11` | `>> 10` | `astro_mars_azim_shift_m14d` | `159.19` | `162.82` | `167.76` |
| `Bits 12-13` | `>> 12` | `astro_mars_elev_shift_m14d` | `25.25` | `30.134` | `37.368` |
| `Bits 14-15` | `>> 14` | `astro_mars_app_mag_shift_m14d` | `1.2125` | `1.2725` | `1.3133` |

### Container: `packed_astro_container_054` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_surf_bright_shift_m14d` | `4.052` | `4.09` | `4.111` |
| `Bits 2-3` | `>> 2` | `astro_mars_dist_shift_m14d` | `2.1316` | `2.2347` | `2.3344` |
| `Bits 4-5` | `>> 4` | `astro_mars_dist_rate_shift_m14d` | `-6.7213` | `-6.641` | `-6.314` |
| `Bits 6-7` | `>> 6` | `astro_mars_helio_dist_shift_m14d` | `1.3979` | `1.4195` | `1.4479` |
| `Bits 8-9` | `>> 8` | `astro_mars_helio_dist_rate_shift_m14d` | `-2.0045` | `-1.6448` | `-1.1421` |
| `Bits 10-11` | `>> 10` | `astro_mars_phase_angle_shift_m14d` | `13.388` | `18.107` | `22.505` |
| `Bits 12-13` | `>> 12` | `astro_mars_elong_shift_m14d` | `19.906` | `26.484` | `32.487` |
| `Bits 14-15` | `>> 14` | `astro_mars_illum_frac_shift_m14d` | `16.156` | `49.482` | `82.502` |

### Container: `packed_astro_container_055` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_ra_icrf_shift_m14d` | `34.562` | `37.811` | `42.576` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_dec_icrf_shift_m14d` | `12.701` | `13.894` | `15.457` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_ra_app_shift_m14d` | `34.886` | `38.137` | `42.906` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_dec_app_shift_m14d` | `12.812` | `14` | `15.556` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_azim_shift_m14d` | `55.736` | `70.853` | `82.727` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_elev_shift_m14d` | `-18.188` | `-1.2641` | `16.074` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_app_mag_shift_m14d` | `-2.378` | `-2.2105` | `-2.0953` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_surf_bright_shift_m14d` | `5.3427` | `5.3605` | `5.369` |

### Container: `packed_astro_container_056` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_dist_shift_m14d` | `4.8993` | `5.3176` | `5.6701` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_dist_rate_shift_m14d` | `19.268` | `25.079` | `26.978` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_helio_dist_shift_m14d` | `4.9902` | `4.9958` | `5.0017` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_helio_dist_rate_shift_m14d` | `0.3531` | `0.37428` | `0.39493` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_phase_angle_shift_m14d` | `7.9541` | `10.321` | `11.101` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_elong_shift_m14d` | `44.005` | `65.892` | `89.587` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_illum_frac_shift_m14d` | `16.156` | `49.482` | `82.502` |
| `Bits 14-15` | `>> 14` | `astro_saturn_ra_icrf_shift_m14d` | `338.03` | `341.02` | `344.06` |

### Container: `packed_astro_container_057` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_dec_icrf_shift_m14d` | `-10.946` | `-9.7721` | `-8.5726` |
| `Bits 2-3` | `>> 2` | `astro_saturn_ra_app_shift_m14d` | `338.35` | `341.33` | `344.37` |
| `Bits 4-5` | `>> 4` | `astro_saturn_dec_app_shift_m14d` | `-10.825` | `-9.6482` | `-8.4461` |
| `Bits 6-7` | `>> 6` | `astro_saturn_azim_shift_m14d` | `111.25` | `127.89` | `150.41` |
| `Bits 8-9` | `>> 8` | `astro_saturn_elev_shift_m14d` | `8.4292` | `25.144` | `38.135` |
| `Bits 10-11` | `>> 10` | `astro_saturn_app_mag_shift_m14d` | `0.9785` | `0.99` | `1.0355` |
| `Bits 12-13` | `>> 12` | `astro_saturn_surf_bright_shift_m14d` | `6.6877` | `6.712` | `6.7378` |
| `Bits 14-15` | `>> 14` | `astro_saturn_dist_shift_m14d` | `10.509` | `10.619` | `10.688` |

### Container: `packed_astro_container_058` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_dist_rate_shift_m14d` | `-9.4794` | `2.0442` | `13.394` |
| `Bits 2-3` | `>> 2` | `astro_saturn_helio_dist_shift_m14d` | `9.7149` | `9.7226` | `9.7303` |
| `Bits 4-5` | `>> 4` | `astro_saturn_helio_dist_rate_shift_m14d` | `-0.49869` | `-0.49544` | `-0.49232` |
| `Bits 6-7` | `>> 6` | `astro_saturn_phase_angle_shift_m14d` | `1.2352` | `2.3697` | `3.4192` |
| `Bits 8-9` | `>> 8` | `astro_saturn_elong_shift_m14d` | `12.217` | `23.915` | `35.82` |
| `Bits 10-11` | `>> 10` | `astro_saturn_illum_frac_shift_m14d` | `16.156` | `49.482` | `82.502` |
| `Bits 12-13` | `>> 12` | `astro_mercury_ra_icrf_shift_m14d` | `22.354` | `272.56` | `313.8` |
| `Bits 14-15` | `>> 14` | `astro_mercury_dec_icrf_shift_m14d` | `-21.386` | `-13.394` | `8.2513` |

### Container: `packed_astro_container_059` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mercury_ra_app_shift_m14d` | `22.669` | `272.91` | `314.13` |
| `Bits 2-3` | `>> 2` | `astro_mercury_dec_app_shift_m14d` | `-21.369` | `-13.278` | `8.3786` |
| `Bits 4-5` | `>> 4` | `astro_mercury_azim_shift_m14d` | `114.34` | `137.47` | `158.94` |
| `Bits 6-7` | `>> 6` | `astro_mercury_elev_shift_m14d` | `26.125` | `28.391` | `32.205` |
| `Bits 8-9` | `>> 8` | `astro_mercury_app_mag_shift_m14d` | `-0.97175` | `-0.3105` | `0.03175` |
| `Bits 10-11` | `>> 10` | `astro_mercury_surf_bright_shift_m14d` | `2.2388` | `2.893` | `3.2868` |
| `Bits 12-13` | `>> 12` | `astro_mercury_dist_shift_m14d` | `0.8663` | `1.1563` | `1.3338` |
| `Bits 14-15` | `>> 14` | `astro_mercury_dist_rate_shift_m14d` | `-26.917` | `-0.63894` | `19.961` |

### Container: `packed_astro_container_060` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mercury_helio_dist_shift_m14d` | `0.34969` | `0.40039` | `0.44142` |
| `Bits 2-3` | `>> 2` | `astro_mercury_helio_dist_rate_shift_m14d` | `-5.4262` | `3.3962` | `8.6645` |
| `Bits 4-5` | `>> 4` | `astro_mercury_phase_angle_shift_m14d` | `28.299` | `55.524` | `99.912` |
| `Bits 6-7` | `>> 6` | `astro_mercury_elong_shift_m14d` | `7.8838` | `14.964` | `19.154` |
| `Bits 8-9` | `>> 8` | `astro_mercury_illum_frac_shift_m14d` | `16.156` | `49.482` | `82.502` |
| `Bits 10-11` | `>> 10` | `astro_venus_ra_icrf_shift_m14d` | `258.26` | `293.78` | `327.75` |
| `Bits 12-13` | `>> 12` | `astro_venus_dec_icrf_shift_m14d` | `-21.464` | `-18.611` | `-8.5698` |
| `Bits 14-15` | `>> 14` | `astro_venus_ra_app_shift_m14d` | `258.61` | `294.13` | `328.07` |

### Container: `packed_astro_container_061` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_dec_app_shift_m14d` | `-21.475` | `-18.572` | `-8.4438` |
| `Bits 2-3` | `>> 2` | `astro_venus_azim_shift_m14d` | `151.43` | `162.18` | `172.31` |
| `Bits 4-5` | `>> 4` | `astro_venus_elev_shift_m14d` | `29.162` | `31.602` | `38.47` |
| `Bits 6-7` | `>> 6` | `astro_venus_app_mag_shift_m14d` | `-3.9537` | `-3.901` | `-3.878` |
| `Bits 8-9` | `>> 8` | `astro_venus_surf_bright_shift_m14d` | `0.90925` | `0.9935` | `1.082` |
| `Bits 10-11` | `>> 10` | `astro_venus_dist_shift_m14d` | `1.3393` | `1.4744` | `1.5855` |
| `Bits 12-13` | `>> 12` | `astro_venus_dist_rate_shift_m14d` | `6.2172` | `7.8987` | `9.4493` |
| `Bits 14-15` | `>> 14` | `astro_venus_helio_dist_shift_m14d` | `0.72391` | `0.7269` | `0.72786` |

### Container: `packed_astro_container_062` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_helio_dist_rate_shift_m14d` | `-0.0086905` | `0.15263` | `0.21938` |
| `Bits 2-3` | `>> 2` | `astro_venus_phase_angle_shift_m14d` | `27.313` | `36.487` | `45.953` |
| `Bits 4-5` | `>> 4` | `astro_venus_elong_shift_m14d` | `19.598` | `25.912` | `31.897` |
| `Bits 6-7` | `>> 6` | `astro_venus_illum_frac_shift_m14d` | `16.156` | `49.482` | `82.502` |
| `Bits 8-9` | `>> 8` | `astro_sun_ra_icrf_shift_m7d` | `26.587` | `304.39` | `333.05` |
| `Bits 10-11` | `>> 10` | `astro_sun_dec_icrf_shift_m7d` | `-18.077` | `-8.7394` | `2.375` |
| `Bits 12-13` | `>> 12` | `astro_sun_ra_app_shift_m7d` | `26.903` | `304.73` | `333.36` |
| `Bits 14-15` | `>> 14` | `astro_sun_dec_app_shift_m7d` | `-17.992` | `-8.617` | `2.5067` |

### Container: `packed_astro_container_063` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_azim_shift_m7d` | `125.33` | `131.8` | `137.67` |
| `Bits 2-3` | `>> 2` | `astro_sun_elev_shift_m7d` | `21.366` | `29.096` | `39.024` |
| `Bits 4-5` | `>> 4` | `astro_sun_app_mag_shift_m7d` | `-26.775` | `-26.764` | `-26.748` |
| `Bits 6-7` | `>> 6` | `astro_sun_dist_shift_m7d` | `0.98487` | `0.99008` | `0.99762` |
| `Bits 8-9` | `>> 8` | `astro_sun_dist_rate_shift_m7d` | `-0.0046566` | `0.17331` | `0.25016` |
| `Bits 10-11` | `>> 10` | `astro_sun_illum_frac_shift_m7d` | `17.846` | `52.67` | `85.543` |
| `Bits 12-13` | `>> 12` | `astro_moon_ra_icrf_shift_m7d` | `100.3` | `178.8` | `252.38` |
| `Bits 14-15` | `>> 14` | `astro_moon_dec_icrf_shift_m7d` | `-18.731` | `0.98323` | `18.694` |

### Container: `packed_astro_container_064` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_ra_app_shift_m7d` | `100.68` | `179.11` | `252.76` |
| `Bits 2-3` | `>> 2` | `astro_moon_dec_app_shift_m7d` | `-18.728` | `1.1146` | `18.588` |
| `Bits 4-5` | `>> 4` | `astro_moon_azim_shift_m7d` | `79.1` | `184.28` | `264.91` |
| `Bits 6-7` | `>> 6` | `astro_moon_elev_shift_m7d` | `-22.564` | `-1.6464` | `19.068` |
| `Bits 8-9` | `>> 8` | `astro_moon_app_mag_shift_m7d` | `-11.421` | `-10.242` | `-8.3295` |
| `Bits 10-11` | `>> 10` | `astro_moon_surf_bright_shift_m7d` | `4.341` | `5.049` | `5.794` |
| `Bits 12-13` | `>> 12` | `astro_moon_dist_shift_m7d` | `0.0024596` | `0.0026038` | `0.0026958` |
| `Bits 14-15` | `>> 14` | `astro_moon_dist_rate_shift_m7d` | `-0.19785` | `-0.0019561` | `0.21133` |

### Container: `packed_astro_container_065` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_helio_dist_shift_m7d` | `0.98528` | `0.99106` | `0.99903` |
| `Bits 2-3` | `>> 2` | `astro_moon_helio_dist_rate_shift_m7d` | `-0.29737` | `0.36358` | `1.0122` |
| `Bits 4-5` | `>> 4` | `astro_moon_phase_angle_shift_m7d` | `44.68` | `86.939` | `130.03` |
| `Bits 6-7` | `>> 6` | `astro_moon_elong_shift_m7d` | `49.859` | `92.91` | `135.21` |
| `Bits 8-9` | `>> 8` | `astro_moon_illum_frac_shift_m7d` | `17.846` | `52.67` | `85.543` |
| `Bits 10-11` | `>> 10` | `astro_mars_ra_icrf_shift_m7d` | `290.04` | `313.01` | `334.81` |
| `Bits 12-13` | `>> 12` | `astro_mars_dec_icrf_shift_m7d` | `-22.983` | `-18.673` | `-11.741` |
| `Bits 14-15` | `>> 14` | `astro_mars_ra_app_shift_m7d` | `290.4` | `313.35` | `335.13` |

### Container: `packed_astro_container_066` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_dec_app_shift_m7d` | `-22.939` | `-18.584` | `-11.622` |
| `Bits 2-3` | `>> 2` | `astro_mars_azim_shift_m7d` | `159.42` | `163.36` | `169.01` |
| `Bits 4-5` | `>> 4` | `astro_mars_elev_shift_m7d` | `25.485` | `30.965` | `38.976` |
| `Bits 6-7` | `>> 6` | `astro_mars_app_mag_shift_m7d` | `1.1985` | `1.269` | `1.3105` |
| `Bits 8-9` | `>> 8` | `astro_mars_surf_bright_shift_m7d` | `4.0545` | `4.093` | `4.1145` |
| `Bits 10-11` | `>> 10` | `astro_mars_dist_shift_m7d` | `2.1115` | `2.2213` | `2.3281` |
| `Bits 12-13` | `>> 12` | `astro_mars_dist_rate_shift_m7d` | `-6.7166` | `-6.628` | `-6.3523` |
| `Bits 14-15` | `>> 14` | `astro_mars_helio_dist_shift_m7d` | `1.3946` | `1.4163` | `1.4459` |

### Container: `packed_astro_container_067` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_helio_dist_rate_shift_m7d` | `-1.9857` | `-1.5867` | `-1.0293` |
| `Bits 2-3` | `>> 2` | `astro_mars_phase_angle_shift_m7d` | `13.704` | `18.701` | `23.326` |
| `Bits 4-5` | `>> 4` | `astro_mars_elong_shift_m7d` | `20.355` | `27.3` | `33.606` |
| `Bits 6-7` | `>> 6` | `astro_mars_illum_frac_shift_m7d` | `17.846` | `52.67` | `85.543` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_ra_icrf_shift_m7d` | `34.718` | `38.36` | `43.643` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_dec_icrf_shift_m7d` | `12.763` | `14.083` | `15.784` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_ra_app_shift_m7d` | `35.042` | `38.686` | `43.974` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_dec_app_shift_m7d` | `12.873` | `14.188` | `15.881` |

### Container: `packed_astro_container_068` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_azim_shift_m7d` | `56.892` | `72.527` | `84.913` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_elev_shift_m7d` | `-17.124` | `1.0052` | `19.451` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_app_mag_shift_m7d` | `-2.3655` | `-2.192` | `-2.0785` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_surf_bright_shift_m7d` | `5.3385` | `5.359` | `5.3685` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_dist_shift_m7d` | `4.9274` | `5.3686` | `5.7274` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_dist_rate_shift_m7d` | `17.827` | `24.582` | `26.893` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_helio_dist_shift_m7d` | `4.9905` | `4.9965` | `5.0029` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_helio_dist_rate_shift_m7d` | `0.35335` | `0.37673` | `0.3993` |

### Container: `packed_astro_container_069` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_phase_angle_shift_m7d` | `7.3472` | `10.163` | `11.068` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_elong_shift_m7d` | `39.88` | `62.938` | `87.973` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_illum_frac_shift_m7d` | `17.846` | `52.67` | `85.543` |
| `Bits 6-7` | `>> 6` | `astro_saturn_ra_icrf_shift_m7d` | `338.22` | `341.42` | `344.64` |
| `Bits 8-9` | `>> 8` | `astro_saturn_dec_icrf_shift_m7d` | `-10.873` | `-9.6136` | `-8.3464` |
| `Bits 10-11` | `>> 10` | `astro_saturn_ra_app_shift_m7d` | `338.53` | `341.73` | `344.94` |
| `Bits 12-13` | `>> 12` | `astro_saturn_dec_app_shift_m7d` | `-10.752` | `-9.4894` | `-8.2194` |
| `Bits 14-15` | `>> 14` | `astro_saturn_azim_shift_m7d` | `112.23` | `130.42` | `155.78` |

### Container: `packed_astro_container_070` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_elev_shift_m7d` | `9.5934` | `27.113` | `39.97` |
| `Bits 2-3` | `>> 2` | `astro_saturn_app_mag_shift_m7d` | `0.9795` | `0.99` | `1.047` |
| `Bits 4-5` | `>> 4` | `astro_saturn_surf_bright_shift_m7d` | `6.69` | `6.715` | `6.755` |
| `Bits 6-7` | `>> 6` | `astro_saturn_dist_shift_m7d` | `10.483` | `10.607` | `10.684` |
| `Bits 8-9` | `>> 8` | `astro_saturn_dist_rate_shift_m7d` | `-11.592` | `0.51312` | `12.7` |
| `Bits 10-11` | `>> 10` | `astro_saturn_helio_dist_shift_m7d` | `9.7134` | `9.7216` | `9.7298` |
| `Bits 12-13` | `>> 12` | `astro_saturn_helio_dist_rate_shift_m7d` | `-0.49901` | `-0.49582` | `-0.49261` |
| `Bits 14-15` | `>> 14` | `astro_saturn_phase_angle_shift_m7d` | `1.3037` | `2.5279` | `3.6171` |

### Container: `packed_astro_container_071` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_elong_shift_m7d` | `12.902` | `25.582` | `38.143` |
| `Bits 2-3` | `>> 2` | `astro_saturn_illum_frac_shift_m7d` | `17.846` | `52.67` | `85.543` |
| `Bits 4-5` | `>> 4` | `astro_mercury_ra_icrf_shift_m7d` | `20.651` | `268.37` | `310.88` |
| `Bits 6-7` | `>> 6` | `astro_mercury_dec_icrf_shift_m7d` | `-21.178` | `-10.947` | `7.8084` |
| `Bits 8-9` | `>> 8` | `astro_mercury_ra_app_shift_m7d` | `20.964` | `268.73` | `311.22` |
| `Bits 10-11` | `>> 10` | `astro_mercury_dec_app_shift_m7d` | `-21.148` | `-10.825` | `7.9364` |
| `Bits 12-13` | `>> 12` | `astro_mercury_azim_shift_m7d` | `115.79` | `138.01` | `158.03` |
| `Bits 14-15` | `>> 14` | `astro_mercury_elev_shift_m7d` | `26.243` | `28.593` | `34.284` |

### Container: `packed_astro_container_072` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mercury_app_mag_shift_m7d` | `-0.91` | `-0.277` | `0.352` |
| `Bits 2-3` | `>> 2` | `astro_mercury_surf_bright_shift_m7d` | `2.3065` | `2.958` | `3.4215` |
| `Bits 4-5` | `>> 4` | `astro_mercury_dist_shift_m7d` | `0.80712` | `1.1253` | `1.3257` |
| `Bits 6-7` | `>> 6` | `astro_mercury_dist_rate_shift_m7d` | `-24.735` | `1.6519` | `18.534` |
| `Bits 8-9` | `>> 8` | `astro_mercury_helio_dist_shift_m7d` | `0.35354` | `0.40678` | `0.44785` |
| `Bits 10-11` | `>> 10` | `astro_mercury_helio_dist_rate_shift_m7d` | `-4.9021` | `3.6882` | `8.4679` |
| `Bits 12-13` | `>> 12` | `astro_mercury_phase_angle_shift_m7d` | `30.351` | `60.172` | `112.55` |
| `Bits 14-15` | `>> 14` | `astro_mercury_elong_shift_m7d` | `8.4995` | `14.921` | `18.789` |

### Container: `packed_astro_container_073` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mercury_illum_frac_shift_m7d` | `17.846` | `52.67` | `85.543` |
| `Bits 2-3` | `>> 2` | `astro_venus_ra_icrf_shift_m7d` | `251.43` | `289.15` | `325.62` |
| `Bits 4-5` | `>> 4` | `astro_venus_dec_icrf_shift_m7d` | `-21.338` | `-17.628` | `-6.1466` |
| `Bits 6-7` | `>> 6` | `astro_venus_ra_app_shift_m7d` | `251.77` | `289.5` | `325.94` |
| `Bits 8-9` | `>> 8` | `astro_venus_dec_app_shift_m7d` | `-21.328` | `-17.536` | `-6.0171` |
| `Bits 10-11` | `>> 10` | `astro_venus_azim_shift_m7d` | `149.15` | `160.82` | `171.67` |
| `Bits 12-13` | `>> 12` | `astro_venus_elev_shift_m7d` | `29.29` | `31.964` | `40.359` |
| `Bits 14-15` | `>> 14` | `astro_venus_app_mag_shift_m7d` | `-3.9495` | `-3.897` | `-3.879` |

### Container: `packed_astro_container_074` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_surf_bright_shift_m7d` | `0.893` | `0.982` | `1.0765` |
| `Bits 2-3` | `>> 2` | `astro_venus_dist_shift_m7d` | `1.3488` | `1.4903` | `1.6042` |
| `Bits 4-5` | `>> 4` | `astro_venus_dist_rate_shift_m7d` | `5.8733` | `7.695` | `9.3525` |
| `Bits 6-7` | `>> 6` | `astro_venus_helio_dist_shift_m7d` | `0.72414` | `0.72672` | `0.72782` |
| `Bits 8-9` | `>> 8` | `astro_venus_helio_dist_rate_shift_m7d` | `-0.042712` | `0.13449` | `0.21709` |
| `Bits 10-11` | `>> 10` | `astro_venus_phase_angle_shift_m7d` | `25.509` | `35.279` | `45.316` |
| `Bits 12-13` | `>> 12` | `astro_venus_elong_shift_m7d` | `18.319` | `25.104` | `31.516` |
| `Bits 14-15` | `>> 14` | `astro_venus_illum_frac_shift_m7d` | `17.846` | `52.67` | `85.543` |

### Container: `packed_astro_container_075` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_ra_icrf_shift_p7d` | `26.587` | `304.39` | `333.05` |
| `Bits 2-3` | `>> 2` | `astro_sun_dec_icrf_shift_p7d` | `-16.089` | `-6.0765` | `5.0923` |
| `Bits 4-5` | `>> 4` | `astro_sun_ra_app_shift_p7d` | `26.903` | `304.73` | `333.36` |
| `Bits 6-7` | `>> 6` | `astro_sun_dec_app_shift_p7d` | `-15.993` | `-5.9493` | `5.2222` |
| `Bits 8-9` | `>> 8` | `astro_sun_azim_shift_p7d` | `123.56` | `130.29` | `136.27` |
| `Bits 10-11` | `>> 10` | `astro_sun_elev_shift_p7d` | `22.905` | `31.449` | `41.437` |
| `Bits 12-13` | `>> 12` | `astro_sun_app_mag_shift_p7d` | `-26.773` | `-26.76` | `-26.743` |
| `Bits 14-15` | `>> 14` | `astro_sun_dist_shift_p7d` | `0.9859` | `0.99182` | `0.99966` |

### Container: `packed_astro_container_076` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_dist_rate_shift_p7d` | `0.047973` | `0.21167` | `0.25016` |
| `Bits 2-3` | `>> 2` | `astro_sun_illum_frac_shift_p7d` | `17.846` | `58.956` | `88.511` |
| `Bits 4-5` | `>> 4` | `astro_moon_ra_icrf_shift_p7d` | `100.3` | `183.74` | `264.58` |
| `Bits 6-7` | `>> 6` | `astro_moon_dec_icrf_shift_p7d` | `-22.071` | `-2.1898` | `18.694` |
| `Bits 8-9` | `>> 8` | `astro_moon_ra_app_shift_p7d` | `100.68` | `184.06` | `264.97` |
| `Bits 10-11` | `>> 10` | `astro_moon_dec_app_shift_p7d` | `-22.069` | `-2.0579` | `18.588` |
| `Bits 12-13` | `>> 12` | `astro_moon_azim_shift_p7d` | `79.1` | `184.28` | `266.54` |
| `Bits 14-15` | `>> 14` | `astro_moon_elev_shift_p7d` | `-23.216` | `-6.3743` | `15.604` |

### Container: `packed_astro_container_077` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_app_mag_shift_p7d` | `-11.599` | `-10.443` | `-8.3295` |
| `Bits 2-3` | `>> 2` | `astro_moon_surf_bright_shift_p7d` | `4.268` | `4.978` | `5.7615` |
| `Bits 4-5` | `>> 4` | `astro_moon_dist_shift_p7d` | `0.0024596` | `0.0025939` | `0.0026958` |
| `Bits 6-7` | `>> 6` | `astro_moon_dist_rate_shift_p7d` | `-0.19785` | `-0.0019561` | `0.21781` |
| `Bits 8-9` | `>> 8` | `astro_moon_helio_dist_shift_p7d` | `0.98632` | `0.99195` | `0.99974` |
| `Bits 10-11` | `>> 10` | `astro_moon_helio_dist_rate_shift_p7d` | `-0.25041` | `0.36358` | `1.0122` |
| `Bits 12-13` | `>> 12` | `astro_moon_phase_angle_shift_p7d` | `39.619` | `79.68` | `130.03` |
| `Bits 14-15` | `>> 14` | `astro_moon_elong_shift_p7d` | `49.859` | `100.17` | `140.28` |

### Container: `packed_astro_container_078` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_illum_frac_shift_p7d` | `17.846` | `58.956` | `88.511` |
| `Bits 2-3` | `>> 2` | `astro_mars_ra_icrf_shift_p7d` | `294.95` | `317.71` | `339.25` |
| `Bits 4-5` | `>> 4` | `astro_mars_dec_icrf_shift_p7d` | `-22.217` | `-17.173` | `-9.7656` |
| `Bits 6-7` | `>> 6` | `astro_mars_ra_app_shift_p7d` | `294.48` | `317.26` | `338.82` |
| `Bits 8-9` | `>> 8` | `astro_mars_dec_app_shift_p7d` | `-22.161` | `-17.076` | `-9.6417` |
| `Bits 10-11` | `>> 10` | `astro_mars_azim_shift_p7d` | `160.33` | `164.52` | `170.86` |
| `Bits 12-13` | `>> 12` | `astro_mars_elev_shift_p7d` | `26.547` | `32.743` | `41.174` |
| `Bits 14-15` | `>> 14` | `astro_mars_app_mag_shift_p7d` | `1.1755` | `1.258` | `1.303` |

### Container: `packed_astro_container_079` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_surf_bright_shift_p7d` | `4.0545` | `4.094` | `4.1335` |
| `Bits 2-3` | `>> 2` | `astro_mars_dist_shift_p7d` | `2.0847` | `2.1944` | `2.3026` |
| `Bits 4-5` | `>> 4` | `astro_mars_dist_rate_shift_p7d` | `-6.7166` | `-6.628` | `-6.4963` |
| `Bits 6-7` | `>> 6` | `astro_mars_helio_dist_shift_p7d` | `1.3907` | `1.4101` | `1.4381` |
| `Bits 8-9` | `>> 8` | `astro_mars_helio_dist_rate_shift_p7d` | `-1.9039` | `-1.4632` | `-0.87286` |
| `Bits 10-11` | `>> 10` | `astro_mars_phase_angle_shift_p7d` | `14.962` | `19.874` | `24.397` |
| `Bits 12-13` | `>> 12` | `astro_mars_elong_shift_p7d` | `22.123` | `28.903` | `35.073` |
| `Bits 14-15` | `>> 14` | `astro_mars_illum_frac_shift_p7d` | `17.846` | `58.956` | `88.511` |

### Container: `packed_astro_container_080` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_ra_icrf_shift_p7d` | `35.424` | `39.53` | `45.119` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_dec_icrf_shift_p7d` | `13.033` | `14.478` | `16.224` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_ra_app_shift_p7d` | `35.748` | `39.857` | `45.452` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_dec_app_shift_p7d` | `13.143` | `14.582` | `16.319` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_azim_shift_p7d` | `61.243` | `75.739` | `87.82` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_elev_shift_p7d` | `-12.785` | `5.5509` | `23.927` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_app_mag_shift_p7d` | `-2.3175` | `-2.159` | `-2.0585` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_surf_bright_shift_p7d` | `5.3335` | `5.356` | `5.3685` |

### Container: `packed_astro_container_081` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_dist_shift_p7d` | `5.0397` | `5.4667` | `5.7968` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_dist_rate_shift_p7d` | `15.805` | `23.219` | `26.893` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_helio_dist_shift_p7d` | `4.992` | `4.9981` | `5.0046` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_helio_dist_rate_shift_p7d` | `0.35977` | `0.38301` | `0.40409` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_phase_angle_shift_p7d` | `6.4901` | `9.5929` | `11.068` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_elong_shift_p7d` | `34.452` | `57.115` | `81.608` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_illum_frac_shift_p7d` | `17.846` | `58.956` | `88.511` |
| `Bits 14-15` | `>> 14` | `astro_saturn_ra_icrf_shift_p7d` | `338.98` | `342.22` | `345.38` |

### Container: `packed_astro_container_082` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_dec_icrf_shift_p7d` | `-10.574` | `-9.2965` | `-8.0535` |
| `Bits 2-3` | `>> 2` | `astro_saturn_ra_app_shift_p7d` | `339.29` | `342.53` | `345.69` |
| `Bits 4-5` | `>> 4` | `astro_saturn_dec_app_shift_p7d` | `-10.452` | `-9.1717` | `-7.9258` |
| `Bits 6-7` | `>> 6` | `astro_saturn_azim_shift_p7d` | `116.26` | `135.83` | `163.43` |
| `Bits 8-9` | `>> 8` | `astro_saturn_elev_shift_p7d` | `14.166` | `30.843` | `41.926` |
| `Bits 10-11` | `>> 10` | `astro_saturn_app_mag_shift_p7d` | `0.9835` | `0.991` | `1.0585` |
| `Bits 12-13` | `>> 12` | `astro_saturn_surf_bright_shift_p7d` | `6.69` | `6.715` | `6.7775` |
| `Bits 14-15` | `>> 14` | `astro_saturn_dist_shift_p7d` | `10.483` | `10.607` | `10.684` |

### Container: `packed_astro_container_083` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_dist_rate_shift_p7d` | `-14.303` | `-2.5463` | `9.8344` |
| `Bits 2-3` | `>> 2` | `astro_saturn_helio_dist_shift_p7d` | `9.7114` | `9.7196` | `9.7278` |
| `Bits 4-5` | `>> 4` | `astro_saturn_helio_dist_rate_shift_p7d` | `-0.49979` | `-0.49682` | `-0.49353` |
| `Bits 6-7` | `>> 6` | `astro_saturn_phase_angle_shift_p7d` | `1.3037` | `2.5279` | `3.6171` |
| `Bits 8-9` | `>> 8` | `astro_saturn_elong_shift_p7d` | `12.902` | `25.582` | `38.143` |
| `Bits 10-11` | `>> 10` | `astro_saturn_illum_frac_shift_p7d` | `17.846` | `58.956` | `88.511` |
| `Bits 12-13` | `>> 12` | `astro_mercury_ra_icrf_shift_p7d` | `18.142` | `268.37` | `310.88` |
| `Bits 14-15` | `>> 14` | `astro_mercury_dec_icrf_shift_p7d` | `-21.178` | `-5.2824` | `7.8084` |

### Container: `packed_astro_container_084` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mercury_ra_app_shift_p7d` | `18.453` | `268.73` | `311.22` |
| `Bits 2-3` | `>> 2` | `astro_mercury_dec_app_shift_p7d` | `-21.148` | `-5.1526` | `7.9364` |
| `Bits 4-5` | `>> 4` | `astro_mercury_azim_shift_p7d` | `115.79` | `138.01` | `153.87` |
| `Bits 6-7` | `>> 6` | `astro_mercury_elev_shift_p7d` | `26.243` | `28.858` | `38.811` |
| `Bits 8-9` | `>> 8` | `astro_mercury_app_mag_shift_p7d` | `-0.91` | `-0.277` | `1.137` |
| `Bits 10-11` | `>> 10` | `astro_mercury_surf_bright_shift_p7d` | `2.3065` | `2.958` | `4.166` |
| `Bits 12-13` | `>> 12` | `astro_mercury_dist_shift_p7d` | `0.70196` | `1.1253` | `1.3257` |
| `Bits 14-15` | `>> 14` | `astro_mercury_dist_rate_shift_p7d` | `-24.735` | `1.6519` | `17.671` |

### Container: `packed_astro_container_085` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mercury_helio_dist_shift_p7d` | `0.36046` | `0.41969` | `0.45425` |
| `Bits 2-3` | `>> 2` | `astro_mercury_helio_dist_rate_shift_p7d` | `-4.9021` | `2.5288` | `7.5591` |
| `Bits 4-5` | `>> 4` | `astro_mercury_phase_angle_shift_p7d` | `30.351` | `60.172` | `124.51` |
| `Bits 6-7` | `>> 6` | `astro_mercury_elong_shift_p7d` | `8.4995` | `14.921` | `19.09` |
| `Bits 8-9` | `>> 8` | `astro_mercury_illum_frac_shift_p7d` | `17.846` | `58.956` | `88.511` |
| `Bits 10-11` | `>> 10` | `astro_venus_ra_icrf_shift_p7d` | `251.43` | `289.15` | `325.62` |
| `Bits 12-13` | `>> 12` | `astro_venus_dec_icrf_shift_p7d` | `-21.338` | `-15.269` | `-2.799` |
| `Bits 14-15` | `>> 14` | `astro_venus_ra_app_shift_p7d` | `251.77` | `289.5` | `325.94` |

### Container: `packed_astro_container_086` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_dec_app_shift_p7d` | `-21.328` | `-15.164` | `-2.667` |
| `Bits 2-3` | `>> 2` | `astro_venus_azim_shift_p7d` | `145.93` | `158.07` | `169.07` |
| `Bits 4-5` | `>> 4` | `astro_venus_elev_shift_p7d` | `29.29` | `33.265` | `42.94` |
| `Bits 6-7` | `>> 6` | `astro_venus_app_mag_shift_p7d` | `-3.933` | `-3.889` | `-3.879` |
| `Bits 8-9` | `>> 8` | `astro_venus_surf_bright_shift_p7d` | `0.8725` | `0.96` | `1.0525` |
| `Bits 10-11` | `>> 10` | `astro_venus_dist_shift_p7d` | `1.386` | `1.521` | `1.6276` |
| `Bits 12-13` | `>> 12` | `astro_venus_dist_rate_shift_p7d` | `5.3881` | `7.2684` | `8.9502` |
| `Bits 14-15` | `>> 14` | `astro_venus_helio_dist_shift_p7d` | `0.72506` | `0.72672` | `0.72782` |

### Container: `packed_astro_container_087` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_helio_dist_rate_shift_p7d` | `-0.086583` | `0.094617` | `0.21709` |
| `Bits 2-3` | `>> 2` | `astro_venus_phase_angle_shift_p7d` | `23.093` | `32.874` | `42.798` |
| `Bits 4-5` | `>> 4` | `astro_venus_elong_shift_p7d` | `16.593` | `23.471` | `29.976` |
| `Bits 6-7` | `>> 6` | `astro_venus_illum_frac_shift_p7d` | `17.846` | `58.956` | `88.511` |
| `Bits 8-9` | `>> 8` | `astro_sun_ra_icrf_shift_p14d` | `24.961` | `308.05` | `334.73` |
| `Bits 10-11` | `>> 10` | `astro_sun_dec_icrf_shift_p14d` | `-14.448` | `-4.7164` | `5.7618` |
| `Bits 12-13` | `>> 12` | `astro_sun_ra_app_shift_p14d` | `25.276` | `308.39` | `335.04` |
| `Bits 14-15` | `>> 14` | `astro_sun_dec_app_shift_p14d` | `-14.343` | `-4.5873` | `5.8909` |

### Container: `packed_astro_container_088` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_azim_shift_p14d` | `123.1` | `129.52` | `135.2` |
| `Bits 2-3` | `>> 2` | `astro_sun_elev_shift_p14d` | `24.231` | `32.662` | `42.025` |
| `Bits 4-5` | `>> 4` | `astro_sun_app_mag_shift_p14d` | `-26.771` | `-26.758` | `-26.742` |
| `Bits 6-7` | `>> 6` | `astro_sun_dist_shift_p14d` | `0.98678` | `0.99274` | `1.0002` |
| `Bits 8-9` | `>> 8` | `astro_sun_dist_rate_shift_p14d` | `0.071491` | `0.22001` | `0.25096` |
| `Bits 10-11` | `>> 10` | `astro_sun_illum_frac_shift_p14d` | `25.228` | `62.482` | `90.075` |
| `Bits 12-13` | `>> 12` | `astro_moon_ra_icrf_shift_p14d` | `93.413` | `174.73` | `252.75` |
| `Bits 14-15` | `>> 14` | `astro_moon_dec_icrf_shift_p14d` | `-19.378` | `1.2952` | `19.518` |

### Container: `packed_astro_container_089` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_ra_app_shift_p14d` | `93.792` | `175.05` | `253.13` |
| `Bits 2-3` | `>> 2` | `astro_moon_dec_app_shift_p14d` | `-19.324` | `1.2926` | `19.607` |
| `Bits 4-5` | `>> 4` | `astro_moon_azim_shift_p14d` | `73.93` | `196.34` | `272.18` |
| `Bits 6-7` | `>> 6` | `astro_moon_elev_shift_p14d` | `-23.692` | `-8.7422` | `13.542` |
| `Bits 8-9` | `>> 8` | `astro_moon_app_mag_shift_p14d` | `-11.649` | `-10.599` | `-8.8875` |
| `Bits 10-11` | `>> 10` | `astro_moon_surf_bright_shift_p14d` | `4.2052` | `4.893` | `5.684` |
| `Bits 12-13` | `>> 12` | `astro_moon_dist_shift_p14d` | `0.0024798` | `0.0026044` | `0.0026966` |
| `Bits 14-15` | `>> 14` | `astro_moon_dist_rate_shift_p14d` | `-0.18319` | `0.021597` | `0.22003` |

### Container: `packed_astro_container_090` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_helio_dist_shift_p14d` | `0.98695` | `0.99226` | `0.99995` |
| `Bits 2-3` | `>> 2` | `astro_moon_helio_dist_rate_shift_p14d` | `-0.24968` | `0.46085` | `1.0221` |
| `Bits 4-5` | `>> 4` | `astro_moon_phase_angle_shift_p14d` | `36.724` | `75.544` | `119.71` |
| `Bits 6-7` | `>> 6` | `astro_moon_elong_shift_p14d` | `60.165` | `104.31` | `143.18` |
| `Bits 8-9` | `>> 8` | `astro_moon_illum_frac_shift_p14d` | `25.228` | `62.482` | `90.075` |
| `Bits 10-11` | `>> 10` | `astro_mars_ra_icrf_shift_p14d` | `299.21` | `320.42` | `340.53` |
| `Bits 12-13` | `>> 12` | `astro_mars_dec_icrf_shift_p14d` | `-21.512` | `-16.368` | `-9.2598` |
| `Bits 14-15` | `>> 14` | `astro_mars_ra_app_shift_p14d` | `298.75` | `319.98` | `340.11` |

### Container: `packed_astro_container_091` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_dec_app_shift_p14d` | `-21.447` | `-16.266` | `-9.1348` |
| `Bits 2-3` | `>> 2` | `astro_mars_azim_shift_p14d` | `161.03` | `165.15` | `171.35` |
| `Bits 4-5` | `>> 4` | `astro_mars_elev_shift_p14d` | `27.469` | `33.685` | `41.731` |
| `Bits 6-7` | `>> 6` | `astro_mars_app_mag_shift_p14d` | `1.1655` | `1.252` | `1.2963` |
| `Bits 8-9` | `>> 8` | `astro_mars_surf_bright_shift_p14d` | `4.052` | `4.0925` | `4.1392` |
| `Bits 10-11` | `>> 10` | `astro_mars_dist_shift_p14d` | `2.078` | `2.1809` | `2.2831` |
| `Bits 12-13` | `>> 12` | `astro_mars_dist_rate_shift_p14d` | `-6.7213` | `-6.641` | `-6.5201` |
| `Bits 14-15` | `>> 14` | `astro_mars_helio_dist_shift_p14d` | `1.3898` | `1.4072` | `1.4324` |

### Container: `packed_astro_container_092` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_helio_dist_rate_shift_p14d` | `-1.8354` | `-1.3979` | `-0.8328` |
| `Bits 2-3` | `>> 2` | `astro_mars_phase_angle_shift_p14d` | `15.894` | `20.453` | `24.662` |
| `Bits 4-5` | `>> 4` | `astro_mars_elong_shift_p14d` | `23.424` | `29.691` | `35.437` |
| `Bits 6-7` | `>> 6` | `astro_mars_illum_frac_shift_p14d` | `25.228` | `62.482` | `90.075` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_ra_icrf_shift_p14d` | `36.039` | `40.149` | `45.497` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_dec_icrf_shift_p14d` | `13.262` | `14.682` | `16.334` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_ra_app_shift_p14d` | `36.364` | `40.477` | `45.83` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_dec_app_shift_p14d` | `13.371` | `14.785` | `16.428` |

### Container: `packed_astro_container_093` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_azim_shift_p14d` | `64.252` | `77.289` | `88.55` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_elev_shift_p14d` | `-9.4643` | `7.8235` | `25.04` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_app_mag_shift_p14d` | `-2.2837` | `-2.144` | `-2.0543` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_surf_bright_shift_p14d` | `5.332` | `5.3535` | `5.369` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_dist_shift_p14d` | `5.1229` | `5.5136` | `5.8129` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_dist_rate_shift_p14d` | `15.279` | `22.457` | `26.891` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_helio_dist_shift_p14d` | `4.9931` | `4.9988` | `5.005` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_helio_dist_rate_shift_p14d` | `0.36392` | `0.38591` | `0.40503` |

### Container: `packed_astro_container_094` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_phase_angle_shift_p14d` | `6.2681` | `9.2746` | `11.098` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_elong_shift_p14d` | `33.106` | `54.245` | `76.929` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_illum_frac_shift_p14d` | `25.228` | `62.482` | `90.075` |
| `Bits 6-7` | `>> 6` | `astro_saturn_ra_icrf_shift_p14d` | `339.57` | `342.62` | `345.57` |
| `Bits 8-9` | `>> 8` | `astro_saturn_dec_icrf_shift_p14d` | `-10.344` | `-9.1386` | `-7.9821` |
| `Bits 10-11` | `>> 10` | `astro_saturn_ra_app_shift_p14d` | `339.88` | `342.93` | `345.88` |
| `Bits 12-13` | `>> 12` | `astro_saturn_dec_app_shift_p14d` | `-10.221` | `-9.0133` | `-7.8542` |
| `Bits 14-15` | `>> 14` | `astro_saturn_azim_shift_p14d` | `119.44` | `138.72` | `165.42` |

### Container: `packed_astro_container_095` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_elev_shift_p14d` | `17.496` | `32.589` | `42.32` |
| `Bits 2-3` | `>> 2` | `astro_saturn_app_mag_shift_p14d` | `0.98575` | `0.997` | `1.0605` |
| `Bits 4-5` | `>> 4` | `astro_saturn_surf_bright_shift_p14d` | `6.6877` | `6.712` | `6.7828` |
| `Bits 6-7` | `>> 6` | `astro_saturn_dist_shift_p14d` | `10.509` | `10.619` | `10.688` |
| `Bits 8-9` | `>> 8` | `astro_saturn_dist_rate_shift_p14d` | `-14.96` | `-4.0753` | `7.5964` |
| `Bits 10-11` | `>> 10` | `astro_saturn_helio_dist_shift_p14d` | `9.7109` | `9.7186` | `9.7263` |
| `Bits 12-13` | `>> 12` | `astro_saturn_helio_dist_rate_shift_p14d` | `-0.49998` | `-0.49718` | `-0.49391` |
| `Bits 14-15` | `>> 14` | `astro_saturn_phase_angle_shift_p14d` | `1.2352` | `2.3697` | `3.4192` |

### Container: `packed_astro_container_096` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_elong_shift_p14d` | `12.217` | `23.915` | `35.82` |
| `Bits 2-3` | `>> 2` | `astro_saturn_illum_frac_shift_p14d` | `25.228` | `62.482` | `90.075` |
| `Bits 4-5` | `>> 4` | `astro_mercury_ra_icrf_shift_p14d` | `17.408` | `272.56` | `313.8` |
| `Bits 6-7` | `>> 6` | `astro_mercury_dec_icrf_shift_p14d` | `-19.947` | `-2.1474` | `8.2513` |
| `Bits 8-9` | `>> 8` | `astro_mercury_ra_app_shift_p14d` | `17.719` | `272.91` | `314.13` |
| `Bits 10-11` | `>> 10` | `astro_mercury_dec_app_shift_p14d` | `-19.862` | `-2.0158` | `8.3786` |
| `Bits 12-13` | `>> 12` | `astro_mercury_azim_shift_p14d` | `114.34` | `135.79` | `151.69` |
| `Bits 14-15` | `>> 14` | `astro_mercury_elev_shift_p14d` | `26.125` | `29.513` | `40.224` |

### Container: `packed_astro_container_097` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mercury_app_mag_shift_p14d` | `-0.97175` | `-0.3105` | `1.2933` |
| `Bits 2-3` | `>> 2` | `astro_mercury_surf_bright_shift_p14d` | `2.2388` | `2.893` | `4.268` |
| `Bits 4-5` | `>> 4` | `astro_mercury_dist_shift_p14d` | `0.68659` | `1.1563` | `1.3338` |
| `Bits 6-7` | `>> 6` | `astro_mercury_dist_rate_shift_p14d` | `-26.917` | `-0.63894` | `15.115` |
| `Bits 8-9` | `>> 8` | `astro_mercury_helio_dist_shift_p14d` | `0.35531` | `0.42445` | `0.45619` |
| `Bits 10-11` | `>> 10` | `astro_mercury_helio_dist_rate_shift_p14d` | `-5.4262` | `1.7839` | `6.7691` |
| `Bits 12-13` | `>> 12` | `astro_mercury_phase_angle_shift_p14d` | `28.299` | `55.524` | `126.98` |
| `Bits 14-15` | `>> 14` | `astro_mercury_elong_shift_p14d` | `7.8838` | `14.307` | `18.468` |

### Container: `packed_astro_container_098` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mercury_illum_frac_shift_p14d` | `25.228` | `62.482` | `90.075` |
| `Bits 2-3` | `>> 2` | `astro_venus_ra_icrf_shift_p14d` | `201.39` | `293.78` | `327.75` |
| `Bits 4-5` | `>> 4` | `astro_venus_dec_icrf_shift_p14d` | `-21.429` | `-13.955` | `-1.9483` |
| `Bits 6-7` | `>> 6` | `astro_venus_ra_app_shift_p14d` | `201.74` | `294.13` | `328.07` |
| `Bits 8-9` | `>> 8` | `astro_venus_dec_app_shift_p14d` | `-21.377` | `-13.844` | `-1.816` |
| `Bits 10-11` | `>> 10` | `astro_venus_azim_shift_p14d` | `145.09` | `156.68` | `167.08` |
| `Bits 12-13` | `>> 12` | `astro_venus_elev_shift_p14d` | `29.162` | `34.276` | `43.586` |
| `Bits 14-15` | `>> 14` | `astro_venus_app_mag_shift_p14d` | `-3.9225` | `-3.8855` | `-3.878` |

### Container: `packed_astro_container_099` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_surf_bright_shift_p14d` | `0.86725` | `0.9485` | `1.035` |
| `Bits 2-3` | `>> 2` | `astro_venus_dist_shift_p14d` | `1.4129` | `1.5357` | `1.6331` |
| `Bits 4-5` | `>> 4` | `astro_venus_dist_rate_shift_p14d` | `5.26` | `7.0433` | `8.6359` |
| `Bits 6-7` | `>> 6` | `astro_venus_helio_dist_shift_p14d` | `0.72545` | `0.7269` | `0.72786` |
| `Bits 8-9` | `>> 8` | `astro_venus_helio_dist_rate_shift_p14d` | `-0.097116` | `0.073265` | `0.20561` |
| `Bits 10-11` | `>> 10` | `astro_venus_phase_angle_shift_p14d` | `22.486` | `31.677` | `40.937` |
| `Bits 12-13` | `>> 12` | `astro_venus_elong_shift_p14d` | `16.158` | `22.647` | `28.806` |
| `Bits 14-15` | `>> 14` | `astro_venus_illum_frac_shift_p14d` | `25.228` | `62.482` | `90.075` |

### Container: `packed_astro_container_100` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_ra_icrf_shift_p21d` | `23.34` | `311.67` | `336.39` |
| `Bits 2-3` | `>> 2` | `astro_sun_dec_icrf_shift_p21d` | `-12.695` | `-3.3438` | `6.4263` |
| `Bits 4-5` | `>> 4` | `astro_sun_ra_app_shift_p21d` | `23.654` | `312.01` | `336.71` |
| `Bits 6-7` | `>> 6` | `astro_sun_dec_app_shift_p21d` | `-12.584` | `-3.2134` | `6.5546` |
| `Bits 8-9` | `>> 8` | `astro_sun_azim_shift_p21d` | `122.64` | `128.73` | `134.11` |
| `Bits 10-11` | `>> 10` | `astro_sun_elev_shift_p21d` | `25.689` | `33.891` | `42.606` |
| `Bits 12-13` | `>> 12` | `astro_sun_app_mag_shift_p21d` | `-26.769` | `-26.756` | `-26.741` |
| `Bits 14-15` | `>> 14` | `astro_sun_dist_shift_p21d` | `0.98774` | `0.99366` | `1.0007` |

### Container: `packed_astro_container_101` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_dist_rate_shift_p21d` | `0.095634` | `0.22314` | `0.25232` |
| `Bits 2-3` | `>> 2` | `astro_sun_illum_frac_shift_p21d` | `23.149` | `64.683` | `90.839` |
| `Bits 4-5` | `>> 4` | `astro_moon_ra_icrf_shift_p21d` | `104.79` | `178.8` | `251.76` |
| `Bits 6-7` | `>> 6` | `astro_moon_dec_icrf_shift_p21d` | `-20.916` | `0.08285` | `19.317` |
| `Bits 8-9` | `>> 8` | `astro_moon_ra_app_shift_p21d` | `105.17` | `179.11` | `252.14` |
| `Bits 10-11` | `>> 10` | `astro_moon_dec_app_shift_p21d` | `-21.013` | `-0.05378` | `19.412` |
| `Bits 12-13` | `>> 12` | `astro_moon_azim_shift_p21d` | `86.008` | `210.27` | `274.85` |
| `Bits 14-15` | `>> 14` | `astro_moon_elev_shift_p21d` | `-23.539` | `-6.9025` | `15.481` |

### Container: `packed_astro_container_102` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_app_mag_shift_p21d` | `-11.707` | `-10.706` | `-8.736` |
| `Bits 2-3` | `>> 2` | `astro_moon_surf_bright_shift_p21d` | `4.185` | `4.876` | `5.673` |
| `Bits 4-5` | `>> 4` | `astro_moon_dist_shift_p21d` | `0.0024819` | `0.0026234` | `0.0027011` |
| `Bits 6-7` | `>> 6` | `astro_moon_dist_rate_shift_p21d` | `-0.17054` | `0.061274` | `0.23746` |
| `Bits 8-9` | `>> 8` | `astro_moon_helio_dist_shift_p21d` | `0.98742` | `0.99248` | `1.0001` |
| `Bits 10-11` | `>> 10` | `astro_moon_helio_dist_rate_shift_p21d` | `-0.26302` | `0.3406` | `1.0126` |
| `Bits 12-13` | `>> 12` | `astro_moon_phase_angle_shift_p21d` | `35.242` | `72.921` | `122.48` |
| `Bits 14-15` | `>> 14` | `astro_moon_elong_shift_p21d` | `57.394` | `106.93` | `144.67` |

### Container: `packed_astro_container_103` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_illum_frac_shift_p21d` | `23.149` | `64.683` | `90.839` |
| `Bits 2-3` | `>> 2` | `astro_mars_ra_icrf_shift_p21d` | `303.45` | `323.12` | `341.81` |
| `Bits 4-5` | `>> 4` | `astro_mars_dec_icrf_shift_p21d` | `-20.7` | `-15.529` | `-8.7499` |
| `Bits 6-7` | `>> 6` | `astro_mars_ra_app_shift_p21d` | `303` | `322.68` | `341.39` |
| `Bits 8-9` | `>> 8` | `astro_mars_dec_app_shift_p21d` | `-20.627` | `-15.424` | `-8.6239` |
| `Bits 10-11` | `>> 10` | `astro_mars_azim_shift_p21d` | `161.74` | `165.81` | `171.87` |
| `Bits 12-13` | `>> 12` | `astro_mars_elev_shift_p21d` | `28.495` | `34.659` | `42.29` |
| `Bits 14-15` | `>> 14` | `astro_mars_app_mag_shift_p21d` | `1.157` | `1.242` | `1.286` |

### Container: `packed_astro_container_104` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_surf_bright_shift_p21d` | `4.049` | `4.094` | `4.146` |
| `Bits 2-3` | `>> 2` | `astro_mars_dist_shift_p21d` | `2.0713` | `2.1674` | `2.2633` |
| `Bits 4-5` | `>> 4` | `astro_mars_dist_rate_shift_p21d` | `-6.7243` | `-6.6508` | `-6.5442` |
| `Bits 6-7` | `>> 6` | `astro_mars_helio_dist_shift_p21d` | `1.389` | `1.4045` | `1.4269` |
| `Bits 8-9` | `>> 8` | `astro_mars_helio_dist_rate_shift_p21d` | `-1.7611` | `-1.3304` | `-0.79239` |
| `Bits 10-11` | `>> 10` | `astro_mars_phase_angle_shift_p21d` | `16.814` | `21.025` | `24.924` |
| `Bits 12-13` | `>> 12` | `astro_mars_elong_shift_p21d` | `24.701` | `30.47` | `35.799` |
| `Bits 14-15` | `>> 14` | `astro_mars_illum_frac_shift_p21d` | `23.149` | `64.683` | `90.839` |

### Container: `packed_astro_container_105` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_ra_icrf_shift_p21d` | `36.723` | `40.79` | `45.878` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_dec_icrf_shift_p21d` | `13.51` | `14.891` | `16.444` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_ra_app_shift_p21d` | `37.048` | `41.118` | `46.211` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_dec_app_shift_p21d` | `13.618` | `14.993` | `16.538` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_azim_shift_p21d` | `67.079` | `78.81` | `89.282` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_elev_shift_p21d` | `-6.1054` | `10.094` | `26.152` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_app_mag_shift_p21d` | `-2.252` | `-2.13` | `-2.05` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_surf_bright_shift_p21d` | `5.331` | `5.35` | `5.368` |

### Container: `packed_astro_container_106` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_dist_shift_p21d` | `5.2046` | `5.5589` | `5.8284` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_dist_rate_shift_p21d` | `14.747` | `21.635` | `26.292` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_helio_dist_shift_p21d` | `4.9942` | `4.9996` | `5.0054` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_helio_dist_rate_shift_p21d` | `0.36799` | `0.38803` | `0.40673` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_phase_angle_shift_p21d` | `6.0433` | `8.9363` | `10.861` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_elong_shift_p21d` | `31.765` | `51.4` | `72.33` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_illum_frac_shift_p21d` | `23.149` | `64.683` | `90.839` |
| `Bits 14-15` | `>> 14` | `astro_saturn_ra_icrf_shift_p21d` | `340.16` | `343.02` | `345.75` |

### Container: `packed_astro_container_107` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_dec_icrf_shift_p21d` | `-10.11` | `-8.9814` | `-7.9114` |
| `Bits 2-3` | `>> 2` | `astro_saturn_ra_app_shift_p21d` | `340.47` | `343.33` | `346.06` |
| `Bits 4-5` | `>> 4` | `astro_saturn_dec_app_shift_p21d` | `-9.9868` | `-8.8559` | `-7.7834` |
| `Bits 6-7` | `>> 6` | `astro_saturn_azim_shift_p21d` | `122.78` | `141.74` | `167.44` |
| `Bits 8-9` | `>> 8` | `astro_saturn_elev_shift_p21d` | `20.727` | `34.248` | `42.673` |
| `Bits 10-11` | `>> 10` | `astro_saturn_app_mag_shift_p21d` | `0.988` | `1.01` | `1.063` |
| `Bits 12-13` | `>> 12` | `astro_saturn_surf_bright_shift_p21d` | `6.687` | `6.709` | `6.788` |
| `Bits 14-15` | `>> 14` | `astro_saturn_dist_shift_p21d` | `10.533` | `10.631` | `10.691` |

### Container: `packed_astro_container_108` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_dist_rate_shift_p21d` | `-15.608` | `-5.5952` | `5.3184` |
| `Bits 2-3` | `>> 2` | `astro_saturn_helio_dist_shift_p21d` | `9.7104` | `9.7176` | `9.7248` |
| `Bits 4-5` | `>> 4` | `astro_saturn_helio_dist_rate_shift_p21d` | `-0.50041` | `-0.49735` | `-0.49465` |
| `Bits 6-7` | `>> 6` | `astro_saturn_phase_angle_shift_p21d` | `1.1667` | `2.2094` | `3.2377` |
| `Bits 8-9` | `>> 8` | `astro_saturn_elong_shift_p21d` | `11.527` | `22.198` | `33.439` |
| `Bits 10-11` | `>> 10` | `astro_saturn_illum_frac_shift_p21d` | `23.149` | `64.683` | `90.839` |
| `Bits 12-13` | `>> 12` | `astro_mercury_ra_icrf_shift_p21d` | `16.776` | `23.699` | `316.73` |
| `Bits 14-15` | `>> 14` | `astro_mercury_dec_icrf_shift_p21d` | `-17.706` | `1.0776` | `8.722` |

### Container: `packed_astro_container_109` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mercury_ra_app_shift_p21d` | `17.086` | `24.016` | `317.06` |
| `Bits 2-3` | `>> 2` | `astro_mercury_dec_app_shift_p21d` | `-17.607` | `1.2095` | `8.8495` |
| `Bits 4-5` | `>> 4` | `astro_mercury_azim_shift_p21d` | `113.21` | `133.53` | `149.18` |
| `Bits 6-7` | `>> 6` | `astro_mercury_elev_shift_p21d` | `26.015` | `30.149` | `41.7` |
| `Bits 8-9` | `>> 8` | `astro_mercury_app_mag_shift_p21d` | `-1.024` | `-0.358` | `1.429` |
| `Bits 10-11` | `>> 10` | `astro_mercury_surf_bright_shift_p21d` | `2.179` | `2.841` | `4.32` |
| `Bits 12-13` | `>> 12` | `astro_mercury_dist_shift_p21d` | `0.67278` | `1.1849` | `1.3401` |
| `Bits 14-15` | `>> 14` | `astro_mercury_dist_rate_shift_p21d` | `-29.241` | `-3.2955` | `12.614` |

### Container: `packed_astro_container_110` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mercury_helio_dist_shift_p21d` | `0.35023` | `0.41985` | `0.45718` |
| `Bits 2-3` | `>> 2` | `astro_mercury_helio_dist_rate_shift_p21d` | `-5.8264` | `1.2948` | `5.9264` |
| `Bits 4-5` | `>> 4` | `astro_mercury_phase_angle_shift_p21d` | `27.267` | `51.66` | `131` |
| `Bits 6-7` | `>> 6` | `astro_mercury_elong_shift_p21d` | `7.2426` | `13.352` | `17.985` |
| `Bits 8-9` | `>> 8` | `astro_mercury_illum_frac_shift_p21d` | `23.149` | `64.683` | `90.839` |
| `Bits 10-11` | `>> 10` | `astro_venus_ra_icrf_shift_p21d` | `28.651` | `298.38` | `329.87` |
| `Bits 12-13` | `>> 12` | `astro_venus_dec_icrf_shift_p21d` | `-20.484` | `-12.563` | `-1.0941` |
| `Bits 14-15` | `>> 14` | `astro_venus_ra_app_shift_p21d` | `28.968` | `298.73` | `330.19` |

### Container: `packed_astro_container_111` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_dec_app_shift_p21d` | `-20.418` | `-12.447` | `-0.96173` |
| `Bits 2-3` | `>> 2` | `astro_venus_azim_shift_p21d` | `144.23` | `155.27` | `165.08` |
| `Bits 4-5` | `>> 4` | `astro_venus_elev_shift_p21d` | `29.425` | `35.354` | `44.231` |
| `Bits 6-7` | `>> 6` | `astro_venus_app_mag_shift_p21d` | `-3.913` | `-3.884` | `-3.878` |
| `Bits 8-9` | `>> 8` | `astro_venus_surf_bright_shift_p21d` | `0.862` | `0.938` | `1.018` |
| `Bits 10-11` | `>> 10` | `astro_venus_dist_shift_p21d` | `1.4388` | `1.55` | `1.6385` |
| `Bits 12-13` | `>> 12` | `astro_venus_dist_rate_shift_p21d` | `5.1291` | `6.8142` | `8.3277` |
| `Bits 14-15` | `>> 14` | `astro_venus_helio_dist_shift_p21d` | `0.72574` | `0.72707` | `0.7279` |

### Container: `packed_astro_container_112` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_helio_dist_rate_shift_p21d` | `-0.10743` | `0.051248` | `0.18656` |
| `Bits 2-3` | `>> 2` | `astro_venus_phase_angle_shift_p21d` | `21.878` | `30.48` | `39.094` |
| `Bits 4-5` | `>> 4` | `astro_venus_elong_shift_p21d` | `15.721` | `21.817` | `27.624` |
| `Bits 6-7` | `>> 6` | `astro_venus_illum_frac_shift_p21d` | `23.149` | `64.683` | `90.839` |
| `Bits 8-9` | `>> 8` | `astro_sun_ra_icrf_shift_p28d` | `21.724` | `315.26` | `338.05` |
| `Bits 10-11` | `>> 10` | `astro_sun_dec_icrf_shift_p28d` | `-10.849` | `-1.9633` | `7.085` |
| `Bits 12-13` | `>> 12` | `astro_sun_ra_app_shift_p28d` | `22.036` | `315.59` | `338.37` |
| `Bits 14-15` | `>> 14` | `astro_sun_dec_app_shift_p28d` | `-10.731` | `-1.832` | `7.2123` |

### Container: `packed_astro_container_113` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_azim_shift_p28d` | `122.16` | `127.94` | `133.01` |
| `Bits 2-3` | `>> 2` | `astro_sun_elev_shift_p28d` | `27.263` | `35.13` | `43.179` |
| `Bits 4-5` | `>> 4` | `astro_sun_app_mag_shift_p28d` | `-26.767` | `-26.754` | `-26.739` |
| `Bits 6-7` | `>> 6` | `astro_sun_dist_shift_p28d` | `0.98879` | `0.99459` | `1.0012` |
| `Bits 8-9` | `>> 8` | `astro_sun_dist_rate_shift_p28d` | `0.13103` | `0.2281` | `0.25322` |
| `Bits 10-11` | `>> 10` | `astro_sun_illum_frac_shift_p28d` | `21.207` | `59.438` | `87.618` |
| `Bits 12-13` | `>> 12` | `astro_moon_ra_icrf_shift_p28d` | `109.64` | `187.84` | `260.05` |
| `Bits 14-15` | `>> 14` | `astro_moon_dec_icrf_shift_p28d` | `-21.977` | `-3.3664` | `16.887` |

### Container: `packed_astro_container_114` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_ra_app_shift_p28d` | `110.01` | `188.15` | `260.43` |
| `Bits 2-3` | `>> 2` | `astro_moon_dec_app_shift_p28d` | `-22.021` | `-3.5012` | `16.774` |
| `Bits 4-5` | `>> 4` | `astro_moon_azim_shift_p28d` | `82.202` | `200.28` | `264.23` |
| `Bits 6-7` | `>> 6` | `astro_moon_elev_shift_p28d` | `-24.628` | `-2.6985` | `16.094` |
| `Bits 8-9` | `>> 8` | `astro_moon_app_mag_shift_p28d` | `-11.544` | `-10.463` | `-8.5698` |
| `Bits 10-11` | `>> 10` | `astro_moon_surf_bright_shift_p28d` | `4.2997` | `4.9585` | `5.7447` |
| `Bits 12-13` | `>> 12` | `astro_moon_dist_shift_p28d` | `0.0024634` | `0.0026044` | `0.0027004` |
| `Bits 14-15` | `>> 14` | `astro_moon_dist_rate_shift_p28d` | `-0.17723` | `0.03536` | `0.22057` |

### Container: `packed_astro_container_115` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_helio_dist_shift_p28d` | `0.99063` | `0.99374` | `1.0002` |
| `Bits 2-3` | `>> 2` | `astro_moon_helio_dist_rate_shift_p28d` | `-0.28441` | `0.34187` | `1.0649` |
| `Bits 4-5` | `>> 4` | `astro_moon_phase_angle_shift_p28d` | `41.191` | `79.12` | `125.17` |
| `Bits 6-7` | `>> 6` | `astro_moon_elong_shift_p28d` | `54.715` | `100.73` | `138.71` |
| `Bits 8-9` | `>> 8` | `astro_moon_illum_frac_shift_p28d` | `21.207` | `59.438` | `87.618` |
| `Bits 10-11` | `>> 10` | `astro_mars_ra_icrf_shift_p28d` | `307.66` | `325.79` | `343.09` |
| `Bits 12-13` | `>> 12` | `astro_mars_dec_icrf_shift_p28d` | `-19.785` | `-14.658` | `-8.2359` |
| `Bits 14-15` | `>> 14` | `astro_mars_ra_app_shift_p28d` | `307.2` | `325.35` | `342.67` |

### Container: `packed_astro_container_116` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_dec_app_shift_p28d` | `-19.704` | `-14.549` | `-8.109` |
| `Bits 2-3` | `>> 2` | `astro_mars_azim_shift_p28d` | `162.49` | `166.51` | `172.39` |
| `Bits 4-5` | `>> 4` | `astro_mars_elev_shift_p28d` | `29.622` | `35.663` | `42.85` |
| `Bits 6-7` | `>> 6` | `astro_mars_app_mag_shift_p28d` | `1.156` | `1.2325` | `1.281` |
| `Bits 8-9` | `>> 8` | `astro_mars_surf_bright_shift_p28d` | `4.0563` | `4.0995` | `4.1517` |
| `Bits 10-11` | `>> 10` | `astro_mars_dist_shift_p28d` | `2.0646` | `2.1538` | `2.2433` |
| `Bits 12-13` | `>> 12` | `astro_mars_dist_rate_shift_p28d` | `-6.7295` | `-6.6604` | `-6.5678` |
| `Bits 14-15` | `>> 14` | `astro_mars_helio_dist_shift_p28d` | `1.3882` | `1.4018` | `1.4217` |

### Container: `packed_astro_container_117` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_helio_dist_rate_shift_p28d` | `-1.6809` | `-1.2608` | `-0.75163` |
| `Bits 2-3` | `>> 2` | `astro_mars_phase_angle_shift_p28d` | `17.722` | `21.591` | `25.185` |
| `Bits 4-5` | `>> 4` | `astro_mars_elong_shift_p28d` | `25.954` | `31.24` | `36.16` |
| `Bits 6-7` | `>> 6` | `astro_mars_illum_frac_shift_p28d` | `21.207` | `59.438` | `87.618` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_ra_icrf_shift_p28d` | `37.472` | `41.45` | `46.263` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_dec_icrf_shift_p28d` | `13.775` | `15.103` | `16.554` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_ra_app_shift_p28d` | `37.798` | `41.779` | `46.596` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_dec_app_shift_p28d` | `13.882` | `15.204` | `16.647` |

### Container: `packed_astro_container_118` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_azim_shift_p28d` | `69.75` | `80.307` | `90.018` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_elev_shift_p28d` | `-2.7202` | `12.361` | `27.26` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_app_mag_shift_p28d` | `-2.2225` | `-2.116` | `-2.0455` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_surf_bright_shift_p28d` | `5.3293` | `5.3475` | `5.3647` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_dist_shift_p28d` | `5.2842` | `5.6025` | `5.8433` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_dist_rate_shift_p28d` | `14.207` | `20.77` | `25.545` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_helio_dist_shift_p28d` | `4.9953` | `5.0004` | `5.0058` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_helio_dist_rate_shift_p28d` | `0.37252` | `0.39043` | `0.40984` |

### Container: `packed_astro_container_119` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_phase_angle_shift_p28d` | `5.8157` | `8.5786` | `10.56` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_elong_shift_p28d` | `30.428` | `48.582` | `67.808` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_illum_frac_shift_p28d` | `21.207` | `59.438` | `87.618` |
| `Bits 6-7` | `>> 6` | `astro_saturn_ra_icrf_shift_p28d` | `340.76` | `343.42` | `345.93` |
| `Bits 8-9` | `>> 8` | `astro_saturn_dec_icrf_shift_p28d` | `-9.8737` | `-8.8254` | `-7.8417` |
| `Bits 10-11` | `>> 10` | `astro_saturn_ra_app_shift_p28d` | `341.07` | `343.73` | `346.24` |
| `Bits 12-13` | `>> 12` | `astro_saturn_dec_app_shift_p28d` | `-9.7501` | `-8.6995` | `-7.7135` |
| `Bits 14-15` | `>> 14` | `astro_saturn_azim_shift_p28d` | `126.31` | `144.9` | `169.49` |

### Container: `packed_astro_container_120` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_elev_shift_p28d` | `23.846` | `35.808` | `42.839` |
| `Bits 2-3` | `>> 2` | `astro_saturn_app_mag_shift_p28d` | `0.989` | `1.0205` | `1.0648` |
| `Bits 4-5` | `>> 4` | `astro_saturn_surf_bright_shift_p28d` | `6.6843` | `6.7175` | `6.7932` |
| `Bits 6-7` | `>> 6` | `astro_saturn_dist_shift_p28d` | `10.523` | `10.641` | `10.693` |
| `Bits 8-9` | `>> 8` | `astro_saturn_dist_rate_shift_p28d` | `-16.246` | `-7.0904` | `3.0282` |
| `Bits 10-11` | `>> 10` | `astro_saturn_helio_dist_shift_p28d` | `9.7099` | `9.7166` | `9.7233` |
| `Bits 12-13` | `>> 12` | `astro_saturn_helio_dist_rate_shift_p28d` | `-0.5005` | `-0.49765` | `-0.49537` |
| `Bits 14-15` | `>> 14` | `astro_saturn_phase_angle_shift_p28d` | `1.0823` | `2.0773` | `3.3106` |

### Container: `packed_astro_container_121` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_elong_shift_p28d` | `10.679` | `20.815` | `34.094` |
| `Bits 2-3` | `>> 2` | `astro_saturn_illum_frac_shift_p28d` | `21.207` | `59.438` | `87.618` |
| `Bits 4-5` | `>> 4` | `astro_mercury_ra_icrf_shift_p28d` | `16.34` | `23.403` | `319.67` |
| `Bits 6-7` | `>> 6` | `astro_mercury_dec_icrf_shift_p28d` | `-14.824` | `4.1292` | `9.3501` |
| `Bits 8-9` | `>> 8` | `astro_mercury_ra_app_shift_p28d` | `16.649` | `23.72` | `320` |
| `Bits 10-11` | `>> 10` | `astro_mercury_dec_app_shift_p28d` | `-14.712` | `4.2589` | `9.4769` |
| `Bits 12-13` | `>> 12` | `astro_mercury_azim_shift_p28d` | `112.01` | `130.65` | `146.44` |
| `Bits 14-15` | `>> 14` | `astro_mercury_elev_shift_p28d` | `26.5` | `30.807` | `43.197` |

### Container: `packed_astro_container_122` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mercury_app_mag_shift_p28d` | `-1.096` | `-0.404` | `1.5953` |
| `Bits 2-3` | `>> 2` | `astro_mercury_surf_bright_shift_p28d` | `2.1277` | `2.773` | `4.4203` |
| `Bits 4-5` | `>> 4` | `astro_mercury_dist_shift_p28d` | `0.66305` | `1.1447` | `1.3465` |
| `Bits 6-7` | `>> 6` | `astro_mercury_dist_rate_shift_p28d` | `-31.143` | `-6.0128` | `9.456` |
| `Bits 8-9` | `>> 8` | `astro_mercury_helio_dist_shift_p28d` | `0.34557` | `0.41093` | `0.45588` |
| `Bits 10-11` | `>> 10` | `astro_mercury_helio_dist_rate_shift_p28d` | `-6.4991` | `0.34104` | `6.3454` |
| `Bits 12-13` | `>> 12` | `astro_mercury_phase_angle_shift_p28d` | `25.044` | `53.898` | `133.23` |
| `Bits 14-15` | `>> 14` | `astro_mercury_elong_shift_p28d` | `7.034` | `12.73` | `17.173` |

### Container: `packed_astro_container_123` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mercury_illum_frac_shift_p28d` | `21.207` | `59.438` | `87.618` |
| `Bits 2-3` | `>> 2` | `astro_venus_ra_icrf_shift_p28d` | `26.616` | `302.94` | `331.97` |
| `Bits 4-5` | `>> 4` | `astro_venus_dec_icrf_shift_p28d` | `-19.26` | `-11.1` | `-0.23742` |
| `Bits 6-7` | `>> 6` | `astro_venus_ra_app_shift_p28d` | `26.931` | `303.29` | `332.29` |
| `Bits 8-9` | `>> 8` | `astro_venus_dec_app_shift_p28d` | `-19.181` | `-10.98` | `-0.10515` |
| `Bits 10-11` | `>> 10` | `astro_venus_azim_shift_p28d` | `143.35` | `153.84` | `163.06` |
| `Bits 12-13` | `>> 12` | `astro_venus_elev_shift_p28d` | `30.285` | `36.493` | `44.871` |
| `Bits 14-15` | `>> 14` | `astro_venus_app_mag_shift_p28d` | `-3.9045` | `-3.883` | `-3.878` |

### Container: `packed_astro_container_124` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_surf_bright_shift_p28d` | `0.85675` | `0.9265` | `1.001` |
| `Bits 2-3` | `>> 2` | `astro_venus_dist_shift_p28d` | `1.4639` | `1.5638` | `1.6438` |
| `Bits 4-5` | `>> 4` | `astro_venus_dist_rate_shift_p28d` | `4.9956` | `6.587` | `8.0277` |
| `Bits 6-7` | `>> 6` | `astro_venus_helio_dist_shift_p28d` | `0.72607` | `0.7272` | `0.72794` |
| `Bits 8-9` | `>> 8` | `astro_venus_helio_dist_rate_shift_p28d` | `-0.11748` | `0.028748` | `0.16356` |
| `Bits 10-11` | `>> 10` | `astro_venus_phase_angle_shift_p28d` | `21.269` | `29.283` | `37.267` |
| `Bits 12-13` | `>> 12` | `astro_venus_elong_shift_p28d` | `15.283` | `20.983` | `26.428` |
| `Bits 14-15` | `>> 14` | `astro_venus_illum_frac_shift_p28d` | `21.207` | `59.438` | `87.618` |

### Container: `packed_astro_container_125` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_ra_icrf_shift_p35d` | `20.111` | `318.8` | `339.71` |
| `Bits 2-3` | `>> 2` | `astro_sun_dec_icrf_shift_p35d` | `-8.9257` | `-0.57985` | `7.7376` |
| `Bits 4-5` | `>> 4` | `astro_sun_ra_app_shift_p35d` | `20.422` | `319.13` | `340.02` |
| `Bits 6-7` | `>> 6` | `astro_sun_dec_app_shift_p35d` | `-8.8037` | `-0.4479` | `7.8639` |
| `Bits 8-9` | `>> 8` | `astro_sun_azim_shift_p35d` | `121.69` | `127.13` | `131.9` |
| `Bits 10-11` | `>> 10` | `astro_sun_elev_shift_p35d` | `28.933` | `36.373` | `43.742` |
| `Bits 12-13` | `>> 12` | `astro_sun_app_mag_shift_p35d` | `-26.764` | `-26.752` | `-26.739` |
| `Bits 14-15` | `>> 14` | `astro_sun_dist_shift_p35d` | `0.98997` | `0.99553` | `1.0017` |

### Container: `packed_astro_container_126` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_dist_rate_shift_p35d` | `0.16978` | `0.23773` | `0.25566` |
| `Bits 2-3` | `>> 2` | `astro_sun_illum_frac_shift_p35d` | `19.275` | `57.148` | `88.511` |
| `Bits 4-5` | `>> 4` | `astro_moon_ra_icrf_shift_p35d` | `100.3` | `183.74` | `264.58` |
| `Bits 6-7` | `>> 6` | `astro_moon_dec_icrf_shift_p35d` | `-22.855` | `-2.1898` | `18.514` |
| `Bits 8-9` | `>> 8` | `astro_moon_ra_app_shift_p35d` | `100.68` | `184.06` | `264.97` |
| `Bits 10-11` | `>> 10` | `astro_moon_dec_app_shift_p35d` | `-22.857` | `-2.0579` | `18.513` |
| `Bits 12-13` | `>> 12` | `astro_moon_azim_shift_p35d` | `75.877` | `184.28` | `262.05` |
| `Bits 14-15` | `>> 14` | `astro_moon_elev_shift_p35d` | `-25.801` | `-6.9025` | `18.873` |

### Container: `packed_astro_container_127` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_app_mag_shift_p35d` | `-11.598` | `-10.415` | `-8.4475` |
| `Bits 2-3` | `>> 2` | `astro_moon_surf_bright_shift_p35d` | `4.268` | `4.968` | `5.8085` |
| `Bits 4-5` | `>> 4` | `astro_moon_dist_shift_p35d` | `0.0024547` | `0.0025939` | `0.0026971` |
| `Bits 6-7` | `>> 6` | `astro_moon_dist_rate_shift_p35d` | `-0.18844` | `-0.0019561` | `0.20857` |
| `Bits 8-9` | `>> 8` | `astro_moon_helio_dist_shift_p35d` | `0.99097` | `0.99651` | `1.0004` |
| `Bits 10-11` | `>> 10` | `astro_moon_helio_dist_rate_shift_p35d` | `-0.18975` | `0.49112` | `1.0977` |
| `Bits 12-13` | `>> 12` | `astro_moon_phase_angle_shift_p35d` | `39.619` | `81.782` | `127.92` |
| `Bits 14-15` | `>> 14` | `astro_moon_elong_shift_p35d` | `51.965` | `98.069` | `140.28` |

### Container: `packed_astro_container_128` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_illum_frac_shift_p35d` | `19.275` | `57.148` | `88.511` |
| `Bits 2-3` | `>> 2` | `astro_mars_ra_icrf_shift_p35d` | `311.83` | `328.45` | `344.36` |
| `Bits 4-5` | `>> 4` | `astro_mars_dec_icrf_shift_p35d` | `-18.773` | `-13.759` | `-7.7184` |
| `Bits 6-7` | `>> 6` | `astro_mars_ra_app_shift_p35d` | `311.37` | `328.01` | `343.94` |
| `Bits 8-9` | `>> 8` | `astro_mars_dec_app_shift_p35d` | `-18.685` | `-13.646` | `-7.5907` |
| `Bits 10-11` | `>> 10` | `astro_mars_azim_shift_p35d` | `163.28` | `167.25` | `172.94` |
| `Bits 12-13` | `>> 12` | `astro_mars_elev_shift_p35d` | `30.844` | `36.693` | `43.411` |
| `Bits 14-15` | `>> 14` | `astro_mars_app_mag_shift_p35d` | `1.1525` | `1.217` | `1.2775` |

### Container: `packed_astro_container_129` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_surf_bright_shift_p35d` | `4.0655` | `4.103` | `4.166` |
| `Bits 2-3` | `>> 2` | `astro_mars_dist_shift_p35d` | `2.0579` | `2.1403` | `2.2232` |
| `Bits 4-5` | `>> 4` | `astro_mars_dist_rate_shift_p35d` | `-6.7328` | `-6.6724` | `-6.5969` |
| `Bits 6-7` | `>> 6` | `astro_mars_helio_dist_shift_p35d` | `1.3875` | `1.3994` | `1.4167` |
| `Bits 8-9` | `>> 8` | `astro_mars_helio_dist_rate_shift_p35d` | `-1.5951` | `-1.1892` | `-0.71055` |
| `Bits 10-11` | `>> 10` | `astro_mars_phase_angle_shift_p35d` | `18.617` | `22.15` | `25.444` |
| `Bits 12-13` | `>> 12` | `astro_mars_elong_shift_p35d` | `27.184` | `32.002` | `36.519` |
| `Bits 14-15` | `>> 14` | `astro_mars_illum_frac_shift_p35d` | `19.275` | `57.148` | `88.511` |

### Container: `packed_astro_container_130` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_ra_icrf_shift_p35d` | `38.28` | `42.129` | `46.65` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_dec_icrf_shift_p35d` | `14.055` | `15.317` | `16.664` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_ra_app_shift_p35d` | `38.607` | `42.459` | `46.984` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_dec_app_shift_p35d` | `14.161` | `15.417` | `16.757` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_azim_shift_p35d` | `72.29` | `81.785` | `90.758` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_elev_shift_p35d` | `0.68078` | `14.623` | `28.366` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_app_mag_shift_p35d` | `-2.195` | `-2.103` | `-2.042` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_surf_bright_shift_p35d` | `5.3285` | `5.345` | `5.3615` |

### Container: `packed_astro_container_131` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_dist_shift_p35d` | `5.3614` | `5.6443` | `5.8577` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_dist_rate_shift_p35d` | `13.657` | `19.865` | `24.672` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_helio_dist_shift_p35d` | `4.9964` | `5.0012` | `5.0062` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_helio_dist_rate_shift_p35d` | `0.37619` | `0.39353` | `0.41009` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_phase_angle_shift_p35d` | `5.5855` | `8.2039` | `10.2` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_elong_shift_p35d` | `29.095` | `45.788` | `63.358` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_illum_frac_shift_p35d` | `19.275` | `57.148` | `88.511` |
| `Bits 14-15` | `>> 14` | `astro_saturn_ra_icrf_shift_p35d` | `341.36` | `343.81` | `346.1` |

### Container: `packed_astro_container_132` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_dec_icrf_shift_p35d` | `-9.6363` | `-8.6709` | `-7.7728` |
| `Bits 2-3` | `>> 2` | `astro_saturn_ra_app_shift_p35d` | `341.67` | `344.12` | `346.41` |
| `Bits 4-5` | `>> 4` | `astro_saturn_dec_app_shift_p35d` | `-9.5121` | `-8.5446` | `-7.6444` |
| `Bits 6-7` | `>> 6` | `astro_saturn_azim_shift_p35d` | `130.06` | `148.21` | `171.57` |
| `Bits 8-9` | `>> 8` | `astro_saturn_elev_shift_p35d` | `26.835` | `37.263` | `42.996` |
| `Bits 10-11` | `>> 10` | `astro_saturn_app_mag_shift_p35d` | `0.9875` | `1.03` | `1.0665` |
| `Bits 12-13` | `>> 12` | `astro_saturn_surf_bright_shift_p35d` | `6.682` | `6.73` | `6.7985` |
| `Bits 14-15` | `>> 14` | `astro_saturn_dist_shift_p35d` | `10.506` | `10.651` | `10.696` |

### Container: `packed_astro_container_133` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_dist_rate_shift_p35d` | `-16.872` | `-8.5545` | `0.73184` |
| `Bits 2-3` | `>> 2` | `astro_saturn_helio_dist_shift_p35d` | `9.7094` | `9.7156` | `9.7218` |
| `Bits 4-5` | `>> 4` | `astro_saturn_helio_dist_rate_shift_p35d` | `-0.50072` | `-0.49822` | `-0.49573` |
| `Bits 6-7` | `>> 6` | `astro_saturn_phase_angle_shift_p35d` | `0.9979` | `1.9443` | `3.4422` |
| `Bits 8-9` | `>> 8` | `astro_saturn_elong_shift_p35d` | `9.8385` | `19.479` | `35.624` |
| `Bits 10-11` | `>> 10` | `astro_saturn_illum_frac_shift_p35d` | `19.275` | `57.148` | `88.511` |
| `Bits 12-13` | `>> 12` | `astro_mercury_ra_icrf_shift_p35d` | `16.143` | `22.901` | `322.63` |
| `Bits 14-15` | `>> 14` | `astro_mercury_dec_icrf_shift_p35d` | `-11.311` | `4.5616` | `9.8678` |

### Container: `packed_astro_container_134` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mercury_ra_app_shift_p35d` | `16.452` | `23.217` | `322.95` |
| `Bits 2-3` | `>> 2` | `astro_mercury_dec_app_shift_p35d` | `-11.19` | `4.6902` | `9.994` |
| `Bits 4-5` | `>> 4` | `astro_mercury_azim_shift_p35d` | `110.64` | `127.57` | `143.35` |
| `Bits 6-7` | `>> 6` | `astro_mercury_elev_shift_p35d` | `27.421` | `31.58` | `44.664` |
| `Bits 8-9` | `>> 8` | `astro_mercury_app_mag_shift_p35d` | `-1.1725` | `-0.486` | `1.838` |
| `Bits 10-11` | `>> 10` | `astro_mercury_surf_bright_shift_p35d` | `2.0705` | `2.689` | `4.517` |
| `Bits 12-13` | `>> 12` | `astro_mercury_dist_shift_p35d` | `0.65155` | `1.0574` | `1.3535` |
| `Bits 14-15` | `>> 14` | `astro_mercury_dist_rate_shift_p35d` | `-32.875` | `-9.0269` | `6.5999` |

### Container: `packed_astro_container_135` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mercury_helio_dist_shift_p35d` | `0.34103` | `0.40146` | `0.44852` |
| `Bits 2-3` | `>> 2` | `astro_mercury_helio_dist_rate_shift_p35d` | `-6.8235` | `0.32913` | `6.9254` |
| `Bits 4-5` | `>> 4` | `astro_mercury_phase_angle_shift_p35d` | `23.823` | `70.086` | `136.16` |
| `Bits 6-7` | `>> 6` | `astro_mercury_elong_shift_p35d` | `6.6493` | `11.704` | `16.423` |
| `Bits 8-9` | `>> 8` | `astro_mercury_illum_frac_shift_p35d` | `19.275` | `57.148` | `88.511` |
| `Bits 10-11` | `>> 10` | `astro_venus_ra_icrf_shift_p35d` | `24.59` | `307.46` | `334.06` |
| `Bits 12-13` | `>> 12` | `astro_venus_dec_icrf_shift_p35d` | `-17.78` | `-9.5777` | `0.6205` |
| `Bits 14-15` | `>> 14` | `astro_venus_ra_app_shift_p35d` | `24.903` | `307.8` | `334.38` |

### Container: `packed_astro_container_136` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_dec_app_shift_p35d` | `-17.689` | `-9.4538` | `0.75251` |
| `Bits 2-3` | `>> 2` | `astro_venus_azim_shift_p35d` | `142.45` | `152.38` | `161.02` |
| `Bits 4-5` | `>> 4` | `astro_venus_elev_shift_p35d` | `31.369` | `37.683` | `45.506` |
| `Bits 6-7` | `>> 6` | `astro_venus_app_mag_shift_p35d` | `-3.8975` | `-3.882` | `-3.877` |
| `Bits 8-9` | `>> 8` | `astro_venus_surf_bright_shift_p35d` | `0.852` | `0.916` | `0.9835` |
| `Bits 10-11` | `>> 10` | `astro_venus_dist_shift_p35d` | `1.4881` | `1.5771` | `1.6489` |
| `Bits 12-13` | `>> 12` | `astro_venus_dist_rate_shift_p35d` | `4.8608` | `6.3621` | `7.7243` |
| `Bits 14-15` | `>> 14` | `astro_venus_helio_dist_shift_p35d` | `0.72635` | `0.72733` | `0.72798` |

### Container: `packed_astro_container_137` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_helio_dist_rate_shift_p35d` | `-0.12726` | `0.0059862` | `0.13715` |
| `Bits 2-3` | `>> 2` | `astro_venus_phase_angle_shift_p35d` | `20.659` | `28.085` | `35.451` |
| `Bits 4-5` | `>> 4` | `astro_venus_elong_shift_p35d` | `14.844` | `20.142` | `25.219` |
| `Bits 6-7` | `>> 6` | `astro_venus_illum_frac_shift_p35d` | `19.275` | `57.148` | `88.511` |

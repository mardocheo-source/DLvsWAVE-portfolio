# DLVS-Wave v2.0 Master Manifest & Decodification Report: Master 1D

> **Generated at**: `2026-08-27 14:11:42 UTC`  
> **Chronological Timeline**: `2024-01-01` to `2024-05-01` (`122` time steps)

## 1. Dataset Dimensions & Compression Summary

| Dimension | Raw Uncompressed | Quantized Bit-Packed (2-Bit / 16-Bit) | Reduction Ratio |
| :--- | :--- | :--- | :--- |
| **Feature Columns** | `1115` columns | `153` columns | **7.97x fewer fields** |
| **Record Count** | `122` rows | `122` rows | 1:1 Synchronized |
| **Storage Size** | `1,179,141 bytes` | `107,238 bytes` | **90.91% space saved** |
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
| **`astro_ceres`** | 165 | `icrf`, `icrf`, `app`, `app`, ... (+161 more) |
| **`astro_jupiter`** | 165 | `icrf`, `icrf`, `app`, `app`, ... (+161 more) |
| **`astro_mars`** | 165 | `icrf`, `icrf`, `app`, `app`, ... (+161 more) |
| **`astro_moon`** | 165 | `icrf`, `icrf`, `app`, `app`, ... (+161 more) |
| **`astro_saturn`** | 165 | `icrf`, `icrf`, `app`, `app`, ... (+161 more) |
| **`astro_sun`** | 110 | `icrf`, `icrf`, `app`, `app`, ... (+106 more) |
| **`astro_venus`** | 165 | `icrf`, `icrf`, `app`, `app`, ... (+161 more) |

## 4. Container Decodification Matrix & Quantile Codebook

This matrix allows 100% exact decompression of packed integer fields into their discrete quantile bins `[0, 1, 2, 3]`.

### Container: `packed_astro_container_000` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_ra_icrf` | `28.216` | `300.68` | `331.36` |
| `Bits 2-3` | `>> 2` | `astro_sun_dec_icrf` | `-17.603` | `-7.4185` | `4.4181` |
| `Bits 4-5` | `>> 4` | `astro_sun_ra_app` | `28.534` | `301.03` | `331.68` |
| `Bits 6-7` | `>> 6` | `astro_sun_dec_app` | `-17.515` | `-7.2935` | `4.5485` |
| `Bits 8-9` | `>> 8` | `astro_sun_azim` | `16.407` | `17.144` | `21.534` |
| `Bits 10-11` | `>> 10` | `astro_sun_elev` | `-63.39` | `-53.422` | `-41.411` |
| `Bits 12-13` | `>> 12` | `astro_sun_app_mag` | `-26.775` | `-26.762` | `-26.744` |
| `Bits 14-15` | `>> 14` | `astro_sun_dist` | `0.98516` | `0.99099` | `0.9992` |

### Container: `packed_astro_container_001` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_dist_rate` | `0.18272` | `0.3704` | `0.39676` |
| `Bits 2-3` | `>> 2` | `astro_sun_illum_frac` | `19.641` | `57.011` | `86.106` |
| `Bits 4-5` | `>> 4` | `astro_moon_ra_icrf` | `105.33` | `186.13` | `261.13` |
| `Bits 6-7` | `>> 6` | `astro_moon_dec_icrf` | `-21.405` | `-2.495` | `17.518` |
| `Bits 8-9` | `>> 8` | `astro_moon_ra_app` | `105.7` | `186.44` | `261.51` |
| `Bits 10-11` | `>> 10` | `astro_moon_dec_app` | `-21.356` | `-2.496` | `17.568` |
| `Bits 12-13` | `>> 12` | `astro_moon_azim` | `109.14` | `172.72` | `282.66` |
| `Bits 14-15` | `>> 14` | `astro_moon_elev` | `-30.445` | `5.7621` | `30.884` |

### Container: `packed_astro_container_002` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_app_mag` | `-11.54` | `-10.39` | `-8.44` |
| `Bits 2-3` | `>> 2` | `astro_moon_surf_bright` | `4.319` | `5.002` | `5.749` |
| `Bits 4-5` | `>> 4` | `astro_moon_dist` | `0.0024982` | `0.0025885` | `0.002661` |
| `Bits 6-7` | `>> 6` | `astro_moon_dist_rate` | `-0.26055` | `-0.0086646` | `0.24067` |
| `Bits 8-9` | `>> 8` | `astro_moon_helio_dist` | `0.98549` | `0.99143` | `0.99956` |
| `Bits 10-11` | `>> 10` | `astro_moon_helio_dist_rate` | `-0.338` | `0.3245` | `0.96295` |
| `Bits 12-13` | `>> 12` | `astro_moon_phase_angle` | `43.765` | `81.938` | `127.38` |
| `Bits 14-15` | `>> 14` | `astro_moon_elong` | `52.503` | `97.913` | `136.13` |

### Container: `packed_astro_container_003` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_illum_frac` | `19.641` | `57.011` | `86.106` |
| `Bits 2-3` | `>> 2` | `astro_saturn_ra_icrf` | `338.41` | `341.82` | `345.2` |
| `Bits 4-5` | `>> 4` | `astro_saturn_dec_icrf` | `-10.799` | `-9.455` | `-8.1257` |
| `Bits 6-7` | `>> 6` | `astro_saturn_ra_app` | `338.72` | `342.13` | `345.51` |
| `Bits 8-9` | `>> 8` | `astro_saturn_dec_app` | `-10.678` | `-9.3305` | `-7.9981` |
| `Bits 10-11` | `>> 10` | `astro_saturn_azim` | `41.744` | `68.56` | `314.78` |
| `Bits 12-13` | `>> 12` | `astro_saturn_elev` | `-55.128` | `-49.73` | `-42.093` |
| `Bits 14-15` | `>> 14` | `astro_saturn_app_mag` | `0.98025` | `0.991` | `1.0555` |

### Container: `packed_astro_container_004` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_surf_bright` | `6.6913` | `6.717` | `6.7722` |
| `Bits 2-3` | `>> 2` | `astro_saturn_dist` | `10.454` | `10.594` | `10.681` |
| `Bits 4-5` | `>> 4` | `astro_saturn_dist_rate` | `-13.757` | `-0.84875` | `12.415` |
| `Bits 6-7` | `>> 6` | `astro_saturn_helio_dist` | `9.7119` | `9.7206` | `9.7293` |
| `Bits 8-9` | `>> 8` | `astro_saturn_helio_dist_rate` | `-0.49952` | `-0.49626` | `-0.49286` |
| `Bits 10-11` | `>> 10` | `astro_saturn_phase_angle` | `1.3721` | `2.6562` | `3.8078` |
| `Bits 12-13` | `>> 12` | `astro_saturn_elong` | `13.58` | `27.007` | `40.403` |
| `Bits 14-15` | `>> 14` | `astro_saturn_illum_frac` | `19.641` | `57.011` | `86.106` |

### Container: `packed_astro_container_005` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_ra_icrf` | `34.881` | `38.933` | `44.744` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_dec_icrf` | `12.826` | `14.278` | `16.113` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_ra_app` | `35.205` | `39.26` | `45.076` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_dec_app` | `12.937` | `14.382` | `16.209` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_azim` | `291.06` | `311.61` | `334.99` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_elev` | `-27.597` | `-18.873` | `-3.9757` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_app_mag` | `-2.3533` | `-2.1755` | `-2.0635` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_surf_bright` | `5.3342` | `5.3575` | `5.368` |

### Container: `packed_astro_container_006` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_dist` | `4.9556` | `5.4184` | `5.7803` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_dist_rate` | `16.781` | `24.516` | `27.378` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_helio_dist` | `4.9909` | `4.9973` | `5.0041` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_helio_dist_rate` | `0.3553` | `0.37993` | `0.40356` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_phase_angle` | `6.7096` | `9.8898` | `11.037` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_elong` | `35.802` | `60.013` | `86.368` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_illum_frac` | `19.641` | `57.011` | `86.106` |
| `Bits 14-15` | `>> 14` | `astro_mars_ra_icrf` | `290.65` | `314.97` | `337.96` |

### Container: `packed_astro_container_007` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_dec_icrf` | `-22.81` | `-17.941` | `-10.267` |
| `Bits 2-3` | `>> 2` | `astro_mars_ra_app` | `290.19` | `314.52` | `337.54` |
| `Bits 4-5` | `>> 4` | `astro_mars_dec_app` | `-22.764` | `-17.848` | `-10.144` |
| `Bits 6-7` | `>> 6` | `astro_mars_azim` | `62.484` | `62.683` | `62.897` |
| `Bits 8-9` | `>> 8` | `astro_mars_elev` | `-57.211` | `-50.058` | `-39.86` |
| `Bits 10-11` | `>> 10` | `astro_mars_app_mag` | `1.184` | `1.2635` | `1.3075` |
| `Bits 12-13` | `>> 12` | `astro_mars_surf_bright` | `4.0553` | `4.096` | `4.125` |
| `Bits 14-15` | `>> 14` | `astro_mars_dist` | `2.0914` | `2.2079` | `2.3219` |

### Container: `packed_astro_container_008` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_dist_rate` | `-6.8524` | `-6.7963` | `-6.4398` |
| `Bits 2-3` | `>> 2` | `astro_mars_helio_dist` | `1.3916` | `1.4131` | `1.4439` |
| `Bits 4-5` | `>> 4` | `astro_mars_helio_dist_rate` | `-1.9663` | `-1.5261` | `-0.91255` |
| `Bits 6-7` | `>> 6` | `astro_mars_phase_angle` | `14.021` | `19.291` | `24.132` |
| `Bits 8-9` | `>> 8` | `astro_mars_elong` | `20.799` | `28.105` | `34.707` |
| `Bits 10-11` | `>> 10` | `astro_mars_illum_frac` | `19.641` | `57.011` | `86.106` |
| `Bits 12-13` | `>> 12` | `astro_ceres_ra_icrf` | `266.77` | `278.19` | `287.28` |
| `Bits 14-15` | `>> 14` | `astro_ceres_dec_icrf` | `-23.459` | `-23.035` | `-22.289` |

### Container: `packed_astro_container_009` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_ceres_ra_app` | `267.12` | `278.55` | `287.65` |
| `Bits 2-3` | `>> 2` | `astro_ceres_dec_app` | `-23.421` | `-23.018` | `-22.299` |
| `Bits 4-5` | `>> 4` | `astro_ceres_azim` | `84.665` | `97.705` | `110.87` |
| `Bits 6-7` | `>> 6` | `astro_ceres_elev` | `-39.535` | `-26.502` | `-12.049` |
| `Bits 8-9` | `>> 8` | `astro_ceres_app_mag` | `8.8422` | `8.9945` | `9.0508` |
| `Bits 10-11` | `>> 10` | `astro_ceres_surf_bright` | `6.7368` | `6.896` | `6.9725` |
| `Bits 12-13` | `>> 12` | `astro_ceres_dist` | `2.7326` | `3.1071` | `3.4155` |
| `Bits 14-15` | `>> 14` | `astro_ceres_dist_rate` | `-22.246` | `-20.251` | `-15.273` |

### Container: `packed_astro_container_010` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_ceres_helio_dist` | `2.7849` | `2.8091` | `2.8326` |
| `Bits 2-3` | `>> 2` | `astro_ceres_helio_dist_rate` | `1.3188` | `1.3677` | `1.4008` |
| `Bits 4-5` | `>> 4` | `astro_ceres_phase_angle` | `14.096` | `18.409` | `20.183` |
| `Bits 6-7` | `>> 6` | `astro_ceres_elong` | `43.511` | `63.526` | `85.351` |
| `Bits 8-9` | `>> 8` | `astro_ceres_illum_frac` | `19.641` | `57.011` | `86.106` |
| `Bits 10-11` | `>> 10` | `astro_venus_ra_icrf` | `244.71` | `284.49` | `323.48` |
| `Bits 12-13` | `>> 12` | `astro_venus_dec_icrf` | `-21.203` | `-16.495` | `-3.6453` |
| `Bits 14-15` | `>> 14` | `astro_venus_ra_app` | `245.05` | `284.85` | `323.8` |

### Container: `packed_astro_container_011` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_dec_app` | `-21.17` | `-16.396` | `-3.5137` |
| `Bits 2-3` | `>> 2` | `astro_venus_azim` | `39.387` | `57.321` | `73.88` |
| `Bits 4-5` | `>> 4` | `astro_venus_elev` | `-50.425` | `-46.843` | `-41.799` |
| `Bits 6-7` | `>> 6` | `astro_venus_app_mag` | `-3.9453` | `-3.8925` | `-3.879` |
| `Bits 8-9` | `>> 8` | `astro_venus_surf_bright` | `0.8775` | `0.971` | `1.0702` |
| `Bits 10-11` | `>> 10` | `astro_venus_dist` | `1.3583` | `1.5059` | `1.622` |
| `Bits 12-13` | `>> 12` | `astro_venus_dist_rate` | `5.5043` | `7.4137` | `9.0903` |
| `Bits 14-15` | `>> 14` | `astro_venus_helio_dist` | `0.72438` | `0.72656` | `0.72778` |

### Container: `packed_astro_container_012` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_helio_dist_rate` | `-0.075854` | `0.11508` | `0.21465` |
| `Bits 2-3` | `>> 2` | `astro_venus_phase_angle` | `23.698` | `34.075` | `44.683` |
| `Bits 4-5` | `>> 4` | `astro_venus_elong` | `17.025` | `24.289` | `31.132` |
| `Bits 6-7` | `>> 6` | `astro_venus_illum_frac` | `19.641` | `57.011` | `86.106` |
| `Bits 8-9` | `>> 8` | `astro_sun_ra_icrf_shift_m35d` | `296.4` | `318.8` | `339.71` |
| `Bits 10-11` | `>> 10` | `astro_sun_dec_icrf_shift_m35d` | `-19.798` | `-13.709` | `-5.8828` |
| `Bits 12-13` | `>> 12` | `astro_sun_ra_app_shift_m35d` | `296.75` | `319.13` | `340.02` |
| `Bits 14-15` | `>> 14` | `astro_sun_dec_app_shift_m35d` | `-19.726` | `-13.601` | `-5.7553` |

### Container: `packed_astro_container_013` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_azim_shift_m35d` | `16.938` | `18.93` | `24.043` |
| `Bits 2-3` | `>> 2` | `astro_sun_elev_shift_m35d` | `-65.368` | `-59.672` | `-51.874` |
| `Bits 4-5` | `>> 4` | `astro_sun_app_mag_shift_m35d` | `-26.777` | `-26.77` | `-26.76` |
| `Bits 6-7` | `>> 6` | `astro_sun_dist_shift_m35d` | `0.98417` | `0.98724` | `0.99201` |
| `Bits 8-9` | `>> 8` | `astro_sun_dist_rate_shift_m35d` | `0.093566` | `0.25827` | `0.3877` |
| `Bits 10-11` | `>> 10` | `astro_sun_illum_frac_shift_m35d` | `17.066` | `53.421` | `85.137` |
| `Bits 12-13` | `>> 12` | `astro_moon_ra_icrf_shift_m35d` | `99.252` | `177.19` | `250.58` |
| `Bits 14-15` | `>> 14` | `astro_moon_dec_icrf_shift_m35d` | `-18.182` | `0.91601` | `18.87` |

### Container: `packed_astro_container_014` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_ra_app_shift_m35d` | `99.633` | `177.5` | `250.94` |
| `Bits 2-3` | `>> 2` | `astro_moon_dec_app_shift_m35d` | `-18.273` | `1.0476` | `18.864` |
| `Bits 4-5` | `>> 4` | `astro_moon_azim_shift_m35d` | `107.42` | `186.24` | `284.33` |
| `Bits 6-7` | `>> 6` | `astro_moon_elev_shift_m35d` | `-34.519` | `6.7741` | `39.246` |
| `Bits 8-9` | `>> 8` | `astro_moon_app_mag_shift_m35d` | `-11.505` | `-10.304` | `-8.235` |
| `Bits 10-11` | `>> 10` | `astro_moon_surf_bright_shift_m35d` | `4.361` | `5.072` | `5.7705` |
| `Bits 12-13` | `>> 12` | `astro_moon_dist_shift_m35d` | `0.0024941` | `0.0025951` | `0.0026658` |
| `Bits 14-15` | `>> 14` | `astro_moon_dist_rate_shift_m35d` | `-0.25516` | `0.015213` | `0.24833` |

### Container: `packed_astro_container_015` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_helio_dist_shift_m35d` | `0.98444` | `0.98715` | `0.99198` |
| `Bits 2-3` | `>> 2` | `astro_moon_helio_dist_rate_shift_m35d` | `-0.36663` | `0.3406` | `0.9608` |
| `Bits 4-5` | `>> 4` | `astro_moon_phase_angle_shift_m35d` | `45.33` | `86.076` | `131.21` |
| `Bits 6-7` | `>> 6` | `astro_moon_elong_shift_m35d` | `48.683` | `93.776` | `134.56` |
| `Bits 8-9` | `>> 8` | `astro_moon_illum_frac_shift_m35d` | `17.066` | `53.421` | `85.137` |
| `Bits 10-11` | `>> 10` | `astro_saturn_ra_icrf_shift_m35d` | `337.48` | `339.82` | `342.28` |
| `Bits 12-13` | `>> 12` | `astro_saturn_dec_icrf_shift_m35d` | `-11.162` | `-10.244` | `-9.2739` |
| `Bits 14-15` | `>> 14` | `astro_saturn_ra_app_shift_m35d` | `337.8` | `340.13` | `342.59` |

### Container: `packed_astro_container_016` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_dec_app_shift_m35d` | `-11.041` | `-10.121` | `-9.149` |
| `Bits 2-3` | `>> 2` | `astro_saturn_azim_shift_m35d` | `31.346` | `301.05` | `325.94` |
| `Bits 4-5` | `>> 4` | `astro_saturn_elev_shift_m35d` | `-56.139` | `-53.295` | `-48.82` |
| `Bits 6-7` | `>> 6` | `astro_saturn_app_mag_shift_m35d` | `0.974` | `0.987` | `0.991` |
| `Bits 8-9` | `>> 8` | `astro_saturn_surf_bright_shift_m35d` | `6.682` | `6.704` | `6.7195` |
| `Bits 10-11` | `>> 10` | `astro_saturn_dist_shift_m35d` | `10.538` | `10.651` | `10.696` |
| `Bits 12-13` | `>> 12` | `astro_saturn_dist_rate_shift_m35d` | `-2.6336` | `6.9429` | `15.9` |
| `Bits 14-15` | `>> 14` | `astro_saturn_helio_dist_shift_m35d` | `9.7195` | `9.7256` | `9.7318` |

### Container: `packed_astro_container_017` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_helio_dist_rate_shift_m35d` | `-0.49688` | `-0.49411` | `-0.49178` |
| `Bits 2-3` | `>> 2` | `astro_saturn_phase_angle_shift_m35d` | `0.99795` | `1.9445` | `3.1999` |
| `Bits 4-5` | `>> 4` | `astro_saturn_elong_shift_m35d` | `9.8385` | `19.478` | `33.468` |
| `Bits 6-7` | `>> 6` | `astro_saturn_illum_frac_shift_m35d` | `17.066` | `53.421` | `85.137` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_ra_icrf_shift_m35d` | `34.149` | `36.323` | `39.617` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_dec_icrf_shift_m35d` | `12.535` | `13.366` | `14.507` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_ra_app_shift_m35d` | `34.473` | `36.648` | `39.944` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_dec_app_shift_m35d` | `12.647` | `13.474` | `14.61` |

### Container: `packed_astro_container_018` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_azim_shift_m35d` | `286.09` | `300.11` | `315.27` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_elev_shift_m35d` | `-20.409` | `-10.925` | `1.3022` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_app_mag_shift_m35d` | `-2.417` | `-2.27` | `-2.157` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_surf_bright_shift_m35d` | `5.3555` | `5.364` | `5.37` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_dist_shift_m35d` | `4.8148` | `5.1581` | `5.4735` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_dist_rate_shift_m35d` | `23.689` | `26.505` | `27.797` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_helio_dist_shift_m35d` | `4.9891` | `4.9935` | `4.9982` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_helio_dist_rate_shift_m35d` | `0.34765` | `0.36502` | `0.38329` |

### Container: `packed_astro_container_019` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_phase_angle_shift_m35d` | `9.5491` | `10.697` | `11.2` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_elong_shift_m35d` | `56.704` | `74.948` | `94.489` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_illum_frac_shift_m35d` | `17.066` | `53.421` | `85.137` |
| `Bits 6-7` | `>> 6` | `astro_mars_ra_icrf_shift_m35d` | `284.3` | `301.84` | `318.87` |
| `Bits 8-9` | `>> 8` | `astro_mars_dec_icrf_shift_m35d` | `-23.543` | `-21.176` | `-17.059` |
| `Bits 10-11` | `>> 10` | `astro_mars_ra_app_shift_m35d` | `284.65` | `302.19` | `319.2` |
| `Bits 12-13` | `>> 12` | `astro_mars_dec_app_shift_m35d` | `-23.512` | `-21.108` | `-16.961` |
| `Bits 14-15` | `>> 14` | `astro_mars_azim_shift_m35d` | `61.699` | `62.763` | `62.974` |

### Container: `packed_astro_container_020` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_elev_shift_m35d` | `-58.683` | `-54.596` | `-48.87` |
| `Bits 2-3` | `>> 2` | `astro_mars_app_mag_shift_m35d` | `1.258` | `1.29` | `1.325` |
| `Bits 4-5` | `>> 4` | `astro_mars_surf_bright_shift_m35d` | `4.0555` | `4.094` | `4.1115` |
| `Bits 6-7` | `>> 6` | `astro_mars_dist_shift_m35d` | `2.1925` | `2.2747` | `2.3531` |
| `Bits 8-9` | `>> 8` | `astro_mars_dist_rate_shift_m35d` | `-6.8692` | `-6.7014` | `-6.2251` |
| `Bits 10-11` | `>> 10` | `astro_mars_helio_dist_shift_m35d` | `1.4097` | `1.43` | `1.4541` |
| `Bits 12-13` | `>> 12` | `astro_mars_helio_dist_rate_shift_m35d` | `-2.0569` | `-1.8043` | `-1.4539` |
| `Bits 14-15` | `>> 14` | `astro_mars_phase_angle_shift_m35d` | `12.431` | `16.29` | `19.958` |

### Container: `packed_astro_container_021` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_elong_shift_m35d` | `18.545` | `23.973` | `29.014` |
| `Bits 2-3` | `>> 2` | `astro_mars_illum_frac_shift_m35d` | `17.066` | `53.421` | `85.137` |
| `Bits 4-5` | `>> 4` | `astro_ceres_ra_icrf_shift_m35d` | `263.18` | `271.79` | `279.55` |
| `Bits 6-7` | `>> 6` | `astro_ceres_dec_icrf_shift_m35d` | `-23.095` | `-22.683` | `-21.931` |
| `Bits 8-9` | `>> 8` | `astro_ceres_ra_app_shift_m35d` | `263.54` | `272.15` | `279.91` |
| `Bits 10-11` | `>> 10` | `astro_ceres_dec_app_shift_m35d` | `-23.074` | `-22.681` | `-21.949` |
| `Bits 12-13` | `>> 12` | `astro_ceres_azim_shift_m35d` | `80.455` | `90.346` | `99.372` |
| `Bits 14-15` | `>> 14` | `astro_ceres_elev_shift_m35d` | `-42.988` | `-34.239` | `-24.664` |

### Container: `packed_astro_container_022` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_ceres_app_mag_shift_m35d` | `8.984` | `9.032` | `9.06` |
| `Bits 2-3` | `>> 2` | `astro_ceres_surf_bright_shift_m35d` | `6.6775` | `6.813` | `6.912` |
| `Bits 4-5` | `>> 4` | `astro_ceres_dist_shift_m35d` | `3.0604` | `3.2961` | `3.487` |
| `Bits 6-7` | `>> 6` | `astro_ceres_dist_rate_shift_m35d` | `-20.754` | `-17.634` | `-13.52` |
| `Bits 8-9` | `>> 8` | `astro_ceres_helio_dist_shift_m35d` | `2.7778` | `2.7951` | `2.8122` |
| `Bits 10-11` | `>> 10` | `astro_ceres_helio_dist_rate_shift_m35d` | `1.3621` | `1.3889` | `1.4073` |
| `Bits 12-13` | `>> 12` | `astro_ceres_phase_angle_shift_m35d` | `12.586` | `16.11` | `18.844` |
| `Bits 14-15` | `>> 14` | `astro_ceres_elong_shift_m35d` | `37.958` | `51.78` | `66.288` |

### Container: `packed_astro_container_023` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_ceres_illum_frac_shift_m35d` | `17.066` | `53.421` | `85.137` |
| `Bits 2-3` | `>> 2` | `astro_venus_ra_icrf_shift_m35d` | `268.49` | `297.07` | `324.4` |
| `Bits 4-5` | `>> 4` | `astro_venus_dec_icrf_shift_m35d` | `-21.824` | `-19.934` | `-15.085` |
| `Bits 6-7` | `>> 6` | `astro_venus_ra_app_shift_m35d` | `268.85` | `297.42` | `324.72` |
| `Bits 8-9` | `>> 8` | `astro_venus_dec_app_shift_m35d` | `-21.813` | `-19.978` | `-14.979` |
| `Bits 10-11` | `>> 10` | `astro_venus_azim_shift_m35d` | `54.722` | `68.035` | `76.497` |
| `Bits 12-13` | `>> 12` | `astro_venus_elev_shift_m35d` | `-51.079` | `-49.203` | `-46.241` |
| `Bits 14-15` | `>> 14` | `astro_venus_app_mag_shift_m35d` | `-3.9675` | `-3.918` | `-3.8885` |

### Container: `packed_astro_container_024` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_surf_bright_shift_m35d` | `0.9585` | `1.028` | `1.1` |
| `Bits 2-3` | `>> 2` | `astro_venus_dist_shift_m35d` | `1.3101` | `1.4242` | `1.5232` |
| `Bits 4-5` | `>> 4` | `astro_venus_dist_rate_shift_m35d` | `7.1749` | `8.3802` | `9.5387` |
| `Bits 6-7` | `>> 6` | `astro_venus_helio_dist_shift_m35d` | `0.72319` | `0.72597` | `0.72782` |
| `Bits 8-9` | `>> 8` | `astro_venus_helio_dist_rate_shift_m35d` | `0.091608` | `0.19431` | `0.22514` |
| `Bits 10-11` | `>> 10` | `astro_venus_phase_angle_shift_m35d` | `32.704` | `40.146` | `47.884` |
| `Bits 12-13` | `>> 12` | `astro_venus_elong_shift_m35d` | `23.352` | `28.3` | `33.028` |
| `Bits 14-15` | `>> 14` | `astro_venus_illum_frac_shift_m35d` | `17.066` | `53.421` | `85.137` |

### Container: `packed_astro_container_025` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_ra_icrf_shift_m28d` | `290.72` | `315.26` | `338.05` |
| `Bits 2-3` | `>> 2` | `astro_sun_dec_icrf_shift_m28d` | `-19.394` | `-12.522` | `-3.8351` |
| `Bits 4-5` | `>> 4` | `astro_sun_ra_app_shift_m28d` | `291.07` | `315.59` | `338.36` |
| `Bits 6-7` | `>> 6` | `astro_sun_dec_app_shift_m28d` | `-19.319` | `-12.41` | `-3.7051` |
| `Bits 8-9` | `>> 8` | `astro_sun_azim_shift_m28d` | `16.741` | `18.427` | `23.497` |
| `Bits 10-11` | `>> 10` | `astro_sun_elev_shift_m28d` | `-65.015` | `-58.509` | `-49.802` |
| `Bits 12-13` | `>> 12` | `astro_sun_app_mag_shift_m28d` | `-26.776` | `-26.768` | `-26.756` |
| `Bits 14-15` | `>> 14` | `astro_sun_dist_shift_m28d` | `0.98433` | `0.98789` | `0.99339` |

### Container: `packed_astro_container_026` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_dist_rate_shift_m28d` | `0.11209` | `0.27696` | `0.3937` |
| `Bits 2-3` | `>> 2` | `astro_sun_illum_frac_shift_m28d` | `20.532` | `57.011` | `85.641` |
| `Bits 4-5` | `>> 4` | `astro_moon_ra_icrf_shift_m28d` | `106.37` | `186.13` | `256.24` |
| `Bits 6-7` | `>> 6` | `astro_moon_dec_icrf_shift_m28d` | `-21.405` | `-2.495` | `17.22` |
| `Bits 8-9` | `>> 8` | `astro_moon_ra_app_shift_m28d` | `106.75` | `186.44` | `256.61` |
| `Bits 10-11` | `>> 10` | `astro_moon_dec_app_shift_m28d` | `-21.356` | `-2.496` | `17.269` |
| `Bits 12-13` | `>> 12` | `astro_moon_azim_shift_m28d` | `108.75` | `165.46` | `281.88` |
| `Bits 14-15` | `>> 14` | `astro_moon_elev_shift_m28d` | `-31.609` | `6.4893` | `38.105` |

### Container: `packed_astro_container_027` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_app_mag_shift_m28d` | `-11.531` | `-10.389` | `-8.4923` |
| `Bits 2-3` | `>> 2` | `astro_moon_surf_bright_shift_m28d` | `4.3445` | `5.0225` | `5.727` |
| `Bits 4-5` | `>> 4` | `astro_moon_dist_shift_m28d` | `0.0025052` | `0.0025977` | `0.002661` |
| `Bits 6-7` | `>> 6` | `astro_moon_dist_rate_shift_m28d` | `-0.2758` | `-0.03675` | `0.24012` |
| `Bits 8-9` | `>> 8` | `astro_moon_helio_dist_shift_m28d` | `0.9846` | `0.98779` | `0.99245` |
| `Bits 10-11` | `>> 10` | `astro_moon_helio_dist_rate_shift_m28d` | `-0.40195` | `0.20012` | `0.94199` |
| `Bits 12-13` | `>> 12` | `astro_moon_phase_angle_shift_m28d` | `44.516` | `81.938` | `126.12` |
| `Bits 14-15` | `>> 14` | `astro_moon_elong_shift_m28d` | `53.765` | `97.913` | `135.38` |

### Container: `packed_astro_container_028` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_illum_frac_shift_m28d` | `20.532` | `57.011` | `85.641` |
| `Bits 2-3` | `>> 2` | `astro_saturn_ra_icrf_shift_m28d` | `337.67` | `340.22` | `342.88` |
| `Bits 4-5` | `>> 4` | `astro_saturn_dec_icrf_shift_m28d` | `-11.091` | `-10.087` | `-9.0374` |
| `Bits 6-7` | `>> 6` | `astro_saturn_ra_app_shift_m28d` | `337.98` | `340.53` | `343.19` |
| `Bits 8-9` | `>> 8` | `astro_saturn_dec_app_shift_m28d` | `-10.97` | `-9.9643` | `-8.912` |
| `Bits 10-11` | `>> 10` | `astro_saturn_azim_shift_m28d` | `33.544` | `297.74` | `323.59` |
| `Bits 12-13` | `>> 12` | `astro_saturn_elev_shift_m28d` | `-55.988` | `-52.59` | `-47.509` |
| `Bits 14-15` | `>> 14` | `astro_saturn_app_mag_shift_m28d` | `0.97525` | `0.988` | `1.006` |

### Container: `packed_astro_container_029` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_surf_bright_shift_m28d` | `6.6843` | `6.7065` | `6.723` |
| `Bits 2-3` | `>> 2` | `astro_saturn_dist_shift_m28d` | `10.553` | `10.641` | `10.693` |
| `Bits 4-5` | `>> 4` | `astro_saturn_dist_rate_shift_m28d` | `-4.9724` | `5.3922` | `15.221` |
| `Bits 6-7` | `>> 6` | `astro_saturn_helio_dist_shift_m28d` | `9.718` | `9.7246` | `9.7313` |
| `Bits 8-9` | `>> 8` | `astro_saturn_helio_dist_rate_shift_m28d` | `-0.49731` | `-0.49474` | `-0.49191` |
| `Bits 10-11` | `>> 10` | `astro_saturn_phase_angle_shift_m28d` | `1.0825` | `2.0773` | `3.0655` |
| `Bits 12-13` | `>> 12` | `astro_saturn_elong_shift_m28d` | `10.679` | `20.815` | `31.882` |
| `Bits 14-15` | `>> 14` | `astro_saturn_illum_frac_shift_m28d` | `20.532` | `57.011` | `85.641` |

### Container: `packed_astro_container_030` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_ra_icrf_shift_m28d` | `34.278` | `36.791` | `40.558` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_dec_icrf_shift_m28d` | `12.588` | `13.534` | `14.816` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_ra_app_shift_m28d` | `34.602` | `37.117` | `40.886` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_dec_app_shift_m28d` | `12.699` | `13.642` | `14.918` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_azim_shift_m28d` | `287.21` | `302.48` | `319.21` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_elev_shift_m28d` | `-22.255` | `-12.667` | `0.21525` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_app_mag_shift_m28d` | `-2.404` | `-2.249` | `-2.135` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_surf_bright_shift_m28d` | `5.3513` | `5.363` | `5.3697` |

### Container: `packed_astro_container_031` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_dist_shift_m28d` | `4.8429` | `5.2122` | `5.5429` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_dist_rate_shift_m28d` | `22.494` | `26.262` | `27.735` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_helio_dist_shift_m28d` | `4.9895` | `4.9943` | `4.9994` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_helio_dist_rate_shift_m28d` | `0.34867` | `0.36913` | `0.38726` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_phase_angle_shift_m28d` | `9.0599` | `10.573` | `11.169` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_elong_shift_m28d` | `52.413` | `71.897` | `92.845` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_illum_frac_shift_m28d` | `20.532` | `57.011` | `85.641` |
| `Bits 14-15` | `>> 14` | `astro_mars_ra_icrf_shift_m28d` | `285.73` | `304.66` | `322.92` |

### Container: `packed_astro_container_032` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_dec_icrf_shift_m28d` | `-23.422` | `-20.616` | `-15.832` |
| `Bits 2-3` | `>> 2` | `astro_mars_ra_app_shift_m28d` | `286.09` | `305` | `323.25` |
| `Bits 4-5` | `>> 4` | `astro_mars_dec_app_shift_m28d` | `-23.389` | `-20.543` | `-15.728` |
| `Bits 6-7` | `>> 6` | `astro_mars_azim_shift_m28d` | `61.891` | `62.734` | `62.956` |
| `Bits 8-9` | `>> 8` | `astro_mars_elev_shift_m28d` | `-58.409` | `-53.776` | `-47.231` |
| `Bits 10-11` | `>> 10` | `astro_mars_app_mag_shift_m28d` | `1.2465` | `1.285` | `1.321` |
| `Bits 12-13` | `>> 12` | `astro_mars_surf_bright_shift_m28d` | `4.0563` | `4.096` | `4.1137` |
| `Bits 14-15` | `>> 14` | `astro_mars_dist_shift_m28d` | `2.1723` | `2.2614` | `2.3469` |

### Container: `packed_astro_container_033` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_dist_rate_shift_m28d` | `-6.8655` | `-6.7487` | `-6.2714` |
| `Bits 2-3` | `>> 2` | `astro_mars_helio_dist_shift_m28d` | `1.4054` | `1.4264` | `1.452` |
| `Bits 4-5` | `>> 4` | `astro_mars_helio_dist_rate_shift_m28d` | `-2.0401` | `-1.7537` | `-1.3548` |
| `Bits 6-7` | `>> 6` | `astro_mars_phase_angle_shift_m28d` | `12.751` | `16.901` | `20.822` |
| `Bits 8-9` | `>> 8` | `astro_mars_elong_shift_m28d` | `19.001` | `24.821` | `30.191` |
| `Bits 10-11` | `>> 10` | `astro_mars_illum_frac_shift_m28d` | `20.532` | `57.011` | `85.641` |
| `Bits 12-13` | `>> 12` | `astro_ceres_ra_icrf_shift_m28d` | `263.91` | `273.12` | `281.27` |
| `Bits 14-15` | `>> 14` | `astro_ceres_dec_icrf_shift_m28d` | `-23.167` | `-22.768` | `-22.009` |

### Container: `packed_astro_container_034` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_ceres_ra_app_shift_m28d` | `264.26` | `273.48` | `281.64` |
| `Bits 2-3` | `>> 2` | `astro_ceres_dec_app_shift_m28d` | `-23.143` | `-22.763` | `-22.025` |
| `Bits 4-5` | `>> 4` | `astro_ceres_azim_shift_m28d` | `81.323` | `91.843` | `101.57` |
| `Bits 6-7` | `>> 6` | `astro_ceres_elev_shift_m28d` | `-42.31` | `-32.733` | `-22.214` |
| `Bits 8-9` | `>> 8` | `astro_ceres_app_mag_shift_m28d` | `8.969` | `9.0255` | `9.0587` |
| `Bits 10-11` | `>> 10` | `astro_ceres_surf_bright_shift_m28d` | `6.6898` | `6.8315` | `6.931` |
| `Bits 12-13` | `>> 12` | `astro_ceres_dist_shift_m28d` | `2.9975` | `3.2605` | `3.4734` |
| `Bits 14-15` | `>> 14` | `astro_ceres_dist_rate_shift_m28d` | `-21.342` | `-18.214` | `-13.878` |

### Container: `packed_astro_container_035` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_ceres_helio_dist_shift_m28d` | `2.7792` | `2.7979` | `2.8164` |
| `Bits 2-3` | `>> 2` | `astro_ceres_helio_dist_rate_shift_m28d` | `1.3543` | `1.3851` | `1.4061` |
| `Bits 4-5` | `>> 4` | `astro_ceres_phase_angle_shift_m28d` | `12.895` | `16.617` | `19.354` |
| `Bits 6-7` | `>> 6` | `astro_ceres_elong_shift_m28d` | `39.061` | `54.09` | `69.965` |
| `Bits 8-9` | `>> 8` | `astro_ceres_illum_frac_shift_m28d` | `20.532` | `57.011` | `85.641` |
| `Bits 10-11` | `>> 10` | `astro_venus_ra_icrf_shift_m28d` | `270.82` | `301.64` | `330.77` |
| `Bits 12-13` | `>> 12` | `astro_venus_dec_icrf_shift_m28d` | `-21.707` | `-19.521` | `-13.068` |
| `Bits 14-15` | `>> 14` | `astro_venus_ra_app_shift_m28d` | `271.17` | `301.99` | `331.09` |

### Container: `packed_astro_container_036` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_dec_app_shift_m28d` | `-21.714` | `-19.513` | `-12.954` |
| `Bits 2-3` | `>> 2` | `astro_venus_azim_shift_m28d` | `51.356` | `66.07` | `76.068` |
| `Bits 4-5` | `>> 4` | `astro_venus_elev_shift_m28d` | `-50.967` | `-48.738` | `-45.44` |
| `Bits 6-7` | `>> 6` | `astro_venus_app_mag_shift_m28d` | `-3.9632` | `-3.912` | `-3.8832` |
| `Bits 8-9` | `>> 8` | `astro_venus_surf_bright_shift_m28d` | `0.94175` | `1.0165` | `1.0942` |
| `Bits 10-11` | `>> 10` | `astro_venus_dist_shift_m28d` | `1.32` | `1.4413` | `1.545` |
| `Bits 12-13` | `>> 12` | `astro_venus_dist_rate_shift_m28d` | `6.8465` | `8.1878` | `9.4513` |
| `Bits 14-15` | `>> 14` | `astro_venus_helio_dist_shift_m28d` | `0.72343` | `0.72636` | `0.72794` |

### Container: `packed_astro_container_037` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_helio_dist_rate_shift_m28d` | `0.059174` | `0.18452` | `0.22339` |
| `Bits 2-3` | `>> 2` | `astro_venus_phase_angle_shift_m28d` | `30.908` | `38.92` | `47.237` |
| `Bits 4-5` | `>> 4` | `astro_venus_elong_shift_m28d` | `22.113` | `27.509` | `32.653` |
| `Bits 6-7` | `>> 6` | `astro_venus_illum_frac_shift_m28d` | `20.532` | `57.011` | `85.641` |
| `Bits 8-9` | `>> 8` | `astro_sun_ra_icrf_shift_m21d` | `284.97` | `311.67` | `336.39` |
| `Bits 10-11` | `>> 10` | `astro_sun_dec_icrf_shift_m21d` | `-18.973` | `-11.296` | `-1.7658` |
| `Bits 12-13` | `>> 12` | `astro_sun_ra_app_shift_m21d` | `285.33` | `312.01` | `336.71` |
| `Bits 14-15` | `>> 14` | `astro_sun_dec_app_shift_m21d` | `-18.894` | `-11.18` | `-1.6344` |

### Container: `packed_astro_container_038` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_azim_shift_m21d` | `16.608` | `18.005` | `22.971` |
| `Bits 2-3` | `>> 2` | `astro_sun_elev_shift_m21d` | `-64.641` | `-57.297` | `-47.703` |
| `Bits 4-5` | `>> 4` | `astro_sun_app_mag_shift_m21d` | `-26.776` | `-26.767` | `-26.753` |
| `Bits 6-7` | `>> 6` | `astro_sun_dist_shift_m21d` | `0.98451` | `0.98859` | `0.99478` |
| `Bits 8-9` | `>> 8` | `astro_sun_dist_rate_shift_m21d` | `0.13069` | `0.30031` | `0.39711` |
| `Bits 10-11` | `>> 10` | `astro_sun_illum_frac_shift_m21d` | `16` | `50.799` | `84.104` |
| `Bits 12-13` | `>> 12` | `astro_moon_ra_icrf_shift_m21d` | `101.07` | `187.7` | `267.8` |
| `Bits 14-15` | `>> 14` | `astro_moon_dec_icrf_shift_m21d` | `-21.24` | `-2.792` | `15.311` |

### Container: `packed_astro_container_039` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_ra_app_shift_m21d` | `101.46` | `188.01` | `268.18` |
| `Bits 2-3` | `>> 2` | `astro_moon_dec_app_shift_m21d` | `-21.335` | `-2.9259` | `15.422` |
| `Bits 4-5` | `>> 4` | `astro_moon_azim_shift_m21d` | `103.39` | `153.37` | `281.32` |
| `Bits 6-7` | `>> 6` | `astro_moon_elev_shift_m21d` | `-35.758` | `-2.6188` | `35.131` |
| `Bits 8-9` | `>> 8` | `astro_moon_app_mag_shift_m21d` | `-11.4` | `-10.102` | `-8.119` |
| `Bits 10-11` | `>> 10` | `astro_moon_surf_bright_shift_m21d` | `4.394` | `5.121` | `5.837` |
| `Bits 12-13` | `>> 12` | `astro_moon_dist_shift_m21d` | `0.0024824` | `0.002579` | `0.0026589` |
| `Bits 14-15` | `>> 14` | `astro_moon_dist_rate_shift_m21d` | `-0.27636` | `-0.047728` | `0.21714` |

### Container: `packed_astro_container_040` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_helio_dist_shift_m21d` | `0.98483` | `0.99025` | `0.99413` |
| `Bits 2-3` | `>> 2` | `astro_moon_helio_dist_rate_shift_m21d` | `-0.36665` | `0.18776` | `0.86393` |
| `Bits 4-5` | `>> 4` | `astro_moon_phase_angle_shift_m21d` | `46.99` | `89.085` | `132.84` |
| `Bits 6-7` | `>> 6` | `astro_moon_elong_shift_m21d` | `47.055` | `90.759` | `132.9` |
| `Bits 8-9` | `>> 8` | `astro_moon_illum_frac_shift_m21d` | `16` | `50.799` | `84.104` |
| `Bits 10-11` | `>> 10` | `astro_saturn_ra_icrf_shift_m21d` | `337.85` | `340.61` | `343.47` |
| `Bits 12-13` | `>> 12` | `astro_saturn_dec_icrf_shift_m21d` | `-11.019` | `-9.9301` | `-8.8032` |
| `Bits 14-15` | `>> 14` | `astro_saturn_ra_app_shift_m21d` | `338.16` | `340.93` | `343.78` |

### Container: `packed_astro_container_041` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_dec_app_shift_m21d` | `-10.898` | `-9.8066` | `-8.6773` |
| `Bits 2-3` | `>> 2` | `astro_saturn_azim_shift_m21d` | `35.684` | `60.499` | `321.3` |
| `Bits 4-5` | `>> 4` | `astro_saturn_elev_shift_m21d` | `-55.829` | `-51.836` | `-46.382` |
| `Bits 6-7` | `>> 6` | `astro_saturn_app_mag_shift_m21d` | `0.976` | `0.989` | `1.022` |
| `Bits 8-9` | `>> 8` | `astro_saturn_surf_bright_shift_m21d` | `6.687` | `6.709` | `6.726` |
| `Bits 10-11` | `>> 10` | `astro_saturn_dist_shift_m21d` | `10.533` | `10.631` | `10.691` |
| `Bits 12-13` | `>> 12` | `astro_saturn_dist_rate_shift_m21d` | `-7.2699` | `3.836` | `14.533` |
| `Bits 14-15` | `>> 14` | `astro_saturn_helio_dist_shift_m21d` | `9.7165` | `9.7236` | `9.7308` |

### Container: `packed_astro_container_042` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_helio_dist_rate_shift_m21d` | `-0.49772` | `-0.49524` | `-0.49216` |
| `Bits 2-3` | `>> 2` | `astro_saturn_phase_angle_shift_m21d` | `1.1669` | `2.2093` | `3.238` |
| `Bits 4-5` | `>> 4` | `astro_saturn_elong_shift_m21d` | `11.527` | `22.199` | `33.438` |
| `Bits 6-7` | `>> 6` | `astro_saturn_illum_frac_shift_m21d` | `16` | `50.799` | `84.104` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_ra_icrf_shift_m21d` | `34.415` | `37.287` | `41.546` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_dec_icrf_shift_m21d` | `12.643` | `13.71` | `15.133` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_ra_app_shift_m21d` | `34.739` | `37.613` | `41.874` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_dec_app_shift_m21d` | `12.754` | `13.817` | `15.234` |

### Container: `packed_astro_container_043` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_azim_shift_m21d` | `288.33` | `304.89` | `323.24` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_elev_shift_m21d` | `-23.904` | `-14.336` | `-0.85663` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_app_mag_shift_m21d` | `-2.391` | `-2.229` | `-2.114` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_surf_bright_shift_m21d` | `5.347` | `5.362` | `5.369` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_dist_shift_m21d` | `4.8711` | `5.2655` | `5.6086` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_dist_rate_shift_m21d` | `21.18` | `25.957` | `27.67` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_helio_dist_shift_m21d` | `4.9898` | `4.995` | `5.0005` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_helio_dist_rate_shift_m21d` | `0.3502` | `0.3718` | `0.3908` |

### Container: `packed_astro_container_044` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_phase_angle_shift_m21d` | `8.5269` | `10.447` | `11.134` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_elong_shift_m21d` | `48.181` | `68.878` | `91.211` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_illum_frac_shift_m21d` | `16` | `50.799` | `84.104` |
| `Bits 6-7` | `>> 6` | `astro_mars_ra_icrf_shift_m21d` | `287.17` | `307.46` | `326.93` |
| `Bits 8-9` | `>> 8` | `astro_mars_dec_icrf_shift_m21d` | `-23.289` | `-20.011` | `-14.531` |
| `Bits 10-11` | `>> 10` | `astro_mars_ra_app_shift_m21d` | `287.53` | `307.8` | `327.25` |
| `Bits 12-13` | `>> 12` | `astro_mars_dec_app_shift_m21d` | `-23.252` | `-19.933` | `-14.422` |
| `Bits 14-15` | `>> 14` | `astro_mars_azim_shift_m21d` | `62.065` | `62.702` | `62.943` |

### Container: `packed_astro_container_045` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_elev_shift_m21d` | `-58.125` | `-52.913` | `-45.504` |
| `Bits 2-3` | `>> 2` | `astro_mars_app_mag_shift_m21d` | `1.23` | `1.282` | `1.319` |
| `Bits 4-5` | `>> 4` | `astro_mars_surf_bright_shift_m21d` | `4.055` | `4.093` | `4.112` |
| `Bits 6-7` | `>> 6` | `astro_mars_dist_shift_m21d` | `2.152` | `2.2481` | `2.3407` |
| `Bits 8-9` | `>> 8` | `astro_mars_dist_rate_shift_m21d` | `-6.8626` | `-6.7833` | `-6.3157` |
| `Bits 10-11` | `>> 10` | `astro_mars_helio_dist_shift_m21d` | `1.4015` | `1.4229` | `1.45` |
| `Bits 12-13` | `>> 12` | `astro_mars_helio_dist_rate_shift_m21d` | `-2.0227` | `-1.7006` | `-1.2507` |
| `Bits 14-15` | `>> 14` | `astro_mars_phase_angle_shift_m21d` | `13.07` | `17.507` | `21.671` |

### Container: `packed_astro_container_046` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_elong_shift_m21d` | `19.455` | `25.657` | `31.349` |
| `Bits 2-3` | `>> 2` | `astro_mars_illum_frac_shift_m21d` | `16` | `50.799` | `84.104` |
| `Bits 4-5` | `>> 4` | `astro_ceres_ra_icrf_shift_m21d` | `264.63` | `274.43` | `282.91` |
| `Bits 6-7` | `>> 6` | `astro_ceres_dec_icrf_shift_m21d` | `-23.235` | `-22.845` | `-22.084` |
| `Bits 8-9` | `>> 8` | `astro_ceres_ra_app_shift_m21d` | `264.98` | `274.79` | `283.28` |
| `Bits 10-11` | `>> 10` | `astro_ceres_dec_app_shift_m21d` | `-23.207` | `-22.837` | `-22.098` |
| `Bits 12-13` | `>> 12` | `astro_ceres_azim_shift_m21d` | `82.177` | `93.323` | `103.81` |
| `Bits 14-15` | `>> 14` | `astro_ceres_elev_shift_m21d` | `-41.626` | `-31.207` | `-19.724` |

### Container: `packed_astro_container_047` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_ceres_app_mag_shift_m21d` | `8.954` | `9.018` | `9.057` |
| `Bits 2-3` | `>> 2` | `astro_ceres_surf_bright_shift_m21d` | `6.702` | `6.849` | `6.947` |
| `Bits 4-5` | `>> 4` | `astro_ceres_dist_shift_m21d` | `2.933` | `3.2237` | `3.4594` |
| `Bits 6-7` | `>> 6` | `astro_ceres_dist_rate_shift_m21d` | `-21.827` | `-18.764` | `-14.232` |
| `Bits 8-9` | `>> 8` | `astro_ceres_helio_dist_shift_m21d` | `2.7806` | `2.8007` | `2.8204` |
| `Bits 10-11` | `>> 10` | `astro_ceres_helio_dist_rate_shift_m21d` | `1.3461` | `1.381` | `1.4049` |
| `Bits 12-13` | `>> 12` | `astro_ceres_phase_angle_shift_m21d` | `13.201` | `17.102` | `19.79` |
| `Bits 14-15` | `>> 14` | `astro_ceres_elong_shift_m21d` | `40.168` | `56.419` | `73.705` |

### Container: `packed_astro_container_048` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_ceres_illum_frac_shift_m21d` | `16` | `50.799` | `84.104` |
| `Bits 2-3` | `>> 2` | `astro_venus_ra_icrf_shift_m21d` | `265.17` | `298.38` | `329.87` |
| `Bits 4-5` | `>> 4` | `astro_venus_dec_icrf_shift_m21d` | `-21.582` | `-19.064` | `-10.887` |
| `Bits 6-7` | `>> 6` | `astro_venus_ra_app_shift_m21d` | `265.53` | `298.73` | `330.19` |
| `Bits 8-9` | `>> 8` | `astro_venus_dec_app_shift_m21d` | `-21.61` | `-19.03` | `-10.766` |
| `Bits 10-11` | `>> 10` | `astro_venus_azim_shift_m21d` | `48.105` | `63.991` | `75.593` |
| `Bits 12-13` | `>> 12` | `astro_venus_elev_shift_m21d` | `-50.851` | `-48.253` | `-44.485` |
| `Bits 14-15` | `>> 14` | `astro_venus_app_mag_shift_m21d` | `-3.958` | `-3.906` | `-3.88` |

### Container: `packed_astro_container_049` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_surf_bright_shift_m21d` | `0.925` | `1.005` | `1.088` |
| `Bits 2-3` | `>> 2` | `astro_venus_dist_shift_m21d` | `1.3297` | `1.4581` | `1.5658` |
| `Bits 4-5` | `>> 4` | `astro_venus_dist_rate_shift_m21d` | `6.5166` | `7.9983` | `9.363` |
| `Bits 6-7` | `>> 6` | `astro_venus_helio_dist_shift_m21d` | `0.72367` | `0.72672` | `0.7279` |
| `Bits 8-9` | `>> 8` | `astro_venus_helio_dist_rate_shift_m21d` | `0.02551` | `0.16938` | `0.22152` |
| `Bits 10-11` | `>> 10` | `astro_venus_phase_angle_shift_m21d` | `29.112` | `37.701` | `46.594` |
| `Bits 12-13` | `>> 12` | `astro_venus_elong_shift_m21d` | `20.862` | `26.713` | `32.275` |
| `Bits 14-15` | `>> 14` | `astro_venus_illum_frac_shift_m21d` | `16` | `50.799` | `84.104` |

### Container: `packed_astro_container_050` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_ra_icrf_shift_m14d` | `24.961` | `308.05` | `334.72` |
| `Bits 2-3` | `>> 2` | `astro_sun_dec_icrf_shift_m14d` | `-18.533` | `-10.033` | `0.30893` |
| `Bits 4-5` | `>> 4` | `astro_sun_ra_app_shift_m14d` | `25.275` | `308.39` | `335.04` |
| `Bits 6-7` | `>> 6` | `astro_sun_dec_app_shift_m14d` | `-18.451` | `-9.9132` | `0.44102` |
| `Bits 8-9` | `>> 8` | `astro_sun_azim_shift_m14d` | `16.522` | `17.657` | `22.469` |
| `Bits 10-11` | `>> 10` | `astro_sun_elev_shift_m14d` | `-64.244` | `-56.041` | `-45.593` |
| `Bits 12-13` | `>> 12` | `astro_sun_app_mag_shift_m14d` | `-26.776` | `-26.765` | `-26.751` |
| `Bits 14-15` | `>> 14` | `astro_sun_dist_shift_m14d` | `0.98471` | `0.98934` | `0.9962` |

### Container: `packed_astro_container_051` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_dist_rate_shift_m14d` | `0.14888` | `0.32589` | `0.40038` |
| `Bits 2-3` | `>> 2` | `astro_sun_illum_frac_shift_m14d` | `15.679` | `48.42` | `81.939` |
| `Bits 4-5` | `>> 4` | `astro_moon_ra_icrf_shift_m14d` | `92.209` | `178.93` | `258.47` |
| `Bits 6-7` | `>> 6` | `astro_moon_dec_icrf_shift_m14d` | `-19.177` | `0.47482` | `19.776` |
| `Bits 8-9` | `>> 8` | `astro_moon_ra_app_shift_m14d` | `92.589` | `179.24` | `258.84` |
| `Bits 10-11` | `>> 10` | `astro_moon_dec_app_shift_m14d` | `-19.141` | `0.47232` | `19.721` |
| `Bits 12-13` | `>> 12` | `astro_moon_azim_shift_m14d` | `105.64` | `169.42` | `288.83` |
| `Bits 14-15` | `>> 14` | `astro_moon_elev_shift_m14d` | `-33.606` | `-2.2857` | `30.67` |

### Container: `packed_astro_container_052` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_app_mag_shift_m14d` | `-11.354` | `-10.078` | `-8.0695` |
| `Bits 2-3` | `>> 2` | `astro_moon_surf_bright_shift_m14d` | `4.4392` | `5.195` | `5.8785` |
| `Bits 4-5` | `>> 4` | `astro_moon_dist_shift_m14d` | `0.0024862` | `0.0025795` | `0.0026567` |
| `Bits 6-7` | `>> 6` | `astro_moon_dist_rate_shift_m14d` | `-0.27275` | `-0.019108` | `0.24451` |
| `Bits 8-9` | `>> 8` | `astro_moon_helio_dist_shift_m14d` | `0.98492` | `0.99075` | `0.99811` |
| `Bits 10-11` | `>> 10` | `astro_moon_helio_dist_rate_shift_m14d` | `-0.35369` | `0.3245` | `0.97676` |
| `Bits 12-13` | `>> 12` | `astro_moon_phase_angle_shift_m14d` | `50.293` | `91.811` | `133.35` |
| `Bits 14-15` | `>> 14` | `astro_moon_elong_shift_m14d` | `46.545` | `88.039` | `129.59` |

### Container: `packed_astro_container_053` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_illum_frac_shift_m14d` | `15.679` | `48.42` | `81.939` |
| `Bits 2-3` | `>> 2` | `astro_saturn_ra_icrf_shift_m14d` | `338.03` | `341.02` | `344.06` |
| `Bits 4-5` | `>> 4` | `astro_saturn_dec_icrf_shift_m14d` | `-10.946` | `-9.772` | `-8.5726` |
| `Bits 6-7` | `>> 6` | `astro_saturn_ra_app_shift_m14d` | `338.35` | `341.33` | `344.37` |
| `Bits 8-9` | `>> 8` | `astro_saturn_dec_app_shift_m14d` | `-10.825` | `-9.6482` | `-8.446` |
| `Bits 10-11` | `>> 10` | `astro_saturn_azim_shift_m14d` | `37.761` | `63.298` | `319.07` |
| `Bits 12-13` | `>> 12` | `astro_saturn_elev_shift_m14d` | `-55.611` | `-51.226` | `-44.839` |
| `Bits 14-15` | `>> 14` | `astro_saturn_app_mag_shift_m14d` | `0.9785` | `0.99` | `1.0355` |

### Container: `packed_astro_container_054` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_surf_bright_shift_m14d` | `6.6877` | `6.712` | `6.7378` |
| `Bits 2-3` | `>> 2` | `astro_saturn_dist_shift_m14d` | `10.509` | `10.619` | `10.688` |
| `Bits 4-5` | `>> 4` | `astro_saturn_dist_rate_shift_m14d` | `-9.4978` | `2.2754` | `13.835` |
| `Bits 6-7` | `>> 6` | `astro_saturn_helio_dist_shift_m14d` | `9.7149` | `9.7226` | `9.7303` |
| `Bits 8-9` | `>> 8` | `astro_saturn_helio_dist_rate_shift_m14d` | `-0.49869` | `-0.49544` | `-0.49232` |
| `Bits 10-11` | `>> 10` | `astro_saturn_phase_angle_shift_m14d` | `1.2354` | `2.3699` | `3.4193` |
| `Bits 12-13` | `>> 12` | `astro_saturn_elong_shift_m14d` | `12.217` | `23.915` | `35.82` |
| `Bits 14-15` | `>> 14` | `astro_saturn_illum_frac_shift_m14d` | `15.679` | `48.42` | `81.939` |

### Container: `packed_astro_container_055` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_ra_icrf_shift_m14d` | `34.562` | `37.811` | `42.575` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_dec_icrf_shift_m14d` | `12.701` | `13.893` | `15.456` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_ra_app_shift_m14d` | `34.886` | `38.137` | `42.905` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_dec_app_shift_m14d` | `12.813` | `14` | `15.556` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_azim_shift_m14d` | `289.45` | `307.33` | `327.35` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_elev_shift_m14d` | `-25.346` | `-15.927` | `-1.912` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_app_mag_shift_m14d` | `-2.378` | `-2.2105` | `-2.0953` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_surf_bright_shift_m14d` | `5.3427` | `5.3605` | `5.369` |

### Container: `packed_astro_container_056` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_dist_shift_m14d` | `4.8992` | `5.3176` | `5.6702` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_dist_rate_shift_m14d` | `19.781` | `25.63` | `27.583` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_helio_dist_shift_m14d` | `4.9902` | `4.9958` | `5.0017` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_helio_dist_rate_shift_m14d` | `0.3531` | `0.37428` | `0.39493` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_phase_angle_shift_m14d` | `7.9546` | `10.322` | `11.101` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_elong_shift_m14d` | `44.005` | `65.893` | `89.587` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_illum_frac_shift_m14d` | `15.679` | `48.42` | `81.939` |
| `Bits 14-15` | `>> 14` | `astro_mars_ra_icrf_shift_m14d` | `288.61` | `310.24` | `330.89` |

### Container: `packed_astro_container_057` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_dec_icrf_shift_m14d` | `-23.142` | `-19.362` | `-13.165` |
| `Bits 2-3` | `>> 2` | `astro_mars_ra_app_shift_m14d` | `288.96` | `310.58` | `331.21` |
| `Bits 4-5` | `>> 4` | `astro_mars_dec_app_shift_m14d` | `-23.102` | `-19.279` | `-13.05` |
| `Bits 6-7` | `>> 6` | `astro_mars_azim_shift_m14d` | `62.22` | `62.677` | `62.929` |
| `Bits 8-9` | `>> 8` | `astro_mars_elev_shift_m14d` | `-57.83` | `-52.004` | `-43.695` |
| `Bits 10-11` | `>> 10` | `astro_mars_app_mag_shift_m14d` | `1.2125` | `1.2725` | `1.3133` |
| `Bits 12-13` | `>> 12` | `astro_mars_surf_bright_shift_m14d` | `4.052` | `4.09` | `4.111` |
| `Bits 14-15` | `>> 14` | `astro_mars_dist_shift_m14d` | `2.1317` | `2.2348` | `2.3345` |

### Container: `packed_astro_container_058` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_dist_rate_shift_m14d` | `-6.8578` | `-6.809` | `-6.3582` |
| `Bits 2-3` | `>> 2` | `astro_mars_helio_dist_shift_m14d` | `1.3979` | `1.4195` | `1.4479` |
| `Bits 4-5` | `>> 4` | `astro_mars_helio_dist_rate_shift_m14d` | `-2.0045` | `-1.6448` | `-1.1421` |
| `Bits 6-7` | `>> 6` | `astro_mars_phase_angle_shift_m14d` | `13.388` | `18.107` | `22.506` |
| `Bits 8-9` | `>> 8` | `astro_mars_elong_shift_m14d` | `19.905` | `26.483` | `32.486` |
| `Bits 10-11` | `>> 10` | `astro_mars_illum_frac_shift_m14d` | `15.679` | `48.42` | `81.939` |
| `Bits 12-13` | `>> 12` | `astro_ceres_ra_icrf_shift_m14d` | `265.34` | `275.71` | `284.47` |
| `Bits 14-15` | `>> 14` | `astro_ceres_dec_icrf_shift_m14d` | `-23.304` | `-22.914` | `-22.155` |

### Container: `packed_astro_container_059` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_ceres_ra_app_shift_m14d` | `265.7` | `276.07` | `284.83` |
| `Bits 2-3` | `>> 2` | `astro_ceres_dec_app_shift_m14d` | `-23.273` | `-22.903` | `-22.168` |
| `Bits 4-5` | `>> 4` | `astro_ceres_azim_shift_m14d` | `83.018` | `94.79` | `106.09` |
| `Bits 6-7` | `>> 6` | `astro_ceres_elev_shift_m14d` | `-40.935` | `-29.658` | `-17.196` |
| `Bits 8-9` | `>> 8` | `astro_ceres_app_mag_shift_m14d` | `8.9253` | `9.0105` | `9.055` |
| `Bits 10-11` | `>> 10` | `astro_ceres_surf_bright_shift_m14d` | `6.7142` | `6.8655` | `6.9605` |
| `Bits 12-13` | `>> 12` | `astro_ceres_dist_shift_m14d` | `2.8671` | `3.1858` | `3.4451` |
| `Bits 14-15` | `>> 14` | `astro_ceres_dist_rate_shift_m14d` | `-22.212` | `-19.285` | `-14.582` |

### Container: `packed_astro_container_060` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_ceres_helio_dist_shift_m14d` | `2.782` | `2.8035` | `2.8245` |
| `Bits 2-3` | `>> 2` | `astro_ceres_helio_dist_rate_shift_m14d` | `1.3375` | `1.3768` | `1.4036` |
| `Bits 4-5` | `>> 4` | `astro_ceres_phase_angle_shift_m14d` | `13.503` | `17.563` | `20.144` |
| `Bits 6-7` | `>> 6` | `astro_ceres_elong_shift_m14d` | `41.279` | `58.767` | `77.512` |
| `Bits 8-9` | `>> 8` | `astro_ceres_illum_frac_shift_m14d` | `15.679` | `48.42` | `81.939` |
| `Bits 10-11` | `>> 10` | `astro_venus_ra_icrf_shift_m14d` | `258.26` | `293.78` | `327.75` |
| `Bits 12-13` | `>> 12` | `astro_venus_dec_icrf_shift_m14d` | `-21.463` | `-18.61` | `-8.5695` |
| `Bits 14-15` | `>> 14` | `astro_venus_ra_app_shift_m14d` | `258.61` | `294.13` | `328.07` |

### Container: `packed_astro_container_061` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_dec_app_shift_m14d` | `-21.474` | `-18.571` | `-8.4436` |
| `Bits 2-3` | `>> 2` | `astro_venus_azim_shift_m14d` | `45.016` | `61.821` | `75.069` |
| `Bits 4-5` | `>> 4` | `astro_venus_elev_shift_m14d` | `-50.719` | `-47.839` | `-43.704` |
| `Bits 6-7` | `>> 6` | `astro_venus_app_mag_shift_m14d` | `-3.9537` | `-3.901` | `-3.878` |
| `Bits 8-9` | `>> 8` | `astro_venus_surf_bright_shift_m14d` | `0.90925` | `0.9935` | `1.082` |
| `Bits 10-11` | `>> 10` | `astro_venus_dist_shift_m14d` | `1.3393` | `1.4744` | `1.5855` |
| `Bits 12-13` | `>> 12` | `astro_venus_dist_rate_shift_m14d` | `6.1894` | `7.8081` | `9.2735` |
| `Bits 14-15` | `>> 14` | `astro_venus_helio_dist_shift_m14d` | `0.72391` | `0.7269` | `0.72786` |

### Container: `packed_astro_container_062` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_helio_dist_rate_shift_m14d` | `-0.0086905` | `0.15263` | `0.21938` |
| `Bits 2-3` | `>> 2` | `astro_venus_phase_angle_shift_m14d` | `27.314` | `36.487` | `45.954` |
| `Bits 4-5` | `>> 4` | `astro_venus_elong_shift_m14d` | `19.597` | `25.911` | `31.896` |
| `Bits 6-7` | `>> 6` | `astro_venus_illum_frac_shift_m14d` | `15.679` | `48.42` | `81.939` |
| `Bits 8-9` | `>> 8` | `astro_sun_ra_icrf_shift_m7d` | `26.586` | `304.39` | `333.05` |
| `Bits 10-11` | `>> 10` | `astro_sun_dec_icrf_shift_m7d` | `-18.076` | `-8.7391` | `2.3747` |
| `Bits 12-13` | `>> 12` | `astro_sun_ra_app_shift_m7d` | `26.902` | `304.73` | `333.36` |
| `Bits 14-15` | `>> 14` | `astro_sun_dec_app_shift_m7d` | `-17.991` | `-8.6167` | `2.5064` |

### Container: `packed_astro_container_063` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_azim_shift_m7d` | `16.461` | `17.373` | `21.99` |
| `Bits 2-3` | `>> 2` | `astro_sun_elev_shift_m7d` | `-63.827` | `-54.748` | `-43.491` |
| `Bits 4-5` | `>> 4` | `astro_sun_app_mag_shift_m7d` | `-26.775` | `-26.764` | `-26.747` |
| `Bits 6-7` | `>> 6` | `astro_sun_dist_shift_m7d` | `0.98493` | `0.99014` | `0.99768` |
| `Bits 8-9` | `>> 8` | `astro_sun_dist_rate_shift_m7d` | `0.16632` | `0.35062` | `0.39824` |
| `Bits 10-11` | `>> 10` | `astro_sun_illum_frac_shift_m7d` | `17.066` | `51.639` | `85.06` |
| `Bits 12-13` | `>> 12` | `astro_moon_ra_icrf_shift_m7d` | `99.252` | `178.43` | `253.36` |
| `Bits 14-15` | `>> 14` | `astro_moon_dec_icrf_shift_m7d` | `-18.559` | `0.91601` | `18.87` |

### Container: `packed_astro_container_064` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_ra_app_shift_m7d` | `99.633` | `178.74` | `253.73` |
| `Bits 2-3` | `>> 2` | `astro_moon_dec_app_shift_m7d` | `-18.541` | `1.0476` | `18.864` |
| `Bits 4-5` | `>> 4` | `astro_moon_azim_shift_m7d` | `108.53` | `187.19` | `284.33` |
| `Bits 6-7` | `>> 6` | `astro_moon_elev_shift_m7d` | `-31.886` | `5.3197` | `32.839` |
| `Bits 8-9` | `>> 8` | `astro_moon_app_mag_shift_m7d` | `-11.432` | `-10.182` | `-8.235` |
| `Bits 10-11` | `>> 10` | `astro_moon_surf_bright_shift_m7d` | `4.353` | `5.072` | `5.8135` |
| `Bits 12-13` | `>> 12` | `astro_moon_dist_shift_m7d` | `0.002491` | `0.0025951` | `0.0026644` |
| `Bits 14-15` | `>> 14` | `astro_moon_dist_rate_shift_m7d` | `-0.25516` | `0.031144` | `0.26185` |

### Container: `packed_astro_container_065` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_helio_dist_shift_m7d` | `0.98528` | `0.99106` | `0.99903` |
| `Bits 2-3` | `>> 2` | `astro_moon_helio_dist_rate_shift_m7d` | `-0.29737` | `0.36358` | `1.0122` |
| `Bits 4-5` | `>> 4` | `astro_moon_phase_angle_shift_m7d` | `45.458` | `88.121` | `131.21` |
| `Bits 6-7` | `>> 6` | `astro_moon_elong_shift_m7d` | `48.683` | `91.728` | `134.43` |
| `Bits 8-9` | `>> 8` | `astro_moon_illum_frac_shift_m7d` | `17.066` | `51.639` | `85.06` |
| `Bits 10-11` | `>> 10` | `astro_saturn_ra_icrf_shift_m7d` | `338.22` | `341.42` | `344.64` |
| `Bits 12-13` | `>> 12` | `astro_saturn_dec_icrf_shift_m7d` | `-10.873` | `-9.6136` | `-8.3464` |
| `Bits 14-15` | `>> 14` | `astro_saturn_ra_app_shift_m7d` | `338.53` | `341.73` | `344.94` |

### Container: `packed_astro_container_066` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_dec_app_shift_m7d` | `-10.752` | `-9.4894` | `-8.2194` |
| `Bits 2-3` | `>> 2` | `astro_saturn_azim_shift_m7d` | `39.78` | `65.982` | `316.9` |
| `Bits 4-5` | `>> 4` | `astro_saturn_elev_shift_m7d` | `-55.377` | `-50.596` | `-43.49` |
| `Bits 6-7` | `>> 6` | `astro_saturn_app_mag_shift_m7d` | `0.9795` | `0.99` | `1.047` |
| `Bits 8-9` | `>> 8` | `astro_saturn_surf_bright_shift_m7d` | `6.69` | `6.715` | `6.755` |
| `Bits 10-11` | `>> 10` | `astro_saturn_dist_shift_m7d` | `10.483` | `10.607` | `10.684` |
| `Bits 12-13` | `>> 12` | `astro_saturn_dist_rate_shift_m7d` | `-11.661` | `0.71312` | `13.13` |
| `Bits 14-15` | `>> 14` | `astro_saturn_helio_dist_shift_m7d` | `9.7134` | `9.7216` | `9.7298` |

### Container: `packed_astro_container_067` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_helio_dist_rate_shift_m7d` | `-0.49901` | `-0.49582` | `-0.49261` |
| `Bits 2-3` | `>> 2` | `astro_saturn_phase_angle_shift_m7d` | `1.3038` | `2.5282` | `3.6173` |
| `Bits 4-5` | `>> 4` | `astro_saturn_elong_shift_m7d` | `12.902` | `25.581` | `38.142` |
| `Bits 6-7` | `>> 6` | `astro_saturn_illum_frac_shift_m7d` | `17.066` | `51.639` | `85.06` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_ra_icrf_shift_m7d` | `34.717` | `38.359` | `43.643` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_dec_icrf_shift_m7d` | `12.763` | `14.083` | `15.784` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_ra_app_shift_m7d` | `35.041` | `38.686` | `43.973` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_dec_app_shift_m7d` | `12.873` | `14.188` | `15.881` |

### Container: `packed_astro_container_068` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_azim_shift_m7d` | `290.58` | `309.81` | `331.54` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_elev_shift_m7d` | `-26.579` | `-17.441` | `-2.9517` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_app_mag_shift_m7d` | `-2.3655` | `-2.192` | `-2.0785` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_surf_bright_shift_m7d` | `5.3385` | `5.359` | `5.3685` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_dist_shift_m7d` | `4.9274` | `5.3686` | `5.7275` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_dist_rate_shift_m7d` | `18.314` | `25.179` | `27.483` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_helio_dist_shift_m7d` | `4.9905` | `4.9965` | `5.0029` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_helio_dist_rate_shift_m7d` | `0.35335` | `0.37673` | `0.3993` |

### Container: `packed_astro_container_069` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_phase_angle_shift_m7d` | `7.3476` | `10.164` | `11.068` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_elong_shift_m7d` | `39.881` | `62.938` | `87.973` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_illum_frac_shift_m7d` | `17.066` | `51.639` | `85.06` |
| `Bits 6-7` | `>> 6` | `astro_mars_ra_icrf_shift_m7d` | `290.04` | `313.01` | `334.81` |
| `Bits 8-9` | `>> 8` | `astro_mars_dec_icrf_shift_m7d` | `-22.982` | `-18.672` | `-11.741` |
| `Bits 10-11` | `>> 10` | `astro_mars_ra_app_shift_m7d` | `290.4` | `313.35` | `335.13` |
| `Bits 12-13` | `>> 12` | `astro_mars_dec_app_shift_m7d` | `-22.939` | `-18.584` | `-11.622` |
| `Bits 14-15` | `>> 14` | `astro_mars_azim_shift_m7d` | `62.36` | `62.669` | `62.907` |

### Container: `packed_astro_container_070` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_elev_shift_m7d` | `-57.526` | `-51.053` | `-41.811` |
| `Bits 2-3` | `>> 2` | `astro_mars_app_mag_shift_m7d` | `1.1985` | `1.269` | `1.3105` |
| `Bits 4-5` | `>> 4` | `astro_mars_surf_bright_shift_m7d` | `4.0545` | `4.093` | `4.1145` |
| `Bits 6-7` | `>> 6` | `astro_mars_dist_shift_m7d` | `2.1115` | `2.2214` | `2.3282` |
| `Bits 8-9` | `>> 8` | `astro_mars_dist_rate_shift_m7d` | `-6.8557` | `-6.8057` | `-6.3995` |
| `Bits 10-11` | `>> 10` | `astro_mars_helio_dist_shift_m7d` | `1.3946` | `1.4163` | `1.4459` |
| `Bits 12-13` | `>> 12` | `astro_mars_helio_dist_rate_shift_m7d` | `-1.9857` | `-1.5867` | `-1.0293` |
| `Bits 14-15` | `>> 14` | `astro_mars_phase_angle_shift_m7d` | `13.705` | `18.702` | `23.326` |

### Container: `packed_astro_container_071` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_elong_shift_m7d` | `20.354` | `27.299` | `33.605` |
| `Bits 2-3` | `>> 2` | `astro_mars_illum_frac_shift_m7d` | `17.066` | `51.639` | `85.06` |
| `Bits 4-5` | `>> 4` | `astro_ceres_ra_icrf_shift_m7d` | `266.06` | `276.96` | `285.93` |
| `Bits 6-7` | `>> 6` | `astro_ceres_dec_icrf_shift_m7d` | `-23.377` | `-22.977` | `-22.224` |
| `Bits 8-9` | `>> 8` | `astro_ceres_ra_app_shift_m7d` | `266.41` | `277.33` | `286.29` |
| `Bits 10-11` | `>> 10` | `astro_ceres_dec_app_shift_m7d` | `-23.343` | `-22.963` | `-22.235` |
| `Bits 12-13` | `>> 12` | `astro_ceres_azim_shift_m7d` | `83.847` | `96.249` | `108.44` |
| `Bits 14-15` | `>> 14` | `astro_ceres_elev_shift_m7d` | `-40.238` | `-28.09` | `-14.636` |

### Container: `packed_astro_container_072` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_ceres_app_mag_shift_m7d` | `8.886` | `9.003` | `9.053` |
| `Bits 2-3` | `>> 2` | `astro_ceres_surf_bright_shift_m7d` | `6.7255` | `6.882` | `6.972` |
| `Bits 4-5` | `>> 4` | `astro_ceres_dist_shift_m7d` | `2.8002` | `3.1469` | `3.4305` |
| `Bits 6-7` | `>> 6` | `astro_ceres_dist_rate_shift_m7d` | `-22.3` | `-19.782` | `-14.929` |
| `Bits 8-9` | `>> 8` | `astro_ceres_helio_dist_shift_m7d` | `2.7835` | `2.8063` | `2.8286` |
| `Bits 10-11` | `>> 10` | `astro_ceres_helio_dist_rate_shift_m7d` | `1.3284` | `1.3723` | `1.4022` |
| `Bits 12-13` | `>> 12` | `astro_ceres_phase_angle_shift_m7d` | `13.801` | `17.999` | `20.238` |
| `Bits 14-15` | `>> 14` | `astro_ceres_elong_shift_m7d` | `42.393` | `61.135` | `81.391` |

### Container: `packed_astro_container_073` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_ceres_illum_frac_shift_m7d` | `17.066` | `51.639` | `85.06` |
| `Bits 2-3` | `>> 2` | `astro_venus_ra_icrf_shift_m7d` | `251.43` | `289.15` | `325.62` |
| `Bits 4-5` | `>> 4` | `astro_venus_dec_icrf_shift_m7d` | `-21.337` | `-17.627` | `-6.1464` |
| `Bits 6-7` | `>> 6` | `astro_venus_ra_app_shift_m7d` | `251.78` | `289.5` | `325.94` |
| `Bits 8-9` | `>> 8` | `astro_venus_dec_app_shift_m7d` | `-21.328` | `-17.535` | `-6.0169` |
| `Bits 10-11` | `>> 10` | `astro_venus_azim_shift_m7d` | `42.109` | `59.589` | `74.497` |
| `Bits 12-13` | `>> 12` | `astro_venus_elev_shift_m7d` | `-50.578` | `-47.374` | `-42.744` |
| `Bits 14-15` | `>> 14` | `astro_venus_app_mag_shift_m7d` | `-3.9495` | `-3.896` | `-3.879` |

### Container: `packed_astro_container_074` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_surf_bright_shift_m7d` | `0.893` | `0.982` | `1.0765` |
| `Bits 2-3` | `>> 2` | `astro_venus_dist_shift_m7d` | `1.3489` | `1.4904` | `1.6043` |
| `Bits 4-5` | `>> 4` | `astro_venus_dist_rate_shift_m7d` | `5.8552` | `7.614` | `9.1826` |
| `Bits 6-7` | `>> 6` | `astro_venus_helio_dist_shift_m7d` | `0.72414` | `0.72672` | `0.72782` |
| `Bits 8-9` | `>> 8` | `astro_venus_helio_dist_rate_shift_m7d` | `-0.042712` | `0.13449` | `0.21709` |
| `Bits 10-11` | `>> 10` | `astro_venus_phase_angle_shift_m7d` | `25.509` | `35.279` | `45.317` |
| `Bits 12-13` | `>> 12` | `astro_venus_elong_shift_m7d` | `18.318` | `25.102` | `31.515` |
| `Bits 14-15` | `>> 14` | `astro_venus_illum_frac_shift_m7d` | `17.066` | `51.639` | `85.06` |

### Container: `packed_astro_container_075` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_ra_icrf_shift_p7d` | `26.586` | `304.39` | `333.05` |
| `Bits 2-3` | `>> 2` | `astro_sun_dec_icrf_shift_p7d` | `-16.089` | `-6.0763` | `5.0919` |
| `Bits 4-5` | `>> 4` | `astro_sun_ra_app_shift_p7d` | `26.902` | `304.73` | `333.36` |
| `Bits 6-7` | `>> 6` | `astro_sun_dec_app_shift_p7d` | `-15.992` | `-5.9491` | `5.2217` |
| `Bits 8-9` | `>> 8` | `astro_sun_azim_shift_p7d` | `16.389` | `16.96` | `20.311` |
| `Bits 10-11` | `>> 10` | `astro_sun_elev_shift_p7d` | `-61.967` | `-52.069` | `-40.726` |
| `Bits 12-13` | `>> 12` | `astro_sun_app_mag_shift_p7d` | `-26.773` | `-26.76` | `-26.742` |
| `Bits 14-15` | `>> 14` | `astro_sun_dist_shift_p7d` | `0.98595` | `0.99188` | `0.99971` |

### Container: `packed_astro_container_076` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_dist_rate_shift_p7d` | `0.22313` | `0.37793` | `0.39824` |
| `Bits 2-3` | `>> 2` | `astro_sun_illum_frac_shift_p7d` | `17.066` | `57.958` | `88.054` |
| `Bits 4-5` | `>> 4` | `astro_moon_ra_icrf_shift_p7d` | `99.252` | `184.56` | `265.96` |
| `Bits 6-7` | `>> 6` | `astro_moon_dec_icrf_shift_p7d` | `-21.95` | `-2.198` | `18.87` |
| `Bits 8-9` | `>> 8` | `astro_moon_ra_app_shift_p7d` | `99.633` | `184.87` | `266.35` |
| `Bits 10-11` | `>> 10` | `astro_moon_dec_app_shift_p7d` | `-21.948` | `-2.0661` | `18.864` |
| `Bits 12-13` | `>> 12` | `astro_moon_azim_shift_p7d` | `117.11` | `187.19` | `284.33` |
| `Bits 14-15` | `>> 14` | `astro_moon_elev_shift_p7d` | `-31.886` | `5.3197` | `31.859` |

### Container: `packed_astro_container_077` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_app_mag_shift_p7d` | `-11.621` | `-10.422` | `-8.235` |
| `Bits 2-3` | `>> 2` | `astro_moon_surf_bright_shift_p7d` | `4.2405` | `5` | `5.7705` |
| `Bits 4-5` | `>> 4` | `astro_moon_dist_shift_p7d` | `0.002491` | `0.002579` | `0.0026555` |
| `Bits 6-7` | `>> 6` | `astro_moon_dist_rate_shift_p7d` | `-0.2279` | `0.031144` | `0.26185` |
| `Bits 8-9` | `>> 8` | `astro_moon_helio_dist_shift_p7d` | `0.98632` | `0.99195` | `0.99974` |
| `Bits 10-11` | `>> 10` | `astro_moon_helio_dist_rate_shift_p7d` | `-0.25041` | `0.36358` | `1.0122` |
| `Bits 12-13` | `>> 12` | `astro_moon_phase_angle_shift_p7d` | `40.428` | `80.841` | `131.21` |
| `Bits 14-15` | `>> 14` | `astro_moon_elong_shift_p7d` | `48.683` | `99.011` | `139.47` |

### Container: `packed_astro_container_078` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_illum_frac_shift_p7d` | `17.066` | `57.958` | `88.054` |
| `Bits 2-3` | `>> 2` | `astro_saturn_ra_icrf_shift_p7d` | `338.98` | `342.22` | `345.38` |
| `Bits 4-5` | `>> 4` | `astro_saturn_dec_icrf_shift_p7d` | `-10.574` | `-9.2965` | `-8.0535` |
| `Bits 6-7` | `>> 6` | `astro_saturn_ra_app_shift_p7d` | `339.29` | `342.53` | `345.69` |
| `Bits 8-9` | `>> 8` | `astro_saturn_dec_app_shift_p7d` | `-10.452` | `-9.1716` | `-7.9258` |
| `Bits 10-11` | `>> 10` | `astro_saturn_azim_shift_p7d` | `39.78` | `65.982` | `316.9` |
| `Bits 12-13` | `>> 12` | `astro_saturn_elev_shift_p7d` | `-55.377` | `-50.596` | `-41.282` |
| `Bits 14-15` | `>> 14` | `astro_saturn_app_mag_shift_p7d` | `0.9835` | `0.991` | `1.0585` |

### Container: `packed_astro_container_079` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_surf_bright_shift_p7d` | `6.69` | `6.715` | `6.7775` |
| `Bits 2-3` | `>> 2` | `astro_saturn_dist_shift_p7d` | `10.483` | `10.607` | `10.684` |
| `Bits 4-5` | `>> 4` | `astro_saturn_dist_rate_shift_p7d` | `-14.439` | `-2.4104` | `10.214` |
| `Bits 6-7` | `>> 6` | `astro_saturn_helio_dist_shift_p7d` | `9.7114` | `9.7196` | `9.7278` |
| `Bits 8-9` | `>> 8` | `astro_saturn_helio_dist_rate_shift_p7d` | `-0.49979` | `-0.49682` | `-0.49353` |
| `Bits 10-11` | `>> 10` | `astro_saturn_phase_angle_shift_p7d` | `1.3038` | `2.5282` | `3.6173` |
| `Bits 12-13` | `>> 12` | `astro_saturn_elong_shift_p7d` | `12.902` | `25.581` | `38.142` |
| `Bits 14-15` | `>> 14` | `astro_saturn_illum_frac_shift_p7d` | `17.066` | `57.958` | `88.054` |

### Container: `packed_astro_container_080` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_ra_icrf_shift_p7d` | `35.423` | `39.529` | `45.119` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_dec_icrf_shift_p7d` | `13.033` | `14.478` | `16.223` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_ra_app_shift_p7d` | `35.748` | `39.857` | `45.451` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_dec_app_shift_p7d` | `13.143` | `14.582` | `16.318` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_azim_shift_p7d` | `294.47` | `314.17` | `336.42` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_elev_shift_p7d` | `-27.887` | `-20.224` | `-6.9478` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_app_mag_shift_p7d` | `-2.3175` | `-2.159` | `-2.0585` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_surf_bright_shift_p7d` | `5.3335` | `5.356` | `5.3685` |

### Container: `packed_astro_container_081` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_dist_shift_p7d` | `5.0397` | `5.4668` | `5.7968` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_dist_rate_shift_p7d` | `16.253` | `23.796` | `27.483` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_helio_dist_shift_p7d` | `4.992` | `4.9981` | `5.0046` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_helio_dist_rate_shift_p7d` | `0.35977` | `0.38301` | `0.40409` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_phase_angle_shift_p7d` | `6.4906` | `9.5935` | `11.068` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_elong_shift_p7d` | `34.453` | `57.115` | `81.608` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_illum_frac_shift_p7d` | `17.066` | `57.958` | `88.054` |
| `Bits 14-15` | `>> 14` | `astro_mars_ra_icrf_shift_p7d` | `294.95` | `317.71` | `339.25` |

### Container: `packed_astro_container_082` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_dec_icrf_shift_p7d` | `-22.216` | `-17.173` | `-9.7654` |
| `Bits 2-3` | `>> 2` | `astro_mars_ra_app_shift_p7d` | `294.48` | `317.26` | `338.82` |
| `Bits 4-5` | `>> 4` | `astro_mars_dec_app_shift_p7d` | `-22.161` | `-17.075` | `-9.6415` |
| `Bits 6-7` | `>> 6` | `astro_mars_azim_shift_p7d` | `62.624` | `62.698` | `62.907` |
| `Bits 8-9` | `>> 8` | `astro_mars_elev_shift_p7d` | `-56.204` | `-49.022` | `-39.197` |
| `Bits 10-11` | `>> 10` | `astro_mars_app_mag_shift_p7d` | `1.1755` | `1.259` | `1.303` |
| `Bits 12-13` | `>> 12` | `astro_mars_surf_bright_shift_p7d` | `4.0545` | `4.094` | `4.1335` |
| `Bits 14-15` | `>> 14` | `astro_mars_dist_shift_p7d` | `2.0847` | `2.1945` | `2.3027` |

### Container: `packed_astro_container_083` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_dist_rate_shift_p7d` | `-6.8557` | `-6.8057` | `-6.5559` |
| `Bits 2-3` | `>> 2` | `astro_mars_helio_dist_shift_p7d` | `1.3907` | `1.4101` | `1.4381` |
| `Bits 4-5` | `>> 4` | `astro_mars_helio_dist_rate_shift_p7d` | `-1.9039` | `-1.4632` | `-0.87286` |
| `Bits 6-7` | `>> 6` | `astro_mars_phase_angle_shift_p7d` | `14.962` | `19.875` | `24.398` |
| `Bits 8-9` | `>> 8` | `astro_mars_elong_shift_p7d` | `22.122` | `28.901` | `35.072` |
| `Bits 10-11` | `>> 10` | `astro_mars_illum_frac_shift_p7d` | `17.066` | `57.958` | `88.054` |
| `Bits 12-13` | `>> 12` | `astro_ceres_ra_icrf_shift_p7d` | `268.87` | `279.38` | `287.71` |
| `Bits 14-15` | `>> 14` | `astro_ceres_dec_icrf_shift_p7d` | `-23.489` | `-23.087` | `-22.468` |

### Container: `packed_astro_container_084` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_ceres_ra_app_shift_p7d` | `269.22` | `279.75` | `288.08` |
| `Bits 2-3` | `>> 2` | `astro_ceres_dec_app_shift_p7d` | `-23.45` | `-23.068` | `-22.473` |
| `Bits 4-5` | `>> 4` | `astro_ceres_azim_shift_p7d` | `87.057` | `99.163` | `111.7` |
| `Bits 6-7` | `>> 6` | `astro_ceres_elev_shift_p7d` | `-37.391` | `-24.895` | `-11.181` |
| `Bits 8-9` | `>> 8` | `astro_ceres_app_mag_shift_p7d` | `8.826` | `9.003` | `9.053` |
| `Bits 10-11` | `>> 10` | `astro_ceres_surf_bright_shift_p7d` | `6.77` | `6.91` | `6.9735` |
| `Bits 12-13` | `>> 12` | `astro_ceres_dist_shift_p7d` | `2.71` | `3.0663` | `3.3684` |
| `Bits 14-15` | `>> 14` | `astro_ceres_dist_rate_shift_p7d` | `-22.3` | `-20.694` | `-16.281` |

### Container: `packed_astro_container_085` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_ceres_helio_dist_shift_p7d` | `2.7891` | `2.8118` | `2.8339` |
| `Bits 2-3` | `>> 2` | `astro_ceres_helio_dist_rate_shift_p7d` | `1.3156` | `1.3628` | `1.3963` |
| `Bits 4-5` | `>> 4` | `astro_ceres_phase_angle_shift_p7d` | `14.955` | `18.792` | `20.238` |
| `Bits 6-7` | `>> 6` | `astro_ceres_elong_shift_p7d` | `46.888` | `65.941` | `86.69` |
| `Bits 8-9` | `>> 8` | `astro_ceres_illum_frac_shift_p7d` | `17.066` | `57.958` | `88.054` |
| `Bits 10-11` | `>> 10` | `astro_venus_ra_icrf_shift_p7d` | `251.43` | `289.15` | `325.62` |
| `Bits 12-13` | `>> 12` | `astro_venus_dec_icrf_shift_p7d` | `-21.337` | `-15.269` | `-2.799` |
| `Bits 14-15` | `>> 14` | `astro_venus_ra_app_shift_p7d` | `251.78` | `289.5` | `325.94` |

### Container: `packed_astro_container_086` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_dec_app_shift_p7d` | `-21.328` | `-15.163` | `-2.667` |
| `Bits 2-3` | `>> 2` | `astro_venus_azim_shift_p7d` | `38.52` | `55.046` | `71.748` |
| `Bits 4-5` | `>> 4` | `astro_venus_elev_shift_p7d` | `-50.578` | `-47.374` | `-42.744` |
| `Bits 6-7` | `>> 6` | `astro_venus_app_mag_shift_p7d` | `-3.933` | `-3.889` | `-3.879` |
| `Bits 8-9` | `>> 8` | `astro_venus_surf_bright_shift_p7d` | `0.8725` | `0.96` | `1.0525` |
| `Bits 10-11` | `>> 10` | `astro_venus_dist_shift_p7d` | `1.3861` | `1.5211` | `1.6276` |
| `Bits 12-13` | `>> 12` | `astro_venus_dist_rate_shift_p7d` | `5.382` | `7.2055` | `8.8039` |
| `Bits 14-15` | `>> 14` | `astro_venus_helio_dist_shift_p7d` | `0.72506` | `0.72672` | `0.72782` |

### Container: `packed_astro_container_087` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_helio_dist_rate_shift_p7d` | `-0.086583` | `0.094617` | `0.21709` |
| `Bits 2-3` | `>> 2` | `astro_venus_phase_angle_shift_p7d` | `23.093` | `32.875` | `42.799` |
| `Bits 4-5` | `>> 4` | `astro_venus_elong_shift_p7d` | `16.592` | `23.47` | `29.975` |
| `Bits 6-7` | `>> 6` | `astro_venus_illum_frac_shift_p7d` | `17.066` | `57.958` | `88.054` |
| `Bits 8-9` | `>> 8` | `astro_sun_ra_icrf_shift_p14d` | `24.961` | `308.05` | `334.72` |
| `Bits 10-11` | `>> 10` | `astro_sun_dec_icrf_shift_p14d` | `-14.447` | `-4.7163` | `5.7613` |
| `Bits 12-13` | `>> 12` | `astro_sun_ra_app_shift_p14d` | `25.275` | `308.39` | `335.04` |
| `Bits 14-15` | `>> 14` | `astro_sun_dec_app_shift_p14d` | `-14.342` | `-4.5872` | `5.8904` |

### Container: `packed_astro_container_088` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_azim_shift_p14d` | `16.368` | `16.816` | `19.3` |
| `Bits 2-3` | `>> 2` | `astro_sun_elev_shift_p14d` | `-60.39` | `-50.695` | `-40.046` |
| `Bits 4-5` | `>> 4` | `astro_sun_app_mag_shift_p14d` | `-26.771` | `-26.758` | `-26.742` |
| `Bits 6-7` | `>> 6` | `astro_sun_dist_shift_p14d` | `0.98684` | `0.99279` | `1.0002` |
| `Bits 8-9` | `>> 8` | `astro_sun_dist_rate_shift_p14d` | `0.2487` | `0.38241` | `0.40038` |
| `Bits 10-11` | `>> 10` | `astro_sun_illum_frac_shift_p14d` | `24.437` | `61.481` | `89.624` |
| `Bits 12-13` | `>> 12` | `astro_moon_ra_icrf_shift_p14d` | `92.209` | `175.6` | `254.16` |
| `Bits 14-15` | `>> 14` | `astro_moon_dec_icrf_shift_p14d` | `-19.207` | `1.2528` | `19.776` |

### Container: `packed_astro_container_089` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_ra_app_shift_p14d` | `92.589` | `175.92` | `254.54` |
| `Bits 2-3` | `>> 2` | `astro_moon_dec_app_shift_p14d` | `-19.173` | `1.2503` | `19.721` |
| `Bits 4-5` | `>> 4` | `astro_moon_azim_shift_p14d` | `122.47` | `195.95` | `283.85` |
| `Bits 6-7` | `>> 6` | `astro_moon_elev_shift_p14d` | `-24.719` | `8.1781` | `33.062` |
| `Bits 8-9` | `>> 8` | `astro_moon_app_mag_shift_p14d` | `-11.66` | `-10.566` | `-8.8023` |
| `Bits 10-11` | `>> 10` | `astro_moon_surf_bright_shift_p14d` | `4.2045` | `4.901` | `5.6828` |
| `Bits 12-13` | `>> 12` | `astro_moon_dist_shift_p14d` | `0.0025024` | `0.0025885` | `0.0026589` |
| `Bits 14-15` | `>> 14` | `astro_moon_dist_rate_shift_p14d` | `-0.22748` | `0.043052` | `0.27073` |

### Container: `packed_astro_container_090` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_helio_dist_shift_p14d` | `0.98695` | `0.99226` | `0.99995` |
| `Bits 2-3` | `>> 2` | `astro_moon_helio_dist_rate_shift_p14d` | `-0.24968` | `0.46085` | `1.0221` |
| `Bits 4-5` | `>> 4` | `astro_moon_phase_angle_shift_p14d` | `37.578` | `76.726` | `120.76` |
| `Bits 6-7` | `>> 6` | `astro_moon_elong_shift_p14d` | `59.113` | `103.13` | `142.33` |
| `Bits 8-9` | `>> 8` | `astro_moon_illum_frac_shift_p14d` | `24.437` | `61.481` | `89.624` |
| `Bits 10-11` | `>> 10` | `astro_saturn_ra_icrf_shift_p14d` | `339.56` | `342.62` | `345.57` |
| `Bits 12-13` | `>> 12` | `astro_saturn_dec_icrf_shift_p14d` | `-10.343` | `-9.1386` | `-7.982` |
| `Bits 14-15` | `>> 14` | `astro_saturn_ra_app_shift_p14d` | `339.88` | `342.93` | `345.88` |

### Container: `packed_astro_container_091` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_dec_app_shift_p14d` | `-10.221` | `-9.0133` | `-7.8542` |
| `Bits 2-3` | `>> 2` | `astro_saturn_azim_shift_p14d` | `37.761` | `63.298` | `319.07` |
| `Bits 4-5` | `>> 4` | `astro_saturn_elev_shift_p14d` | `-55.611` | `-51.226` | `-40.28` |
| `Bits 6-7` | `>> 6` | `astro_saturn_app_mag_shift_p14d` | `0.98575` | `0.997` | `1.0605` |
| `Bits 8-9` | `>> 8` | `astro_saturn_surf_bright_shift_p14d` | `6.6877` | `6.712` | `6.7828` |
| `Bits 10-11` | `>> 10` | `astro_saturn_dist_shift_p14d` | `10.509` | `10.619` | `10.688` |
| `Bits 12-13` | `>> 12` | `astro_saturn_dist_rate_shift_p14d` | `-15.112` | `-3.9722` | `7.935` |
| `Bits 14-15` | `>> 14` | `astro_saturn_helio_dist_shift_p14d` | `9.7109` | `9.7186` | `9.7263` |

### Container: `packed_astro_container_092` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_helio_dist_rate_shift_p14d` | `-0.49998` | `-0.49718` | `-0.49391` |
| `Bits 2-3` | `>> 2` | `astro_saturn_phase_angle_shift_p14d` | `1.2354` | `2.3699` | `3.4193` |
| `Bits 4-5` | `>> 4` | `astro_saturn_elong_shift_p14d` | `12.217` | `23.915` | `35.82` |
| `Bits 6-7` | `>> 6` | `astro_saturn_illum_frac_shift_p14d` | `24.437` | `61.481` | `89.624` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_ra_icrf_shift_p14d` | `36.038` | `40.149` | `45.497` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_dec_icrf_shift_p14d` | `13.262` | `14.682` | `16.334` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_ra_app_shift_p14d` | `36.363` | `40.477` | `45.829` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_dec_app_shift_p14d` | `13.371` | `14.785` | `16.428` |

### Container: `packed_astro_container_093` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_azim_shift_p14d` | `297.93` | `316.76` | `337.85` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_elev_shift_p14d` | `-28.153` | `-21.488` | `-9.7658` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_app_mag_shift_p14d` | `-2.2837` | `-2.144` | `-2.0543` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_surf_bright_shift_p14d` | `5.332` | `5.3535` | `5.369` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_dist_shift_p14d` | `5.1229` | `5.5136` | `5.8129` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_dist_rate_shift_p14d` | `15.718` | `23.022` | `27.509` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_helio_dist_shift_p14d` | `4.9931` | `4.9988` | `5.005` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_helio_dist_rate_shift_p14d` | `0.36392` | `0.38591` | `0.40503` |

### Container: `packed_astro_container_094` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_phase_angle_shift_p14d` | `6.2686` | `9.2752` | `11.098` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_elong_shift_p14d` | `33.107` | `54.245` | `76.929` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_illum_frac_shift_p14d` | `24.437` | `61.481` | `89.624` |
| `Bits 6-7` | `>> 6` | `astro_mars_ra_icrf_shift_p14d` | `299.22` | `320.42` | `340.53` |
| `Bits 8-9` | `>> 8` | `astro_mars_dec_icrf_shift_p14d` | `-21.511` | `-16.367` | `-9.2596` |
| `Bits 10-11` | `>> 10` | `astro_mars_ra_app_shift_p14d` | `298.75` | `319.98` | `340.11` |
| `Bits 12-13` | `>> 12` | `astro_mars_dec_app_shift_p14d` | `-21.447` | `-16.266` | `-9.1346` |
| `Bits 14-15` | `>> 14` | `astro_mars_azim_shift_p14d` | `62.629` | `62.711` | `62.929` |

### Container: `packed_astro_container_095` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_elev_shift_p14d` | `-55.1` | `-47.944` | `-38.527` |
| `Bits 2-3` | `>> 2` | `astro_mars_app_mag_shift_p14d` | `1.1655` | `1.252` | `1.2963` |
| `Bits 4-5` | `>> 4` | `astro_mars_surf_bright_shift_p14d` | `4.052` | `4.0925` | `4.1392` |
| `Bits 6-7` | `>> 6` | `astro_mars_dist_shift_p14d` | `2.078` | `2.181` | `2.2831` |
| `Bits 8-9` | `>> 8` | `astro_mars_dist_rate_shift_p14d` | `-6.8578` | `-6.8145` | `-6.6627` |
| `Bits 10-11` | `>> 10` | `astro_mars_helio_dist_shift_p14d` | `1.3898` | `1.4072` | `1.4324` |
| `Bits 12-13` | `>> 12` | `astro_mars_helio_dist_rate_shift_p14d` | `-1.8354` | `-1.3979` | `-0.8328` |
| `Bits 14-15` | `>> 14` | `astro_mars_phase_angle_shift_p14d` | `15.894` | `20.453` | `24.662` |

### Container: `packed_astro_container_096` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_elong_shift_p14d` | `23.423` | `29.689` | `35.435` |
| `Bits 2-3` | `>> 2` | `astro_mars_illum_frac_shift_p14d` | `24.437` | `61.481` | `89.624` |
| `Bits 4-5` | `>> 4` | `astro_ceres_ra_icrf_shift_p14d` | `270.92` | `280.54` | `288.13` |
| `Bits 6-7` | `>> 6` | `astro_ceres_dec_icrf_shift_p14d` | `-23.521` | `-23.136` | `-22.623` |
| `Bits 8-9` | `>> 8` | `astro_ceres_ra_app_shift_p14d` | `271.28` | `280.91` | `288.49` |
| `Bits 10-11` | `>> 10` | `astro_ceres_dec_app_shift_p14d` | `-23.481` | `-23.114` | `-22.623` |
| `Bits 12-13` | `>> 12` | `astro_ceres_azim_shift_p14d` | `89.372` | `100.63` | `112.54` |
| `Bits 14-15` | `>> 14` | `astro_ceres_elev_shift_p14d` | `-35.196` | `-23.269` | `-10.312` |

### Container: `packed_astro_container_097` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_ceres_app_mag_shift_p14d` | `8.8095` | `9.0005` | `9.055` |
| `Bits 2-3` | `>> 2` | `astro_ceres_surf_bright_shift_p14d` | `6.8005` | `6.923` | `6.9752` |
| `Bits 4-5` | `>> 4` | `astro_ceres_dist_shift_p14d` | `2.6873` | `3.0247` | `3.3184` |
| `Bits 6-7` | `>> 6` | `astro_ceres_dist_rate_shift_p14d` | `-22.356` | `-21.102` | `-17.242` |
| `Bits 8-9` | `>> 8` | `astro_ceres_helio_dist_shift_p14d` | `2.7933` | `2.8146` | `2.8352` |
| `Bits 10-11` | `>> 10` | `astro_ceres_helio_dist_rate_shift_p14d` | `1.3122` | `1.3577` | `1.3912` |
| `Bits 12-13` | `>> 12` | `astro_ceres_phase_angle_shift_p14d` | `15.773` | `19.144` | `20.293` |
| `Bits 14-15` | `>> 14` | `astro_ceres_elong_shift_p14d` | `50.304` | `68.382` | `88.04` |

### Container: `packed_astro_container_098` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_ceres_illum_frac_shift_p14d` | `24.437` | `61.481` | `89.624` |
| `Bits 2-3` | `>> 2` | `astro_venus_ra_icrf_shift_p14d` | `201.39` | `293.78` | `327.75` |
| `Bits 4-5` | `>> 4` | `astro_venus_dec_icrf_shift_p14d` | `-21.429` | `-13.954` | `-1.9483` |
| `Bits 6-7` | `>> 6` | `astro_venus_ra_app_shift_p14d` | `201.74` | `294.13` | `328.07` |
| `Bits 8-9` | `>> 8` | `astro_venus_dec_app_shift_p14d` | `-21.377` | `-13.843` | `-1.816` |
| `Bits 10-11` | `>> 10` | `astro_venus_azim_shift_p14d` | `37.671` | `52.788` | `69.224` |
| `Bits 12-13` | `>> 12` | `astro_venus_elev_shift_p14d` | `-50.719` | `-47.839` | `-42.605` |
| `Bits 14-15` | `>> 14` | `astro_venus_app_mag_shift_p14d` | `-3.9225` | `-3.8855` | `-3.878` |

### Container: `packed_astro_container_099` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_surf_bright_shift_p14d` | `0.86725` | `0.9485` | `1.035` |
| `Bits 2-3` | `>> 2` | `astro_venus_dist_shift_p14d` | `1.413` | `1.5358` | `1.6332` |
| `Bits 4-5` | `>> 4` | `astro_venus_dist_rate_shift_p14d` | `5.2568` | `6.9887` | `8.5068` |
| `Bits 6-7` | `>> 6` | `astro_venus_helio_dist_shift_p14d` | `0.72545` | `0.7269` | `0.72786` |
| `Bits 8-9` | `>> 8` | `astro_venus_helio_dist_rate_shift_p14d` | `-0.097116` | `0.073265` | `0.20561` |
| `Bits 10-11` | `>> 10` | `astro_venus_phase_angle_shift_p14d` | `22.486` | `31.677` | `40.938` |
| `Bits 12-13` | `>> 12` | `astro_venus_elong_shift_p14d` | `16.157` | `22.646` | `28.805` |
| `Bits 14-15` | `>> 14` | `astro_venus_illum_frac_shift_p14d` | `24.437` | `61.481` | `89.624` |

### Container: `packed_astro_container_100` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_ra_icrf_shift_p21d` | `23.34` | `311.67` | `336.39` |
| `Bits 2-3` | `>> 2` | `astro_sun_dec_icrf_shift_p21d` | `-12.694` | `-3.3438` | `6.4258` |
| `Bits 4-5` | `>> 4` | `astro_sun_ra_app_shift_p21d` | `23.653` | `312.01` | `336.71` |
| `Bits 6-7` | `>> 6` | `astro_sun_dec_app_shift_p21d` | `-12.583` | `-3.2134` | `6.5541` |
| `Bits 8-9` | `>> 8` | `astro_sun_azim_shift_p21d` | `16.347` | `16.704` | `18.493` |
| `Bits 10-11` | `>> 10` | `astro_sun_elev_shift_p21d` | `-58.678` | `-49.305` | `-39.371` |
| `Bits 12-13` | `>> 12` | `astro_sun_app_mag_shift_p21d` | `-26.769` | `-26.756` | `-26.741` |
| `Bits 14-15` | `>> 14` | `astro_sun_dist_shift_p21d` | `0.9878` | `0.99372` | `1.0007` |

### Container: `packed_astro_container_101` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_dist_rate_shift_p21d` | `0.27391` | `0.38546` | `0.4031` |
| `Bits 2-3` | `>> 2` | `astro_sun_illum_frac_shift_p21d` | `22.227` | `63.765` | `90.456` |
| `Bits 4-5` | `>> 4` | `astro_moon_ra_icrf_shift_p21d` | `104.68` | `178.43` | `253.17` |
| `Bits 6-7` | `>> 6` | `astro_moon_dec_icrf_shift_p21d` | `-21.24` | `0.03364` | `19.594` |
| `Bits 8-9` | `>> 8` | `astro_moon_ra_app_shift_p21d` | `105.06` | `178.74` | `253.55` |
| `Bits 10-11` | `>> 10` | `astro_moon_dec_app_shift_p21d` | `-21.335` | `-0.10299` | `19.49` |
| `Bits 12-13` | `>> 12` | `astro_moon_azim_shift_p21d` | `118.43` | `183.58` | `273.83` |
| `Bits 14-15` | `>> 14` | `astro_moon_elev_shift_p21d` | `-24.607` | `8.4402` | `33.561` |

### Container: `packed_astro_container_102` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_app_mag_shift_p21d` | `-11.712` | `-10.693` | `-8.65` |
| `Bits 2-3` | `>> 2` | `astro_moon_surf_bright_shift_p21d` | `4.178` | `4.862` | `5.679` |
| `Bits 4-5` | `>> 4` | `astro_moon_dist_shift_p21d` | `0.0025101` | `0.0026021` | `0.0026639` |
| `Bits 6-7` | `>> 6` | `astro_moon_dist_rate_shift_p21d` | `-0.24932` | `-0.0010517` | `0.2406` |
| `Bits 8-9` | `>> 8` | `astro_moon_helio_dist_shift_p21d` | `0.98742` | `0.99248` | `1.0001` |
| `Bits 10-11` | `>> 10` | `astro_moon_helio_dist_rate_shift_p21d` | `-0.26302` | `0.3406` | `1.0126` |
| `Bits 12-13` | `>> 12` | `astro_moon_phase_angle_shift_p21d` | `35.986` | `74.018` | `123.75` |
| `Bits 14-15` | `>> 14` | `astro_moon_elong_shift_p21d` | `56.133` | `105.84` | `143.92` |

### Container: `packed_astro_container_103` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_illum_frac_shift_p21d` | `22.227` | `63.765` | `90.456` |
| `Bits 2-3` | `>> 2` | `astro_saturn_ra_icrf_shift_p21d` | `340.16` | `343.02` | `345.75` |
| `Bits 4-5` | `>> 4` | `astro_saturn_dec_icrf_shift_p21d` | `-10.11` | `-8.9814` | `-7.9114` |
| `Bits 6-7` | `>> 6` | `astro_saturn_ra_app_shift_p21d` | `340.47` | `343.33` | `346.06` |
| `Bits 8-9` | `>> 8` | `astro_saturn_dec_app_shift_p21d` | `-9.9868` | `-8.8558` | `-7.7834` |
| `Bits 10-11` | `>> 10` | `astro_saturn_azim_shift_p21d` | `35.684` | `60.499` | `321.3` |
| `Bits 12-13` | `>> 12` | `astro_saturn_elev_shift_p21d` | `-55.829` | `-51.821` | `-39.263` |
| `Bits 14-15` | `>> 14` | `astro_saturn_app_mag_shift_p21d` | `0.988` | `1.01` | `1.063` |

### Container: `packed_astro_container_104` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_surf_bright_shift_p21d` | `6.687` | `6.709` | `6.788` |
| `Bits 2-3` | `>> 2` | `astro_saturn_dist_shift_p21d` | `10.533` | `10.631` | `10.691` |
| `Bits 4-5` | `>> 4` | `astro_saturn_dist_rate_shift_p21d` | `-15.777` | `-5.5252` | `5.6141` |
| `Bits 6-7` | `>> 6` | `astro_saturn_helio_dist_shift_p21d` | `9.7104` | `9.7176` | `9.7248` |
| `Bits 8-9` | `>> 8` | `astro_saturn_helio_dist_rate_shift_p21d` | `-0.50041` | `-0.49735` | `-0.49465` |
| `Bits 10-11` | `>> 10` | `astro_saturn_phase_angle_shift_p21d` | `1.1669` | `2.2093` | `3.238` |
| `Bits 12-13` | `>> 12` | `astro_saturn_elong_shift_p21d` | `11.527` | `22.199` | `33.438` |
| `Bits 14-15` | `>> 14` | `astro_saturn_illum_frac_shift_p21d` | `22.227` | `63.765` | `90.456` |

### Container: `packed_astro_container_105` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_ra_icrf_shift_p21d` | `36.722` | `40.789` | `45.878` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_dec_icrf_shift_p21d` | `13.51` | `14.891` | `16.444` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_ra_app_shift_p21d` | `37.048` | `41.117` | `46.211` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_dec_app_shift_p21d` | `13.618` | `14.993` | `16.538` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_azim_shift_p21d` | `301.46` | `319.4` | `339.29` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_elev_shift_p21d` | `-28.396` | `-22.666` | `-12.423` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_app_mag_shift_p21d` | `-2.252` | `-2.129` | `-2.05` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_surf_bright_shift_p21d` | `5.331` | `5.35` | `5.368` |

### Container: `packed_astro_container_106` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_dist_shift_p21d` | `5.2046` | `5.5589` | `5.8284` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_dist_rate_shift_p21d` | `15.175` | `22.188` | `26.908` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_helio_dist_shift_p21d` | `4.9942` | `4.9996` | `5.0054` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_helio_dist_rate_shift_p21d` | `0.36799` | `0.38803` | `0.40673` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_phase_angle_shift_p21d` | `6.0438` | `8.9368` | `10.862` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_elong_shift_p21d` | `31.765` | `51.4` | `72.33` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_illum_frac_shift_p21d` | `22.227` | `63.765` | `90.456` |
| `Bits 14-15` | `>> 14` | `astro_mars_ra_icrf_shift_p21d` | `303.46` | `323.12` | `341.81` |

### Container: `packed_astro_container_107` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_dec_icrf_shift_p21d` | `-20.699` | `-15.529` | `-8.7497` |
| `Bits 2-3` | `>> 2` | `astro_mars_ra_app_shift_p21d` | `303` | `322.68` | `341.39` |
| `Bits 4-5` | `>> 4` | `astro_mars_dec_app_shift_p21d` | `-20.627` | `-15.423` | `-8.6237` |
| `Bits 6-7` | `>> 6` | `astro_mars_azim_shift_p21d` | `62.638` | `62.729` | `62.943` |
| `Bits 8-9` | `>> 8` | `astro_mars_elev_shift_p21d` | `-53.897` | `-46.827` | `-37.851` |
| `Bits 10-11` | `>> 10` | `astro_mars_app_mag_shift_p21d` | `1.157` | `1.242` | `1.286` |
| `Bits 12-13` | `>> 12` | `astro_mars_surf_bright_shift_p21d` | `4.049` | `4.094` | `4.146` |
| `Bits 14-15` | `>> 14` | `astro_mars_dist_shift_p21d` | `2.0713` | `2.1674` | `2.2633` |

### Container: `packed_astro_container_108` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_dist_rate_shift_p21d` | `-6.8626` | `-6.8243` | `-6.743` |
| `Bits 2-3` | `>> 2` | `astro_mars_helio_dist_shift_p21d` | `1.389` | `1.4045` | `1.4269` |
| `Bits 4-5` | `>> 4` | `astro_mars_helio_dist_rate_shift_p21d` | `-1.7611` | `-1.3304` | `-0.79239` |
| `Bits 6-7` | `>> 6` | `astro_mars_phase_angle_shift_p21d` | `16.814` | `21.025` | `24.925` |
| `Bits 8-9` | `>> 8` | `astro_mars_elong_shift_p21d` | `24.7` | `30.469` | `35.797` |
| `Bits 10-11` | `>> 10` | `astro_mars_illum_frac_shift_p21d` | `22.227` | `63.765` | `90.456` |
| `Bits 12-13` | `>> 12` | `astro_ceres_ra_icrf_shift_p21d` | `272.93` | `281.67` | `288.53` |
| `Bits 14-15` | `>> 14` | `astro_ceres_dec_icrf_shift_p21d` | `-23.554` | `-23.183` | `-22.756` |

### Container: `packed_astro_container_109` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_ceres_ra_app_shift_p21d` | `273.29` | `282.04` | `288.9` |
| `Bits 2-3` | `>> 2` | `astro_ceres_dec_app_shift_p21d` | `-23.513` | `-23.158` | `-22.752` |
| `Bits 4-5` | `>> 4` | `astro_ceres_azim_shift_p21d` | `91.631` | `102.1` | `113.4` |
| `Bits 6-7` | `>> 6` | `astro_ceres_elev_shift_p21d` | `-32.95` | `-21.625` | `-9.4401` |
| `Bits 8-9` | `>> 8` | `astro_ceres_app_mag_shift_p21d` | `8.793` | `8.983` | `9.057` |
| `Bits 10-11` | `>> 10` | `astro_ceres_surf_bright_shift_p21d` | `6.829` | `6.935` | `6.976` |
| `Bits 12-13` | `>> 12` | `astro_ceres_dist_shift_p21d` | `2.6646` | `2.9823` | `3.2656` |
| `Bits 14-15` | `>> 14` | `astro_ceres_dist_rate_shift_p21d` | `-22.414` | `-21.368` | `-18.133` |

### Container: `packed_astro_container_110` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_ceres_helio_dist_shift_p21d` | `2.7975` | `2.8173` | `2.8366` |
| `Bits 2-3` | `>> 2` | `astro_ceres_helio_dist_rate_shift_p21d` | `1.3089` | `1.3524` | `1.3856` |
| `Bits 4-5` | `>> 4` | `astro_ceres_phase_angle_shift_p21d` | `16.546` | `19.377` | `20.346` |
| `Bits 6-7` | `>> 6` | `astro_ceres_elong_shift_p21d` | `53.759` | `70.85` | `89.4` |
| `Bits 8-9` | `>> 8` | `astro_ceres_illum_frac_shift_p21d` | `22.227` | `63.765` | `90.456` |
| `Bits 10-11` | `>> 10` | `astro_venus_ra_icrf_shift_p21d` | `28.651` | `298.38` | `329.87` |
| `Bits 12-13` | `>> 12` | `astro_venus_dec_icrf_shift_p21d` | `-20.483` | `-12.563` | `-1.0942` |
| `Bits 14-15` | `>> 14` | `astro_venus_ra_app_shift_p21d` | `28.967` | `298.73` | `330.19` |

### Container: `packed_astro_container_111` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_dec_app_shift_p21d` | `-20.417` | `-12.447` | `-0.96178` |
| `Bits 2-3` | `>> 2` | `astro_venus_azim_shift_p21d` | `36.841` | `50.569` | `66.359` |
| `Bits 4-5` | `>> 4` | `astro_venus_elev_shift_p21d` | `-50.851` | `-48.253` | `-41.956` |
| `Bits 6-7` | `>> 6` | `astro_venus_app_mag_shift_p21d` | `-3.913` | `-3.884` | `-3.878` |
| `Bits 8-9` | `>> 8` | `astro_venus_surf_bright_shift_p21d` | `0.862` | `0.938` | `1.018` |
| `Bits 10-11` | `>> 10` | `astro_venus_dist_shift_p21d` | `1.4389` | `1.55` | `1.6386` |
| `Bits 12-13` | `>> 12` | `astro_venus_dist_rate_shift_p21d` | `5.1287` | `6.7675` | `8.215` |
| `Bits 14-15` | `>> 14` | `astro_venus_helio_dist_shift_p21d` | `0.72574` | `0.72707` | `0.7279` |

### Container: `packed_astro_container_112` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_helio_dist_rate_shift_p21d` | `-0.10743` | `0.051248` | `0.18656` |
| `Bits 2-3` | `>> 2` | `astro_venus_phase_angle_shift_p21d` | `21.878` | `30.48` | `39.095` |
| `Bits 4-5` | `>> 4` | `astro_venus_elong_shift_p21d` | `15.72` | `21.816` | `27.623` |
| `Bits 6-7` | `>> 6` | `astro_venus_illum_frac_shift_p21d` | `22.227` | `63.765` | `90.456` |
| `Bits 8-9` | `>> 8` | `astro_sun_ra_icrf_shift_p28d` | `21.723` | `315.26` | `338.05` |
| `Bits 10-11` | `>> 10` | `astro_sun_dec_icrf_shift_p28d` | `-10.848` | `-1.9634` | `7.0845` |
| `Bits 12-13` | `>> 12` | `astro_sun_ra_app_shift_p28d` | `22.035` | `315.59` | `338.36` |
| `Bits 14-15` | `>> 14` | `astro_sun_dec_app_shift_p28d` | `-10.731` | `-1.832` | `7.2118` |

### Container: `packed_astro_container_113` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_azim_shift_p28d` | `16.323` | `16.619` | `17.873` |
| `Bits 2-3` | `>> 2` | `astro_sun_elev_shift_p28d` | `-56.853` | `-47.904` | `-38.702` |
| `Bits 4-5` | `>> 4` | `astro_sun_app_mag_shift_p28d` | `-26.767` | `-26.754` | `-26.739` |
| `Bits 6-7` | `>> 6` | `astro_sun_dist_shift_p28d` | `0.98885` | `0.99465` | `1.0012` |
| `Bits 8-9` | `>> 8` | `astro_sun_dist_rate_shift_p28d` | `0.30937` | `0.38772` | `0.40542` |
| `Bits 10-11` | `>> 10` | `astro_sun_illum_frac_shift_p28d` | `20.532` | `58.428` | `87.086` |
| `Bits 12-13` | `>> 12` | `astro_moon_ra_icrf_shift_p28d` | `108.3` | `188.34` | `261.13` |
| `Bits 14-15` | `>> 14` | `astro_moon_dec_icrf_shift_p28d` | `-21.951` | `-3.4694` | `17.109` |

### Container: `packed_astro_container_114` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_ra_app_shift_p28d` | `108.67` | `188.65` | `261.51` |
| `Bits 2-3` | `>> 2` | `astro_moon_dec_app_shift_p28d` | `-21.992` | `-3.604` | `16.997` |
| `Bits 4-5` | `>> 4` | `astro_moon_azim_shift_p28d` | `116.92` | `172.72` | `282.66` |
| `Bits 6-7` | `>> 6` | `astro_moon_elev_shift_p28d` | `-26.205` | `6.0469` | `30.156` |
| `Bits 8-9` | `>> 8` | `astro_moon_app_mag_shift_p28d` | `-11.54` | `-10.432` | `-8.4848` |
| `Bits 10-11` | `>> 10` | `astro_moon_surf_bright_shift_p28d` | `4.268` | `4.9795` | `5.7308` |
| `Bits 12-13` | `>> 12` | `astro_moon_dist_shift_p28d` | `0.0024989` | `0.0025987` | `0.0026647` |
| `Bits 14-15` | `>> 14` | `astro_moon_dist_rate_shift_p28d` | `-0.25782` | `-0.021198` | `0.24019` |

### Container: `packed_astro_container_115` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_helio_dist_shift_p28d` | `0.99063` | `0.99374` | `1.0002` |
| `Bits 2-3` | `>> 2` | `astro_moon_helio_dist_rate_shift_p28d` | `-0.28441` | `0.34187` | `1.0649` |
| `Bits 4-5` | `>> 4` | `astro_moon_phase_angle_shift_p28d` | `42.112` | `80.295` | `126.12` |
| `Bits 6-7` | `>> 6` | `astro_moon_elong_shift_p28d` | `53.765` | `99.555` | `137.79` |
| `Bits 8-9` | `>> 8` | `astro_moon_illum_frac_shift_p28d` | `20.532` | `58.428` | `87.086` |
| `Bits 10-11` | `>> 10` | `astro_saturn_ra_icrf_shift_p28d` | `340.76` | `343.42` | `345.93` |
| `Bits 12-13` | `>> 12` | `astro_saturn_dec_icrf_shift_p28d` | `-9.8737` | `-8.8254` | `-7.8416` |
| `Bits 14-15` | `>> 14` | `astro_saturn_ra_app_shift_p28d` | `341.07` | `343.73` | `346.24` |

### Container: `packed_astro_container_116` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_dec_app_shift_p28d` | `-9.7501` | `-8.6995` | `-7.7134` |
| `Bits 2-3` | `>> 2` | `astro_saturn_azim_shift_p28d` | `33.544` | `57.565` | `74.976` |
| `Bits 4-5` | `>> 4` | `astro_saturn_elev_shift_p28d` | `-55.988` | `-50.381` | `-38.23` |
| `Bits 6-7` | `>> 6` | `astro_saturn_app_mag_shift_p28d` | `0.98925` | `1.021` | `1.0648` |
| `Bits 8-9` | `>> 8` | `astro_saturn_surf_bright_shift_p28d` | `6.6843` | `6.7175` | `6.7932` |
| `Bits 10-11` | `>> 10` | `astro_saturn_dist_shift_p28d` | `10.523` | `10.641` | `10.693` |
| `Bits 12-13` | `>> 12` | `astro_saturn_dist_rate_shift_p28d` | `-16.431` | `-7.0537` | `3.2791` |
| `Bits 14-15` | `>> 14` | `astro_saturn_helio_dist_shift_p28d` | `9.7099` | `9.7166` | `9.7233` |

### Container: `packed_astro_container_117` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_helio_dist_rate_shift_p28d` | `-0.5005` | `-0.49765` | `-0.49537` |
| `Bits 2-3` | `>> 2` | `astro_saturn_phase_angle_shift_p28d` | `1.0825` | `2.0773` | `3.3106` |
| `Bits 4-5` | `>> 4` | `astro_saturn_elong_shift_p28d` | `10.679` | `20.815` | `34.093` |
| `Bits 6-7` | `>> 6` | `astro_saturn_illum_frac_shift_p28d` | `20.532` | `58.428` | `87.086` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_ra_icrf_shift_p28d` | `37.471` | `41.45` | `46.262` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_dec_icrf_shift_p28d` | `13.775` | `15.103` | `16.554` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_ra_app_shift_p28d` | `37.797` | `41.779` | `46.596` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_dec_app_shift_p28d` | `13.882` | `15.204` | `16.647` |

### Container: `packed_astro_container_118` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_azim_shift_p28d` | `305.06` | `322.08` | `340.73` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_elev_shift_p28d` | `-28.612` | `-23.755` | `-14.913` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_app_mag_shift_p28d` | `-2.2225` | `-2.116` | `-2.0455` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_surf_bright_shift_p28d` | `5.3293` | `5.3475` | `5.3647` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_dist_shift_p28d` | `5.2842` | `5.6025` | `5.8434` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_dist_rate_shift_p28d` | `14.624` | `21.308` | `26.154` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_helio_dist_shift_p28d` | `4.9953` | `5.0004` | `5.0058` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_helio_dist_rate_shift_p28d` | `0.37252` | `0.39043` | `0.40984` |

### Container: `packed_astro_container_119` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_phase_angle_shift_p28d` | `5.8162` | `8.5793` | `10.561` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_elong_shift_p28d` | `30.428` | `48.582` | `67.808` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_illum_frac_shift_p28d` | `20.532` | `58.428` | `87.086` |
| `Bits 6-7` | `>> 6` | `astro_mars_ra_icrf_shift_p28d` | `307.66` | `325.79` | `343.09` |
| `Bits 8-9` | `>> 8` | `astro_mars_dec_icrf_shift_p28d` | `-19.784` | `-14.658` | `-8.2357` |
| `Bits 10-11` | `>> 10` | `astro_mars_ra_app_shift_p28d` | `307.2` | `325.35` | `342.67` |
| `Bits 12-13` | `>> 12` | `astro_mars_dec_app_shift_p28d` | `-19.704` | `-14.549` | `-8.1089` |
| `Bits 14-15` | `>> 14` | `astro_mars_azim_shift_p28d` | `62.651` | `62.747` | `62.956` |

### Container: `packed_astro_container_120` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_elev_shift_p28d` | `-52.593` | `-45.671` | `-37.169` |
| `Bits 2-3` | `>> 2` | `astro_mars_app_mag_shift_p28d` | `1.1562` | `1.2325` | `1.281` |
| `Bits 4-5` | `>> 4` | `astro_mars_surf_bright_shift_p28d` | `4.0563` | `4.0995` | `4.1517` |
| `Bits 6-7` | `>> 6` | `astro_mars_dist_shift_p28d` | `2.0647` | `2.1539` | `2.2434` |
| `Bits 8-9` | `>> 8` | `astro_mars_dist_rate_shift_p28d` | `-6.8655` | `-6.8323` | `-6.781` |
| `Bits 10-11` | `>> 10` | `astro_mars_helio_dist_shift_p28d` | `1.3882` | `1.4018` | `1.4217` |
| `Bits 12-13` | `>> 12` | `astro_mars_helio_dist_rate_shift_p28d` | `-1.6809` | `-1.2608` | `-0.75163` |
| `Bits 14-15` | `>> 14` | `astro_mars_phase_angle_shift_p28d` | `17.722` | `21.591` | `25.186` |

### Container: `packed_astro_container_121` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_elong_shift_p28d` | `25.953` | `31.239` | `36.158` |
| `Bits 2-3` | `>> 2` | `astro_mars_illum_frac_shift_p28d` | `20.532` | `58.428` | `87.086` |
| `Bits 4-5` | `>> 4` | `astro_ceres_ra_icrf_shift_p28d` | `274.89` | `282.76` | `288.92` |
| `Bits 6-7` | `>> 6` | `astro_ceres_dec_icrf_shift_p28d` | `-23.589` | `-23.229` | `-22.871` |
| `Bits 8-9` | `>> 8` | `astro_ceres_ra_app_shift_p28d` | `275.25` | `283.13` | `289.29` |
| `Bits 10-11` | `>> 10` | `astro_ceres_dec_app_shift_p28d` | `-23.548` | `-23.201` | `-22.861` |
| `Bits 12-13` | `>> 12` | `astro_ceres_azim_shift_p28d` | `93.848` | `103.59` | `114.26` |
| `Bits 14-15` | `>> 14` | `astro_ceres_elev_shift_p28d` | `-30.656` | `-19.963` | `-8.5668` |

### Container: `packed_astro_container_122` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_ceres_app_mag_shift_p28d` | `8.7748` | `8.963` | `9.0565` |
| `Bits 2-3` | `>> 2` | `astro_ceres_surf_bright_shift_p28d` | `6.8552` | `6.9455` | `6.9778` |
| `Bits 4-5` | `>> 4` | `astro_ceres_dist_shift_p28d` | `2.6418` | `2.9392` | `3.2103` |
| `Bits 6-7` | `>> 6` | `astro_ceres_dist_rate_shift_p28d` | `-22.463` | `-21.549` | `-18.953` |
| `Bits 8-9` | `>> 8` | `astro_ceres_helio_dist_shift_p28d` | `2.8017` | `2.8201` | `2.8379` |
| `Bits 10-11` | `>> 10` | `astro_ceres_helio_dist_rate_shift_p28d` | `1.3054` | `1.3469` | `1.3795` |
| `Bits 12-13` | `>> 12` | `astro_ceres_phase_angle_shift_p28d` | `17.269` | `19.56` | `20.38` |
| `Bits 14-15` | `>> 14` | `astro_ceres_elong_shift_p28d` | `57.255` | `73.347` | `90.772` |

### Container: `packed_astro_container_123` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_ceres_illum_frac_shift_p28d` | `20.532` | `58.428` | `87.086` |
| `Bits 2-3` | `>> 2` | `astro_venus_ra_icrf_shift_p28d` | `26.616` | `302.94` | `331.97` |
| `Bits 4-5` | `>> 4` | `astro_venus_dec_icrf_shift_p28d` | `-19.26` | `-11.1` | `-0.23749` |
| `Bits 6-7` | `>> 6` | `astro_venus_ra_app_shift_p28d` | `26.931` | `303.29` | `332.29` |
| `Bits 8-9` | `>> 8` | `astro_venus_dec_app_shift_p28d` | `-19.18` | `-10.98` | `-0.10522` |
| `Bits 10-11` | `>> 10` | `astro_venus_azim_shift_p28d` | `36.029` | `48.409` | `63.225` |
| `Bits 12-13` | `>> 12` | `astro_venus_elev_shift_p28d` | `-50.967` | `-48.738` | `-41.298` |
| `Bits 14-15` | `>> 14` | `astro_venus_app_mag_shift_p28d` | `-3.9045` | `-3.883` | `-3.878` |

### Container: `packed_astro_container_124` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_surf_bright_shift_p28d` | `0.85675` | `0.9265` | `1.001` |
| `Bits 2-3` | `>> 2` | `astro_venus_dist_shift_p28d` | `1.464` | `1.5638` | `1.6438` |
| `Bits 4-5` | `>> 4` | `astro_venus_dist_rate_shift_p28d` | `4.9982` | `6.5478` | `7.9306` |
| `Bits 6-7` | `>> 6` | `astro_venus_helio_dist_shift_p28d` | `0.72607` | `0.7272` | `0.72794` |
| `Bits 8-9` | `>> 8` | `astro_venus_helio_dist_rate_shift_p28d` | `-0.11748` | `0.028748` | `0.16356` |
| `Bits 10-11` | `>> 10` | `astro_venus_phase_angle_shift_p28d` | `21.269` | `29.283` | `37.267` |
| `Bits 12-13` | `>> 12` | `astro_venus_elong_shift_p28d` | `15.282` | `20.982` | `26.427` |
| `Bits 14-15` | `>> 14` | `astro_venus_illum_frac_shift_p28d` | `20.532` | `58.428` | `87.086` |

### Container: `packed_astro_container_125` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_ra_icrf_shift_p35d` | `20.111` | `318.8` | `339.71` |
| `Bits 2-3` | `>> 2` | `astro_sun_dec_icrf_shift_p35d` | `-8.9253` | `-0.57996` | `7.7371` |
| `Bits 4-5` | `>> 4` | `astro_sun_ra_app_shift_p35d` | `20.422` | `319.13` | `340.02` |
| `Bits 6-7` | `>> 6` | `astro_sun_dec_app_shift_p35d` | `-8.8034` | `-0.44801` | `7.8634` |
| `Bits 8-9` | `>> 8` | `astro_sun_azim_shift_p35d` | `16.297` | `16.554` | `17.41` |
| `Bits 10-11` | `>> 10` | `astro_sun_elev_shift_p35d` | `-54.934` | `-46.497` | `-38.04` |
| `Bits 12-13` | `>> 12` | `astro_sun_app_mag_shift_p35d` | `-26.764` | `-26.752` | `-26.739` |
| `Bits 14-15` | `>> 14` | `astro_sun_dist_shift_p35d` | `0.99002` | `0.99559` | `1.0017` |

### Container: `packed_astro_container_126` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_dist_rate_shift_p35d` | `0.34722` | `0.39044` | `0.40767` |
| `Bits 2-3` | `>> 2` | `astro_sun_illum_frac_shift_p35d` | `18.585` | `56.064` | `88.054` |
| `Bits 4-5` | `>> 4` | `astro_moon_ra_icrf_shift_p35d` | `99.252` | `184.56` | `265.96` |
| `Bits 6-7` | `>> 6` | `astro_moon_dec_icrf_shift_p35d` | `-22.752` | `-2.198` | `18.424` |
| `Bits 8-9` | `>> 8` | `astro_moon_ra_app_shift_p35d` | `99.633` | `184.87` | `266.35` |
| `Bits 10-11` | `>> 10` | `astro_moon_dec_app_shift_p35d` | `-22.751` | `-2.0661` | `18.524` |
| `Bits 12-13` | `>> 12` | `astro_moon_azim_shift_p35d` | `117.59` | `187.19` | `286.07` |
| `Bits 14-15` | `>> 14` | `astro_moon_elev_shift_p35d` | `-29.829` | `5.2124` | `29.897` |

### Container: `packed_astro_container_127` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_app_mag_shift_p35d` | `-11.61` | `-10.359` | `-8.3545` |
| `Bits 2-3` | `>> 2` | `astro_moon_surf_bright_shift_p35d` | `4.2405` | `4.987` | `5.8315` |
| `Bits 4-5` | `>> 4` | `astro_moon_dist_shift_p35d` | `0.0024861` | `0.002579` | `0.0026555` |
| `Bits 6-7` | `>> 6` | `astro_moon_dist_rate_shift_p35d` | `-0.2279` | `0.031144` | `0.26185` |
| `Bits 8-9` | `>> 8` | `astro_moon_helio_dist_shift_p35d` | `0.99097` | `0.99651` | `1.0004` |
| `Bits 10-11` | `>> 10` | `astro_moon_helio_dist_rate_shift_p35d` | `-0.18975` | `0.49112` | `1.0977` |
| `Bits 12-13` | `>> 12` | `astro_moon_phase_angle_shift_p35d` | `40.428` | `83.035` | `128.94` |
| `Bits 14-15` | `>> 14` | `astro_moon_elong_shift_p35d` | `50.952` | `96.815` | `139.47` |

### Container: `packed_astro_container_128` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_illum_frac_shift_p35d` | `18.585` | `56.064` | `88.054` |
| `Bits 2-3` | `>> 2` | `astro_saturn_ra_icrf_shift_p35d` | `341.36` | `343.81` | `346.1` |
| `Bits 4-5` | `>> 4` | `astro_saturn_dec_icrf_shift_p35d` | `-9.6362` | `-8.6709` | `-7.7727` |
| `Bits 6-7` | `>> 6` | `astro_saturn_ra_app_shift_p35d` | `341.67` | `344.12` | `346.41` |
| `Bits 8-9` | `>> 8` | `astro_saturn_dec_app_shift_p35d` | `-9.5121` | `-8.5446` | `-7.6444` |
| `Bits 10-11` | `>> 10` | `astro_saturn_azim_shift_p35d` | `31.346` | `54.486` | `71.399` |
| `Bits 12-13` | `>> 12` | `astro_saturn_elev_shift_p35d` | `-56.131` | `-48.818` | `-37.184` |
| `Bits 14-15` | `>> 14` | `astro_saturn_app_mag_shift_p35d` | `0.9875` | `1.03` | `1.0665` |

### Container: `packed_astro_container_129` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_surf_bright_shift_p35d` | `6.682` | `6.73` | `6.7985` |
| `Bits 2-3` | `>> 2` | `astro_saturn_dist_shift_p35d` | `10.506` | `10.651` | `10.696` |
| `Bits 4-5` | `>> 4` | `astro_saturn_dist_rate_shift_p35d` | `-17.073` | `-8.5513` | `0.93633` |
| `Bits 6-7` | `>> 6` | `astro_saturn_helio_dist_shift_p35d` | `9.7094` | `9.7156` | `9.7218` |
| `Bits 8-9` | `>> 8` | `astro_saturn_helio_dist_rate_shift_p35d` | `-0.50072` | `-0.49822` | `-0.49573` |
| `Bits 10-11` | `>> 10` | `astro_saturn_phase_angle_shift_p35d` | `0.99795` | `1.9445` | `3.4423` |
| `Bits 12-13` | `>> 12` | `astro_saturn_elong_shift_p35d` | `9.8385` | `19.478` | `35.623` |
| `Bits 14-15` | `>> 14` | `astro_saturn_illum_frac_shift_p35d` | `18.585` | `56.064` | `88.054` |

### Container: `packed_astro_container_130` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_ra_icrf_shift_p35d` | `38.279` | `42.129` | `46.65` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_dec_icrf_shift_p35d` | `14.055` | `15.317` | `16.664` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_ra_app_shift_p35d` | `38.606` | `42.458` | `46.983` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_dec_app_shift_p35d` | `14.161` | `15.417` | `16.756` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_azim_shift_p35d` | `308.74` | `324.79` | `342.18` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_elev_shift_p35d` | `-28.804` | `-24.754` | `-17.229` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_app_mag_shift_p35d` | `-2.195` | `-2.103` | `-2.042` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_surf_bright_shift_p35d` | `5.3285` | `5.345` | `5.3615` |

### Container: `packed_astro_container_131` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_dist_shift_p35d` | `5.3614` | `5.6443` | `5.8578` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_dist_rate_shift_p35d` | `14.064` | `20.389` | `25.27` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_helio_dist_shift_p35d` | `4.9964` | `5.0012` | `5.0062` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_helio_dist_rate_shift_p35d` | `0.37619` | `0.39353` | `0.41009` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_phase_angle_shift_p35d` | `5.586` | `8.2045` | `10.201` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_elong_shift_p35d` | `29.096` | `45.788` | `63.358` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_illum_frac_shift_p35d` | `18.585` | `56.064` | `88.054` |
| `Bits 14-15` | `>> 14` | `astro_mars_ra_icrf_shift_p35d` | `311.83` | `328.45` | `344.36` |

### Container: `packed_astro_container_132` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_dec_icrf_shift_p35d` | `-18.773` | `-13.758` | `-7.7183` |
| `Bits 2-3` | `>> 2` | `astro_mars_ra_app_shift_p35d` | `311.37` | `328.01` | `343.94` |
| `Bits 4-5` | `>> 4` | `astro_mars_dec_app_shift_p35d` | `-18.685` | `-13.646` | `-7.5906` |
| `Bits 6-7` | `>> 6` | `astro_mars_azim_shift_p35d` | `62.663` | `62.763` | `62.974` |
| `Bits 8-9` | `>> 8` | `astro_mars_elev_shift_p35d` | `-51.191` | `-44.48` | `-36.482` |
| `Bits 10-11` | `>> 10` | `astro_mars_app_mag_shift_p35d` | `1.153` | `1.217` | `1.278` |
| `Bits 12-13` | `>> 12` | `astro_mars_surf_bright_shift_p35d` | `4.0655` | `4.103` | `4.166` |
| `Bits 14-15` | `>> 14` | `astro_mars_dist_shift_p35d` | `2.058` | `2.1404` | `2.2233` |

### Container: `packed_astro_container_133` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_dist_rate_shift_p35d` | `-6.8692` | `-6.8409` | `-6.786` |
| `Bits 2-3` | `>> 2` | `astro_mars_helio_dist_shift_p35d` | `1.3875` | `1.3994` | `1.4167` |
| `Bits 4-5` | `>> 4` | `astro_mars_helio_dist_rate_shift_p35d` | `-1.5951` | `-1.1892` | `-0.71055` |
| `Bits 6-7` | `>> 6` | `astro_mars_phase_angle_shift_p35d` | `18.617` | `22.15` | `25.445` |
| `Bits 8-9` | `>> 8` | `astro_mars_elong_shift_p35d` | `27.183` | `32.001` | `36.518` |
| `Bits 10-11` | `>> 10` | `astro_mars_illum_frac_shift_p35d` | `18.585` | `56.064` | `88.054` |
| `Bits 12-13` | `>> 12` | `astro_ceres_ra_icrf_shift_p35d` | `276.79` | `283.81` | `289.3` |
| `Bits 14-15` | `>> 14` | `astro_ceres_dec_icrf_shift_p35d` | `-23.627` | `-23.274` | `-22.969` |

### Container: `packed_astro_container_134` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_ceres_ra_app_shift_p35d` | `277.15` | `284.18` | `289.66` |
| `Bits 2-3` | `>> 2` | `astro_ceres_dec_app_shift_p35d` | `-23.584` | `-23.244` | `-22.955` |
| `Bits 4-5` | `>> 4` | `astro_ceres_azim_shift_p35d` | `96.041` | `105.11` | `115.15` |
| `Bits 6-7` | `>> 6` | `astro_ceres_elev_shift_p35d` | `-28.315` | `-18.284` | `-7.6922` |
| `Bits 8-9` | `>> 8` | `astro_ceres_app_mag_shift_p35d` | `8.757` | `8.941` | `9.0435` |
| `Bits 10-11` | `>> 10` | `astro_ceres_surf_bright_shift_p35d` | `6.8795` | `6.955` | `6.9795` |
| `Bits 12-13` | `>> 12` | `astro_ceres_dist_shift_p35d` | `2.6191` | `2.8955` | `3.1525` |
| `Bits 14-15` | `>> 14` | `astro_ceres_dist_rate_shift_p35d` | `-22.505` | `-21.743` | `-19.712` |

### Container: `packed_astro_container_135` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_ceres_helio_dist_shift_p35d` | `2.8059` | `2.8228` | `2.8392` |
| `Bits 2-3` | `>> 2` | `astro_ceres_helio_dist_rate_shift_p35d` | `1.302` | `1.3413` | `1.373` |
| `Bits 4-5` | `>> 4` | `astro_ceres_phase_angle_shift_p35d` | `17.938` | `19.713` | `20.416` |
| `Bits 6-7` | `>> 6` | `astro_ceres_elong_shift_p35d` | `60.796` | `75.872` | `92.155` |
| `Bits 8-9` | `>> 8` | `astro_ceres_illum_frac_shift_p35d` | `18.585` | `56.064` | `88.054` |
| `Bits 10-11` | `>> 10` | `astro_venus_ra_icrf_shift_p35d` | `24.59` | `307.46` | `334.06` |
| `Bits 12-13` | `>> 12` | `astro_venus_dec_icrf_shift_p35d` | `-17.78` | `-9.5775` | `0.6204` |
| `Bits 14-15` | `>> 14` | `astro_venus_ra_app_shift_p35d` | `24.903` | `307.8` | `334.38` |

### Container: `packed_astro_container_136` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_dec_app_shift_p35d` | `-17.689` | `-9.4535` | `0.7524` |
| `Bits 2-3` | `>> 2` | `astro_venus_azim_shift_p35d` | `35.233` | `46.318` | `59.91` |
| `Bits 4-5` | `>> 4` | `astro_venus_elev_shift_p35d` | `-51.079` | `-47.942` | `-40.634` |
| `Bits 6-7` | `>> 6` | `astro_venus_app_mag_shift_p35d` | `-3.897` | `-3.882` | `-3.877` |
| `Bits 8-9` | `>> 8` | `astro_venus_surf_bright_shift_p35d` | `0.852` | `0.916` | `0.9835` |
| `Bits 10-11` | `>> 10` | `astro_venus_dist_shift_p35d` | `1.4881` | `1.5772` | `1.649` |
| `Bits 12-13` | `>> 12` | `astro_venus_dist_rate_shift_p35d` | `4.8662` | `6.3299` | `7.642` |
| `Bits 14-15` | `>> 14` | `astro_venus_helio_dist_shift_p35d` | `0.72635` | `0.72733` | `0.72798` |

### Container: `packed_astro_container_137` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_helio_dist_rate_shift_p35d` | `-0.12726` | `0.0059862` | `0.13715` |
| `Bits 2-3` | `>> 2` | `astro_venus_phase_angle_shift_p35d` | `20.658` | `28.085` | `35.451` |
| `Bits 4-5` | `>> 4` | `astro_venus_elong_shift_p35d` | `14.843` | `20.141` | `25.218` |
| `Bits 6-7` | `>> 6` | `astro_venus_illum_frac_shift_p35d` | `18.585` | `56.064` | `88.054` |

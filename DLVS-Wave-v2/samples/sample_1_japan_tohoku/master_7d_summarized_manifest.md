# DLVS-Wave v2.0 Master Manifest & Decodification Report: Master 7D Summarized (sample_1_japan_tohoku)

> **Generated at**: `2026-08-27 14:11:41 UTC`  
> **Chronological Timeline**: `2024-01-01` to `2024-04-29` (`18` time steps)

## 1. Dataset Dimensions & Compression Summary

| Dimension | Raw Uncompressed | Quantized Bit-Packed (2-Bit / 16-Bit) | Reduction Ratio |
| :--- | :--- | :--- | :--- |
| **Feature Columns** | `2009` columns | `259` columns | **8.0x fewer fields** |
| **Record Count** | `18` rows | `18` rows | 1:1 Synchronized |
| **Storage Size** | `493,345 bytes` | `34,137 bytes` | **93.08% space saved** |
| **Container Type** | `Float64` | `uint16` (`2` bits/field, `4` quantiles) | Compact Binary |

## 2. Preserved Seismic Features (In Chiaro / Uncompressed)

All seismic parameters (core 3D coordinates + magnitude and historical lag shifts) are preserved uncompressed as leading columns immediately following `date` for instant inspection:

- **`seis_core_magnitude`**
- **`seis_core_latitude`**
- **`seis_core_longitude`**
- **`seis_core_depth`**
- **`seis_core_magnitude_shift_m14d`**
- **`seis_core_depth_shift_m14d`**
- **`seis_core_magnitude_shift_m7d`**
- **`seis_core_depth_shift_m7d`**

## 3. Tracked Astronomical Bodies & Feature Groups Catalog

| Prefix / Body Group | Fields Count | Sample Features Included |
| :--- | :--- | :--- |
| **`astro_jupiter`** | 300 | `min`, `min`, `min`, `min`, ... (+296 more) |
| **`astro_mars`** | 300 | `min`, `min`, `min`, `min`, ... (+296 more) |
| **`astro_mercury`** | 300 | `min`, `min`, `min`, `min`, ... (+296 more) |
| **`astro_moon`** | 300 | `min`, `min`, `min`, `min`, ... (+296 more) |
| **`astro_saturn`** | 300 | `min`, `min`, `min`, `min`, ... (+296 more) |
| **`astro_sun`** | 200 | `min`, `min`, `min`, `min`, ... (+196 more) |
| **`astro_venus`** | 300 | `min`, `min`, `min`, `min`, ... (+296 more) |

## 4. Container Decodification Matrix & Quantile Codebook

This matrix allows 100% exact decompression of packed integer fields into their discrete quantile bins `[0, 1, 2, 3]`.

### Container: `packed_astro_container_000` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_ra_icrf_min` | `24.968` | `292.07` | `323.03` |
| `Bits 2-3` | `>> 2` | `astro_sun_dec_icrf_min` | `-17.717` | `-7.787` | `3.833` |
| `Bits 4-5` | `>> 4` | `astro_sun_ra_app_min` | `25.283` | `292.42` | `323.35` |
| `Bits 6-7` | `>> 6` | `astro_sun_dec_app_min` | `-17.63` | `-7.6629` | `3.9637` |
| `Bits 8-9` | `>> 8` | `astro_sun_azim_min` | `122.83` | `129.95` | `136.22` |
| `Bits 10-11` | `>> 10` | `astro_sun_elev_min` | `21.646` | `29.938` | `40.32` |
| `Bits 12-13` | `>> 12` | `astro_sun_app_mag_min` | `-26.774` | `-26.762` | `-26.745` |
| `Bits 14-15` | `>> 14` | `astro_sun_dist_min` | `0.98506` | `0.99071` | `0.99871` |

### Container: `packed_astro_container_001` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_dist_rate_min` | `0.0044146` | `0.18702` | `0.24475` |
| `Bits 2-3` | `>> 2` | `astro_sun_illum_frac_min` | `1.6935` | `31.757` | `58.504` |
| `Bits 4-5` | `>> 4` | `astro_moon_ra_icrf_min` | `79.478` | `161.83` | `225.97` |
| `Bits 6-7` | `>> 6` | `astro_moon_dec_icrf_min` | `-28.911` | `-21.709` | `0.65784` |
| `Bits 8-9` | `>> 8` | `astro_moon_ra_app_min` | `79.855` | `162.14` | `226.31` |
| `Bits 10-11` | `>> 10` | `astro_moon_dec_app_min` | `-28.903` | `-21.798` | `0.58844` |
| `Bits 12-13` | `>> 12` | `astro_moon_azim_min` | `22.394` | `116.04` | `216.47` |
| `Bits 14-15` | `>> 14` | `astro_moon_elev_min` | `-26.515` | `-14.335` | `-0.86206` |

### Container: `packed_astro_container_002` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_app_mag_min` | `-12.209` | `-11.22` | `-10.201` |
| `Bits 2-3` | `>> 2` | `astro_moon_surf_bright_min` | `3.7245` | `4.4275` | `4.8985` |
| `Bits 4-5` | `>> 4` | `astro_moon_dist_min` | `0.0023852` | `0.0025377` | `0.0026089` |
| `Bits 6-7` | `>> 6` | `astro_moon_dist_rate_min` | `-0.27142` | `-0.12866` | `0.083179` |
| `Bits 8-9` | `>> 8` | `astro_moon_helio_dist_min` | `0.98497` | `0.99084` | `0.9989` |
| `Bits 10-11` | `>> 10` | `astro_moon_helio_dist_rate_min` | `-0.50816` | `-0.30062` | `0.52921` |
| `Bits 12-13` | `>> 12` | `astro_moon_phase_angle_min` | `14.501` | `55.103` | `87.343` |
| `Bits 14-15` | `>> 14` | `astro_moon_elong_min` | `13.361` | `68.094` | `99.645` |

### Container: `packed_astro_container_003` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_illum_frac_min` | `1.6935` | `31.757` | `58.504` |
| `Bits 2-3` | `>> 2` | `astro_mars_ra_icrf_min` | `285.32` | `309.44` | `332.38` |
| `Bits 4-5` | `>> 4` | `astro_mars_dec_icrf_min` | `-22.842` | `-18.135` | `-10.685` |
| `Bits 6-7` | `>> 6` | `astro_mars_ra_app_min` | `285.68` | `309.78` | `332.7` |
| `Bits 8-9` | `>> 8` | `astro_mars_dec_app_min` | `-22.797` | `-18.044` | `-10.564` |
| `Bits 10-11` | `>> 10` | `astro_mars_azim_min` | `159.58` | `163.78` | `169.99` |
| `Bits 12-13` | `>> 12` | `astro_mars_elev_min` | `25.678` | `31.601` | `40.152` |
| `Bits 14-15` | `>> 14` | `astro_mars_app_mag_min` | `1.175` | `1.2425` | `1.2902` |

### Container: `packed_astro_container_004` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_surf_bright_min` | `4.0442` | `4.077` | `4.1013` |
| `Bits 2-3` | `>> 2` | `astro_mars_dist_min` | `2.0742` | `2.1886` | `2.3016` |
| `Bits 4-5` | `>> 4` | `astro_mars_dist_rate_min` | `-6.7179` | `-6.622` | `-6.4782` |
| `Bits 6-7` | `>> 6` | `astro_mars_helio_dist_min` | `1.3894` | `1.4089` | `1.4378` |
| `Bits 8-9` | `>> 8` | `astro_mars_helio_dist_rate_min` | `-1.9709` | `-1.5425` | `-0.94567` |
| `Bits 10-11` | `>> 10` | `astro_mars_phase_angle_min` | `13.929` | `19.12` | `23.901` |
| `Bits 12-13` | `>> 12` | `astro_mars_elong_min` | `20.67` | `27.872` | `34.393` |
| `Bits 14-15` | `>> 14` | `astro_mars_illum_frac_min` | `1.6935` | `31.757` | `58.504` |

### Container: `packed_astro_container_005` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_ra_icrf_min` | `34.846` | `38.779` | `44.432` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_dec_icrf_min` | `12.812` | `14.224` | `16.019` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_ra_app_min` | `35.17` | `39.106` | `44.764` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_dec_app_min` | `12.922` | `14.329` | `16.115` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_azim_min` | `57.661` | `73.672` | `86.469` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_elev_min` | `-16.346` | `2.6289` | `21.85` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_app_mag_min` | `-2.357` | `-2.181` | `-2.068` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_surf_bright_min` | `5.3312` | `5.3545` | `5.366` |

### Container: `packed_astro_container_006` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_dist_min` | `4.9475` | `5.4036` | `5.7649` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_dist_rate_min` | `14.966` | `22.872` | `26.22` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_helio_dist_min` | `4.9908` | `4.9971` | `5.0038` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_helio_dist_rate_min` | `0.35471` | `0.37817` | `0.40206` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_phase_angle_min` | `6.1357` | `9.4486` | `10.769` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_elong_min` | `32.346` | `55.895` | `81.397` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_illum_frac_min` | `1.6935` | `31.757` | `58.504` |
| `Bits 14-15` | `>> 14` | `astro_saturn_ra_icrf_min` | `338.36` | `341.7` | `345.04` |

### Container: `packed_astro_container_007` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_dec_icrf_min` | `-10.819` | `-9.5003` | `-8.1891` |
| `Bits 2-3` | `>> 2` | `astro_saturn_ra_app_min` | `338.67` | `342.02` | `345.35` |
| `Bits 4-5` | `>> 4` | `astro_saturn_dec_app_min` | `-10.698` | `-9.3759` | `-8.0617` |
| `Bits 6-7` | `>> 6` | `astro_saturn_azim_min` | `112.95` | `132.36` | `159.86` |
| `Bits 8-9` | `>> 8` | `astro_saturn_elev_min` | `10.408` | `28.443` | `41.039` |
| `Bits 10-11` | `>> 10` | `astro_saturn_app_mag_min` | `0.97525` | `0.9895` | `1.053` |
| `Bits 12-13` | `>> 12` | `astro_saturn_surf_bright_min` | `6.6893` | `6.714` | `6.7672` |
| `Bits 14-15` | `>> 14` | `astro_saturn_dist_min` | `10.403` | `10.561` | `10.665` |

### Container: `packed_astro_container_008` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_dist_rate_min` | `-15.318` | `-3.2006` | `9.718` |
| `Bits 2-3` | `>> 2` | `astro_saturn_helio_dist_min` | `9.7106` | `9.7192` | `9.7277` |
| `Bits 4-5` | `>> 4` | `astro_saturn_helio_dist_rate_min` | `-0.50083` | `-0.49719` | `-0.49408` |
| `Bits 6-7` | `>> 6` | `astro_saturn_phase_angle_min` | `1.1534` | `2.4898` | `3.6974` |
| `Bits 8-9` | `>> 8` | `astro_saturn_elong_min` | `11.418` | `25.199` | `39.035` |
| `Bits 10-11` | `>> 10` | `astro_saturn_illum_frac_min` | `1.6935` | `31.757` | `58.504` |
| `Bits 12-13` | `>> 12` | `astro_mercury_ra_icrf_min` | `16.343` | `262.5` | `299.01` |
| `Bits 14-15` | `>> 14` | `astro_mercury_dec_icrf_min` | `-21.473` | `-8.9111` | `5.873` |

### Container: `packed_astro_container_009` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mercury_ra_app_min` | `16.652` | `262.85` | `299.36` |
| `Bits 2-3` | `>> 2` | `astro_mercury_dec_app_min` | `-21.427` | `-8.7863` | `6.0014` |
| `Bits 4-5` | `>> 4` | `astro_mercury_azim_min` | `113.71` | `138.84` | `153.88` |
| `Bits 6-7` | `>> 6` | `astro_mercury_elev_min` | `26.202` | `28.476` | `36.647` |
| `Bits 8-9` | `>> 8` | `astro_mercury_app_mag_min` | `-0.9165` | `-0.27` | `0.7365` |
| `Bits 10-11` | `>> 10` | `astro_mercury_surf_bright_min` | `2.2803` | `2.9815` | `3.7843` |
| `Bits 12-13` | `>> 12` | `astro_mercury_dist_min` | `0.6914` | `0.98991` | `1.2588` |
| `Bits 14-15` | `>> 14` | `astro_mercury_dist_rate_min` | `-26.937` | `0.85336` | `18.36` |

### Container: `packed_astro_container_010` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mercury_helio_dist_min` | `0.34668` | `0.40039` | `0.44456` |
| `Bits 2-3` | `>> 2` | `astro_mercury_helio_dist_rate_min` | `-5.9662` | `0.81566` | `6.7989` |
| `Bits 4-5` | `>> 4` | `astro_mercury_phase_angle_min` | `30.144` | `60.981` | `113.49` |
| `Bits 6-7` | `>> 6` | `astro_mercury_elong_min` | `6.1812` | `14.319` | `17.647` |
| `Bits 8-9` | `>> 8` | `astro_mercury_illum_frac_min` | `1.6935` | `31.757` | `58.504` |
| `Bits 10-11` | `>> 10` | `astro_venus_ra_icrf_min` | `80.768` | `272.49` | `311.59` |
| `Bits 12-13` | `>> 12` | `astro_venus_dec_icrf_min` | `-21.386` | `-16.781` | `-4.3558` |
| `Bits 14-15` | `>> 14` | `astro_venus_ra_app_min` | `81.09` | `272.85` | `311.93` |

### Container: `packed_astro_container_011` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_dec_app_min` | `-21.396` | `-16.684` | `-4.2249` |
| `Bits 2-3` | `>> 2` | `astro_venus_azim_min` | `144.57` | `157.47` | `168.97` |
| `Bits 4-5` | `>> 4` | `astro_venus_elev_min` | `29.129` | `32.123` | `41.742` |
| `Bits 6-7` | `>> 6` | `astro_venus_app_mag_min` | `-3.9468` | `-3.894` | `-3.8807` |
| `Bits 8-9` | `>> 8` | `astro_venus_surf_bright_min` | `0.864` | `0.955` | `1.052` |
| `Bits 10-11` | `>> 10` | `astro_venus_dist_min` | `1.3554` | `1.5013` | `1.6168` |
| `Bits 12-13` | `>> 12` | `astro_venus_dist_rate_min` | `5.1814` | `7.1693` | `8.9341` |
| `Bits 14-15` | `>> 14` | `astro_venus_helio_dist_min` | `0.72431` | `0.72612` | `0.72752` |

### Container: `packed_astro_container_012` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_helio_dist_rate_min` | `-0.10271` | `0.085169` | `0.2015` |
| `Bits 2-3` | `>> 2` | `astro_venus_phase_angle_min` | `22.137` | `32.362` | `42.713` |
| `Bits 4-5` | `>> 4` | `astro_venus_elong_min` | `15.906` | `23.116` | `29.919` |
| `Bits 6-7` | `>> 6` | `astro_venus_illum_frac_min` | `1.6935` | `31.757` | `58.504` |
| `Bits 8-9` | `>> 8` | `astro_sun_ra_icrf_max` | `36.219` | `305.94` | `335.67` |
| `Bits 10-11` | `>> 10` | `astro_sun_dec_icrf_max` | `-15.994` | `-5.4878` | `6.1348` |
| `Bits 12-13` | `>> 12` | `astro_sun_ra_app_max` | `36.544` | `306.28` | `335.98` |
| `Bits 14-15` | `>> 14` | `astro_sun_dec_app_max` | `-15.897` | `-5.36` | `6.2633` |

### Container: `packed_astro_container_013` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_azim_max` | `124.39` | `131.26` | `137.42` |
| `Bits 2-3` | `>> 2` | `astro_sun_elev_max` | `22.988` | `31.976` | `42.347` |
| `Bits 4-5` | `>> 4` | `astro_sun_app_mag_max` | `-26.773` | `-26.759` | `-26.741` |
| `Bits 6-7` | `>> 6` | `astro_sun_dist_max` | `0.98595` | `0.99222` | `1.0005` |
| `Bits 8-9` | `>> 8` | `astro_sun_dist_rate_max` | `0.047217` | `0.21246` | `0.2536` |
| `Bits 10-11` | `>> 10` | `astro_sun_illum_frac_max` | `52.284` | `78.604` | `98.403` |
| `Bits 12-13` | `>> 12` | `astro_moon_ra_icrf_max` | `172.9` | `246.64` | `337.9` |
| `Bits 14-15` | `>> 14` | `astro_moon_dec_icrf_max` | `-5.1742` | `10.282` | `27.275` |

### Container: `packed_astro_container_014` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_ra_app_max` | `173.22` | `247.01` | `338.22` |
| `Bits 2-3` | `>> 2` | `astro_moon_dec_app_max` | `-5.1093` | `10.154` | `27.265` |
| `Bits 4-5` | `>> 4` | `astro_moon_azim_max` | `194.95` | `258.83` | `326.33` |
| `Bits 6-7` | `>> 6` | `astro_moon_elev_max` | `-8.3127` | `10.293` | `26.797` |
| `Bits 8-9` | `>> 8` | `astro_moon_app_mag_max` | `-10.436` | `-9.185` | `-5.4693` |
| `Bits 10-11` | `>> 10` | `astro_moon_surf_bright_max` | `5.0272` | `5.612` | `6.3317` |
| `Bits 12-13` | `>> 12` | `astro_moon_dist_max` | `0.0025743` | `0.0026502` | `0.0027327` |
| `Bits 14-15` | `>> 14` | `astro_moon_dist_rate_max` | `0.0059437` | `0.19134` | `0.27856` |

### Container: `packed_astro_container_015` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_helio_dist_max` | `0.98707` | `0.99243` | `1.0003` |
| `Bits 2-3` | `>> 2` | `astro_moon_helio_dist_rate_max` | `0.21016` | `0.7127` | `1.2544` |
| `Bits 4-5` | `>> 4` | `astro_moon_phase_angle_max` | `80.205` | `111.77` | `166.61` |
| `Bits 6-7` | `>> 6` | `astro_moon_elong_max` | `92.51` | `124.77` | `165.46` |
| `Bits 8-9` | `>> 8` | `astro_moon_illum_frac_max` | `52.284` | `78.604` | `98.403` |
| `Bits 10-11` | `>> 10` | `astro_mars_ra_icrf_max` | `295.96` | `319.64` | `341.99` |
| `Bits 12-13` | `>> 12` | `astro_mars_dec_icrf_max` | `-22.168` | `-16.815` | `-8.9627` |
| `Bits 14-15` | `>> 14` | `astro_mars_ra_app_max` | `296.31` | `319.97` | `342.3` |

### Container: `packed_astro_container_016` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_dec_app_max` | `-22.112` | `-16.716` | `-8.8372` |
| `Bits 2-3` | `>> 2` | `astro_mars_azim_max` | `160.37` | `164.8` | `171.67` |
| `Bits 4-5` | `>> 4` | `astro_mars_elev_max` | `26.606` | `33.159` | `42.053` |
| `Bits 6-7` | `>> 6` | `astro_mars_app_mag_max` | `1.1927` | `1.288` | `1.3213` |
| `Bits 8-9` | `>> 8` | `astro_mars_surf_bright_max` | `4.0953` | `4.1135` | `4.1677` |
| `Bits 10-11` | `>> 10` | `astro_mars_dist_max` | `2.0971` | `2.2117` | `2.3236` |
| `Bits 12-13` | `>> 12` | `astro_mars_dist_rate_max` | `-6.685` | `-6.5843` | `-6.3777` |
| `Bits 14-15` | `>> 14` | `astro_mars_helio_dist_max` | `1.3925` | `1.4141` | `1.4445` |

### Container: `packed_astro_container_017` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_helio_dist_rate_max` | `-1.8998` | `-1.4343` | `-0.80923` |
| `Bits 2-3` | `>> 2` | `astro_mars_phase_angle_max` | `15.005` | `20.12` | `24.81` |
| `Bits 4-5` | `>> 4` | `astro_mars_elong_max` | `22.182` | `29.237` | `35.642` |
| `Bits 6-7` | `>> 6` | `astro_mars_illum_frac_max` | `52.284` | `78.604` | `98.403` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_ra_icrf_max` | `35.463` | `39.804` | `45.72` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_dec_icrf_max` | `13.047` | `14.567` | `16.397` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_ra_app_max` | `35.788` | `40.131` | `46.052` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_dec_app_max` | `13.157` | `14.67` | `16.491` |

### Container: `packed_astro_container_018` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_azim_max` | `61.357` | `76.391` | `88.972` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_elev_max` | `-12.62` | `6.5243` | `25.672` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_app_mag_max` | `-2.3165` | `-2.153` | `-2.0515` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_surf_bright_max` | `5.3355` | `5.3595` | `5.3685` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_dist_max` | `5.0435` | `5.4863` | `5.821` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_dist_rate_max` | `16.749` | `24.096` | `26.954` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_helio_dist_max` | `4.992` | `4.9984` | `5.0052` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_helio_dist_rate_max` | `0.36101` | `0.38458` | `0.40823` |

### Container: `packed_astro_container_019` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_phase_angle_max` | `6.8896` | `9.9585` | `11.081` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_elong_max` | `36.97` | `60.859` | `86.839` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_illum_frac_max` | `52.284` | `78.604` | `98.403` |
| `Bits 6-7` | `>> 6` | `astro_saturn_ra_icrf_max` | `339.01` | `342.39` | `345.67` |
| `Bits 8-9` | `>> 8` | `astro_saturn_dec_icrf_max` | `-10.562` | `-9.2291` | `-7.9428` |
| `Bits 10-11` | `>> 10` | `astro_saturn_ra_app_max` | `339.32` | `342.7` | `345.98` |
| `Bits 12-13` | `>> 12` | `astro_saturn_dec_app_max` | `-10.44` | `-9.1041` | `-7.8148` |
| `Bits 14-15` | `>> 14` | `astro_saturn_azim_max` | `116.43` | `137.12` | `166.62` |

### Container: `packed_astro_container_020` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_elev_max` | `14.312` | `31.56` | `42.466` |
| `Bits 2-3` | `>> 2` | `astro_saturn_app_mag_max` | `0.986` | `0.997` | `1.0615` |
| `Bits 4-5` | `>> 4` | `astro_saturn_surf_bright_max` | `6.6978` | `6.7225` | `6.7858` |
| `Bits 6-7` | `>> 6` | `astro_saturn_dist_max` | `10.469` | `10.607` | `10.689` |
| `Bits 8-9` | `>> 8` | `astro_saturn_dist_rate_max` | `-13.049` | `-0.57941` | `12.185` |
| `Bits 10-11` | `>> 10` | `astro_saturn_helio_dist_max` | `9.7124` | `9.7209` | `9.7294` |
| `Bits 12-13` | `>> 12` | `astro_saturn_helio_dist_rate_max` | `-0.49877` | `-0.4958` | `-0.49197` |
| `Bits 14-15` | `>> 14` | `astro_saturn_phase_angle_max` | `1.6737` | `2.9704` | `4.1076` |

### Container: `packed_astro_container_021` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_elong_max` | `16.647` | `30.514` | `44.348` |
| `Bits 2-3` | `>> 2` | `astro_saturn_illum_frac_max` | `52.284` | `78.604` | `98.403` |
| `Bits 4-5` | `>> 4` | `astro_mercury_ra_icrf_max` | `20.138` | `266.25` | `308.83` |
| `Bits 6-7` | `>> 6` | `astro_mercury_dec_icrf_max` | `-20.065` | `-3.8826` | `8.3472` |
| `Bits 8-9` | `>> 8` | `astro_mercury_ra_app_max` | `20.451` | `266.6` | `309.17` |
| `Bits 10-11` | `>> 10` | `astro_mercury_dec_app_max` | `-20.06` | `-3.7525` | `8.4743` |
| `Bits 12-13` | `>> 12` | `astro_mercury_azim_max` | `124.87` | `145.21` | `157.24` |
| `Bits 14-15` | `>> 14` | `astro_mercury_elev_max` | `27.212` | `29.288` | `41.157` |

### Container: `packed_astro_container_022` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mercury_app_mag_max` | `-0.564` | `-0.229` | `1.1438` |
| `Bits 2-3` | `>> 2` | `astro_mercury_surf_bright_max` | `2.5753` | `3.081` | `4.1803` |
| `Bits 4-5` | `>> 4` | `astro_mercury_dist_max` | `0.7683` | `1.1197` | `1.3316` |
| `Bits 6-7` | `>> 6` | `astro_mercury_dist_rate_max` | `-14.531` | `9.4967` | `21.951` |
| `Bits 8-9` | `>> 8` | `astro_mercury_helio_dist_max` | `0.38084` | `0.42985` | `0.46031` |
| `Bits 10-11` | `>> 10` | `astro_mercury_helio_dist_rate_max` | `-1.0225` | `4.821` | `9.1436` |
| `Bits 12-13` | `>> 12` | `astro_mercury_phase_angle_max` | `38` | `78.058` | `125.69` |
| `Bits 14-15` | `>> 14` | `astro_mercury_elong_max` | `12.776` | `17.351` | `21.996` |

### Container: `packed_astro_container_023` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mercury_illum_frac_max` | `52.284` | `78.604` | `98.403` |
| `Bits 2-3` | `>> 2` | `astro_venus_ra_icrf_max` | `250.48` | `289.8` | `327.73` |
| `Bits 4-5` | `>> 4` | `astro_venus_dec_icrf_max` | `-20.288` | `-14.675` | `-1.4553` |
| `Bits 6-7` | `>> 6` | `astro_venus_ra_app_max` | `250.82` | `290.15` | `328.05` |
| `Bits 8-9` | `>> 8` | `astro_venus_dec_app_max` | `-20.306` | `-14.567` | `-1.3232` |
| `Bits 10-11` | `>> 10` | `astro_venus_azim_max` | `147.43` | `159.84` | `171.2` |
| `Bits 12-13` | `>> 12` | `astro_venus_elev_max` | `30.001` | `33.726` | `43.952` |
| `Bits 14-15` | `>> 14` | `astro_venus_app_mag_max` | `-3.9325` | `-3.8875` | `-3.8785` |

### Container: `packed_astro_container_024` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_surf_bright_max` | `0.88225` | `0.974` | `1.072` |
| `Bits 2-3` | `>> 2` | `astro_venus_dist_max` | `1.3872` | `1.5271` | `1.636` |
| `Bits 4-5` | `>> 4` | `astro_venus_dist_rate_max` | `5.615` | `7.5425` | `9.2802` |
| `Bits 6-7` | `>> 6` | `astro_venus_helio_dist_max` | `0.72502` | `0.72675` | `0.72787` |
| `Bits 8-9` | `>> 8` | `astro_venus_helio_dist_rate_max` | `-0.066316` | `0.12019` | `0.21915` |
| `Bits 10-11` | `>> 10` | `astro_venus_phase_angle_max` | `24.215` | `34.42` | `44.867` |
| `Bits 12-13` | `>> 12` | `astro_venus_elong_max` | `17.395` | `24.52` | `31.241` |
| `Bits 14-15` | `>> 14` | `astro_venus_illum_frac_max` | `52.284` | `78.604` | `98.403` |

### Container: `packed_astro_container_025` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_ra_icrf_mean` | `33.857` | `295.31` | `325.99` |
| `Bits 2-3` | `>> 2` | `astro_sun_dec_icrf_mean` | `-16.868` | `-6.6414` | `4.9875` |
| `Bits 4-5` | `>> 4` | `astro_sun_ra_app_mean` | `34.18` | `295.65` | `326.31` |
| `Bits 6-7` | `>> 6` | `astro_sun_dec_app_mean` | `-16.776` | `-6.5153` | `5.1172` |
| `Bits 8-9` | `>> 8` | `astro_sun_azim_mean` | `123.61` | `130.61` | `136.82` |
| `Bits 10-11` | `>> 10` | `astro_sun_elev_mean` | `22.303` | `30.952` | `41.339` |
| `Bits 12-13` | `>> 12` | `astro_sun_app_mag_mean` | `-26.774` | `-26.761` | `-26.743` |
| `Bits 14-15` | `>> 14` | `astro_sun_dist_mean` | `0.98549` | `0.99146` | `0.99959` |

### Container: `packed_astro_container_026` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_dist_rate_mean` | `0.026867` | `0.20098` | `0.24772` |
| `Bits 2-3` | `>> 2` | `astro_sun_illum_frac_mean` | `23.891` | `58.93` | `81.669` |
| `Bits 4-5` | `>> 4` | `astro_moon_ra_icrf_mean` | `126.79` | `194.3` | `269.9` |
| `Bits 6-7` | `>> 6` | `astro_moon_dec_icrf_mean` | `-20.182` | `-6.0382` | `15.821` |
| `Bits 8-9` | `>> 8` | `astro_moon_ra_app_mean` | `127.12` | `194.62` | `270.25` |
| `Bits 10-11` | `>> 10` | `astro_moon_dec_app_mean` | `-20.148` | `-6.1586` | `15.767` |
| `Bits 12-13` | `>> 12` | `astro_moon_azim_mean` | `105.65` | `190.43` | `250.55` |
| `Bits 14-15` | `>> 14` | `astro_moon_elev_mean` | `-23.28` | `-2.2422` | `18.535` |

### Container: `packed_astro_container_027` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_app_mag_mean` | `-11.352` | `-10.409` | `-8.2499` |
| `Bits 2-3` | `>> 2` | `astro_moon_surf_bright_mean` | `4.395` | `5.0203` | `5.7514` |
| `Bits 4-5` | `>> 4` | `astro_moon_dist_mean` | `0.002463` | `0.0025938` | `0.0026816` |
| `Bits 6-7` | `>> 6` | `astro_moon_dist_rate_mean` | `-0.17324` | `0.034764` | `0.22379` |
| `Bits 8-9` | `>> 8` | `astro_moon_helio_dist_mean` | `0.98632` | `0.99171` | `0.99998` |
| `Bits 10-11` | `>> 10` | `astro_moon_helio_dist_rate_mean` | `-0.20385` | `0.15494` | `0.95732` |
| `Bits 12-13` | `>> 12` | `astro_moon_phase_angle_mean` | `47.01` | `79.376` | `125.97` |
| `Bits 14-15` | `>> 14` | `astro_moon_elong_mean` | `53.927` | `100.49` | `132.88` |

### Container: `packed_astro_container_028` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_illum_frac_mean` | `23.891` | `58.93` | `81.669` |
| `Bits 2-3` | `>> 2` | `astro_mars_ra_icrf_mean` | `287.78` | `311.81` | `334.62` |
| `Bits 4-5` | `>> 4` | `astro_mars_dec_icrf_mean` | `-22.515` | `-17.483` | `-9.8277` |
| `Bits 6-7` | `>> 6` | `astro_mars_ra_app_mean` | `288.14` | `312.15` | `334.94` |
| `Bits 8-9` | `>> 8` | `astro_mars_dec_app_mean` | `-22.465` | `-17.387` | `-9.7041` |
| `Bits 10-11` | `>> 10` | `astro_mars_azim_mean` | `159.98` | `164.28` | `170.82` |
| `Bits 12-13` | `>> 12` | `astro_mars_elev_mean` | `26.132` | `32.373` | `41.101` |
| `Bits 14-15` | `>> 14` | `astro_mars_app_mag_mean` | `1.1832` | `1.2654` | `1.3031` |

### Container: `packed_astro_container_029` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_surf_bright_mean` | `4.0625` | `4.1007` | `4.1345` |
| `Bits 2-3` | `>> 2` | `astro_mars_dist_mean` | `2.0856` | `2.2002` | `2.3126` |
| `Bits 4-5` | `>> 4` | `astro_mars_dist_rate_mean` | `-6.7023` | `-6.6039` | `-6.4313` |
| `Bits 6-7` | `>> 6` | `astro_mars_helio_dist_mean` | `1.3909` | `1.4115` | `1.4411` |
| `Bits 8-9` | `>> 8` | `astro_mars_helio_dist_rate_mean` | `-1.9359` | `-1.4889` | `-0.87775` |
| `Bits 10-11` | `>> 10` | `astro_mars_phase_angle_mean` | `14.468` | `19.621` | `24.356` |
| `Bits 12-13` | `>> 12` | `astro_mars_elong_mean` | `21.428` | `28.556` | `35.018` |
| `Bits 14-15` | `>> 14` | `astro_mars_illum_frac_mean` | `23.891` | `58.93` | `81.669` |

### Container: `packed_astro_container_030` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_ra_icrf_mean` | `35.148` | `39.287` | `45.073` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_dec_icrf_mean` | `12.927` | `14.395` | `16.208` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_ra_app_mean` | `35.472` | `39.614` | `45.405` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_dec_app_mean` | `13.037` | `14.499` | `16.303` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_azim_mean` | `59.53` | `75.039` | `87.719` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_elev_mean` | `-14.489` | `4.5766` | `23.763` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_app_mag_mean` | `-2.3365` | `-2.1667` | `-2.0596` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_surf_bright_mean` | `5.3336` | `5.357` | `5.3674` |

### Container: `packed_astro_container_031` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_dist_mean` | `4.9956` | `5.4452` | `5.7934` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_dist_rate_mean` | `15.863` | `23.494` | `26.608` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_helio_dist_mean` | `4.9914` | `4.9977` | `5.0045` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_helio_dist_rate_mean` | `0.35754` | `0.38137` | `0.40427` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_phase_angle_mean` | `6.5151` | `9.708` | `10.933` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_elong_mean` | `34.654` | `58.371` | `84.11` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_illum_frac_mean` | `23.891` | `58.93` | `81.669` |
| `Bits 14-15` | `>> 14` | `astro_saturn_ra_icrf_mean` | `338.68` | `342.05` | `345.35` |

### Container: `packed_astro_container_032` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_dec_icrf_mean` | `-10.691` | `-9.3646` | `-8.0653` |
| `Bits 2-3` | `>> 2` | `astro_saturn_ra_app_mean` | `338.99` | `342.36` | `345.66` |
| `Bits 4-5` | `>> 4` | `astro_saturn_dec_app_mean` | `-10.569` | `-9.2399` | `-7.9377` |
| `Bits 6-7` | `>> 6` | `astro_saturn_azim_mean` | `114.68` | `134.71` | `163.22` |
| `Bits 8-9` | `>> 8` | `astro_saturn_elev_mean` | `12.367` | `30.017` | `41.785` |
| `Bits 10-11` | `>> 10` | `astro_saturn_app_mag_mean` | `0.98296` | `0.99057` | `1.0575` |
| `Bits 12-13` | `>> 12` | `astro_saturn_surf_bright_mean` | `6.6928` | `6.7169` | `6.7765` |
| `Bits 14-15` | `>> 14` | `astro_saturn_dist_mean` | `10.437` | `10.585` | `10.678` |

### Container: `packed_astro_container_033` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_dist_rate_mean` | `-14.191` | `-1.8905` | `10.959` |
| `Bits 2-3` | `>> 2` | `astro_saturn_helio_dist_mean` | `9.7115` | `9.72` | `9.7286` |
| `Bits 4-5` | `>> 4` | `astro_saturn_helio_dist_rate_mean` | `-0.49975` | `-0.49644` | `-0.49314` |
| `Bits 6-7` | `>> 6` | `astro_saturn_phase_angle_mean` | `1.4141` | `2.7315` | `3.9048` |
| `Bits 8-9` | `>> 8` | `astro_saturn_elong_mean` | `14.036` | `27.855` | `41.69` |
| `Bits 10-11` | `>> 10` | `astro_saturn_illum_frac_mean` | `23.891` | `58.93` | `81.669` |
| `Bits 12-13` | `>> 12` | `astro_mercury_ra_icrf_mean` | `17.383` | `264.14` | `303.9` |
| `Bits 14-15` | `>> 14` | `astro_mercury_dec_icrf_mean` | `-20.729` | `-6.4365` | `7.0424` |

### Container: `packed_astro_container_034` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mercury_ra_app_mean` | `17.693` | `264.49` | `304.25` |
| `Bits 2-3` | `>> 2` | `astro_mercury_dec_app_mean` | `-20.677` | `-6.3087` | `7.1703` |
| `Bits 4-5` | `>> 4` | `astro_mercury_azim_mean` | `119.11` | `142.37` | `155.6` |
| `Bits 6-7` | `>> 6` | `astro_mercury_elev_mean` | `26.693` | `28.938` | `38.834` |
| `Bits 8-9` | `>> 8` | `astro_mercury_app_mag_mean` | `-0.71089` | `-0.24921` | `0.91714` |
| `Bits 10-11` | `>> 10` | `astro_mercury_surf_bright_mean` | `2.4533` | `3.0318` | `4.0432` |
| `Bits 12-13` | `>> 12` | `astro_mercury_dist_mean` | `0.71883` | `1.0557` | `1.297` |
| `Bits 14-15` | `>> 14` | `astro_mercury_dist_rate_mean` | `-20.234` | `5.3465` | `20.504` |

### Container: `packed_astro_container_035` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mercury_helio_dist_mean` | `0.36364` | `0.41558` | `0.45309` |
| `Bits 2-3` | `>> 2` | `astro_mercury_helio_dist_rate_mean` | `-3.5241` | `3.0944` | `8.202` |
| `Bits 4-5` | `>> 4` | `astro_mercury_phase_angle_mean` | `34.314` | `70.535` | `118.79` |
| `Bits 6-7` | `>> 6` | `astro_mercury_elong_mean` | `10.154` | `16.075` | `20.227` |
| `Bits 8-9` | `>> 8` | `astro_mercury_illum_frac_mean` | `23.891` | `58.93` | `81.669` |
| `Bits 10-11` | `>> 10` | `astro_venus_ra_icrf_mean` | `214.61` | `276.49` | `315.37` |
| `Bits 12-13` | `>> 12` | `astro_venus_dec_icrf_mean` | `-20.861` | `-15.746` | `-2.9093` |
| `Bits 14-15` | `>> 14` | `astro_venus_ra_app_mean` | `214.92` | `276.84` | `315.7` |

### Container: `packed_astro_container_036` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_dec_app_mean` | `-20.875` | `-15.644` | `-2.7777` |
| `Bits 2-3` | `>> 2` | `astro_venus_azim_mean` | `146.02` | `158.66` | `170.09` |
| `Bits 4-5` | `>> 4` | `astro_venus_elev_mean` | `29.544` | `32.908` | `42.847` |
| `Bits 6-7` | `>> 6` | `astro_venus_app_mag_mean` | `-3.9396` | `-3.8906` | `-3.8796` |
| `Bits 8-9` | `>> 8` | `astro_venus_surf_bright_mean` | `0.87307` | `0.96464` | `1.062` |
| `Bits 10-11` | `>> 10` | `astro_venus_dist_mean` | `1.3714` | `1.5143` | `1.6265` |
| `Bits 12-13` | `>> 12` | `astro_venus_dist_rate_mean` | `5.4003` | `7.3573` | `9.1082` |
| `Bits 14-15` | `>> 14` | `astro_venus_helio_dist_mean` | `0.72469` | `0.72644` | `0.7277` |

### Container: `packed_astro_container_037` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_helio_dist_rate_mean` | `-0.084672` | `0.10287` | `0.21074` |
| `Bits 2-3` | `>> 2` | `astro_venus_phase_angle_mean` | `23.177` | `33.391` | `43.788` |
| `Bits 4-5` | `>> 4` | `astro_venus_elong_mean` | `16.652` | `23.819` | `30.581` |
| `Bits 6-7` | `>> 6` | `astro_venus_illum_frac_mean` | `23.891` | `58.93` | `81.669` |
| `Bits 8-9` | `>> 8` | `astro_sun_ra_icrf_median` | `27.759` | `295.31` | `325.99` |
| `Bits 10-11` | `>> 10` | `astro_sun_dec_icrf_median` | `-16.878` | `-6.6446` | `4.9904` |
| `Bits 12-13` | `>> 12` | `astro_sun_ra_app_median` | `28.076` | `295.66` | `326.31` |
| `Bits 14-15` | `>> 14` | `astro_sun_dec_app_median` | `-16.786` | `-6.5184` | `5.1202` |

### Container: `packed_astro_container_038` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_azim_median` | `123.62` | `130.61` | `136.82` |
| `Bits 2-3` | `>> 2` | `astro_sun_elev_median` | `22.292` | `30.948` | `41.343` |
| `Bits 4-5` | `>> 4` | `astro_sun_app_mag_median` | `-26.773` | `-26.761` | `-26.743` |
| `Bits 6-7` | `>> 6` | `astro_sun_dist_median` | `0.98549` | `0.99145` | `0.99959` |
| `Bits 8-9` | `>> 8` | `astro_sun_dist_rate_median` | `0.027715` | `0.20199` | `0.24793` |
| `Bits 10-11` | `>> 10` | `astro_sun_illum_frac_median` | `21.434` | `59.309` | `84.26` |
| `Bits 12-13` | `>> 12` | `astro_moon_ra_icrf_median` | `120.83` | `193.56` | `269.59` |
| `Bits 14-15` | `>> 14` | `astro_moon_dec_icrf_median` | `-22.705` | `-6.2797` | `17.65` |

### Container: `packed_astro_container_039` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_ra_app_median` | `121.19` | `193.87` | `269.96` |
| `Bits 2-3` | `>> 2` | `astro_moon_dec_app_median` | `-22.664` | `-6.4099` | `17.698` |
| `Bits 4-5` | `>> 4` | `astro_moon_azim_median` | `79.452` | `193.47` | `260.96` |
| `Bits 6-7` | `>> 6` | `astro_moon_elev_median` | `-24.044` | `-2.469` | `19.62` |
| `Bits 8-9` | `>> 8` | `astro_moon_app_mag_median` | `-11.375` | `-10.478` | `-8.582` |
| `Bits 10-11` | `>> 10` | `astro_moon_surf_bright_median` | `4.411` | `5.0105` | `5.7337` |
| `Bits 12-13` | `>> 12` | `astro_moon_dist_median` | `0.0024535` | `0.002601` | `0.0026926` |
| `Bits 14-15` | `>> 14` | `astro_moon_dist_rate_median` | `-0.19367` | `0.037601` | `0.23078` |

### Container: `packed_astro_container_040` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_helio_dist_median` | `0.98635` | `0.99186` | `0.9998` |
| `Bits 2-3` | `>> 2` | `astro_moon_helio_dist_rate_median` | `-0.25854` | `0.13619` | `0.99541` |
| `Bits 4-5` | `>> 4` | `astro_moon_phase_angle_median` | `46.743` | `79.141` | `125.11` |
| `Bits 6-7` | `>> 6` | `astro_moon_elong_median` | `54.774` | `100.71` | `133.14` |
| `Bits 8-9` | `>> 8` | `astro_moon_illum_frac_median` | `21.434` | `59.309` | `84.26` |
| `Bits 10-11` | `>> 10` | `astro_mars_ra_icrf_median` | `293.51` | `317.31` | `339.79` |
| `Bits 12-13` | `>> 12` | `astro_mars_dec_icrf_median` | `-22.523` | `-17.489` | `-9.8306` |
| `Bits 14-15` | `>> 14` | `astro_mars_ra_app_median` | `288.14` | `312.15` | `334.94` |

### Container: `packed_astro_container_041` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_dec_app_median` | `-22.473` | `-17.393` | `-9.707` |
| `Bits 2-3` | `>> 2` | `astro_mars_azim_median` | `159.98` | `164.28` | `170.81` |
| `Bits 4-5` | `>> 4` | `astro_mars_elev_median` | `26.125` | `32.367` | `41.099` |
| `Bits 6-7` | `>> 6` | `astro_mars_app_mag_median` | `1.1835` | `1.2635` | `1.3022` |
| `Bits 8-9` | `>> 8` | `astro_mars_surf_bright_median` | `4.0572` | `4.0985` | `4.1345` |
| `Bits 10-11` | `>> 10` | `astro_mars_dist_median` | `2.0856` | `2.2002` | `2.3126` |
| `Bits 12-13` | `>> 12` | `astro_mars_dist_rate_median` | `-6.703` | `-6.6046` | `-6.4316` |
| `Bits 14-15` | `>> 14` | `astro_mars_helio_dist_median` | `1.3909` | `1.4115` | `1.4411` |

### Container: `packed_astro_container_042` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_helio_dist_rate_median` | `-1.9363` | `-1.4893` | `-0.87799` |
| `Bits 2-3` | `>> 2` | `astro_mars_phase_angle_median` | `14.469` | `19.622` | `24.357` |
| `Bits 4-5` | `>> 4` | `astro_mars_elong_median` | `21.429` | `28.558` | `35.019` |
| `Bits 6-7` | `>> 6` | `astro_mars_illum_frac_median` | `21.434` | `59.309` | `84.26` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_ra_icrf_median` | `35.142` | `39.283` | `45.071` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_dec_icrf_median` | `12.926` | `14.394` | `16.208` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_ra_app_median` | `35.467` | `39.61` | `45.403` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_dec_app_median` | `13.036` | `14.498` | `16.303` |

### Container: `packed_astro_container_043` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_azim_median` | `59.547` | `75.045` | `87.718` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_elev_median` | `-14.494` | `4.5766` | `23.764` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_app_mag_median` | `-2.3362` | `-2.1665` | `-2.0598` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_surf_bright_median` | `5.3332` | `5.357` | `5.3673` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_dist_median` | `4.9956` | `5.4455` | `5.7937` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_dist_rate_median` | `15.867` | `23.503` | `26.624` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_helio_dist_median` | `4.9914` | `4.9977` | `5.0045` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_helio_dist_rate_median` | `0.35784` | `0.38064` | `0.40335` |

### Container: `packed_astro_container_044` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_phase_angle_median` | `6.5171` | `9.7116` | `10.939` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_elong_median` | `34.651` | `58.367` | `84.104` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_illum_frac_median` | `21.434` | `59.309` | `84.26` |
| `Bits 6-7` | `>> 6` | `astro_saturn_ra_icrf_median` | `338.68` | `342.05` | `345.35` |
| `Bits 8-9` | `>> 8` | `astro_saturn_dec_icrf_median` | `-10.692` | `-9.3646` | `-8.0648` |
| `Bits 10-11` | `>> 10` | `astro_saturn_ra_app_median` | `338.99` | `342.36` | `345.66` |
| `Bits 12-13` | `>> 12` | `astro_saturn_dec_app_median` | `-10.57` | `-9.2399` | `-7.9372` |
| `Bits 14-15` | `>> 14` | `astro_saturn_azim_median` | `114.67` | `134.69` | `163.2` |

### Container: `packed_astro_container_045` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_elev_median` | `12.373` | `30.03` | `41.811` |
| `Bits 2-3` | `>> 2` | `astro_saturn_app_mag_median` | `0.983` | `0.991` | `1.0573` |
| `Bits 4-5` | `>> 4` | `astro_saturn_surf_bright_median` | `6.693` | `6.717` | `6.7765` |
| `Bits 6-7` | `>> 6` | `astro_saturn_dist_median` | `10.437` | `10.585` | `10.678` |
| `Bits 8-9` | `>> 8` | `astro_saturn_dist_rate_median` | `-14.197` | `-1.8909` | `10.964` |
| `Bits 10-11` | `>> 10` | `astro_saturn_helio_dist_median` | `9.7115` | `9.72` | `9.7286` |
| `Bits 12-13` | `>> 12` | `astro_saturn_helio_dist_rate_median` | `-0.49984` | `-0.49638` | `-0.49331` |
| `Bits 14-15` | `>> 14` | `astro_saturn_phase_angle_median` | `1.4145` | `2.7327` | `3.9066` |

### Container: `packed_astro_container_046` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_elong_median` | `14.035` | `27.854` | `41.689` |
| `Bits 2-3` | `>> 2` | `astro_saturn_illum_frac_median` | `21.434` | `59.309` | `84.26` |
| `Bits 4-5` | `>> 4` | `astro_mercury_ra_icrf_median` | `17.305` | `263.93` | `303.89` |
| `Bits 6-7` | `>> 6` | `astro_mercury_dec_icrf_median` | `-20.753` | `-6.4683` | `6.9879` |
| `Bits 8-9` | `>> 8` | `astro_mercury_ra_app_median` | `17.616` | `264.29` | `304.24` |
| `Bits 10-11` | `>> 10` | `astro_mercury_dec_app_median` | `-20.7` | `-6.3403` | `7.1159` |
| `Bits 12-13` | `>> 12` | `astro_mercury_azim_median` | `118.97` | `142.42` | `155.64` |
| `Bits 14-15` | `>> 14` | `astro_mercury_elev_median` | `26.681` | `28.965` | `38.78` |

### Container: `packed_astro_container_047` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mercury_app_mag_median` | `-0.70875` | `-0.249` | `0.9045` |
| `Bits 2-3` | `>> 2` | `astro_mercury_surf_bright_median` | `2.4585` | `3.0325` | `4.0375` |
| `Bits 4-5` | `>> 4` | `astro_mercury_dist_median` | `0.71831` | `1.0565` | `1.299` |
| `Bits 6-7` | `>> 6` | `astro_mercury_dist_rate_median` | `-20.128` | `5.4843` | `20.57` |
| `Bits 8-9` | `>> 8` | `astro_mercury_helio_dist_median` | `0.36354` | `0.41595` | `0.45361` |
| `Bits 10-11` | `>> 10` | `astro_mercury_helio_dist_rate_median` | `-3.6146` | `3.1518` | `8.2461` |
| `Bits 12-13` | `>> 12` | `astro_mercury_phase_angle_median` | `34.311` | `70.281` | `118.79` |
| `Bits 14-15` | `>> 14` | `astro_mercury_elong_median` | `10.226` | `16.176` | `20.463` |

### Container: `packed_astro_container_048` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mercury_illum_frac_median` | `21.434` | `59.309` | `84.26` |
| `Bits 2-3` | `>> 2` | `astro_venus_ra_icrf_median` | `246.63` | `285.81` | `324.07` |
| `Bits 4-5` | `>> 4` | `astro_venus_dec_icrf_median` | `-20.881` | `-15.761` | `-2.9124` |
| `Bits 6-7` | `>> 6` | `astro_venus_ra_app_median` | `246.98` | `286.17` | `324.39` |
| `Bits 8-9` | `>> 8` | `astro_venus_dec_app_median` | `-20.895` | `-15.659` | `-2.7806` |
| `Bits 10-11` | `>> 10` | `astro_venus_azim_median` | `146.03` | `158.66` | `170.09` |
| `Bits 12-13` | `>> 12` | `astro_venus_elev_median` | `29.527` | `32.895` | `42.848` |
| `Bits 14-15` | `>> 14` | `astro_venus_app_mag_median` | `-3.9392` | `-3.8905` | `-3.8795` |

### Container: `packed_astro_container_049` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_surf_bright_median` | `0.873` | `0.965` | `1.062` |
| `Bits 2-3` | `>> 2` | `astro_venus_dist_median` | `1.3715` | `1.5144` | `1.6266` |
| `Bits 4-5` | `>> 4` | `astro_venus_dist_rate_median` | `5.4021` | `7.3584` | `9.109` |
| `Bits 6-7` | `>> 6` | `astro_venus_helio_dist_median` | `0.7247` | `0.72645` | `0.72771` |
| `Bits 8-9` | `>> 8` | `astro_venus_helio_dist_rate_median` | `-0.0848` | `0.10303` | `0.21106` |
| `Bits 10-11` | `>> 10` | `astro_venus_phase_angle_median` | `23.178` | `33.39` | `43.786` |
| `Bits 12-13` | `>> 12` | `astro_venus_elong_median` | `16.653` | `23.82` | `30.582` |
| `Bits 14-15` | `>> 14` | `astro_venus_illum_frac_median` | `21.434` | `59.309` | `84.26` |

### Container: `packed_astro_container_050` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_ra_icrf_min_shift_m14d` | `280.57` | `280.57` | `280.57` |
| `Bits 2-3` | `>> 2` | `astro_sun_dec_icrf_min_shift_m14d` | `-23.083` | `-23.083` | `-23.083` |
| `Bits 4-5` | `>> 4` | `astro_sun_ra_app_min_shift_m14d` | `280.92` | `280.92` | `280.92` |
| `Bits 6-7` | `>> 6` | `astro_sun_dec_app_min_shift_m14d` | `-23.06` | `-23.06` | `-23.06` |
| `Bits 8-9` | `>> 8` | `astro_sun_azim_min_shift_m14d` | `141.74` | `141.74` | `141.74` |
| `Bits 10-11` | `>> 10` | `astro_sun_elev_min_shift_m14d` | `18.317` | `18.317` | `18.317` |
| `Bits 12-13` | `>> 12` | `astro_sun_app_mag_min_shift_m14d` | `-26.779` | `-26.779` | `-26.779` |
| `Bits 14-15` | `>> 14` | `astro_sun_dist_min_shift_m14d` | `0.98329` | `0.98329` | `0.9833` |

### Container: `packed_astro_container_051` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_dist_rate_min_shift_m14d` | `-0.22834` | `-0.22834` | `-0.22834` |
| `Bits 2-3` | `>> 2` | `astro_sun_illum_frac_min_shift_m14d` | `23.414` | `23.414` | `23.414` |
| `Bits 4-5` | `>> 4` | `astro_moon_ra_icrf_min_shift_m14d` | `158.08` | `158.08` | `158.08` |
| `Bits 6-7` | `>> 6` | `astro_moon_dec_icrf_min_shift_m14d` | `-20.271` | `-20.271` | `-20.271` |
| `Bits 8-9` | `>> 8` | `astro_moon_ra_app_min_shift_m14d` | `158.4` | `158.4` | `158.4` |
| `Bits 10-11` | `>> 10` | `astro_moon_dec_app_min_shift_m14d` | `-20.365` | `-20.365` | `-20.365` |
| `Bits 12-13` | `>> 12` | `astro_moon_azim_min_shift_m14d` | `204.29` | `204.29` | `204.29` |
| `Bits 14-15` | `>> 14` | `astro_moon_elev_min_shift_m14d` | `12.366` | `12.366` | `12.366` |

### Container: `packed_astro_container_052` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_app_mag_min_shift_m14d` | `-11.172` | `-11.172` | `-11.172` |
| `Bits 2-3` | `>> 2` | `astro_moon_surf_bright_min_shift_m14d` | `4.551` | `4.551` | `4.551` |
| `Bits 4-5` | `>> 4` | `astro_moon_dist_min_shift_m14d` | `0.0025734` | `0.0025744` | `0.0025754` |
| `Bits 6-7` | `>> 6` | `astro_moon_dist_rate_min_shift_m14d` | `0.067918` | `0.067919` | `0.06792` |
| `Bits 8-9` | `>> 8` | `astro_moon_helio_dist_min_shift_m14d` | `0.98196` | `0.98196` | `0.98196` |
| `Bits 10-11` | `>> 10` | `astro_moon_helio_dist_rate_min_shift_m14d` | `-0.87805` | `-0.87805` | `-0.87805` |
| `Bits 12-13` | `>> 12` | `astro_moon_phase_angle_min_shift_m14d` | `55.416` | `55.416` | `55.416` |
| `Bits 14-15` | `>> 14` | `astro_moon_elong_min_shift_m14d` | `57.755` | `57.755` | `57.755` |

### Container: `packed_astro_container_053` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_illum_frac_min_shift_m14d` | `23.414` | `23.414` | `23.414` |
| `Bits 2-3` | `>> 2` | `astro_mars_ra_icrf_min_shift_m14d` | `266.7` | `266.7` | `266.7` |
| `Bits 4-5` | `>> 4` | `astro_mars_dec_icrf_min_shift_m14d` | `-24.038` | `-24.038` | `-24.038` |
| `Bits 6-7` | `>> 6` | `astro_mars_ra_app_min_shift_m14d` | `267.05` | `267.05` | `267.05` |
| `Bits 8-9` | `>> 8` | `astro_mars_dec_app_min_shift_m14d` | `-24.036` | `-24.036` | `-24.036` |
| `Bits 10-11` | `>> 10` | `astro_mars_azim_min_shift_m14d` | `155.27` | `155.27` | `155.27` |
| `Bits 12-13` | `>> 12` | `astro_mars_elev_min_shift_m14d` | `23.091` | `23.091` | `23.091` |
| `Bits 14-15` | `>> 14` | `astro_mars_app_mag_min_shift_m14d` | `1.411` | `1.411` | `1.411` |

### Container: `packed_astro_container_054` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_surf_bright_min_shift_m14d` | `4.085` | `4.085` | `4.085` |
| `Bits 2-3` | `>> 2` | `astro_mars_dist_min_shift_m14d` | `2.4051` | `2.4051` | `2.4051` |
| `Bits 4-5` | `>> 4` | `astro_mars_dist_rate_min_shift_m14d` | `-5.6567` | `-5.6567` | `-5.6567` |
| `Bits 6-7` | `>> 6` | `astro_mars_helio_dist_min_shift_m14d` | `1.4731` | `1.4731` | `1.4731` |
| `Bits 8-9` | `>> 8` | `astro_mars_helio_dist_rate_min_shift_m14d` | `-2.208` | `-2.208` | `-2.208` |
| `Bits 10-11` | `>> 10` | `astro_mars_phase_angle_min_shift_m14d` | `8.4225` | `8.4225` | `8.4225` |
| `Bits 12-13` | `>> 12` | `astro_mars_elong_min_shift_m14d` | `12.743` | `12.743` | `12.743` |
| `Bits 14-15` | `>> 14` | `astro_mars_illum_frac_min_shift_m14d` | `23.414` | `23.414` | `23.414` |

### Container: `packed_astro_container_055` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_ra_icrf_min_shift_m14d` | `33.362` | `33.362` | `33.362` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_dec_icrf_min_shift_m14d` | `12.151` | `12.151` | `12.151` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_ra_app_min_shift_m14d` | `33.686` | `33.686` | `33.686` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_dec_app_min_shift_m14d` | `12.264` | `12.264` | `12.264` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_azim_min_shift_m14d` | `33.512` | `33.512` | `33.512` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_elev_min_shift_m14d` | `-32.48` | `-32.48` | `-32.48` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_app_mag_min_shift_m14d` | `-2.589` | `-2.589` | `-2.589` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_surf_bright_min_shift_m14d` | `5.357` | `5.357` | `5.357` |

### Container: `packed_astro_container_056` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_dist_min_shift_m14d` | `4.4815` | `4.4815` | `4.4815` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_dist_rate_min_shift_m14d` | `25.054` | `25.054` | `25.054` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_helio_dist_min_shift_m14d` | `4.9849` | `4.9849` | `4.9849` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_helio_dist_rate_min_shift_m14d` | `0.32902` | `0.32902` | `0.32902` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_phase_angle_min_shift_m14d` | `10.248` | `10.248` | `10.248` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_elong_min_shift_m14d` | `109.5` | `109.5` | `109.5` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_illum_frac_min_shift_m14d` | `23.414` | `23.414` | `23.414` |
| `Bits 14-15` | `>> 14` | `astro_saturn_ra_icrf_min_shift_m14d` | `335.46` | `335.46` | `335.46` |

### Container: `packed_astro_container_057` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_dec_icrf_min_shift_m14d` | `-11.958` | `-11.958` | `-11.958` |
| `Bits 2-3` | `>> 2` | `astro_saturn_ra_app_min_shift_m14d` | `335.78` | `335.78` | `335.78` |
| `Bits 4-5` | `>> 4` | `astro_saturn_dec_app_min_shift_m14d` | `-11.839` | `-11.839` | `-11.839` |
| `Bits 6-7` | `>> 6` | `astro_saturn_azim_min_shift_m14d` | `97.076` | `97.076` | `97.076` |
| `Bits 8-9` | `>> 8` | `astro_saturn_elev_min_shift_m14d` | `-10.178` | `-10.178` | `-10.178` |
| `Bits 10-11` | `>> 10` | `astro_saturn_app_mag_min_shift_m14d` | `0.955` | `0.955` | `0.955` |
| `Bits 12-13` | `>> 12` | `astro_saturn_surf_bright_min_shift_m14d` | `6.723` | `6.723` | `6.723` |
| `Bits 14-15` | `>> 14` | `astro_saturn_dist_min_shift_m14d` | `10.295` | `10.295` | `10.295` |

### Container: `packed_astro_container_058` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_dist_rate_min_shift_m14d` | `20.847` | `20.847` | `20.847` |
| `Bits 2-3` | `>> 2` | `astro_saturn_helio_dist_min_shift_m14d` | `9.7361` | `9.7361` | `9.7362` |
| `Bits 4-5` | `>> 4` | `astro_saturn_helio_dist_rate_min_shift_m14d` | `-0.49018` | `-0.49018` | `-0.49018` |
| `Bits 6-7` | `>> 6` | `astro_saturn_phase_angle_min_shift_m14d` | `4.2833` | `4.2833` | `4.2833` |
| `Bits 8-9` | `>> 8` | `astro_saturn_elong_min_shift_m14d` | `47.66` | `47.66` | `47.66` |
| `Bits 10-11` | `>> 10` | `astro_saturn_illum_frac_min_shift_m14d` | `23.414` | `23.414` | `23.414` |
| `Bits 12-13` | `>> 12` | `astro_mercury_ra_icrf_min_shift_m14d` | `261.33` | `261.33` | `261.33` |
| `Bits 14-15` | `>> 14` | `astro_mercury_dec_icrf_min_shift_m14d` | `-20.842` | `-20.842` | `-20.842` |

### Container: `packed_astro_container_059` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mercury_ra_app_min_shift_m14d` | `261.68` | `261.68` | `261.68` |
| `Bits 2-3` | `>> 2` | `astro_mercury_dec_app_min_shift_m14d` | `-20.86` | `-20.86` | `-20.86` |
| `Bits 4-5` | `>> 4` | `astro_mercury_azim_min_shift_m14d` | `159.01` | `159.01` | `159.01` |
| `Bits 6-7` | `>> 6` | `astro_mercury_elev_min_shift_m14d` | `28.285` | `28.285` | `28.285` |
| `Bits 8-9` | `>> 8` | `astro_mercury_app_mag_min_shift_m14d` | `-0.048` | `-0.047999` | `-0.047998` |
| `Bits 10-11` | `>> 10` | `astro_mercury_surf_bright_min_shift_m14d` | `3.281` | `3.281` | `3.281` |
| `Bits 12-13` | `>> 12` | `astro_mercury_dist_min_shift_m14d` | `0.77753` | `0.77753` | `0.77753` |
| `Bits 14-15` | `>> 14` | `astro_mercury_dist_rate_min_shift_m14d` | `32.986` | `32.986` | `32.986` |

### Container: `packed_astro_container_060` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mercury_helio_dist_min_shift_m14d` | `0.34246` | `0.34246` | `0.34247` |
| `Bits 2-3` | `>> 2` | `astro_mercury_helio_dist_rate_min_shift_m14d` | `9.213` | `9.213` | `9.213` |
| `Bits 4-5` | `>> 4` | `astro_mercury_phase_angle_min_shift_m14d` | `91.21` | `91.21` | `91.21` |
| `Bits 6-7` | `>> 6` | `astro_mercury_elong_min_shift_m14d` | `18.011` | `18.011` | `18.011` |
| `Bits 8-9` | `>> 8` | `astro_mercury_illum_frac_min_shift_m14d` | `23.414` | `23.414` | `23.414` |
| `Bits 10-11` | `>> 10` | `astro_venus_ra_icrf_min_shift_m14d` | `240.61` | `240.61` | `240.61` |
| `Bits 12-13` | `>> 12` | `astro_venus_dec_icrf_min_shift_m14d` | `-20.155` | `-20.155` | `-20.155` |
| `Bits 14-15` | `>> 14` | `astro_venus_ra_app_min_shift_m14d` | `240.95` | `240.95` | `240.95` |

### Container: `packed_astro_container_061` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_dec_app_min_shift_m14d` | `-20.206` | `-20.206` | `-20.206` |
| `Bits 2-3` | `>> 2` | `astro_venus_azim_min_shift_m14d` | `179.46` | `179.46` | `179.46` |
| `Bits 4-5` | `>> 4` | `astro_venus_elev_min_shift_m14d` | `31.042` | `31.042` | `31.042` |
| `Bits 6-7` | `>> 6` | `astro_venus_app_mag_min_shift_m14d` | `-4.039` | `-4.039` | `-4.039` |
| `Bits 8-9` | `>> 8` | `astro_venus_surf_bright_min_shift_m14d` | `1.155` | `1.155` | `1.155` |
| `Bits 10-11` | `>> 10` | `astro_venus_dist_min_shift_m14d` | `1.1819` | `1.1819` | `1.1819` |
| `Bits 12-13` | `>> 12` | `astro_venus_dist_rate_min_shift_m14d` | `10.575` | `10.575` | `10.575` |
| `Bits 14-15` | `>> 14` | `astro_venus_helio_dist_min_shift_m14d` | `0.72045` | `0.72045` | `0.72045` |

### Container: `packed_astro_container_062` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_helio_dist_rate_min_shift_m14d` | `0.19155` | `0.19155` | `0.19155` |
| `Bits 2-3` | `>> 2` | `astro_venus_phase_angle_min_shift_m14d` | `53.769` | `53.769` | `53.769` |
| `Bits 4-5` | `>> 4` | `astro_venus_elong_min_shift_m14d` | `36.267` | `36.267` | `36.267` |
| `Bits 6-7` | `>> 6` | `astro_venus_illum_frac_min_shift_m14d` | `23.414` | `23.414` | `23.414` |
| `Bits 8-9` | `>> 8` | `astro_sun_ra_icrf_max_shift_m14d` | `287.17` | `287.17` | `287.17` |
| `Bits 10-11` | `>> 10` | `astro_sun_dec_icrf_max_shift_m14d` | `-22.5` | `-22.5` | `-22.5` |
| `Bits 12-13` | `>> 12` | `astro_sun_ra_app_max_shift_m14d` | `287.52` | `287.52` | `287.52` |
| `Bits 14-15` | `>> 14` | `astro_sun_dec_app_max_shift_m14d` | `-22.463` | `-22.463` | `-22.463` |

### Container: `packed_astro_container_063` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_azim_max_shift_m14d` | `142.63` | `142.63` | `142.63` |
| `Bits 2-3` | `>> 2` | `astro_sun_elev_max_shift_m14d` | `18.499` | `18.499` | `18.499` |
| `Bits 4-5` | `>> 4` | `astro_sun_app_mag_max_shift_m14d` | `-26.779` | `-26.779` | `-26.779` |
| `Bits 6-7` | `>> 6` | `astro_sun_dist_max_shift_m14d` | `0.98333` | `0.98333` | `0.98334` |
| `Bits 8-9` | `>> 8` | `astro_sun_dist_rate_max_shift_m14d` | `-0.17915` | `-0.17915` | `-0.17915` |
| `Bits 10-11` | `>> 10` | `astro_sun_illum_frac_max_shift_m14d` | `78.383` | `78.383` | `78.383` |
| `Bits 12-13` | `>> 12` | `astro_moon_ra_icrf_max_shift_m14d` | `224.73` | `224.73` | `224.73` |
| `Bits 14-15` | `>> 14` | `astro_moon_dec_icrf_max_shift_m14d` | `12.219` | `12.219` | `12.219` |

### Container: `packed_astro_container_064` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_ra_app_max_shift_m14d` | `225.06` | `225.06` | `225.06` |
| `Bits 2-3` | `>> 2` | `astro_moon_dec_app_max_shift_m14d` | `12.095` | `12.095` | `12.095` |
| `Bits 4-5` | `>> 4` | `astro_moon_azim_max_shift_m14d` | `275.69` | `275.69` | `275.69` |
| `Bits 6-7` | `>> 6` | `astro_moon_elev_max_shift_m14d` | `27.076` | `27.076` | `27.076` |
| `Bits 8-9` | `>> 8` | `astro_moon_app_mag_max_shift_m14d` | `-8.692` | `-8.692` | `-8.692` |
| `Bits 10-11` | `>> 10` | `astro_moon_surf_bright_max_shift_m14d` | `5.819` | `5.819` | `5.819` |
| `Bits 12-13` | `>> 12` | `astro_moon_dist_max_shift_m14d` | `0.0026954` | `0.0026964` | `0.0026974` |
| `Bits 14-15` | `>> 14` | `astro_moon_dist_rate_max_shift_m14d` | `0.35466` | `0.35466` | `0.35466` |

### Container: `packed_astro_container_065` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_helio_dist_max_shift_m14d` | `0.98483` | `0.98483` | `0.98483` |
| `Bits 2-3` | `>> 2` | `astro_moon_helio_dist_rate_max_shift_m14d` | `-0.71371` | `-0.71371` | `-0.71371` |
| `Bits 4-5` | `>> 4` | `astro_moon_phase_angle_max_shift_m14d` | `122.12` | `122.12` | `122.12` |
| `Bits 6-7` | `>> 6` | `astro_moon_elong_max_shift_m14d` | `124.46` | `124.46` | `124.46` |
| `Bits 8-9` | `>> 8` | `astro_moon_illum_frac_max_shift_m14d` | `78.383` | `78.383` | `78.383` |
| `Bits 10-11` | `>> 10` | `astro_mars_ra_icrf_max_shift_m14d` | `271.58` | `271.58` | `271.58` |
| `Bits 12-13` | `>> 12` | `astro_mars_dec_icrf_max_shift_m14d` | `-23.953` | `-23.953` | `-23.953` |
| `Bits 14-15` | `>> 14` | `astro_mars_ra_app_max_shift_m14d` | `271.94` | `271.94` | `271.94` |

### Container: `packed_astro_container_066` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_dec_app_max_shift_m14d` | `-23.962` | `-23.962` | `-23.962` |
| `Bits 2-3` | `>> 2` | `astro_mars_azim_max_shift_m14d` | `156.26` | `156.26` | `156.26` |
| `Bits 4-5` | `>> 4` | `astro_mars_elev_max_shift_m14d` | `23.352` | `23.352` | `23.352` |
| `Bits 6-7` | `>> 6` | `astro_mars_app_mag_max_shift_m14d` | `1.44` | `1.44` | `1.44` |
| `Bits 8-9` | `>> 8` | `astro_mars_surf_bright_max_shift_m14d` | `4.112` | `4.112` | `4.112` |
| `Bits 10-11` | `>> 10` | `astro_mars_dist_max_shift_m14d` | `2.4238` | `2.4238` | `2.4238` |
| `Bits 12-13` | `>> 12` | `astro_mars_dist_rate_max_shift_m14d` | `-5.4023` | `-5.4023` | `-5.4023` |
| `Bits 14-15` | `>> 14` | `astro_mars_helio_dist_max_shift_m14d` | `1.4807` | `1.4807` | `1.4807` |

### Container: `packed_astro_container_067` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_helio_dist_rate_max_shift_m14d` | `-2.176` | `-2.176` | `-2.176` |
| `Bits 2-3` | `>> 2` | `astro_mars_phase_angle_max_shift_m14d` | `9.5533` | `9.5533` | `9.5533` |
| `Bits 4-5` | `>> 4` | `astro_mars_elong_max_shift_m14d` | `14.397` | `14.397` | `14.397` |
| `Bits 6-7` | `>> 6` | `astro_mars_illum_frac_max_shift_m14d` | `78.383` | `78.383` | `78.383` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_ra_icrf_max_shift_m14d` | `33.429` | `33.429` | `33.429` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_dec_icrf_max_shift_m14d` | `12.207` | `12.207` | `12.207` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_ra_app_max_shift_m14d` | `33.753` | `33.753` | `33.753` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_dec_app_max_shift_m14d` | `12.319` | `12.319` | `12.319` |

### Container: `packed_astro_container_068` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_azim_max_shift_m14d` | `39.357` | `39.357` | `39.357` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_elev_max_shift_m14d` | `-29.722` | `-29.722` | `-29.722` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_app_mag_max_shift_m14d` | `-2.539` | `-2.539` | `-2.539` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_surf_bright_max_shift_m14d` | `5.362` | `5.362` | `5.362` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_dist_max_shift_m14d` | `4.5709` | `4.5709` | `4.5709` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_dist_rate_max_shift_m14d` | `26.135` | `26.135` | `26.135` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_helio_dist_max_shift_m14d` | `4.986` | `4.986` | `4.986` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_helio_dist_rate_max_shift_m14d` | `0.33541` | `0.33541` | `0.33541` |

### Container: `packed_astro_container_069` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_phase_angle_max_shift_m14d` | `10.71` | `10.71` | `10.71` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_elong_max_shift_m14d` | `115.54` | `115.54` | `115.54` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_illum_frac_max_shift_m14d` | `78.383` | `78.383` | `78.383` |
| `Bits 6-7` | `>> 6` | `astro_saturn_ra_icrf_max_shift_m14d` | `335.99` | `335.99` | `335.99` |
| `Bits 8-9` | `>> 8` | `astro_saturn_dec_icrf_max_shift_m14d` | `-11.752` | `-11.752` | `-11.752` |
| `Bits 10-11` | `>> 10` | `astro_saturn_ra_app_max_shift_m14d` | `336.3` | `336.3` | `336.3` |
| `Bits 12-13` | `>> 12` | `astro_saturn_dec_app_max_shift_m14d` | `-11.633` | `-11.633` | `-11.633` |
| `Bits 14-15` | `>> 14` | `astro_saturn_azim_max_shift_m14d` | `100.2` | `100.2` | `100.2` |

### Container: `packed_astro_container_070` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_elev_max_shift_m14d` | `-5.8934` | `-5.8934` | `-5.8934` |
| `Bits 2-3` | `>> 2` | `astro_saturn_app_mag_max_shift_m14d` | `0.967` | `0.967` | `0.967` |
| `Bits 4-5` | `>> 4` | `astro_saturn_surf_bright_max_shift_m14d` | `6.727` | `6.727` | `6.727` |
| `Bits 6-7` | `>> 6` | `astro_saturn_dist_max_shift_m14d` | `10.371` | `10.371` | `10.371` |
| `Bits 8-9` | `>> 8` | `astro_saturn_dist_rate_max_shift_m14d` | `22.619` | `22.619` | `22.619` |
| `Bits 10-11` | `>> 10` | `astro_saturn_helio_dist_max_shift_m14d` | `9.7378` | `9.7378` | `9.7378` |
| `Bits 12-13` | `>> 12` | `astro_saturn_helio_dist_rate_max_shift_m14d` | `-0.48811` | `-0.48811` | `-0.48811` |
| `Bits 14-15` | `>> 14` | `astro_saturn_phase_angle_max_shift_m14d` | `4.6406` | `4.6406` | `4.6406` |

### Container: `packed_astro_container_071` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_elong_max_shift_m14d` | `53.221` | `53.221` | `53.221` |
| `Bits 2-3` | `>> 2` | `astro_saturn_illum_frac_max_shift_m14d` | `78.383` | `78.383` | `78.383` |
| `Bits 4-5` | `>> 4` | `astro_mercury_ra_icrf_max_shift_m14d` | `262.99` | `262.99` | `262.99` |
| `Bits 6-7` | `>> 6` | `astro_mercury_dec_icrf_max_shift_m14d` | `-20.135` | `-20.135` | `-20.135` |
| `Bits 8-9` | `>> 8` | `astro_mercury_ra_app_max_shift_m14d` | `263.34` | `263.34` | `263.34` |
| `Bits 10-11` | `>> 10` | `astro_mercury_dec_app_max_shift_m14d` | `-20.156` | `-20.156` | `-20.156` |
| `Bits 12-13` | `>> 12` | `astro_mercury_azim_max_shift_m14d` | `163.7` | `163.7` | `163.7` |
| `Bits 14-15` | `>> 14` | `astro_mercury_elev_max_shift_m14d` | `28.79` | `28.79` | `28.79` |

### Container: `packed_astro_container_072` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mercury_app_mag_max_shift_m14d` | `0.508` | `0.508` | `0.508` |
| `Bits 2-3` | `>> 2` | `astro_mercury_surf_bright_max_shift_m14d` | `3.51` | `3.51` | `3.51` |
| `Bits 4-5` | `>> 4` | `astro_mercury_dist_max_shift_m14d` | `0.9005` | `0.9005` | `0.9005` |
| `Bits 6-7` | `>> 6` | `astro_mercury_dist_rate_max_shift_m14d` | `36.196` | `36.196` | `36.196` |
| `Bits 8-9` | `>> 8` | `astro_mercury_helio_dist_max_shift_m14d` | `0.37652` | `0.37652` | `0.37653` |
| `Bits 10-11` | `>> 10` | `astro_mercury_helio_dist_rate_max_shift_m14d` | `10.059` | `10.059` | `10.059` |
| `Bits 12-13` | `>> 12` | `astro_mercury_phase_angle_max_shift_m14d` | `117.4` | `117.4` | `117.4` |
| `Bits 14-15` | `>> 14` | `astro_mercury_elong_max_shift_m14d` | `22.508` | `22.508` | `22.508` |

### Container: `packed_astro_container_073` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mercury_illum_frac_max_shift_m14d` | `78.383` | `78.383` | `78.383` |
| `Bits 2-3` | `>> 2` | `astro_venus_ra_icrf_max_shift_m14d` | `248.21` | `248.21` | `248.21` |
| `Bits 4-5` | `>> 4` | `astro_venus_dec_icrf_max_shift_m14d` | `-18.705` | `-18.705` | `-18.705` |
| `Bits 6-7` | `>> 6` | `astro_venus_ra_app_max_shift_m14d` | `248.56` | `248.56` | `248.56` |
| `Bits 8-9` | `>> 8` | `astro_venus_dec_app_max_shift_m14d` | `-18.771` | `-18.771` | `-18.771` |
| `Bits 10-11` | `>> 10` | `astro_venus_azim_max_shift_m14d` | `181.35` | `181.35` | `181.35` |
| `Bits 12-13` | `>> 12` | `astro_venus_elev_max_shift_m14d` | `32.468` | `32.468` | `32.468` |
| `Bits 14-15` | `>> 14` | `astro_venus_app_mag_max_shift_m14d` | `-4.017` | `-4.017` | `-4.017` |

### Container: `packed_astro_container_074` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_surf_bright_max_shift_m14d` | `1.176` | `1.176` | `1.176` |
| `Bits 2-3` | `>> 2` | `astro_venus_dist_max_shift_m14d` | `1.2191` | `1.2191` | `1.2191` |
| `Bits 4-5` | `>> 4` | `astro_venus_dist_rate_max_shift_m14d` | `10.893` | `10.893` | `10.893` |
| `Bits 6-7` | `>> 6` | `astro_venus_helio_dist_max_shift_m14d` | `0.72115` | `0.72115` | `0.72116` |
| `Bits 8-9` | `>> 8` | `astro_venus_helio_dist_rate_max_shift_m14d` | `0.21206` | `0.21206` | `0.21206` |
| `Bits 10-11` | `>> 10` | `astro_venus_phase_angle_max_shift_m14d` | `56.135` | `56.135` | `56.135` |
| `Bits 12-13` | `>> 12` | `astro_venus_elong_max_shift_m14d` | `37.471` | `37.471` | `37.471` |
| `Bits 14-15` | `>> 14` | `astro_venus_illum_frac_max_shift_m14d` | `78.383` | `78.383` | `78.383` |

### Container: `packed_astro_container_075` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_ra_icrf_mean_shift_m14d` | `283.87` | `283.87` | `283.87` |
| `Bits 2-3` | `>> 2` | `astro_sun_dec_icrf_mean_shift_m14d` | `-22.81` | `-22.81` | `-22.81` |
| `Bits 4-5` | `>> 4` | `astro_sun_ra_app_mean_shift_m14d` | `284.23` | `284.23` | `284.23` |
| `Bits 6-7` | `>> 6` | `astro_sun_dec_app_mean_shift_m14d` | `-22.781` | `-22.781` | `-22.781` |
| `Bits 8-9` | `>> 8` | `astro_sun_azim_mean_shift_m14d` | `142.19` | `142.19` | `142.19` |
| `Bits 10-11` | `>> 10` | `astro_sun_elev_mean_shift_m14d` | `18.391` | `18.391` | `18.391` |
| `Bits 12-13` | `>> 12` | `astro_sun_app_mag_mean_shift_m14d` | `-26.779` | `-26.779` | `-26.779` |
| `Bits 14-15` | `>> 14` | `astro_sun_dist_mean_shift_m14d` | `0.98331` | `0.98331` | `0.98331` |

### Container: `packed_astro_container_076` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_dist_rate_mean_shift_m14d` | `-0.20272` | `-0.20272` | `-0.20271` |
| `Bits 2-3` | `>> 2` | `astro_sun_illum_frac_mean_shift_m14d` | `51.384` | `51.384` | `51.384` |
| `Bits 4-5` | `>> 4` | `astro_moon_ra_icrf_mean_shift_m14d` | `190.62` | `190.62` | `190.62` |
| `Bits 6-7` | `>> 6` | `astro_moon_dec_icrf_mean_shift_m14d` | `-4.1583` | `-4.1583` | `-4.1583` |
| `Bits 8-9` | `>> 8` | `astro_moon_ra_app_mean_shift_m14d` | `190.94` | `190.94` | `190.94` |
| `Bits 10-11` | `>> 10` | `astro_moon_dec_app_mean_shift_m14d` | `-4.28` | `-4.28` | `-4.28` |
| `Bits 12-13` | `>> 12` | `astro_moon_azim_mean_shift_m14d` | `241.51` | `241.51` | `241.51` |
| `Bits 14-15` | `>> 14` | `astro_moon_elev_mean_shift_m14d` | `21.883` | `21.883` | `21.883` |

### Container: `packed_astro_container_077` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_app_mag_mean_shift_m14d` | `-10.055` | `-10.055` | `-10.055` |
| `Bits 2-3` | `>> 2` | `astro_moon_surf_bright_mean_shift_m14d` | `5.163` | `5.163` | `5.163` |
| `Bits 4-5` | `>> 4` | `astro_moon_dist_mean_shift_m14d` | `0.0026517` | `0.0026527` | `0.0026537` |
| `Bits 6-7` | `>> 6` | `astro_moon_dist_rate_mean_shift_m14d` | `0.23706` | `0.23706` | `0.23706` |
| `Bits 8-9` | `>> 8` | `astro_moon_helio_dist_mean_shift_m14d` | `0.98339` | `0.98339` | `0.98339` |
| `Bits 10-11` | `>> 10` | `astro_moon_helio_dist_rate_mean_shift_m14d` | `-0.81159` | `-0.81159` | `-0.81159` |
| `Bits 12-13` | `>> 12` | `astro_moon_phase_angle_mean_shift_m14d` | `88.31` | `88.31` | `88.31` |
| `Bits 14-15` | `>> 14` | `astro_moon_elong_mean_shift_m14d` | `91.547` | `91.547` | `91.547` |

### Container: `packed_astro_container_078` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_illum_frac_mean_shift_m14d` | `51.384` | `51.384` | `51.384` |
| `Bits 2-3` | `>> 2` | `astro_mars_ra_icrf_mean_shift_m14d` | `269.14` | `269.14` | `269.14` |
| `Bits 4-5` | `>> 4` | `astro_mars_dec_icrf_mean_shift_m14d` | `-24.006` | `-24.006` | `-24.006` |
| `Bits 6-7` | `>> 6` | `astro_mars_ra_app_mean_shift_m14d` | `269.49` | `269.49` | `269.49` |
| `Bits 8-9` | `>> 8` | `astro_mars_dec_app_mean_shift_m14d` | `-24.01` | `-24.01` | `-24.01` |
| `Bits 10-11` | `>> 10` | `astro_mars_azim_mean_shift_m14d` | `155.77` | `155.77` | `155.77` |
| `Bits 12-13` | `>> 12` | `astro_mars_elev_mean_shift_m14d` | `23.213` | `23.213` | `23.213` |
| `Bits 14-15` | `>> 14` | `astro_mars_app_mag_mean_shift_m14d` | `1.426` | `1.426` | `1.426` |

### Container: `packed_astro_container_079` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_surf_bright_mean_shift_m14d` | `4.1006` | `4.1006` | `4.1006` |
| `Bits 2-3` | `>> 2` | `astro_mars_dist_mean_shift_m14d` | `2.4145` | `2.4145` | `2.4145` |
| `Bits 4-5` | `>> 4` | `astro_mars_dist_rate_mean_shift_m14d` | `-5.5303` | `-5.5303` | `-5.5303` |
| `Bits 6-7` | `>> 6` | `astro_mars_helio_dist_mean_shift_m14d` | `1.4769` | `1.4769` | `1.4769` |
| `Bits 8-9` | `>> 8` | `astro_mars_helio_dist_rate_mean_shift_m14d` | `-2.1925` | `-2.1925` | `-2.1925` |
| `Bits 10-11` | `>> 10` | `astro_mars_phase_angle_mean_shift_m14d` | `8.9884` | `8.9884` | `8.9884` |
| `Bits 12-13` | `>> 12` | `astro_mars_elong_mean_shift_m14d` | `13.572` | `13.572` | `13.572` |
| `Bits 14-15` | `>> 14` | `astro_mars_illum_frac_mean_shift_m14d` | `51.384` | `51.384` | `51.384` |

### Container: `packed_astro_container_080` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_ra_icrf_mean_shift_m14d` | `33.387` | `33.387` | `33.387` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_dec_icrf_mean_shift_m14d` | `12.176` | `12.176` | `12.176` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_ra_app_mean_shift_m14d` | `33.711` | `33.711` | `33.711` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_dec_app_mean_shift_m14d` | `12.289` | `12.289` | `12.289` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_azim_mean_shift_m14d` | `36.473` | `36.473` | `36.473` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_elev_mean_shift_m14d` | `-31.125` | `-31.125` | `-31.125` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_app_mag_mean_shift_m14d` | `-2.564` | `-2.564` | `-2.564` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_surf_bright_mean_shift_m14d` | `5.3599` | `5.3599` | `5.3599` |

### Container: `packed_astro_container_081` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_dist_mean_shift_m14d` | `4.526` | `4.526` | `4.526` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_dist_rate_mean_shift_m14d` | `25.616` | `25.616` | `25.616` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_helio_dist_mean_shift_m14d` | `4.9855` | `4.9855` | `4.9855` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_helio_dist_rate_mean_shift_m14d` | `0.33256` | `0.33256` | `0.33256` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_phase_angle_mean_shift_m14d` | `10.488` | `10.488` | `10.488` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_elong_mean_shift_m14d` | `112.51` | `112.51` | `112.51` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_illum_frac_mean_shift_m14d` | `51.384` | `51.384` | `51.384` |
| `Bits 14-15` | `>> 14` | `astro_saturn_ra_icrf_mean_shift_m14d` | `335.72` | `335.72` | `335.72` |

### Container: `packed_astro_container_082` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_dec_icrf_mean_shift_m14d` | `-11.856` | `-11.856` | `-11.856` |
| `Bits 2-3` | `>> 2` | `astro_saturn_ra_app_mean_shift_m14d` | `336.04` | `336.04` | `336.04` |
| `Bits 4-5` | `>> 4` | `astro_saturn_dec_app_mean_shift_m14d` | `-11.737` | `-11.737` | `-11.737` |
| `Bits 6-7` | `>> 6` | `astro_saturn_azim_mean_shift_m14d` | `98.639` | `98.639` | `98.639` |
| `Bits 8-9` | `>> 8` | `astro_saturn_elev_mean_shift_m14d` | `-8.0321` | `-8.0321` | `-8.0321` |
| `Bits 10-11` | `>> 10` | `astro_saturn_app_mag_mean_shift_m14d` | `0.961` | `0.961` | `0.961` |
| `Bits 12-13` | `>> 12` | `astro_saturn_surf_bright_mean_shift_m14d` | `6.7253` | `6.7253` | `6.7253` |
| `Bits 14-15` | `>> 14` | `astro_saturn_dist_mean_shift_m14d` | `10.333` | `10.333` | `10.333` |

### Container: `packed_astro_container_083` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_dist_rate_mean_shift_m14d` | `21.747` | `21.747` | `21.747` |
| `Bits 2-3` | `>> 2` | `astro_saturn_helio_dist_mean_shift_m14d` | `9.737` | `9.737` | `9.737` |
| `Bits 4-5` | `>> 4` | `astro_saturn_helio_dist_rate_mean_shift_m14d` | `-0.48885` | `-0.48885` | `-0.48885` |
| `Bits 6-7` | `>> 6` | `astro_saturn_phase_angle_mean_shift_m14d` | `4.4646` | `4.4646` | `4.4646` |
| `Bits 8-9` | `>> 8` | `astro_saturn_elong_mean_shift_m14d` | `50.438` | `50.438` | `50.438` |
| `Bits 10-11` | `>> 10` | `astro_saturn_illum_frac_mean_shift_m14d` | `51.384` | `51.384` | `51.384` |
| `Bits 12-13` | `>> 12` | `astro_mercury_ra_icrf_mean_shift_m14d` | `261.87` | `261.87` | `261.87` |
| `Bits 14-15` | `>> 14` | `astro_mercury_dec_icrf_mean_shift_m14d` | `-20.437` | `-20.437` | `-20.437` |

### Container: `packed_astro_container_084` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mercury_ra_app_mean_shift_m14d` | `262.22` | `262.22` | `262.22` |
| `Bits 2-3` | `>> 2` | `astro_mercury_dec_app_mean_shift_m14d` | `-20.457` | `-20.457` | `-20.457` |
| `Bits 4-5` | `>> 4` | `astro_mercury_azim_mean_shift_m14d` | `161.7` | `161.7` | `161.7` |
| `Bits 6-7` | `>> 6` | `astro_mercury_elev_mean_shift_m14d` | `28.644` | `28.644` | `28.644` |
| `Bits 8-9` | `>> 8` | `astro_mercury_app_mag_mean_shift_m14d` | `0.173` | `0.173` | `0.173` |
| `Bits 10-11` | `>> 10` | `astro_mercury_surf_bright_mean_shift_m14d` | `3.3753` | `3.3753` | `3.3753` |
| `Bits 12-13` | `>> 12` | `astro_mercury_dist_mean_shift_m14d` | `0.83832` | `0.83832` | `0.83832` |
| `Bits 14-15` | `>> 14` | `astro_mercury_dist_rate_mean_shift_m14d` | `35.248` | `35.248` | `35.248` |

### Container: `packed_astro_container_085` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mercury_helio_dist_mean_shift_m14d` | `0.3593` | `0.3593` | `0.3593` |
| `Bits 2-3` | `>> 2` | `astro_mercury_helio_dist_rate_mean_shift_m14d` | `9.7955` | `9.7955` | `9.7955` |
| `Bits 4-5` | `>> 4` | `astro_mercury_phase_angle_mean_shift_m14d` | `103.62` | `103.62` | `103.62` |
| `Bits 6-7` | `>> 6` | `astro_mercury_elong_mean_shift_m14d` | `20.583` | `20.583` | `20.583` |
| `Bits 8-9` | `>> 8` | `astro_mercury_illum_frac_mean_shift_m14d` | `51.384` | `51.384` | `51.384` |
| `Bits 10-11` | `>> 10` | `astro_venus_ra_icrf_mean_shift_m14d` | `244.4` | `244.4` | `244.4` |
| `Bits 12-13` | `>> 12` | `astro_venus_dec_icrf_mean_shift_m14d` | `-19.451` | `-19.451` | `-19.451` |
| `Bits 14-15` | `>> 14` | `astro_venus_ra_app_mean_shift_m14d` | `244.74` | `244.74` | `244.74` |

### Container: `packed_astro_container_086` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_dec_app_mean_shift_m14d` | `-19.51` | `-19.51` | `-19.51` |
| `Bits 2-3` | `>> 2` | `astro_venus_azim_mean_shift_m14d` | `180.41` | `180.41` | `180.41` |
| `Bits 4-5` | `>> 4` | `astro_venus_elev_mean_shift_m14d` | `31.737` | `31.737` | `31.737` |
| `Bits 6-7` | `>> 6` | `astro_venus_app_mag_mean_shift_m14d` | `-4.0276` | `-4.0276` | `-4.0276` |
| `Bits 8-9` | `>> 8` | `astro_venus_surf_bright_mean_shift_m14d` | `1.1654` | `1.1654` | `1.1654` |
| `Bits 10-11` | `>> 10` | `astro_venus_dist_mean_shift_m14d` | `1.2006` | `1.2006` | `1.2006` |
| `Bits 12-13` | `>> 12` | `astro_venus_dist_rate_mean_shift_m14d` | `10.736` | `10.736` | `10.736` |
| `Bits 14-15` | `>> 14` | `astro_venus_helio_dist_mean_shift_m14d` | `0.7208` | `0.7208` | `0.7208` |

### Container: `packed_astro_container_087` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_helio_dist_rate_mean_shift_m14d` | `0.20221` | `0.20221` | `0.20221` |
| `Bits 2-3` | `>> 2` | `astro_venus_phase_angle_mean_shift_m14d` | `54.948` | `54.948` | `54.948` |
| `Bits 4-5` | `>> 4` | `astro_venus_elong_mean_shift_m14d` | `36.871` | `36.871` | `36.871` |
| `Bits 6-7` | `>> 6` | `astro_venus_illum_frac_mean_shift_m14d` | `51.384` | `51.384` | `51.384` |
| `Bits 8-9` | `>> 8` | `astro_sun_ra_icrf_median_shift_m14d` | `283.88` | `283.88` | `283.88` |
| `Bits 10-11` | `>> 10` | `astro_sun_dec_icrf_median_shift_m14d` | `-22.825` | `-22.825` | `-22.825` |
| `Bits 12-13` | `>> 12` | `astro_sun_ra_app_median_shift_m14d` | `284.23` | `284.23` | `284.23` |
| `Bits 14-15` | `>> 14` | `astro_sun_dec_app_median_shift_m14d` | `-22.796` | `-22.796` | `-22.796` |

### Container: `packed_astro_container_088` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_azim_median_shift_m14d` | `142.2` | `142.2` | `142.2` |
| `Bits 2-3` | `>> 2` | `astro_sun_elev_median_shift_m14d` | `18.377` | `18.377` | `18.377` |
| `Bits 4-5` | `>> 4` | `astro_sun_app_mag_median_shift_m14d` | `-26.779` | `-26.779` | `-26.779` |
| `Bits 6-7` | `>> 6` | `astro_sun_dist_median_shift_m14d` | `0.9833` | `0.9833` | `0.98331` |
| `Bits 8-9` | `>> 8` | `astro_sun_dist_rate_median_shift_m14d` | `-0.20189` | `-0.20189` | `-0.20189` |
| `Bits 10-11` | `>> 10` | `astro_sun_illum_frac_median_shift_m14d` | `51.795` | `51.795` | `51.795` |
| `Bits 12-13` | `>> 12` | `astro_moon_ra_icrf_median_shift_m14d` | `190.01` | `190.01` | `190.01` |
| `Bits 14-15` | `>> 14` | `astro_moon_dec_icrf_median_shift_m14d` | `-4.247` | `-4.2469` | `-4.2469` |

### Container: `packed_astro_container_089` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_ra_app_median_shift_m14d` | `190.31` | `190.31` | `190.31` |
| `Bits 2-3` | `>> 2` | `astro_moon_dec_app_median_shift_m14d` | `-4.3784` | `-4.3784` | `-4.3784` |
| `Bits 4-5` | `>> 4` | `astro_moon_azim_median_shift_m14d` | `242.76` | `242.76` | `242.76` |
| `Bits 6-7` | `>> 6` | `astro_moon_elev_median_shift_m14d` | `23.611` | `23.611` | `23.611` |
| `Bits 8-9` | `>> 8` | `astro_moon_app_mag_median_shift_m14d` | `-10.151` | `-10.151` | `-10.151` |
| `Bits 10-11` | `>> 10` | `astro_moon_surf_bright_median_shift_m14d` | `5.145` | `5.145` | `5.145` |
| `Bits 12-13` | `>> 12` | `astro_moon_dist_median_shift_m14d` | `0.0026659` | `0.0026669` | `0.0026679` |
| `Bits 14-15` | `>> 14` | `astro_moon_dist_rate_median_shift_m14d` | `0.25786` | `0.25786` | `0.25786` |

### Container: `packed_astro_container_090` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_helio_dist_median_shift_m14d` | `0.98339` | `0.98339` | `0.98339` |
| `Bits 2-3` | `>> 2` | `astro_moon_helio_dist_rate_median_shift_m14d` | `-0.81843` | `-0.81843` | `-0.81843` |
| `Bits 4-5` | `>> 4` | `astro_moon_phase_angle_median_shift_m14d` | `87.943` | `87.943` | `87.943` |
| `Bits 6-7` | `>> 6` | `astro_moon_elong_median_shift_m14d` | `91.901` | `91.902` | `91.902` |
| `Bits 8-9` | `>> 8` | `astro_moon_illum_frac_median_shift_m14d` | `51.795` | `51.795` | `51.795` |
| `Bits 10-11` | `>> 10` | `astro_mars_ra_icrf_median_shift_m14d` | `269.13` | `269.13` | `269.13` |
| `Bits 12-13` | `>> 12` | `astro_mars_dec_icrf_median_shift_m14d` | `-24.014` | `-24.014` | `-24.014` |
| `Bits 14-15` | `>> 14` | `astro_mars_ra_app_median_shift_m14d` | `269.49` | `269.49` | `269.49` |

### Container: `packed_astro_container_091` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_dec_app_median_shift_m14d` | `-24.018` | `-24.018` | `-24.018` |
| `Bits 2-3` | `>> 2` | `astro_mars_azim_median_shift_m14d` | `155.78` | `155.78` | `155.78` |
| `Bits 4-5` | `>> 4` | `astro_mars_elev_median_shift_m14d` | `23.207` | `23.207` | `23.207` |
| `Bits 6-7` | `>> 6` | `astro_mars_app_mag_median_shift_m14d` | `1.429` | `1.429` | `1.429` |
| `Bits 8-9` | `>> 8` | `astro_mars_surf_bright_median_shift_m14d` | `4.099` | `4.099` | `4.099` |
| `Bits 10-11` | `>> 10` | `astro_mars_dist_median_shift_m14d` | `2.4146` | `2.4146` | `2.4146` |
| `Bits 12-13` | `>> 12` | `astro_mars_dist_rate_median_shift_m14d` | `-5.531` | `-5.531` | `-5.531` |
| `Bits 14-15` | `>> 14` | `astro_mars_helio_dist_median_shift_m14d` | `1.4769` | `1.4769` | `1.4769` |

### Container: `packed_astro_container_092` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_helio_dist_rate_median_shift_m14d` | `-2.1929` | `-2.1929` | `-2.1929` |
| `Bits 2-3` | `>> 2` | `astro_mars_phase_angle_median_shift_m14d` | `8.9888` | `8.9888` | `8.9888` |
| `Bits 4-5` | `>> 4` | `astro_mars_elong_median_shift_m14d` | `13.573` | `13.573` | `13.573` |
| `Bits 6-7` | `>> 6` | `astro_mars_illum_frac_median_shift_m14d` | `51.795` | `51.795` | `51.795` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_ra_icrf_median_shift_m14d` | `33.381` | `33.381` | `33.381` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_dec_icrf_median_shift_m14d` | `12.174` | `12.174` | `12.174` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_ra_app_median_shift_m14d` | `33.704` | `33.704` | `33.704` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_dec_app_median_shift_m14d` | `12.286` | `12.286` | `12.286` |

### Container: `packed_astro_container_093` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_azim_median_shift_m14d` | `36.504` | `36.504` | `36.504` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_elev_median_shift_m14d` | `-31.145` | `-31.145` | `-31.145` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_app_mag_median_shift_m14d` | `-2.564` | `-2.564` | `-2.564` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_surf_bright_median_shift_m14d` | `5.36` | `5.36` | `5.36` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_dist_median_shift_m14d` | `4.5258` | `4.5258` | `4.5258` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_dist_rate_median_shift_m14d` | `25.632` | `25.632` | `25.632` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_helio_dist_median_shift_m14d` | `4.9855` | `4.9855` | `4.9855` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_helio_dist_rate_median_shift_m14d` | `0.3332` | `0.3332` | `0.3332` |

### Container: `packed_astro_container_094` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_phase_angle_median_shift_m14d` | `10.495` | `10.495` | `10.495` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_elong_median_shift_m14d` | `112.5` | `112.5` | `112.5` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_illum_frac_median_shift_m14d` | `51.795` | `51.795` | `51.795` |
| `Bits 6-7` | `>> 6` | `astro_saturn_ra_icrf_median_shift_m14d` | `335.72` | `335.72` | `335.72` |
| `Bits 8-9` | `>> 8` | `astro_saturn_dec_icrf_median_shift_m14d` | `-11.857` | `-11.857` | `-11.857` |
| `Bits 10-11` | `>> 10` | `astro_saturn_ra_app_median_shift_m14d` | `336.03` | `336.03` | `336.03` |
| `Bits 12-13` | `>> 12` | `astro_saturn_dec_app_median_shift_m14d` | `-11.738` | `-11.738` | `-11.738` |
| `Bits 14-15` | `>> 14` | `astro_saturn_azim_median_shift_m14d` | `98.64` | `98.64` | `98.64` |

### Container: `packed_astro_container_095` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_elev_median_shift_m14d` | `-8.0292` | `-8.0292` | `-8.0292` |
| `Bits 2-3` | `>> 2` | `astro_saturn_app_mag_median_shift_m14d` | `0.961` | `0.961` | `0.961` |
| `Bits 4-5` | `>> 4` | `astro_saturn_surf_bright_median_shift_m14d` | `6.725` | `6.725` | `6.725` |
| `Bits 6-7` | `>> 6` | `astro_saturn_dist_median_shift_m14d` | `10.334` | `10.334` | `10.334` |
| `Bits 8-9` | `>> 8` | `astro_saturn_dist_rate_median_shift_m14d` | `21.759` | `21.759` | `21.759` |
| `Bits 10-11` | `>> 10` | `astro_saturn_helio_dist_median_shift_m14d` | `9.737` | `9.737` | `9.737` |
| `Bits 12-13` | `>> 12` | `astro_saturn_helio_dist_rate_median_shift_m14d` | `-0.4886` | `-0.4886` | `-0.4886` |
| `Bits 14-15` | `>> 14` | `astro_saturn_phase_angle_median_shift_m14d` | `4.4668` | `4.4668` | `4.4668` |

### Container: `packed_astro_container_096` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_elong_median_shift_m14d` | `50.436` | `50.436` | `50.436` |
| `Bits 2-3` | `>> 2` | `astro_saturn_illum_frac_median_shift_m14d` | `51.795` | `51.795` | `51.795` |
| `Bits 4-5` | `>> 4` | `astro_mercury_ra_icrf_median_shift_m14d` | `261.59` | `261.59` | `261.59` |
| `Bits 6-7` | `>> 6` | `astro_mercury_dec_icrf_median_shift_m14d` | `-20.396` | `-20.396` | `-20.396` |
| `Bits 8-9` | `>> 8` | `astro_mercury_ra_app_median_shift_m14d` | `261.94` | `261.94` | `261.94` |
| `Bits 10-11` | `>> 10` | `astro_mercury_dec_app_median_shift_m14d` | `-20.417` | `-20.417` | `-20.417` |
| `Bits 12-13` | `>> 12` | `astro_mercury_azim_median_shift_m14d` | `161.97` | `161.97` | `161.97` |
| `Bits 14-15` | `>> 14` | `astro_mercury_elev_median_shift_m14d` | `28.695` | `28.695` | `28.695` |

### Container: `packed_astro_container_097` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mercury_app_mag_median_shift_m14d` | `0.129` | `0.129` | `0.129` |
| `Bits 2-3` | `>> 2` | `astro_mercury_surf_bright_median_shift_m14d` | `3.36` | `3.36` | `3.36` |
| `Bits 4-5` | `>> 4` | `astro_mercury_dist_median_shift_m14d` | `0.83778` | `0.83779` | `0.83779` |
| `Bits 6-7` | `>> 6` | `astro_mercury_dist_rate_median_shift_m14d` | `35.828` | `35.828` | `35.828` |
| `Bits 8-9` | `>> 8` | `astro_mercury_helio_dist_median_shift_m14d` | `0.35915` | `0.35915` | `0.35915` |
| `Bits 10-11` | `>> 10` | `astro_mercury_helio_dist_rate_median_shift_m14d` | `9.9345` | `9.9345` | `9.9345` |
| `Bits 12-13` | `>> 12` | `astro_mercury_phase_angle_median_shift_m14d` | `103.07` | `103.07` | `103.07` |
| `Bits 14-15` | `>> 14` | `astro_mercury_elong_median_shift_m14d` | `20.842` | `20.842` | `20.842` |

### Container: `packed_astro_container_098` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mercury_illum_frac_median_shift_m14d` | `51.795` | `51.795` | `51.795` |
| `Bits 2-3` | `>> 2` | `astro_venus_ra_icrf_median_shift_m14d` | `244.39` | `244.39` | `244.39` |
| `Bits 4-5` | `>> 4` | `astro_venus_dec_icrf_median_shift_m14d` | `-19.468` | `-19.468` | `-19.468` |
| `Bits 6-7` | `>> 6` | `astro_venus_ra_app_median_shift_m14d` | `244.73` | `244.73` | `244.73` |
| `Bits 8-9` | `>> 8` | `astro_venus_dec_app_median_shift_m14d` | `-19.526` | `-19.526` | `-19.526` |
| `Bits 10-11` | `>> 10` | `astro_venus_azim_median_shift_m14d` | `180.42` | `180.42` | `180.42` |
| `Bits 12-13` | `>> 12` | `astro_venus_elev_median_shift_m14d` | `31.723` | `31.723` | `31.723` |
| `Bits 14-15` | `>> 14` | `astro_venus_app_mag_median_shift_m14d` | `-4.027` | `-4.027` | `-4.027` |

### Container: `packed_astro_container_099` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_surf_bright_median_shift_m14d` | `1.165` | `1.165` | `1.165` |
| `Bits 2-3` | `>> 2` | `astro_venus_dist_median_shift_m14d` | `1.2006` | `1.2006` | `1.2006` |
| `Bits 4-5` | `>> 4` | `astro_venus_dist_rate_median_shift_m14d` | `10.737` | `10.737` | `10.737` |
| `Bits 6-7` | `>> 6` | `astro_venus_helio_dist_median_shift_m14d` | `0.72079` | `0.7208` | `0.7208` |
| `Bits 8-9` | `>> 8` | `astro_venus_helio_dist_rate_median_shift_m14d` | `0.20253` | `0.20253` | `0.20253` |
| `Bits 10-11` | `>> 10` | `astro_venus_phase_angle_median_shift_m14d` | `54.945` | `54.945` | `54.945` |
| `Bits 12-13` | `>> 12` | `astro_venus_elong_median_shift_m14d` | `36.873` | `36.873` | `36.873` |
| `Bits 14-15` | `>> 14` | `astro_venus_illum_frac_median_shift_m14d` | `51.795` | `51.795` | `51.795` |

### Container: `packed_astro_container_100` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_ra_icrf_min_shift_m7d` | `280.57` | `292.07` | `323.03` |
| `Bits 2-3` | `>> 2` | `astro_sun_dec_icrf_min_shift_m7d` | `-23.083` | `-21.844` | `-14.59` |
| `Bits 4-5` | `>> 4` | `astro_sun_ra_app_min_shift_m7d` | `280.92` | `292.42` | `323.35` |
| `Bits 6-7` | `>> 6` | `astro_sun_dec_app_min_shift_m7d` | `-23.06` | `-21.797` | `-14.486` |
| `Bits 8-9` | `>> 8` | `astro_sun_azim_min_shift_m7d` | `134.06` | `139.93` | `141.74` |
| `Bits 10-11` | `>> 10` | `astro_sun_elev_min_shift_m7d` | `18.317` | `18.842` | `24.121` |
| `Bits 12-13` | `>> 12` | `astro_sun_app_mag_min_shift_m7d` | `-26.779` | `-26.779` | `-26.771` |
| `Bits 14-15` | `>> 14` | `astro_sun_dist_min_shift_m7d` | `0.98329` | `0.98348` | `0.98671` |

### Container: `packed_astro_container_101` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_dist_rate_min_shift_m7d` | `-0.22834` | `-0.15247` | `0.068517` |
| `Bits 2-3` | `>> 2` | `astro_sun_illum_frac_min_shift_m7d` | `9.1701` | `23.414` | `23.414` |
| `Bits 4-5` | `>> 4` | `astro_moon_ra_icrf_min_shift_m7d` | `105.44` | `158.08` | `163.7` |
| `Bits 6-7` | `>> 6` | `astro_moon_dec_icrf_min_shift_m7d` | `-22.429` | `-20.271` | `-12.849` |
| `Bits 8-9` | `>> 8` | `astro_moon_ra_app_min_shift_m7d` | `105.81` | `158.4` | `164.02` |
| `Bits 10-11` | `>> 10` | `astro_moon_dec_app_min_shift_m7d` | `-22.514` | `-20.365` | `-12.778` |
| `Bits 12-13` | `>> 12` | `astro_moon_azim_min_shift_m7d` | `61.482` | `204.29` | `204.29` |
| `Bits 14-15` | `>> 14` | `astro_moon_elev_min_shift_m7d` | `-14.768` | `10.839` | `12.366` |

### Container: `packed_astro_container_102` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_app_mag_min_shift_m7d` | `-11.243` | `-11.172` | `-10.822` |
| `Bits 2-3` | `>> 2` | `astro_moon_surf_bright_min_shift_m7d` | `4.5435` | `4.551` | `4.7992` |
| `Bits 4-5` | `>> 4` | `astro_moon_dist_min_shift_m7d` | `0.0024234` | `0.0025734` | `0.0025744` |
| `Bits 6-7` | `>> 6` | `astro_moon_dist_rate_min_shift_m7d` | `-0.26533` | `0.067918` | `0.067919` |
| `Bits 8-9` | `>> 8` | `astro_moon_helio_dist_min_shift_m7d` | `0.98196` | `0.98199` | `0.98578` |
| `Bits 10-11` | `>> 10` | `astro_moon_helio_dist_rate_min_shift_m7d` | `-0.87805` | `-0.6153` | `-0.23252` |
| `Bits 12-13` | `>> 12` | `astro_moon_phase_angle_min_shift_m7d` | `54.947` | `55.416` | `68.545` |
| `Bits 14-15` | `>> 14` | `astro_moon_elong_min_shift_m7d` | `34.314` | `57.755` | `57.755` |

### Container: `packed_astro_container_103` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_illum_frac_min_shift_m7d` | `9.1701` | `23.414` | `23.414` |
| `Bits 2-3` | `>> 2` | `astro_mars_ra_icrf_min_shift_m7d` | `266.7` | `275.27` | `299.62` |
| `Bits 4-5` | `>> 4` | `astro_mars_dec_icrf_min_shift_m7d` | `-24.038` | `-23.975` | `-21.566` |
| `Bits 6-7` | `>> 6` | `astro_mars_ra_app_min_shift_m7d` | `267.05` | `275.62` | `299.96` |
| `Bits 8-9` | `>> 8` | `astro_mars_dec_app_min_shift_m7d` | `-24.036` | `-23.964` | `-21.502` |
| `Bits 10-11` | `>> 10` | `astro_mars_azim_min_shift_m7d` | `155.27` | `156.94` | `160.96` |
| `Bits 12-13` | `>> 12` | `astro_mars_elev_min_shift_m7d` | `23.091` | `23.65` | `27.394` |
| `Bits 14-15` | `>> 14` | `astro_mars_app_mag_min_shift_m7d` | `1.2617` | `1.3525` | `1.411` |

### Container: `packed_astro_container_104` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_surf_bright_min_shift_m7d` | `4.054` | `4.085` | `4.085` |
| `Bits 2-3` | `>> 2` | `astro_mars_dist_min_shift_m7d` | `2.2623` | `2.3702` | `2.4051` |
| `Bits 4-5` | `>> 4` | `astro_mars_dist_rate_min_shift_m7d` | `-6.6607` | `-6.0413` | `-5.6567` |
| `Bits 6-7` | `>> 6` | `astro_mars_helio_dist_min_shift_m7d` | `1.4267` | `1.4601` | `1.4731` |
| `Bits 8-9` | `>> 8` | `astro_mars_helio_dist_rate_min_shift_m7d` | `-2.208` | `-2.1455` | `-1.8412` |
| `Bits 10-11` | `>> 10` | `astro_mars_phase_angle_min_shift_m7d` | `8.4225` | `10.394` | `15.804` |
| `Bits 12-13` | `>> 12` | `astro_mars_elong_min_shift_m7d` | `12.743` | `15.616` | `23.297` |
| `Bits 14-15` | `>> 14` | `astro_mars_illum_frac_min_shift_m7d` | `9.1701` | `23.414` | `23.414` |

### Container: `packed_astro_container_105` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_ra_icrf_min_shift_m7d` | `33.362` | `33.579` | `35.989` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_dec_icrf_min_shift_m7d` | `12.151` | `12.282` | `13.242` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_ra_app_min_shift_m7d` | `33.686` | `33.903` | `36.314` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_dec_app_min_shift_m7d` | `12.264` | `12.394` | `13.351` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_azim_min_shift_m7d` | `33.512` | `43.299` | `63.943` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_elev_min_shift_m7d` | `-32.48` | `-27.4` | `-9.7754` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_app_mag_min_shift_m7d` | `-2.589` | `-2.503` | `-2.2872` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_surf_bright_min_shift_m7d` | `5.357` | `5.357` | `5.366` |

### Container: `packed_astro_container_106` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_dist_min_shift_m7d` | `4.4815` | `4.6407` | `5.1148` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_dist_rate_min_shift_m7d` | `25.054` | `25.054` | `26.22` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_helio_dist_min_shift_m7d` | `4.9849` | `4.9869` | `4.993` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_helio_dist_rate_min_shift_m7d` | `0.32902` | `0.33788` | `0.36269` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_phase_angle_min_shift_m7d` | `10.248` | `10.248` | `10.769` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_elong_min_shift_m7d` | `72.126` | `99.263` | `109.5` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_illum_frac_min_shift_m7d` | `9.1701` | `23.414` | `23.414` |
| `Bits 14-15` | `>> 14` | `astro_saturn_ra_icrf_min_shift_m7d` | `335.46` | `336.41` | `339.51` |

### Container: `packed_astro_container_107` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_dec_icrf_min_shift_m7d` | `-11.958` | `-11.587` | `-10.365` |
| `Bits 2-3` | `>> 2` | `astro_saturn_ra_app_min_shift_m7d` | `335.78` | `336.72` | `339.82` |
| `Bits 4-5` | `>> 4` | `astro_saturn_dec_app_min_shift_m7d` | `-11.839` | `-11.467` | `-10.242` |
| `Bits 6-7` | `>> 6` | `astro_saturn_azim_min_shift_m7d` | `97.076` | `102.55` | `119.16` |
| `Bits 8-9` | `>> 8` | `astro_saturn_elev_min_shift_m7d` | `-10.178` | `-2.7274` | `17.167` |
| `Bits 10-11` | `>> 10` | `astro_saturn_app_mag_min_shift_m7d` | `0.955` | `0.9595` | `0.98125` |
| `Bits 12-13` | `>> 12` | `astro_saturn_surf_bright_min_shift_m7d` | `6.6893` | `6.714` | `6.723` |
| `Bits 14-15` | `>> 14` | `astro_saturn_dist_min_shift_m7d` | `10.295` | `10.423` | `10.665` |

### Container: `packed_astro_container_108` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_dist_rate_min_shift_m7d` | `5.2074` | `17.259` | `20.847` |
| `Bits 2-3` | `>> 2` | `astro_saturn_helio_dist_min_shift_m7d` | `9.7247` | `9.7332` | `9.7361` |
| `Bits 4-5` | `>> 4` | `astro_saturn_helio_dist_rate_min_shift_m7d` | `-0.49543` | `-0.49132` | `-0.49018` |
| `Bits 6-7` | `>> 6` | `astro_saturn_phase_angle_min_shift_m7d` | `1.1534` | `3.5667` | `4.2833` |
| `Bits 8-9` | `>> 8` | `astro_saturn_elong_min_shift_m7d` | `11.418` | `38.024` | `47.66` |
| `Bits 10-11` | `>> 10` | `astro_saturn_illum_frac_min_shift_m7d` | `9.1701` | `23.414` | `23.414` |
| `Bits 12-13` | `>> 12` | `astro_mercury_ra_icrf_min_shift_m7d` | `261.33` | `262.5` | `299.01` |
| `Bits 14-15` | `>> 14` | `astro_mercury_dec_icrf_min_shift_m7d` | `-21.473` | `-20.842` | `-19.815` |

### Container: `packed_astro_container_109` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mercury_ra_app_min_shift_m7d` | `261.68` | `262.85` | `299.36` |
| `Bits 2-3` | `>> 2` | `astro_mercury_dec_app_min_shift_m7d` | `-21.427` | `-20.86` | `-19.753` |
| `Bits 4-5` | `>> 4` | `astro_mercury_azim_min_shift_m7d` | `144.56` | `159.01` | `159.01` |
| `Bits 6-7` | `>> 6` | `astro_mercury_elev_min_shift_m7d` | `26.202` | `28.285` | `28.285` |
| `Bits 8-9` | `>> 8` | `astro_mercury_app_mag_min_shift_m7d` | `-0.81725` | `-0.221` | `-0.048` |
| `Bits 10-11` | `>> 10` | `astro_mercury_surf_bright_min_shift_m7d` | `2.3178` | `3.0975` | `3.281` |
| `Bits 12-13` | `>> 12` | `astro_mercury_dist_min_shift_m7d` | `0.77753` | `0.98942` | `1.2588` |
| `Bits 14-15` | `>> 14` | `astro_mercury_dist_rate_min_shift_m7d` | `4.1234` | `28.759` | `32.986` |

### Container: `packed_astro_container_110` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mercury_helio_dist_min_shift_m7d` | `0.34246` | `0.34246` | `0.41513` |
| `Bits 2-3` | `>> 2` | `astro_mercury_helio_dist_rate_min_shift_m7d` | `-5.9662` | `7.2761` | `9.213` |
| `Bits 4-5` | `>> 4` | `astro_mercury_phase_angle_min_shift_m7d` | `30.144` | `63.65` | `91.21` |
| `Bits 6-7` | `>> 6` | `astro_mercury_elong_min_shift_m7d` | `11.217` | `18.011` | `18.011` |
| `Bits 8-9` | `>> 8` | `astro_mercury_illum_frac_min_shift_m7d` | `9.1701` | `23.414` | `23.414` |
| `Bits 10-11` | `>> 10` | `astro_venus_ra_icrf_min_shift_m7d` | `240.61` | `254.04` | `293.44` |
| `Bits 12-13` | `>> 12` | `astro_venus_dec_icrf_min_shift_m7d` | `-21.386` | `-20.155` | `-20.155` |
| `Bits 14-15` | `>> 14` | `astro_venus_ra_app_min_shift_m7d` | `240.95` | `254.39` | `293.79` |

### Container: `packed_astro_container_111` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_dec_app_min_shift_m7d` | `-21.396` | `-20.206` | `-20.206` |
| `Bits 2-3` | `>> 2` | `astro_venus_azim_min_shift_m7d` | `164.98` | `175.94` | `179.46` |
| `Bits 4-5` | `>> 4` | `astro_venus_elev_min_shift_m7d` | `29.129` | `31.042` | `31.042` |
| `Bits 6-7` | `>> 6` | `astro_venus_app_mag_min_shift_m7d` | `-4.039` | `-4.0015` | `-3.9235` |
| `Bits 8-9` | `>> 8` | `astro_venus_surf_bright_min_shift_m7d` | `1.0168` | `1.1175` | `1.155` |
| `Bits 10-11` | `>> 10` | `astro_venus_dist_min_shift_m7d` | `1.1819` | `1.2461` | `1.4102` |
| `Bits 12-13` | `>> 12` | `astro_venus_dist_rate_min_shift_m7d` | `8.315` | `9.9998` | `10.575` |
| `Bits 14-15` | `>> 14` | `astro_venus_helio_dist_min_shift_m7d` | `0.72045` | `0.72173` | `0.72564` |

### Container: `packed_astro_container_112` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_helio_dist_rate_min_shift_m7d` | `0.18157` | `0.19155` | `0.2015` |
| `Bits 2-3` | `>> 2` | `astro_venus_phase_angle_min_shift_m7d` | `39.01` | `49.757` | `53.769` |
| `Bits 4-5` | `>> 4` | `astro_venus_elong_min_shift_m7d` | `27.565` | `34.088` | `36.267` |
| `Bits 6-7` | `>> 6` | `astro_venus_illum_frac_min_shift_m7d` | `9.1701` | `23.414` | `23.414` |
| `Bits 8-9` | `>> 8` | `astro_sun_ra_icrf_max_shift_m7d` | `287.17` | `298.53` | `328.93` |
| `Bits 10-11` | `>> 10` | `astro_sun_dec_icrf_max_shift_m7d` | `-22.5` | `-20.808` | `-12.593` |
| `Bits 12-13` | `>> 12` | `astro_sun_ra_app_max_shift_m7d` | `287.52` | `298.88` | `329.24` |
| `Bits 14-15` | `>> 14` | `astro_sun_dec_app_max_shift_m7d` | `-22.463` | `-20.747` | `-12.482` |

### Container: `packed_astro_container_113` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_azim_max_shift_m7d` | `135.3` | `140.98` | `142.63` |
| `Bits 2-3` | `>> 2` | `astro_sun_elev_max_shift_m7d` | `18.499` | `19.459` | `25.781` |
| `Bits 4-5` | `>> 4` | `astro_sun_app_mag_max_shift_m7d` | `-26.779` | `-26.777` | `-26.769` |
| `Bits 6-7` | `>> 6` | `astro_sun_dist_max_shift_m7d` | `0.98333` | `0.98378` | `0.9878` |
| `Bits 8-9` | `>> 8` | `astro_sun_dist_rate_max_shift_m7d` | `-0.17915` | `-0.11212` | `0.099156` |
| `Bits 10-11` | `>> 10` | `astro_sun_illum_frac_max_shift_m7d` | `68.108` | `78.383` | `78.715` |
| `Bits 12-13` | `>> 12` | `astro_moon_ra_icrf_max_shift_m7d` | `224.73` | `224.73` | `309.32` |
| `Bits 14-15` | `>> 14` | `astro_moon_dec_icrf_max_shift_m7d` | `9.3134` | `12.219` | `20.972` |

### Container: `packed_astro_container_114` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_ra_app_max_shift_m7d` | `225.06` | `225.06` | `309.65` |
| `Bits 2-3` | `>> 2` | `astro_moon_dec_app_max_shift_m7d` | `9.1843` | `12.095` | `20.988` |
| `Bits 4-5` | `>> 4` | `astro_moon_azim_max_shift_m7d` | `211.46` | `275.69` | `275.69` |
| `Bits 6-7` | `>> 6` | `astro_moon_elev_max_shift_m7d` | `12.493` | `27.076` | `27.076` |
| `Bits 8-9` | `>> 8` | `astro_moon_app_mag_max_shift_m7d` | `-8.692` | `-8.692` | `-7.2805` |
| `Bits 10-11` | `>> 10` | `astro_moon_surf_bright_max_shift_m7d` | `5.819` | `5.819` | `6.249` |
| `Bits 12-13` | `>> 12` | `astro_moon_dist_max_shift_m7d` | `0.0026005` | `0.0026954` | `0.0026964` |
| `Bits 14-15` | `>> 14` | `astro_moon_dist_rate_max_shift_m7d` | `0.10523` | `0.33942` | `0.35466` |

### Container: `packed_astro_container_115` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_helio_dist_max_shift_m7d` | `0.98483` | `0.98483` | `0.98847` |
| `Bits 2-3` | `>> 2` | `astro_moon_helio_dist_rate_max_shift_m7d` | `-0.71371` | `-0.065935` | `0.76477` |
| `Bits 4-5` | `>> 4` | `astro_moon_phase_angle_max_shift_m7d` | `122.12` | `122.12` | `145.61` |
| `Bits 6-7` | `>> 6` | `astro_moon_elong_max_shift_m7d` | `111.31` | `124.46` | `124.93` |
| `Bits 8-9` | `>> 8` | `astro_moon_illum_frac_max_shift_m7d` | `68.108` | `78.383` | `78.715` |
| `Bits 10-11` | `>> 10` | `astro_mars_ra_icrf_max_shift_m7d` | `271.58` | `280.19` | `304.45` |
| `Bits 12-13` | `>> 12` | `astro_mars_dec_icrf_max_shift_m7d` | `-23.953` | `-23.79` | `-20.641` |
| `Bits 14-15` | `>> 14` | `astro_mars_ra_app_max_shift_m7d` | `271.94` | `280.55` | `304.8` |

### Container: `packed_astro_container_116` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_dec_app_max_shift_m7d` | `-23.962` | `-23.768` | `-20.568` |
| `Bits 2-3` | `>> 2` | `astro_mars_azim_max_shift_m7d` | `156.26` | `157.8` | `161.78` |
| `Bits 4-5` | `>> 4` | `astro_mars_elev_max_shift_m7d` | `23.352` | `24.132` | `28.563` |
| `Bits 6-7` | `>> 6` | `astro_mars_app_mag_max_shift_m7d` | `1.3153` | `1.4095` | `1.44` |
| `Bits 8-9` | `>> 8` | `astro_mars_surf_bright_max_shift_m7d` | `4.1013` | `4.112` | `4.112` |
| `Bits 10-11` | `>> 10` | `astro_mars_dist_max_shift_m7d` | `2.2849` | `2.3904` | `2.4238` |
| `Bits 12-13` | `>> 12` | `astro_mars_dist_rate_max_shift_m7d` | `-6.5817` | `-5.8327` | `-5.4023` |
| `Bits 14-15` | `>> 14` | `astro_mars_helio_dist_max_shift_m7d` | `1.4329` | `1.4675` | `1.4807` |

### Container: `packed_astro_container_117` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_helio_dist_rate_max_shift_m7d` | `-2.176` | `-2.0997` | `-1.7565` |
| `Bits 2-3` | `>> 2` | `astro_mars_phase_angle_max_shift_m7d` | `9.5533` | `11.509` | `16.856` |
| `Bits 4-5` | `>> 4` | `astro_mars_elong_max_shift_m7d` | `14.397` | `17.224` | `24.757` |
| `Bits 6-7` | `>> 6` | `astro_mars_illum_frac_max_shift_m7d` | `68.108` | `78.383` | `78.715` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_ra_icrf_max_shift_m7d` | `33.429` | `33.853` | `36.768` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_dec_icrf_max_shift_m7d` | `12.207` | `12.408` | `13.525` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_ra_app_max_shift_m7d` | `33.753` | `34.177` | `37.094` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_dec_app_max_shift_m7d` | `12.319` | `12.52` | `13.633` |

### Container: `packed_astro_container_118` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_azim_max_shift_m7d` | `39.357` | `48.242` | `67.183` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_elev_max_shift_m7d` | `-29.722` | `-24.151` | `-5.94` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_app_mag_max_shift_m7d` | `-2.539` | `-2.4555` | `-2.2513` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_surf_bright_max_shift_m7d` | `5.362` | `5.362` | `5.3685` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_dist_max_shift_m7d` | `4.5709` | `4.7351` | `5.2081` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_dist_rate_max_shift_m7d` | `26.135` | `26.135` | `26.954` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_helio_dist_max_shift_m7d` | `4.986` | `4.9881` | `4.9942` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_helio_dist_rate_max_shift_m7d` | `0.33541` | `0.34494` | `0.36919` |

### Container: `packed_astro_container_119` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_phase_angle_max_shift_m7d` | `10.71` | `10.71` | `11.081` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_elong_max_shift_m7d` | `77.385` | `105.08` | `115.54` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_illum_frac_max_shift_m7d` | `68.108` | `78.383` | `78.715` |
| `Bits 6-7` | `>> 6` | `astro_saturn_ra_icrf_max_shift_m7d` | `335.99` | `336.99` | `340.19` |
| `Bits 8-9` | `>> 8` | `astro_saturn_dec_icrf_max_shift_m7d` | `-11.752` | `-11.359` | `-10.098` |
| `Bits 10-11` | `>> 10` | `astro_saturn_ra_app_max_shift_m7d` | `336.3` | `337.3` | `340.5` |
| `Bits 12-13` | `>> 12` | `astro_saturn_dec_app_max_shift_m7d` | `-11.633` | `-11.238` | `-9.9751` |
| `Bits 14-15` | `>> 14` | `astro_saturn_azim_max_shift_m7d` | `100.2` | `105.71` | `122.98` |

### Container: `packed_astro_container_120` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_elev_max_shift_m7d` | `-5.8934` | `1.4507` | `20.86` |
| `Bits 2-3` | `>> 2` | `astro_saturn_app_mag_max_shift_m7d` | `0.967` | `0.9725` | `0.98975` |
| `Bits 4-5` | `>> 4` | `astro_saturn_surf_bright_max_shift_m7d` | `6.6978` | `6.7225` | `6.727` |
| `Bits 6-7` | `>> 6` | `astro_saturn_dist_max_shift_m7d` | `10.371` | `10.488` | `10.689` |
| `Bits 8-9` | `>> 8` | `astro_saturn_dist_rate_max_shift_m7d` | `7.8031` | `19.354` | `22.619` |
| `Bits 10-11` | `>> 10` | `astro_saturn_helio_dist_max_shift_m7d` | `9.7264` | `9.7349` | `9.7378` |
| `Bits 12-13` | `>> 12` | `astro_saturn_helio_dist_rate_max_shift_m7d` | `-0.49337` | `-0.49039` | `-0.48811` |
| `Bits 14-15` | `>> 14` | `astro_saturn_phase_angle_max_shift_m7d` | `1.6737` | `3.9851` | `4.6406` |

### Container: `packed_astro_container_121` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_elong_max_shift_m7d` | `16.667` | `43.52` | `53.221` |
| `Bits 2-3` | `>> 2` | `astro_saturn_illum_frac_max_shift_m7d` | `68.108` | `78.383` | `78.715` |
| `Bits 4-5` | `>> 4` | `astro_mercury_ra_icrf_max_shift_m7d` | `262.99` | `266.25` | `308.83` |
| `Bits 6-7` | `>> 6` | `astro_mercury_dec_icrf_max_shift_m7d` | `-20.135` | `-20.135` | `-17.477` |
| `Bits 8-9` | `>> 8` | `astro_mercury_ra_app_max_shift_m7d` | `263.34` | `266.6` | `309.17` |
| `Bits 10-11` | `>> 10` | `astro_mercury_dec_app_max_shift_m7d` | `-20.156` | `-20.156` | `-17.378` |
| `Bits 12-13` | `>> 12` | `astro_mercury_azim_max_shift_m7d` | `149.71` | `163.7` | `163.7` |
| `Bits 14-15` | `>> 14` | `astro_mercury_elev_max_shift_m7d` | `27.212` | `28.79` | `28.79` |

### Container: `packed_astro_container_122` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mercury_app_mag_max_shift_m7d` | `-0.564` | `-0.146` | `0.508` |
| `Bits 2-3` | `>> 2` | `astro_mercury_surf_bright_max_shift_m7d` | `2.5753` | `3.199` | `3.51` |
| `Bits 4-5` | `>> 4` | `astro_mercury_dist_max_shift_m7d` | `0.9005` | `1.0977` | `1.3316` |
| `Bits 6-7` | `>> 6` | `astro_mercury_dist_rate_max_shift_m7d` | `9.2332` | `33.358` | `36.196` |
| `Bits 8-9` | `>> 8` | `astro_mercury_helio_dist_max_shift_m7d` | `0.37652` | `0.37652` | `0.44104` |
| `Bits 10-11` | `>> 10` | `astro_mercury_helio_dist_rate_max_shift_m7d` | `-1.0225` | `9.1165` | `10.059` |
| `Bits 12-13` | `>> 12` | `astro_mercury_phase_angle_max_shift_m7d` | `38` | `78.058` | `117.4` |
| `Bits 14-15` | `>> 14` | `astro_mercury_elong_max_shift_m7d` | `15.747` | `22.508` | `22.508` |

### Container: `packed_astro_container_123` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mercury_illum_frac_max_shift_m7d` | `68.108` | `78.383` | `78.715` |
| `Bits 2-3` | `>> 2` | `astro_venus_ra_icrf_max_shift_m7d` | `248.21` | `261.89` | `301.3` |
| `Bits 4-5` | `>> 4` | `astro_venus_dec_icrf_max_shift_m7d` | `-20.288` | `-18.705` | `-18.705` |
| `Bits 6-7` | `>> 6` | `astro_venus_ra_app_max_shift_m7d` | `248.56` | `262.24` | `301.65` |
| `Bits 8-9` | `>> 8` | `astro_venus_dec_app_max_shift_m7d` | `-20.306` | `-18.771` | `-18.771` |
| `Bits 10-11` | `>> 10` | `astro_venus_azim_max_shift_m7d` | `167.27` | `177.97` | `181.35` |
| `Bits 12-13` | `>> 12` | `astro_venus_elev_max_shift_m7d` | `30.001` | `32.468` | `32.468` |
| `Bits 14-15` | `>> 14` | `astro_venus_app_mag_max_shift_m7d` | `-4.017` | `-3.9825` | `-3.9122` |

### Container: `packed_astro_container_124` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_surf_bright_max_shift_m7d` | `1.0368` | `1.1385` | `1.176` |
| `Bits 2-3` | `>> 2` | `astro_venus_dist_max_shift_m7d` | `1.2191` | `1.2813` | `1.4399` |
| `Bits 4-5` | `>> 4` | `astro_venus_dist_rate_max_shift_m7d` | `8.666` | `10.327` | `10.893` |
| `Bits 6-7` | `>> 6` | `astro_venus_helio_dist_max_shift_m7d` | `0.72115` | `0.72252` | `0.72632` |
| `Bits 8-9` | `>> 8` | `astro_venus_helio_dist_rate_max_shift_m7d` | `0.20412` | `0.21206` | `0.21915` |
| `Bits 10-11` | `>> 10` | `astro_venus_phase_angle_max_shift_m7d` | `41.117` | `52.037` | `56.135` |
| `Bits 12-13` | `>> 12` | `astro_venus_elong_max_shift_m7d` | `28.916` | `35.34` | `37.471` |
| `Bits 14-15` | `>> 14` | `astro_venus_illum_frac_max_shift_m7d` | `68.108` | `78.383` | `78.715` |

### Container: `packed_astro_container_125` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_ra_icrf_mean_shift_m7d` | `283.87` | `295.31` | `325.99` |
| `Bits 2-3` | `>> 2` | `astro_sun_dec_icrf_mean_shift_m7d` | `-22.81` | `-21.343` | `-13.601` |
| `Bits 4-5` | `>> 4` | `astro_sun_ra_app_mean_shift_m7d` | `284.23` | `295.65` | `326.31` |
| `Bits 6-7` | `>> 6` | `astro_sun_dec_app_mean_shift_m7d` | `-22.781` | `-21.289` | `-13.493` |
| `Bits 8-9` | `>> 8` | `astro_sun_azim_mean_shift_m7d` | `134.68` | `140.46` | `142.19` |
| `Bits 10-11` | `>> 10` | `astro_sun_elev_mean_shift_m7d` | `18.391` | `19.133` | `24.94` |
| `Bits 12-13` | `>> 12` | `astro_sun_app_mag_mean_shift_m7d` | `-26.779` | `-26.778` | `-26.77` |
| `Bits 14-15` | `>> 14` | `astro_sun_dist_mean_shift_m7d` | `0.98331` | `0.98362` | `0.98725` |

### Container: `packed_astro_container_126` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_dist_rate_mean_shift_m7d` | `-0.20272` | `-0.13278` | `0.083222` |
| `Bits 2-3` | `>> 2` | `astro_sun_illum_frac_mean_shift_m7d` | `37.657` | `51.384` | `51.384` |
| `Bits 4-5` | `>> 4` | `astro_moon_ra_icrf_mean_shift_m7d` | `142.87` | `190.62` | `196.14` |
| `Bits 6-7` | `>> 6` | `astro_moon_dec_icrf_mean_shift_m7d` | `-6.9781` | `-4.1583` | `5.1481` |
| `Bits 8-9` | `>> 8` | `astro_moon_ra_app_mean_shift_m7d` | `143.22` | `190.94` | `196.46` |
| `Bits 10-11` | `>> 10` | `astro_moon_dec_app_mean_shift_m7d` | `-7.0979` | `-4.28` | `5.2007` |
| `Bits 12-13` | `>> 12` | `astro_moon_azim_mean_shift_m7d` | `169.49` | `241.51` | `241.51` |
| `Bits 14-15` | `>> 14` | `astro_moon_elev_mean_shift_m7d` | `-1.061` | `20.913` | `21.883` |

### Container: `packed_astro_container_127` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_app_mag_mean_shift_m7d` | `-10.055` | `-10.055` | `-9.3457` |
| `Bits 2-3` | `>> 2` | `astro_moon_surf_bright_mean_shift_m7d` | `5.163` | `5.163` | `5.5091` |
| `Bits 4-5` | `>> 4` | `astro_moon_dist_mean_shift_m7d` | `0.0024988` | `0.0026517` | `0.0026527` |
| `Bits 6-7` | `>> 6` | `astro_moon_dist_rate_mean_shift_m7d` | `-0.099321` | `0.23706` | `0.23706` |
| `Bits 8-9` | `>> 8` | `astro_moon_helio_dist_mean_shift_m7d` | `0.98339` | `0.98356` | `0.9868` |
| `Bits 10-11` | `>> 10` | `astro_moon_helio_dist_rate_mean_shift_m7d` | `-0.81159` | `-0.37403` | `0.25273` |
| `Bits 12-13` | `>> 12` | `astro_moon_phase_angle_mean_shift_m7d` | `88.31` | `88.31` | `106.09` |
| `Bits 14-15` | `>> 14` | `astro_moon_elong_mean_shift_m7d` | `73.784` | `91.547` | `91.547` |

### Container: `packed_astro_container_128` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_illum_frac_mean_shift_m7d` | `37.657` | `51.384` | `51.384` |
| `Bits 2-3` | `>> 2` | `astro_mars_ra_icrf_mean_shift_m7d` | `269.14` | `277.73` | `302.04` |
| `Bits 4-5` | `>> 4` | `astro_mars_dec_icrf_mean_shift_m7d` | `-24.006` | `-23.893` | `-21.113` |
| `Bits 6-7` | `>> 6` | `astro_mars_ra_app_mean_shift_m7d` | `269.49` | `278.09` | `302.38` |
| `Bits 8-9` | `>> 8` | `astro_mars_dec_app_mean_shift_m7d` | `-24.01` | `-23.877` | `-21.045` |
| `Bits 10-11` | `>> 10` | `astro_mars_azim_mean_shift_m7d` | `155.77` | `157.37` | `161.37` |
| `Bits 12-13` | `>> 12` | `astro_mars_elev_mean_shift_m7d` | `23.213` | `23.882` | `27.969` |
| `Bits 14-15` | `>> 14` | `astro_mars_app_mag_mean_shift_m7d` | `1.2876` | `1.3837` | `1.426` |

### Container: `packed_astro_container_129` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_surf_bright_mean_shift_m7d` | `4.0744` | `4.1006` | `4.1006` |
| `Bits 2-3` | `>> 2` | `astro_mars_dist_mean_shift_m7d` | `2.2736` | `2.3803` | `2.4145` |
| `Bits 4-5` | `>> 4` | `astro_mars_dist_rate_mean_shift_m7d` | `-6.6238` | `-5.9397` | `-5.5303` |
| `Bits 6-7` | `>> 6` | `astro_mars_helio_dist_mean_shift_m7d` | `1.4298` | `1.4638` | `1.4769` |
| `Bits 8-9` | `>> 8` | `astro_mars_helio_dist_rate_mean_shift_m7d` | `-2.1925` | `-2.1231` | `-1.7994` |
| `Bits 10-11` | `>> 10` | `astro_mars_phase_angle_mean_shift_m7d` | `8.9884` | `10.952` | `16.331` |
| `Bits 12-13` | `>> 12` | `astro_mars_elong_mean_shift_m7d` | `13.572` | `16.422` | `24.029` |
| `Bits 14-15` | `>> 14` | `astro_mars_illum_frac_mean_shift_m7d` | `37.657` | `51.384` | `51.384` |

### Container: `packed_astro_container_130` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_ra_icrf_mean_shift_m7d` | `33.387` | `33.708` | `36.372` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_dec_icrf_mean_shift_m7d` | `12.176` | `12.342` | `13.382` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_ra_app_mean_shift_m7d` | `33.711` | `34.032` | `36.698` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_dec_app_mean_shift_m7d` | `12.289` | `12.454` | `13.49` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_azim_mean_shift_m7d` | `36.473` | `45.804` | `65.578` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_elev_mean_shift_m7d` | `-31.125` | `-25.791` | `-7.8607` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_app_mag_mean_shift_m7d` | `-2.564` | `-2.4792` | `-2.269` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_surf_bright_mean_shift_m7d` | `5.3599` | `5.3599` | `5.3674` |

### Container: `packed_astro_container_131` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_dist_mean_shift_m7d` | `4.526` | `4.6877` | `5.1616` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_dist_rate_mean_shift_m7d` | `25.616` | `25.616` | `26.608` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_helio_dist_mean_shift_m7d` | `4.9855` | `4.9875` | `4.9936` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_helio_dist_rate_mean_shift_m7d` | `0.33256` | `0.34145` | `0.36589` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_phase_angle_mean_shift_m7d` | `10.488` | `10.488` | `10.933` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_elong_mean_shift_m7d` | `74.748` | `102.16` | `112.51` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_illum_frac_mean_shift_m7d` | `37.657` | `51.384` | `51.384` |
| `Bits 14-15` | `>> 14` | `astro_saturn_ra_icrf_mean_shift_m7d` | `335.72` | `336.69` | `339.85` |

### Container: `packed_astro_container_132` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_dec_icrf_mean_shift_m7d` | `-11.856` | `-11.473` | `-10.232` |
| `Bits 2-3` | `>> 2` | `astro_saturn_ra_app_mean_shift_m7d` | `336.04` | `337.01` | `340.16` |
| `Bits 4-5` | `>> 4` | `astro_saturn_dec_app_mean_shift_m7d` | `-11.737` | `-11.353` | `-10.109` |
| `Bits 6-7` | `>> 6` | `astro_saturn_azim_mean_shift_m7d` | `98.639` | `104.12` | `121.05` |
| `Bits 8-9` | `>> 8` | `astro_saturn_elev_mean_shift_m7d` | `-8.0321` | `-0.63362` | `19.023` |
| `Bits 10-11` | `>> 10` | `astro_saturn_app_mag_mean_shift_m7d` | `0.961` | `0.967` | `0.98746` |
| `Bits 12-13` | `>> 12` | `astro_saturn_surf_bright_mean_shift_m7d` | `6.6928` | `6.7169` | `6.7253` |
| `Bits 14-15` | `>> 14` | `astro_saturn_dist_mean_shift_m7d` | `10.333` | `10.456` | `10.678` |

### Container: `packed_astro_container_133` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_dist_rate_mean_shift_m7d` | `6.5075` | `18.318` | `21.747` |
| `Bits 2-3` | `>> 2` | `astro_saturn_helio_dist_mean_shift_m7d` | `9.7256` | `9.734` | `9.737` |
| `Bits 4-5` | `>> 4` | `astro_saturn_helio_dist_rate_mean_shift_m7d` | `-0.4945` | `-0.49088` | `-0.48885` |
| `Bits 6-7` | `>> 6` | `astro_saturn_phase_angle_mean_shift_m7d` | `1.4141` | `3.778` | `4.4646` |
| `Bits 8-9` | `>> 8` | `astro_saturn_elong_mean_shift_m7d` | `14.041` | `40.769` | `50.438` |
| `Bits 10-11` | `>> 10` | `astro_saturn_illum_frac_mean_shift_m7d` | `37.657` | `51.384` | `51.384` |
| `Bits 12-13` | `>> 12` | `astro_mercury_ra_icrf_mean_shift_m7d` | `261.87` | `264.14` | `303.9` |
| `Bits 14-15` | `>> 14` | `astro_mercury_dec_icrf_mean_shift_m7d` | `-20.729` | `-20.437` | `-18.711` |

### Container: `packed_astro_container_134` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mercury_ra_app_mean_shift_m7d` | `262.22` | `264.49` | `304.25` |
| `Bits 2-3` | `>> 2` | `astro_mercury_dec_app_mean_shift_m7d` | `-20.677` | `-20.457` | `-18.644` |
| `Bits 4-5` | `>> 4` | `astro_mercury_azim_mean_shift_m7d` | `147.18` | `161.7` | `161.7` |
| `Bits 6-7` | `>> 6` | `astro_mercury_elev_mean_shift_m7d` | `26.693` | `28.644` | `28.644` |
| `Bits 8-9` | `>> 8` | `astro_mercury_app_mag_mean_shift_m7d` | `-0.68268` | `-0.18864` | `0.173` |
| `Bits 10-11` | `>> 10` | `astro_mercury_surf_bright_mean_shift_m7d` | `2.4533` | `3.1475` | `3.3753` |
| `Bits 12-13` | `>> 12` | `astro_mercury_dist_mean_shift_m7d` | `0.83832` | `1.0447` | `1.297` |
| `Bits 14-15` | `>> 14` | `astro_mercury_dist_rate_mean_shift_m7d` | `6.7198` | `31.154` | `35.248` |

### Container: `packed_astro_container_135` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mercury_helio_dist_mean_shift_m7d` | `0.3593` | `0.3593` | `0.42863` |
| `Bits 2-3` | `>> 2` | `astro_mercury_helio_dist_rate_mean_shift_m7d` | `-3.5241` | `8.2587` | `9.7955` |
| `Bits 4-5` | `>> 4` | `astro_mercury_phase_angle_mean_shift_m7d` | `34.314` | `70.535` | `103.62` |
| `Bits 6-7` | `>> 6` | `astro_mercury_elong_mean_shift_m7d` | `13.555` | `20.583` | `20.583` |
| `Bits 8-9` | `>> 8` | `astro_mercury_illum_frac_mean_shift_m7d` | `37.657` | `51.384` | `51.384` |
| `Bits 10-11` | `>> 10` | `astro_venus_ra_icrf_mean_shift_m7d` | `244.4` | `257.95` | `297.38` |
| `Bits 12-13` | `>> 12` | `astro_venus_dec_icrf_mean_shift_m7d` | `-20.861` | `-19.451` | `-19.451` |
| `Bits 14-15` | `>> 14` | `astro_venus_ra_app_mean_shift_m7d` | `244.74` | `258.31` | `297.73` |

### Container: `packed_astro_container_136` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_dec_app_mean_shift_m7d` | `-20.875` | `-19.51` | `-19.51` |
| `Bits 2-3` | `>> 2` | `astro_venus_azim_mean_shift_m7d` | `166.13` | `176.96` | `180.41` |
| `Bits 4-5` | `>> 4` | `astro_venus_elev_mean_shift_m7d` | `29.544` | `31.737` | `31.737` |
| `Bits 6-7` | `>> 6` | `astro_venus_app_mag_mean_shift_m7d` | `-4.0276` | `-3.9919` | `-3.9179` |
| `Bits 8-9` | `>> 8` | `astro_venus_surf_bright_mean_shift_m7d` | `1.027` | `1.1281` | `1.1654` |
| `Bits 10-11` | `>> 10` | `astro_venus_dist_mean_shift_m7d` | `1.2006` | `1.2638` | `1.4252` |
| `Bits 12-13` | `>> 12` | `astro_venus_dist_rate_mean_shift_m7d` | `8.4899` | `10.163` | `10.736` |
| `Bits 14-15` | `>> 14` | `astro_venus_helio_dist_mean_shift_m7d` | `0.7208` | `0.72212` | `0.72599` |

### Container: `packed_astro_container_137` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_helio_dist_rate_mean_shift_m7d` | `0.19322` | `0.20221` | `0.21074` |
| `Bits 2-3` | `>> 2` | `astro_venus_phase_angle_mean_shift_m7d` | `40.062` | `50.894` | `54.948` |
| `Bits 4-5` | `>> 4` | `astro_venus_elong_mean_shift_m7d` | `28.242` | `34.716` | `36.871` |
| `Bits 6-7` | `>> 6` | `astro_venus_illum_frac_mean_shift_m7d` | `37.657` | `51.384` | `51.384` |
| `Bits 8-9` | `>> 8` | `astro_sun_ra_icrf_median_shift_m7d` | `283.88` | `295.31` | `325.99` |
| `Bits 10-11` | `>> 10` | `astro_sun_dec_icrf_median_shift_m7d` | `-22.825` | `-21.357` | `-13.608` |
| `Bits 12-13` | `>> 12` | `astro_sun_ra_app_median_shift_m7d` | `284.23` | `295.66` | `326.31` |
| `Bits 14-15` | `>> 14` | `astro_sun_dec_app_median_shift_m7d` | `-22.796` | `-21.302` | `-13.5` |

### Container: `packed_astro_container_138` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_azim_median_shift_m7d` | `134.68` | `140.47` | `142.2` |
| `Bits 2-3` | `>> 2` | `astro_sun_elev_median_shift_m7d` | `18.377` | `19.12` | `24.931` |
| `Bits 4-5` | `>> 4` | `astro_sun_app_mag_median_shift_m7d` | `-26.779` | `-26.778` | `-26.77` |
| `Bits 6-7` | `>> 6` | `astro_sun_dist_median_shift_m7d` | `0.9833` | `0.98361` | `0.98724` |
| `Bits 8-9` | `>> 8` | `astro_sun_dist_rate_median_shift_m7d` | `-0.20189` | `-0.13316` | `0.082721` |
| `Bits 10-11` | `>> 10` | `astro_sun_illum_frac_median_shift_m7d` | `36.877` | `51.795` | `51.795` |
| `Bits 12-13` | `>> 12` | `astro_moon_ra_icrf_median_shift_m7d` | `143.72` | `190.01` | `195.33` |
| `Bits 14-15` | `>> 14` | `astro_moon_dec_icrf_median_shift_m7d` | `-7.2961` | `-4.247` | `6.0366` |

### Container: `packed_astro_container_139` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_ra_app_median_shift_m7d` | `144.07` | `190.31` | `195.65` |
| `Bits 2-3` | `>> 2` | `astro_moon_dec_app_median_shift_m7d` | `-7.4257` | `-4.3784` | `6.0959` |
| `Bits 4-5` | `>> 4` | `astro_moon_azim_median_shift_m7d` | `170.58` | `242.76` | `242.76` |
| `Bits 6-7` | `>> 6` | `astro_moon_elev_median_shift_m7d` | `-1.2434` | `22.264` | `23.611` |
| `Bits 8-9` | `>> 8` | `astro_moon_app_mag_median_shift_m7d` | `-10.151` | `-10.151` | `-9.5687` |
| `Bits 10-11` | `>> 10` | `astro_moon_surf_bright_median_shift_m7d` | `5.145` | `5.145` | `5.487` |
| `Bits 12-13` | `>> 12` | `astro_moon_dist_median_shift_m7d` | `0.0024946` | `0.0026659` | `0.0026669` |
| `Bits 14-15` | `>> 14` | `astro_moon_dist_rate_median_shift_m7d` | `-0.11223` | `0.25786` | `0.25786` |

### Container: `packed_astro_container_140` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_helio_dist_median_shift_m7d` | `0.98339` | `0.98355` | `0.98692` |
| `Bits 2-3` | `>> 2` | `astro_moon_helio_dist_rate_median_shift_m7d` | `-0.81843` | `-0.42658` | `0.25188` |
| `Bits 4-5` | `>> 4` | `astro_moon_phase_angle_median_shift_m7d` | `87.943` | `87.943` | `105.34` |
| `Bits 6-7` | `>> 6` | `astro_moon_elong_median_shift_m7d` | `74.523` | `91.901` | `91.902` |
| `Bits 8-9` | `>> 8` | `astro_moon_illum_frac_median_shift_m7d` | `36.877` | `51.795` | `51.795` |
| `Bits 10-11` | `>> 10` | `astro_mars_ra_icrf_median_shift_m7d` | `269.13` | `277.73` | `302.04` |
| `Bits 12-13` | `>> 12` | `astro_mars_dec_icrf_median_shift_m7d` | `-24.014` | `-23.902` | `-21.12` |
| `Bits 14-15` | `>> 14` | `astro_mars_ra_app_median_shift_m7d` | `269.49` | `278.08` | `302.39` |

### Container: `packed_astro_container_141` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_dec_app_median_shift_m7d` | `-24.018` | `-23.886` | `-21.052` |
| `Bits 2-3` | `>> 2` | `astro_mars_azim_median_shift_m7d` | `155.78` | `157.38` | `161.37` |
| `Bits 4-5` | `>> 4` | `astro_mars_elev_median_shift_m7d` | `23.207` | `23.874` | `27.961` |
| `Bits 6-7` | `>> 6` | `astro_mars_app_mag_median_shift_m7d` | `1.2843` | `1.383` | `1.429` |
| `Bits 8-9` | `>> 8` | `astro_mars_surf_bright_median_shift_m7d` | `4.0753` | `4.099` | `4.099` |
| `Bits 10-11` | `>> 10` | `astro_mars_dist_median_shift_m7d` | `2.2736` | `2.3804` | `2.4146` |
| `Bits 12-13` | `>> 12` | `astro_mars_dist_rate_median_shift_m7d` | `-6.6259` | `-5.9418` | `-5.531` |
| `Bits 14-15` | `>> 14` | `astro_mars_helio_dist_median_shift_m7d` | `1.4298` | `1.4638` | `1.4769` |

### Container: `packed_astro_container_142` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_helio_dist_rate_median_shift_m7d` | `-2.1929` | `-2.1236` | `-1.7998` |
| `Bits 2-3` | `>> 2` | `astro_mars_phase_angle_median_shift_m7d` | `8.9888` | `10.953` | `16.332` |
| `Bits 4-5` | `>> 4` | `astro_mars_elong_median_shift_m7d` | `13.573` | `16.424` | `24.031` |
| `Bits 6-7` | `>> 6` | `astro_mars_illum_frac_median_shift_m7d` | `36.877` | `51.795` | `51.795` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_ra_icrf_median_shift_m7d` | `33.381` | `33.701` | `36.368` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_dec_icrf_median_shift_m7d` | `12.174` | `12.34` | `13.381` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_ra_app_median_shift_m7d` | `33.704` | `34.025` | `36.693` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_dec_app_median_shift_m7d` | `12.286` | `12.452` | `13.489` |

### Container: `packed_astro_container_143` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_azim_median_shift_m7d` | `36.504` | `45.83` | `65.59` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_elev_median_shift_m7d` | `-31.145` | `-25.804` | `-7.8631` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_app_mag_median_shift_m7d` | `-2.564` | `-2.479` | `-2.2687` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_surf_bright_median_shift_m7d` | `5.36` | `5.36` | `5.3673` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_dist_median_shift_m7d` | `4.5258` | `4.6876` | `5.1617` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_dist_rate_median_shift_m7d` | `25.632` | `25.632` | `26.624` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_helio_dist_median_shift_m7d` | `4.9855` | `4.9875` | `4.9936` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_helio_dist_rate_median_shift_m7d` | `0.3332` | `0.34203` | `0.3657` |

### Container: `packed_astro_container_144` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_phase_angle_median_shift_m7d` | `10.495` | `10.495` | `10.939` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_elong_median_shift_m7d` | `74.742` | `102.16` | `112.5` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_illum_frac_median_shift_m7d` | `36.877` | `51.795` | `51.795` |
| `Bits 6-7` | `>> 6` | `astro_saturn_ra_icrf_median_shift_m7d` | `335.72` | `336.69` | `339.85` |
| `Bits 8-9` | `>> 8` | `astro_saturn_dec_icrf_median_shift_m7d` | `-11.857` | `-11.474` | `-10.232` |
| `Bits 10-11` | `>> 10` | `astro_saturn_ra_app_median_shift_m7d` | `336.03` | `337.01` | `340.16` |
| `Bits 12-13` | `>> 12` | `astro_saturn_dec_app_median_shift_m7d` | `-11.738` | `-11.354` | `-10.109` |
| `Bits 14-15` | `>> 14` | `astro_saturn_azim_median_shift_m7d` | `98.64` | `104.12` | `121.04` |

### Container: `packed_astro_container_145` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_elev_median_shift_m7d` | `-8.0292` | `-0.62984` | `19.031` |
| `Bits 2-3` | `>> 2` | `astro_saturn_app_mag_median_shift_m7d` | `0.961` | `0.967` | `0.9875` |
| `Bits 4-5` | `>> 4` | `astro_saturn_surf_bright_median_shift_m7d` | `6.693` | `6.717` | `6.725` |
| `Bits 6-7` | `>> 6` | `astro_saturn_dist_median_shift_m7d` | `10.334` | `10.457` | `10.678` |
| `Bits 8-9` | `>> 8` | `astro_saturn_dist_rate_median_shift_m7d` | `6.5093` | `18.326` | `21.759` |
| `Bits 10-11` | `>> 10` | `astro_saturn_helio_dist_median_shift_m7d` | `9.7256` | `9.734` | `9.737` |
| `Bits 12-13` | `>> 12` | `astro_saturn_helio_dist_rate_median_shift_m7d` | `-0.49447` | `-0.49088` | `-0.4886` |
| `Bits 14-15` | `>> 14` | `astro_saturn_phase_angle_median_shift_m7d` | `1.4145` | `3.7798` | `4.4668` |

### Container: `packed_astro_container_146` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_elong_median_shift_m7d` | `14.039` | `40.767` | `50.436` |
| `Bits 2-3` | `>> 2` | `astro_saturn_illum_frac_median_shift_m7d` | `36.877` | `51.795` | `51.795` |
| `Bits 4-5` | `>> 4` | `astro_mercury_ra_icrf_median_shift_m7d` | `261.59` | `263.93` | `303.89` |
| `Bits 6-7` | `>> 6` | `astro_mercury_dec_icrf_median_shift_m7d` | `-20.753` | `-20.396` | `-18.736` |
| `Bits 8-9` | `>> 8` | `astro_mercury_ra_app_median_shift_m7d` | `261.94` | `264.29` | `304.24` |
| `Bits 10-11` | `>> 10` | `astro_mercury_dec_app_median_shift_m7d` | `-20.7` | `-20.417` | `-18.668` |
| `Bits 12-13` | `>> 12` | `astro_mercury_azim_median_shift_m7d` | `147.22` | `161.97` | `161.97` |
| `Bits 14-15` | `>> 14` | `astro_mercury_elev_median_shift_m7d` | `26.681` | `28.695` | `28.695` |

### Container: `packed_astro_container_147` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mercury_app_mag_median_shift_m7d` | `-0.6765` | `-0.1925` | `0.129` |
| `Bits 2-3` | `>> 2` | `astro_mercury_surf_bright_median_shift_m7d` | `2.4585` | `3.147` | `3.36` |
| `Bits 4-5` | `>> 4` | `astro_mercury_dist_median_shift_m7d` | `0.83778` | `1.0456` | `1.299` |
| `Bits 6-7` | `>> 6` | `astro_mercury_dist_rate_median_shift_m7d` | `6.7528` | `31.228` | `35.828` |
| `Bits 8-9` | `>> 8` | `astro_mercury_helio_dist_median_shift_m7d` | `0.35915` | `0.35915` | `0.42906` |
| `Bits 10-11` | `>> 10` | `astro_mercury_helio_dist_rate_median_shift_m7d` | `-3.6146` | `8.3084` | `9.9345` |
| `Bits 12-13` | `>> 12` | `astro_mercury_phase_angle_median_shift_m7d` | `34.311` | `70.281` | `103.07` |
| `Bits 14-15` | `>> 14` | `astro_mercury_elong_median_shift_m7d` | `13.612` | `20.842` | `20.842` |

### Container: `packed_astro_container_148` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mercury_illum_frac_median_shift_m7d` | `36.877` | `51.795` | `51.795` |
| `Bits 2-3` | `>> 2` | `astro_venus_ra_icrf_median_shift_m7d` | `244.39` | `257.95` | `297.38` |
| `Bits 4-5` | `>> 4` | `astro_venus_dec_icrf_median_shift_m7d` | `-20.881` | `-19.468` | `-19.468` |
| `Bits 6-7` | `>> 6` | `astro_venus_ra_app_median_shift_m7d` | `244.73` | `258.3` | `297.73` |
| `Bits 8-9` | `>> 8` | `astro_venus_dec_app_median_shift_m7d` | `-20.895` | `-19.526` | `-19.526` |
| `Bits 10-11` | `>> 10` | `astro_venus_azim_median_shift_m7d` | `166.13` | `176.97` | `180.42` |
| `Bits 12-13` | `>> 12` | `astro_venus_elev_median_shift_m7d` | `29.527` | `31.723` | `31.723` |
| `Bits 14-15` | `>> 14` | `astro_venus_app_mag_median_shift_m7d` | `-4.027` | `-3.992` | `-3.9183` |

### Container: `packed_astro_container_149` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_surf_bright_median_shift_m7d` | `1.0267` | `1.128` | `1.165` |
| `Bits 2-3` | `>> 2` | `astro_venus_dist_median_shift_m7d` | `1.2006` | `1.2638` | `1.4252` |
| `Bits 4-5` | `>> 4` | `astro_venus_dist_rate_median_shift_m7d` | `8.4893` | `10.163` | `10.737` |
| `Bits 6-7` | `>> 6` | `astro_venus_helio_dist_median_shift_m7d` | `0.72079` | `0.72212` | `0.72599` |
| `Bits 8-9` | `>> 8` | `astro_venus_helio_dist_rate_median_shift_m7d` | `0.19352` | `0.20253` | `0.21106` |
| `Bits 10-11` | `>> 10` | `astro_venus_phase_angle_median_shift_m7d` | `40.061` | `50.892` | `54.945` |
| `Bits 12-13` | `>> 12` | `astro_venus_elong_median_shift_m7d` | `28.243` | `34.717` | `36.873` |
| `Bits 14-15` | `>> 14` | `astro_venus_illum_frac_median_shift_m7d` | `36.877` | `51.795` | `51.795` |

### Container: `packed_astro_container_150` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_ra_icrf_min_shift_p7d` | `24.968` | `36.455` | `36.455` |
| `Bits 2-3` | `>> 2` | `astro_sun_dec_icrf_min_shift_p7d` | `-0.28476` | `10.959` | `14.442` |
| `Bits 4-5` | `>> 4` | `astro_sun_ra_app_min_shift_p7d` | `25.283` | `36.78` | `36.78` |
| `Bits 6-7` | `>> 6` | `astro_sun_dec_app_min_shift_p7d` | `-0.15292` | `11.078` | `14.55` |
| `Bits 8-9` | `>> 8` | `astro_sun_azim_min_shift_p7d` | `115.34` | `117.33` | `125.51` |
| `Bits 10-11` | `>> 10` | `astro_sun_elev_min_shift_p7d` | `36.638` | `46.452` | `49.239` |
| `Bits 12-13` | `>> 12` | `astro_sun_app_mag_min_shift_p7d` | `-26.751` | `-26.733` | `-26.727` |
| `Bits 14-15` | `>> 14` | `astro_sun_dist_min_shift_p7d` | `0.99574` | `1.0042` | `1.007` |

### Container: `packed_astro_container_151` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_dist_rate_min_shift_p7d` | `0.23584` | `0.23974` | `0.24475` |
| `Bits 2-3` | `>> 2` | `astro_sun_illum_frac_min_shift_p7d` | `46.068` | `56.123` | `56.892` |
| `Bits 4-5` | `>> 4` | `astro_moon_ra_icrf_min_shift_p7d` | `124.85` | `261.02` | `277.73` |
| `Bits 6-7` | `>> 6` | `astro_moon_dec_icrf_min_shift_p7d` | `-28.981` | `-28.981` | `-8.0661` |
| `Bits 8-9` | `>> 8` | `astro_moon_ra_app_min_shift_p7d` | `125.21` | `261.4` | `278.12` |
| `Bits 10-11` | `>> 10` | `astro_moon_dec_app_min_shift_p7d` | `-28.964` | `-28.964` | `-7.9835` |
| `Bits 12-13` | `>> 12` | `astro_moon_azim_min_shift_p7d` | `76.215` | `227.79` | `227.79` |
| `Bits 14-15` | `>> 14` | `astro_moon_elev_min_shift_p7d` | `-25.976` | `-11.546` | `-11.546` |

### Container: `packed_astro_container_152` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_app_mag_min_shift_p7d` | `-12.075` | `-11.149` | `-11.149` |
| `Bits 2-3` | `>> 2` | `astro_moon_surf_bright_min_shift_p7d` | `3.8435` | `4.651` | `4.651` |
| `Bits 4-5` | `>> 4` | `astro_moon_dist_min_shift_p7d` | `0.0025021` | `0.0025031` | `0.0026032` |
| `Bits 6-7` | `>> 6` | `astro_moon_dist_rate_min_shift_p7d` | `-0.13211` | `0.20557` | `0.2064` |
| `Bits 8-9` | `>> 8` | `astro_moon_helio_dist_min_shift_p7d` | `0.9965` | `1.0052` | `1.0078` |
| `Bits 10-11` | `>> 10` | `astro_moon_helio_dist_rate_min_shift_p7d` | `-0.51557` | `-0.4839` | `0.16185` |
| `Bits 12-13` | `>> 12` | `astro_moon_phase_angle_min_shift_p7d` | `19.956` | `58.02` | `58.02` |
| `Bits 14-15` | `>> 14` | `astro_moon_elong_min_shift_p7d` | `85.33` | `96.892` | `97.775` |

### Container: `packed_astro_container_153` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_illum_frac_min_shift_p7d` | `46.068` | `56.123` | `56.892` |
| `Bits 2-3` | `>> 2` | `astro_mars_ra_icrf_min_shift_p7d` | `0.44575` | `309.44` | `332.38` |
| `Bits 4-5` | `>> 4` | `astro_mars_dec_icrf_min_shift_p7d` | `-13.552` | `-5.0097` | `-1.8007` |
| `Bits 6-7` | `>> 6` | `astro_mars_ra_app_min_shift_p7d` | `0.0452` | `309.78` | `332.7` |
| `Bits 8-9` | `>> 8` | `astro_mars_dec_app_min_shift_p7d` | `-13.439` | `-4.8786` | `-1.6676` |
| `Bits 10-11` | `>> 10` | `astro_mars_azim_min_shift_p7d` | `167.44` | `176.03` | `180.16` |
| `Bits 12-13` | `>> 12` | `astro_mars_elev_min_shift_p7d` | `36.925` | `46.288` | `49.582` |
| `Bits 14-15` | `>> 14` | `astro_mars_app_mag_min_shift_p7d` | `1.172` | `1.172` | `1.184` |

### Container: `packed_astro_container_154` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_surf_bright_min_shift_p7d` | `4.068` | `4.1675` | `4.219` |
| `Bits 2-3` | `>> 2` | `astro_mars_dist_min_shift_p7d` | `1.9766` | `2.0011` | `2.1143` |
| `Bits 4-5` | `>> 4` | `astro_mars_dist_rate_min_shift_p7d` | `-6.7179` | `-6.5772` | `-6.5135` |
| `Bits 6-7` | `>> 6` | `astro_mars_helio_dist_min_shift_p7d` | `1.3819` | `1.383` | `1.3951` |
| `Bits 8-9` | `>> 8` | `astro_mars_helio_dist_rate_min_shift_p7d` | `-1.1729` | `-0.49445` | `-0.23626` |
| `Bits 10-11` | `>> 10` | `astro_mars_phase_angle_min_shift_p7d` | `22.266` | `26.746` | `28.216` |
| `Bits 12-13` | `>> 12` | `astro_mars_elong_min_shift_p7d` | `32.161` | `38.349` | `40.459` |
| `Bits 14-15` | `>> 14` | `astro_mars_illum_frac_min_shift_p7d` | `46.068` | `56.123` | `56.892` |

### Container: `packed_astro_container_155` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_ra_icrf_min_shift_p7d` | `42.284` | `48.69` | `51.134` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_dec_icrf_min_shift_p7d` | `15.364` | `17.224` | `17.864` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_ra_app_min_shift_p7d` | `42.613` | `49.026` | `51.472` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_dec_app_min_shift_p7d` | `15.464` | `17.313` | `17.949` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_azim_min_shift_p7d` | `82.096` | `94.678` | `99.539` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_elev_min_shift_p7d` | `15.105` | `34.006` | `40.494` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_app_mag_min_shift_p7d` | `-2.101` | `-2.024` | `-2.008` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_surf_bright_min_shift_p7d` | `5.319` | `5.321` | `5.3395` |

### Container: `packed_astro_container_156` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_dist_min_shift_p7d` | `5.6523` | `5.9217` | `5.9794` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_dist_rate_min_shift_p7d` | `6.6384` | `8.7975` | `18.028` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_helio_dist_min_shift_p7d` | `5.0014` | `5.0083` | `5.0109` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_helio_dist_rate_min_shift_p7d` | `0.39378` | `0.41709` | `0.42497` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_phase_angle_min_shift_p7d` | `2.6008` | `3.5251` | `7.4308` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_elong_min_shift_p7d` | `13.03` | `17.84` | `40.474` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_illum_frac_min_shift_p7d` | `46.068` | `56.123` | `56.892` |
| `Bits 14-15` | `>> 14` | `astro_saturn_ra_icrf_min_shift_p7d` | `343.89` | `346.97` | `347.91` |

### Container: `packed_astro_container_157` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_dec_icrf_min_shift_p7d` | `-8.6388` | `-7.4361` | `-7.0762` |
| `Bits 2-3` | `>> 2` | `astro_saturn_ra_app_min_shift_p7d` | `344.2` | `347.28` | `348.22` |
| `Bits 4-5` | `>> 4` | `astro_saturn_dec_app_min_shift_p7d` | `-8.5124` | `-7.3069` | `-6.946` |
| `Bits 6-7` | `>> 6` | `astro_saturn_azim_min_shift_p7d` | `148.99` | `182.5` | `195.35` |
| `Bits 8-9` | `>> 8` | `astro_saturn_elev_min_shift_p7d` | `37.514` | `42.791` | `42.791` |
| `Bits 10-11` | `>> 10` | `astro_saturn_app_mag_min_shift_p7d` | `1.032` | `1.0715` | `1.072` |
| `Bits 12-13` | `>> 12` | `astro_saturn_surf_bright_min_shift_p7d` | `6.732` | `6.8235` | `6.851` |
| `Bits 14-15` | `>> 14` | `astro_saturn_dist_min_shift_p7d` | `10.254` | `10.337` | `10.625` |

### Container: `packed_astro_container_158` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_dist_rate_min_shift_p7d` | `-23.403` | `-21.624` | `-11.283` |
| `Bits 2-3` | `>> 2` | `astro_saturn_helio_dist_min_shift_p7d` | `9.7032` | `9.7051` | `9.7137` |
| `Bits 4-5` | `>> 4` | `astro_saturn_helio_dist_rate_min_shift_p7d` | `-0.50417` | `-0.50269` | `-0.49946` |
| `Bits 6-7` | `>> 6` | `astro_saturn_phase_angle_min_shift_p7d` | `1.7626` | `4.0762` | `4.7356` |
| `Bits 8-9` | `>> 8` | `astro_saturn_elong_min_shift_p7d` | `17.518` | `43.506` | `52.731` |
| `Bits 10-11` | `>> 10` | `astro_saturn_illum_frac_min_shift_p7d` | `46.068` | `56.123` | `56.892` |
| `Bits 12-13` | `>> 12` | `astro_mercury_ra_icrf_min_shift_p7d` | `15.645` | `15.645` | `19.916` |
| `Bits 14-15` | `>> 14` | `astro_mercury_dec_icrf_min_shift_p7d` | `4.4464` | `4.4464` | `5.873` |

### Container: `packed_astro_container_159` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mercury_ra_app_min_shift_p7d` | `15.953` | `15.953` | `20.229` |
| `Bits 2-3` | `>> 2` | `astro_mercury_dec_app_min_shift_p7d` | `4.5747` | `4.5747` | `6.0014` |
| `Bits 4-5` | `>> 4` | `astro_mercury_azim_min_shift_p7d` | `113.71` | `138.84` | `152.12` |
| `Bits 6-7` | `>> 6` | `astro_mercury_elev_min_shift_p7d` | `31.899` | `49.962` | `52.715` |
| `Bits 8-9` | `>> 8` | `astro_mercury_app_mag_min_shift_p7d` | `-0.7225` | `0.998` | `0.998` |
| `Bits 10-11` | `>> 10` | `astro_mercury_surf_bright_min_shift_p7d` | `2.5717` | `4.203` | `4.203` |
| `Bits 12-13` | `>> 12` | `astro_mercury_dist_min_shift_p7d` | `0.67278` | `0.67279` | `0.87852` |
| `Bits 14-15` | `>> 14` | `astro_mercury_dist_rate_min_shift_p7d` | `-26.937` | `5.9182` | `20.977` |

### Container: `packed_astro_container_160` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mercury_helio_dist_min_shift_p7d` | `0.35989` | `0.44475` | `0.46631` |
| `Bits 2-3` | `>> 2` | `astro_mercury_helio_dist_rate_min_shift_p7d` | `-0.15454` | `-0.15454` | `1.0552` |
| `Bits 4-5` | `>> 4` | `astro_mercury_phase_angle_min_shift_p7d` | `73.711` | `118.41` | `118.41` |
| `Bits 6-7` | `>> 6` | `astro_mercury_elong_min_shift_p7d` | `6.2662` | `16.423` | `22.786` |
| `Bits 8-9` | `>> 8` | `astro_mercury_illum_frac_min_shift_p7d` | `46.068` | `56.123` | `56.892` |
| `Bits 10-11` | `>> 10` | `astro_venus_ra_icrf_min_shift_p7d` | `27.487` | `27.487` | `311.59` |
| `Bits 12-13` | `>> 12` | `astro_venus_dec_icrf_min_shift_p7d` | `-9.2261` | `5.0027` | `9.9547` |
| `Bits 14-15` | `>> 14` | `astro_venus_ra_app_min_shift_p7d` | `27.803` | `27.803` | `311.93` |

### Container: `packed_astro_container_161` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_dec_app_min_shift_p7d` | `-9.1018` | `5.1307` | `10.073` |
| `Bits 2-3` | `>> 2` | `astro_venus_azim_min_shift_p7d` | `129.61` | `133.82` | `149.46` |
| `Bits 4-5` | `>> 4` | `astro_venus_elev_min_shift_p7d` | `37.957` | `48.597` | `51.738` |
| `Bits 6-7` | `>> 6` | `astro_venus_app_mag_min_shift_p7d` | `-3.885` | `-3.885` | `-3.8807` |
| `Bits 8-9` | `>> 8` | `astro_venus_surf_bright_min_shift_p7d` | `0.797` | `0.8125` | `0.8955` |
| `Bits 10-11` | `>> 10` | `astro_venus_dist_min_shift_p7d` | `1.5798` | `1.6729` | `1.6969` |
| `Bits 12-13` | `>> 12` | `astro_venus_dist_rate_min_shift_p7d` | `3.1446` | `3.6831` | `5.9205` |
| `Bits 14-15` | `>> 14` | `astro_venus_helio_dist_min_shift_p7d` | `0.72523` | `0.726` | `0.72752` |

### Container: `packed_astro_container_162` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_helio_dist_rate_min_shift_p7d` | `-0.21712` | `-0.19592` | `-0.037737` |
| `Bits 2-3` | `>> 2` | `astro_venus_phase_angle_min_shift_p7d` | `13.005` | `15.346` | `25.766` |
| `Bits 4-5` | `>> 4` | `astro_venus_elong_min_shift_p7d` | `9.3214` | `11.012` | `18.5` |
| `Bits 6-7` | `>> 6` | `astro_venus_illum_frac_min_shift_p7d` | `46.068` | `56.123` | `56.892` |
| `Bits 8-9` | `>> 8` | `astro_sun_ra_icrf_max_shift_p7d` | `36.219` | `38.36` | `262.6` |
| `Bits 10-11` | `>> 10` | `astro_sun_dec_icrf_max_shift_p7d` | `2.0771` | `12.983` | `15.056` |
| `Bits 12-13` | `>> 12` | `astro_sun_ra_app_max_shift_p7d` | `36.544` | `38.687` | `262.91` |
| `Bits 14-15` | `>> 14` | `astro_sun_dec_app_max_shift_p7d` | `2.2088` | `13.096` | `15.161` |

### Container: `packed_astro_container_163` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_azim_max_shift_p7d` | `115.96` | `119.11` | `126.94` |
| `Bits 2-3` | `>> 2` | `astro_sun_elev_max_shift_p7d` | `38.755` | `48.09` | `49.703` |
| `Bits 4-5` | `>> 4` | `astro_sun_app_mag_max_shift_p7d` | `-26.748` | `-26.73` | `-26.726` |
| `Bits 6-7` | `>> 6` | `astro_sun_dist_max_shift_p7d` | `0.99741` | `1.0058` | `1.0075` |
| `Bits 8-9` | `>> 8` | `astro_sun_dist_rate_max_shift_p7d` | `0.24478` | `0.24478` | `0.2536` |
| `Bits 10-11` | `>> 10` | `astro_sun_illum_frac_max_shift_p7d` | `76.483` | `76.483` | `96.618` |
| `Bits 12-13` | `>> 12` | `astro_moon_ra_icrf_max_shift_p7d` | `194.48` | `307.59` | `307.59` |
| `Bits 14-15` | `>> 14` | `astro_moon_dec_icrf_max_shift_p7d` | `-24.633` | `-7.5052` | `21.34` |

### Container: `packed_astro_container_164` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_ra_app_max_shift_p7d` | `194.81` | `307.95` | `307.95` |
| `Bits 2-3` | `>> 2` | `astro_moon_dec_app_max_shift_p7d` | `-24.551` | `-7.3754` | `21.275` |
| `Bits 4-5` | `>> 4` | `astro_moon_azim_max_shift_p7d` | `241.98` | `241.98` | `306.47` |
| `Bits 6-7` | `>> 6` | `astro_moon_elev_max_shift_p7d` | `-3.3137` | `9.3349` | `9.3349` |
| `Bits 8-9` | `>> 8` | `astro_moon_app_mag_max_shift_p7d` | `-10.415` | `-10.415` | `-9.9047` |
| `Bits 10-11` | `>> 10` | `astro_moon_surf_bright_max_shift_p7d` | `5.0633` | `5.106` | `5.3152` |
| `Bits 12-13` | `>> 12` | `astro_moon_dist_max_shift_p7d` | `0.0025695` | `0.0025715` | `0.0027327` |
| `Bits 14-15` | `>> 14` | `astro_moon_dist_rate_max_shift_p7d` | `0.17714` | `0.25633` | `0.25634` |

### Container: `packed_astro_container_165` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_helio_dist_max_shift_p7d` | `0.99965` | `1.0077` | `1.0083` |
| `Bits 2-3` | `>> 2` | `astro_moon_helio_dist_rate_max_shift_p7d` | `-0.37549` | `0.12081` | `1.0805` |
| `Bits 4-5` | `>> 4` | `astro_moon_phase_angle_max_shift_p7d` | `82.078` | `82.967` | `94.524` |
| `Bits 6-7` | `>> 6` | `astro_moon_elong_max_shift_p7d` | `121.86` | `121.86` | `159.99` |
| `Bits 8-9` | `>> 8` | `astro_moon_illum_frac_max_shift_p7d` | `76.483` | `76.483` | `96.618` |
| `Bits 10-11` | `>> 10` | `astro_mars_ra_icrf_max_shift_p7d` | `334.25` | `355.84` | `359.74` |
| `Bits 12-13` | `>> 12` | `astro_mars_dec_icrf_max_shift_p7d` | `-11.94` | `-3.1798` | `-1.1864` |
| `Bits 14-15` | `>> 14` | `astro_mars_ra_app_max_shift_p7d` | `334.57` | `356.14` | `359.34` |

### Container: `packed_astro_container_166` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_dec_app_max_shift_p7d` | `-11.822` | `-3.0474` | `-1.0531` |
| `Bits 2-3` | `>> 2` | `astro_mars_azim_max_shift_p7d` | `168.84` | `178.33` | `181.03` |
| `Bits 4-5` | `>> 4` | `astro_mars_elev_max_shift_p7d` | `38.749` | `48.181` | `50.192` |
| `Bits 6-7` | `>> 6` | `astro_mars_app_mag_max_shift_p7d` | `1.183` | `1.183` | `1.2393` |
| `Bits 8-9` | `>> 8` | `astro_mars_surf_bright_max_shift_p7d` | `4.1303` | `4.19` | `4.223` |
| `Bits 10-11` | `>> 10` | `astro_mars_dist_max_shift_p7d` | `1.9841` | `2.0237` | `2.1374` |
| `Bits 12-13` | `>> 12` | `astro_mars_dist_rate_max_shift_p7d` | `-6.685` | `-6.5377` | `-6.5092` |
| `Bits 14-15` | `>> 14` | `astro_mars_helio_dist_max_shift_p7d` | `1.3822` | `1.3845` | `1.3989` |

### Container: `packed_astro_container_167` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_helio_dist_rate_max_shift_p7d` | `-1.045` | `-0.34749` | `-0.18645` |
| `Bits 2-3` | `>> 2` | `astro_mars_phase_angle_max_shift_p7d` | `23.207` | `27.591` | `28.489` |
| `Bits 4-5` | `>> 4` | `astro_mars_elong_max_shift_p7d` | `33.445` | `39.557` | `40.859` |
| `Bits 6-7` | `>> 6` | `astro_mars_illum_frac_max_shift_p7d` | `76.483` | `76.483` | `96.618` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_ra_icrf_max_shift_p7d` | `43.494` | `50.08` | `51.608` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_dec_icrf_max_shift_p7d` | `15.737` | `17.592` | `17.984` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_ra_app_max_shift_p7d` | `43.825` | `50.417` | `51.947` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_dec_app_max_shift_p7d` | `15.835` | `17.679` | `18.068` |

### Container: `packed_astro_container_168` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_azim_max_shift_p7d` | `84.6` | `97.417` | `100.53` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_elev_max_shift_p7d` | `18.967` | `37.725` | `41.714` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_app_mag_max_shift_p7d` | `-2.0808` | `-2.0145` | `-2.006` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_surf_bright_max_shift_p7d` | `5.319` | `5.3235` | `5.3438` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_dist_max_shift_p7d` | `5.7188` | `5.9566` | `5.9878` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_dist_rate_max_shift_p7d` | `7.3096` | `10.762` | `19.659` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_helio_dist_max_shift_p7d` | `5.0028` | `5.0098` | `5.0114` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_helio_dist_rate_max_shift_p7d` | `0.40019` | `0.4225` | `0.42614` |

### Container: `packed_astro_container_169` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_phase_angle_max_shift_p7d` | `2.8877` | `4.3634` | `8.1155` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_elong_max_shift_p7d` | `14.504` | `22.313` | `45.201` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_illum_frac_max_shift_p7d` | `76.483` | `76.483` | `96.618` |
| `Bits 6-7` | `>> 6` | `astro_saturn_ra_icrf_max_shift_p7d` | `344.55` | `347.52` | `348.08` |
| `Bits 8-9` | `>> 8` | `astro_saturn_dec_icrf_max_shift_p7d` | `-8.3793` | `-7.2266` | `-7.0132` |
| `Bits 10-11` | `>> 10` | `astro_saturn_ra_app_max_shift_p7d` | `344.86` | `347.83` | `348.39` |
| `Bits 12-13` | `>> 12` | `astro_saturn_dec_app_max_shift_p7d` | `-8.2524` | `-7.0968` | `-6.8828` |
| `Bits 14-15` | `>> 14` | `astro_saturn_azim_max_shift_p7d` | `155.05` | `189.85` | `197.75` |

### Container: `packed_astro_container_170` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_elev_max_shift_p7d` | `39.676` | `43.131` | `43.131` |
| `Bits 2-3` | `>> 2` | `astro_saturn_app_mag_max_shift_p7d` | `1.045` | `1.072` | `1.072` |
| `Bits 4-5` | `>> 4` | `astro_saturn_surf_bright_max_shift_p7d` | `6.7527` | `6.84` | `6.856` |
| `Bits 6-7` | `>> 6` | `astro_saturn_dist_max_shift_p7d` | `10.28` | `10.409` | `10.659` |
| `Bits 8-9` | `>> 8` | `astro_saturn_dist_rate_max_shift_p7d` | `-22.885` | `-19.838` | `-8.8536` |
| `Bits 10-11` | `>> 10` | `astro_saturn_helio_dist_max_shift_p7d` | `9.7037` | `9.7068` | `9.7154` |
| `Bits 12-13` | `>> 12` | `astro_saturn_helio_dist_rate_max_shift_p7d` | `-0.50336` | `-0.50084` | `-0.49773` |
| `Bits 14-15` | `>> 14` | `astro_saturn_phase_angle_max_shift_p7d` | `2.2699` | `4.4625` | `4.8475` |

### Container: `packed_astro_container_171` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_elong_max_shift_p7d` | `22.748` | `48.773` | `54.495` |
| `Bits 2-3` | `>> 2` | `astro_saturn_illum_frac_max_shift_p7d` | `76.483` | `76.483` | `96.618` |
| `Bits 4-5` | `>> 4` | `astro_mercury_ra_icrf_max_shift_p7d` | `16.427` | `16.427` | `23.168` |
| `Bits 6-7` | `>> 6` | `astro_mercury_dec_icrf_max_shift_p7d` | `4.483` | `4.483` | `8.3472` |
| `Bits 8-9` | `>> 8` | `astro_mercury_ra_app_max_shift_p7d` | `16.735` | `16.735` | `23.484` |
| `Bits 10-11` | `>> 10` | `astro_mercury_dec_app_max_shift_p7d` | `4.6114` | `4.6114` | `8.4743` |
| `Bits 12-13` | `>> 12` | `astro_mercury_azim_max_shift_p7d` | `124.87` | `146.54` | `153.98` |
| `Bits 14-15` | `>> 14` | `astro_mercury_elev_max_shift_p7d` | `34.111` | `51.803` | `53.105` |

### Container: `packed_astro_container_172` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mercury_app_mag_max_shift_p7d` | `0.06225` | `1.187` | `1.187` |
| `Bits 2-3` | `>> 2` | `astro_mercury_surf_bright_max_shift_p7d` | `3.1738` | `4.31` | `4.31` |
| `Bits 4-5` | `>> 4` | `astro_mercury_dist_max_shift_p7d` | `0.69808` | `0.69808` | `1.0363` |
| `Bits 6-7` | `>> 6` | `astro_mercury_dist_rate_max_shift_p7d` | `-14.531` | `15.609` | `22.578` |
| `Bits 8-9` | `>> 8` | `astro_mercury_helio_dist_max_shift_p7d` | `0.39435` | `0.45972` | `0.46669` |
| `Bits 10-11` | `>> 10` | `astro_mercury_helio_dist_rate_max_shift_p7d` | `0.81244` | `0.81244` | `5.7788` |
| `Bits 12-13` | `>> 12` | `astro_mercury_phase_angle_max_shift_p7d` | `101.3` | `123.24` | `125.69` |
| `Bits 14-15` | `>> 14` | `astro_mercury_elong_max_shift_p7d` | `14.823` | `20.372` | `24.043` |

### Container: `packed_astro_container_173` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mercury_illum_frac_max_shift_p7d` | `76.483` | `76.483` | `96.618` |
| `Bits 2-3` | `>> 2` | `astro_venus_ra_icrf_max_shift_p7d` | `29.818` | `29.818` | `327.73` |
| `Bits 4-5` | `>> 4` | `astro_venus_dec_icrf_max_shift_p7d` | `-6.4859` | `7.8566` | `10.856` |
| `Bits 6-7` | `>> 6` | `astro_venus_ra_app_max_shift_p7d` | `30.136` | `30.136` | `328.05` |
| `Bits 8-9` | `>> 8` | `astro_venus_dec_app_max_shift_p7d` | `-6.357` | `7.9798` | `10.972` |
| `Bits 10-11` | `>> 10` | `astro_venus_azim_max_shift_p7d` | `130.96` | `137.46` | `152.05` |
| `Bits 12-13` | `>> 12` | `astro_venus_elev_max_shift_p7d` | `40.093` | `50.454` | `52.238` |
| `Bits 14-15` | `>> 14` | `astro_venus_app_mag_max_shift_p7d` | `-3.884` | `-3.884` | `-3.8785` |

### Container: `packed_astro_container_174` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_surf_bright_max_shift_p7d` | `0.802` | `0.8275` | `0.91375` |
| `Bits 2-3` | `>> 2` | `astro_venus_dist_max_shift_p7d` | `1.6014` | `1.6871` | `1.7008` |
| `Bits 4-5` | `>> 4` | `astro_venus_dist_rate_max_shift_p7d` | `3.3157` | `4.1612` | `6.3129` |
| `Bits 6-7` | `>> 6` | `astro_venus_helio_dist_max_shift_p7d` | `0.72548` | `0.72663` | `0.72787` |
| `Bits 8-9` | `>> 8` | `astro_venus_helio_dist_rate_max_shift_p7d` | `-0.21161` | `-0.17166` | `0.0011154` |
| `Bits 10-11` | `>> 10` | `astro_venus_phase_angle_max_shift_p7d` | `13.73` | `17.487` | `27.827` |
| `Bits 12-13` | `>> 12` | `astro_venus_elong_max_shift_p7d` | `9.8445` | `12.557` | `19.958` |
| `Bits 14-15` | `>> 14` | `astro_venus_illum_frac_max_shift_p7d` | `76.483` | `76.483` | `96.618` |

### Container: `packed_astro_container_175` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_ra_icrf_mean_shift_p7d` | `33.857` | `37.407` | `125.43` |
| `Bits 2-3` | `>> 2` | `astro_sun_dec_icrf_mean_shift_p7d` | `0.89733` | `11.979` | `14.749` |
| `Bits 4-5` | `>> 4` | `astro_sun_ra_app_mean_shift_p7d` | `34.18` | `37.733` | `125.74` |
| `Bits 6-7` | `>> 6` | `astro_sun_dec_app_mean_shift_p7d` | `1.0292` | `12.095` | `14.856` |
| `Bits 8-9` | `>> 8` | `astro_sun_azim_mean_shift_p7d` | `115.65` | `118.22` | `126.23` |
| `Bits 10-11` | `>> 10` | `astro_sun_elev_mean_shift_p7d` | `37.698` | `47.282` | `49.472` |
| `Bits 12-13` | `>> 12` | `astro_sun_app_mag_mean_shift_p7d` | `-26.749` | `-26.731` | `-26.726` |
| `Bits 14-15` | `>> 14` | `astro_sun_dist_mean_shift_p7d` | `0.99657` | `1.005` | `1.0073` |

### Container: `packed_astro_container_176` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_dist_rate_mean_shift_p7d` | `0.24236` | `0.24236` | `0.24772` |
| `Bits 2-3` | `>> 2` | `astro_sun_illum_frac_mean_shift_p7d` | `66.477` | `66.477` | `78.027` |
| `Bits 4-5` | `>> 4` | `astro_moon_ra_icrf_mean_shift_p7d` | `160.54` | `292.7` | `292.7` |
| `Bits 6-7` | `>> 6` | `astro_moon_dec_icrf_mean_shift_p7d` | `-27.077` | `-21.841` | `8.6978` |
| `Bits 8-9` | `>> 8` | `astro_moon_ra_app_mean_shift_p7d` | `160.88` | `293.08` | `293.08` |
| `Bits 10-11` | `>> 10` | `astro_moon_dec_app_mean_shift_p7d` | `-27.027` | `-21.773` | `8.7361` |
| `Bits 12-13` | `>> 12` | `astro_moon_azim_mean_shift_p7d` | `186.1` | `234.88` | `234.88` |
| `Bits 14-15` | `>> 14` | `astro_moon_elev_mean_shift_p7d` | `-21.411` | `-1.1663` | `-1.1663` |

### Container: `packed_astro_container_177` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_app_mag_mean_shift_p7d` | `-11.2` | `-10.79` | `-10.785` |
| `Bits 2-3` | `>> 2` | `astro_moon_surf_bright_mean_shift_p7d` | `4.5012` | `4.8777` | `4.8777` |
| `Bits 4-5` | `>> 4` | `astro_moon_dist_mean_shift_p7d` | `0.0025359` | `0.0025369` | `0.0026816` |
| `Bits 6-7` | `>> 6` | `astro_moon_dist_rate_mean_shift_p7d` | `0.024321` | `0.2334` | `0.2334` |
| `Bits 8-9` | `>> 8` | `astro_moon_helio_dist_mean_shift_p7d` | `0.99817` | `1.0066` | `1.0081` |
| `Bits 10-11` | `>> 10` | `astro_moon_helio_dist_rate_mean_shift_p7d` | `-0.45221` | `-0.2493` | `0.65312` |
| `Bits 12-13` | `>> 12` | `astro_moon_phase_angle_mean_shift_p7d` | `52.533` | `70.442` | `70.442` |
| `Bits 14-15` | `>> 14` | `astro_moon_elong_mean_shift_p7d` | `109.42` | `109.42` | `127.35` |

### Container: `packed_astro_container_178` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_illum_frac_mean_shift_p7d` | `66.477` | `66.477` | `78.027` |
| `Bits 2-3` | `>> 2` | `astro_mars_ra_icrf_mean_shift_p7d` | `239.74` | `311.81` | `334.62` |
| `Bits 4-5` | `>> 4` | `astro_mars_dec_icrf_mean_shift_p7d` | `-12.751` | `-4.0958` | `-1.4935` |
| `Bits 6-7` | `>> 6` | `astro_mars_ra_app_mean_shift_p7d` | `120.05` | `312.15` | `334.94` |
| `Bits 8-9` | `>> 8` | `astro_mars_dec_app_mean_shift_p7d` | `-12.635` | `-3.964` | `-1.3604` |
| `Bits 10-11` | `>> 10` | `astro_mars_azim_mean_shift_p7d` | `168.13` | `177.17` | `180.6` |
| `Bits 12-13` | `>> 12` | `astro_mars_elev_mean_shift_p7d` | `37.833` | `47.237` | `49.888` |
| `Bits 14-15` | `>> 14` | `astro_mars_app_mag_mean_shift_p7d` | `1.178` | `1.178` | `1.2148` |

### Container: `packed_astro_container_179` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_surf_bright_mean_shift_p7d` | `4.1036` | `4.1801` | `4.2213` |
| `Bits 2-3` | `>> 2` | `astro_mars_dist_mean_shift_p7d` | `1.9803` | `2.0124` | `2.1259` |
| `Bits 4-5` | `>> 4` | `astro_mars_dist_rate_mean_shift_p7d` | `-6.7023` | `-6.5568` | `-6.5112` |
| `Bits 6-7` | `>> 6` | `astro_mars_helio_dist_mean_shift_p7d` | `1.382` | `1.3837` | `1.397` |
| `Bits 8-9` | `>> 8` | `astro_mars_helio_dist_rate_mean_shift_p7d` | `-1.1093` | `-0.42112` | `-0.21136` |
| `Bits 10-11` | `>> 10` | `astro_mars_phase_angle_mean_shift_p7d` | `22.738` | `27.17` | `28.352` |
| `Bits 12-13` | `>> 12` | `astro_mars_elong_mean_shift_p7d` | `32.804` | `38.954` | `40.659` |
| `Bits 14-15` | `>> 14` | `astro_mars_illum_frac_mean_shift_p7d` | `66.477` | `66.477` | `78.027` |

### Container: `packed_astro_container_180` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_ra_icrf_mean_shift_p7d` | `42.885` | `49.383` | `51.371` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_dec_icrf_mean_shift_p7d` | `15.55` | `17.409` | `17.924` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_ra_app_mean_shift_p7d` | `43.216` | `49.72` | `51.71` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_dec_app_mean_shift_p7d` | `15.649` | `17.496` | `18.008` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_azim_mean_shift_p7d` | `83.35` | `96.038` | `100.03` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_elev_mean_shift_p7d` | `17.037` | `35.868` | `41.104` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_app_mag_mean_shift_p7d` | `-2.0908` | `-2.0191` | `-2.007` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_surf_bright_mean_shift_p7d` | `5.319` | `5.3222` | `5.3416` |

### Container: `packed_astro_container_181` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_dist_mean_shift_p7d` | `5.6859` | `5.9396` | `5.9837` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_dist_rate_mean_shift_p7d` | `6.9745` | `9.7804` | `18.849` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_helio_dist_mean_shift_p7d` | `5.0021` | `5.0091` | `5.0111` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_helio_dist_rate_mean_shift_p7d` | `0.3965` | `0.41878` | `0.42537` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_phase_angle_mean_shift_p7d` | `2.7443` | `3.9455` | `7.7763` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_elong_mean_shift_p7d` | `13.767` | `20.074` | `42.833` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_illum_frac_mean_shift_p7d` | `66.477` | `66.477` | `78.027` |
| `Bits 14-15` | `>> 14` | `astro_saturn_ra_icrf_mean_shift_p7d` | `344.22` | `347.25` | `347.99` |

### Container: `packed_astro_container_182` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_dec_icrf_mean_shift_p7d` | `-8.5086` | `-7.3304` | `-7.0446` |
| `Bits 2-3` | `>> 2` | `astro_saturn_ra_app_mean_shift_p7d` | `344.53` | `347.56` | `348.31` |
| `Bits 4-5` | `>> 4` | `astro_saturn_dec_app_mean_shift_p7d` | `-8.382` | `-7.2009` | `-6.9143` |
| `Bits 6-7` | `>> 6` | `astro_saturn_azim_mean_shift_p7d` | `151.99` | `186.18` | `196.55` |
| `Bits 8-9` | `>> 8` | `astro_saturn_elev_mean_shift_p7d` | `38.621` | `42.964` | `42.964` |
| `Bits 10-11` | `>> 10` | `astro_saturn_app_mag_mean_shift_p7d` | `1.0385` | `1.072` | `1.072` |
| `Bits 12-13` | `>> 12` | `astro_saturn_surf_bright_mean_shift_p7d` | `6.7425` | `6.8319` | `6.8533` |
| `Bits 14-15` | `>> 14` | `astro_saturn_dist_mean_shift_p7d` | `10.267` | `10.374` | `10.643` |

### Container: `packed_astro_container_183` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_dist_rate_mean_shift_p7d` | `-23.145` | `-20.743` | `-10.074` |
| `Bits 2-3` | `>> 2` | `astro_saturn_helio_dist_mean_shift_p7d` | `9.7035` | `9.7059` | `9.7145` |
| `Bits 4-5` | `>> 4` | `astro_saturn_helio_dist_rate_mean_shift_p7d` | `-0.50379` | `-0.50172` | `-0.49888` |
| `Bits 6-7` | `>> 6` | `astro_saturn_phase_angle_mean_shift_p7d` | `2.0172` | `4.2716` | `4.7917` |
| `Bits 8-9` | `>> 8` | `astro_saturn_elong_mean_shift_p7d` | `20.133` | `46.138` | `53.613` |
| `Bits 10-11` | `>> 10` | `astro_saturn_illum_frac_mean_shift_p7d` | `66.477` | `66.477` | `78.027` |
| `Bits 12-13` | `>> 12` | `astro_mercury_ra_icrf_mean_shift_p7d` | `16.025` | `16.025` | `21.755` |
| `Bits 14-15` | `>> 14` | `astro_mercury_dec_icrf_mean_shift_p7d` | `4.4601` | `4.4601` | `7.0424` |

### Container: `packed_astro_container_184` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mercury_ra_app_mean_shift_p7d` | `16.334` | `16.334` | `22.07` |
| `Bits 2-3` | `>> 2` | `astro_mercury_dec_app_mean_shift_p7d` | `4.5884` | `4.5884` | `7.1703` |
| `Bits 4-5` | `>> 4` | `astro_mercury_azim_mean_shift_p7d` | `119.11` | `142.87` | `153.07` |
| `Bits 6-7` | `>> 6` | `astro_mercury_elev_mean_shift_p7d` | `32.926` | `50.958` | `52.908` |
| `Bits 8-9` | `>> 8` | `astro_mercury_app_mag_mean_shift_p7d` | `-0.35343` | `1.0907` | `1.0907` |
| `Bits 10-11` | `>> 10` | `astro_mercury_surf_bright_mean_shift_p7d` | `2.8644` | `4.2557` | `4.2557` |
| `Bits 12-13` | `>> 12` | `astro_mercury_dist_mean_shift_p7d` | `0.68535` | `0.68535` | `0.95737` |
| `Bits 14-15` | `>> 14` | `astro_mercury_dist_rate_mean_shift_p7d` | `-20.234` | `11.033` | `21.788` |

### Container: `packed_astro_container_185` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mercury_helio_dist_mean_shift_p7d` | `0.37721` | `0.45289` | `0.46655` |
| `Bits 2-3` | `>> 2` | `astro_mercury_helio_dist_rate_mean_shift_p7d` | `0.32901` | `0.32901` | `3.2796` |
| `Bits 4-5` | `>> 4` | `astro_mercury_phase_angle_mean_shift_p7d` | `87.917` | `120.81` | `120.81` |
| `Bits 6-7` | `>> 6` | `astro_mercury_elong_mean_shift_p7d` | `10.697` | `18.538` | `23.427` |
| `Bits 8-9` | `>> 8` | `astro_mercury_illum_frac_mean_shift_p7d` | `66.477` | `66.477` | `78.027` |
| `Bits 10-11` | `>> 10` | `astro_venus_ra_icrf_mean_shift_p7d` | `28.652` | `28.652` | `315.37` |
| `Bits 12-13` | `>> 12` | `astro_venus_dec_icrf_mean_shift_p7d` | `-7.8649` | `6.4354` | `10.406` |
| `Bits 14-15` | `>> 14` | `astro_venus_ra_app_mean_shift_p7d` | `28.969` | `28.969` | `315.7` |

### Container: `packed_astro_container_186` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_dec_app_mean_shift_p7d` | `-7.7382` | `6.5611` | `10.523` |
| `Bits 2-3` | `>> 2` | `astro_venus_azim_mean_shift_p7d` | `130.28` | `135.66` | `150.76` |
| `Bits 4-5` | `>> 4` | `astro_venus_elev_mean_shift_p7d` | `39.019` | `49.54` | `51.989` |
| `Bits 6-7` | `>> 6` | `astro_venus_app_mag_mean_shift_p7d` | `-3.8847` | `-3.8847` | `-3.8796` |
| `Bits 8-9` | `>> 8` | `astro_venus_surf_bright_mean_shift_p7d` | `0.79933` | `0.81986` | `0.90457` |
| `Bits 10-11` | `>> 10` | `astro_venus_dist_mean_shift_p7d` | `1.5907` | `1.6801` | `1.6989` |
| `Bits 12-13` | `>> 12` | `astro_venus_dist_rate_mean_shift_p7d` | `3.2303` | `3.9233` | `6.1175` |
| `Bits 14-15` | `>> 14` | `astro_venus_helio_dist_mean_shift_p7d` | `0.72535` | `0.72632` | `0.7277` |

### Container: `packed_astro_container_187` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_helio_dist_rate_mean_shift_p7d` | `-0.21439` | `-0.18414` | `-0.018345` |
| `Bits 2-3` | `>> 2` | `astro_venus_phase_angle_mean_shift_p7d` | `13.367` | `16.418` | `26.797` |
| `Bits 4-5` | `>> 4` | `astro_venus_elong_mean_shift_p7d` | `9.583` | `11.786` | `19.231` |
| `Bits 6-7` | `>> 6` | `astro_venus_illum_frac_mean_shift_p7d` | `66.477` | `66.477` | `78.027` |
| `Bits 8-9` | `>> 8` | `astro_sun_ra_icrf_median_shift_p7d` | `27.759` | `37.406` | `37.406` |
| `Bits 10-11` | `>> 10` | `astro_sun_dec_icrf_median_shift_p7d` | `0.89826` | `11.986` | `14.751` |
| `Bits 12-13` | `>> 12` | `astro_sun_ra_app_median_shift_p7d` | `28.076` | `37.732` | `37.732` |
| `Bits 14-15` | `>> 14` | `astro_sun_dec_app_median_shift_p7d` | `1.0302` | `12.102` | `14.857` |

### Container: `packed_astro_container_188` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_azim_median_shift_p7d` | `115.65` | `118.23` | `126.23` |
| `Bits 2-3` | `>> 2` | `astro_sun_elev_median_shift_p7d` | `37.7` | `47.291` | `49.473` |
| `Bits 4-5` | `>> 4` | `astro_sun_app_mag_median_shift_p7d` | `-26.75` | `-26.731` | `-26.726` |
| `Bits 6-7` | `>> 6` | `astro_sun_dist_median_shift_p7d` | `0.99657` | `1.005` | `1.0073` |
| `Bits 8-9` | `>> 8` | `astro_sun_dist_rate_median_shift_p7d` | `0.24257` | `0.24257` | `0.24793` |
| `Bits 10-11` | `>> 10` | `astro_sun_illum_frac_median_shift_p7d` | `66.824` | `66.824` | `80.404` |
| `Bits 12-13` | `>> 12` | `astro_moon_ra_icrf_median_shift_p7d` | `161.27` | `292.78` | `292.78` |
| `Bits 14-15` | `>> 14` | `astro_moon_dec_icrf_median_shift_p7d` | `-27.616` | `-24.933` | `9.8073` |

### Container: `packed_astro_container_189` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_ra_app_median_shift_p7d` | `161.6` | `293.16` | `293.16` |
| `Bits 2-3` | `>> 2` | `astro_moon_dec_app_median_shift_p7d` | `-27.565` | `-24.854` | `9.6924` |
| `Bits 4-5` | `>> 4` | `astro_moon_azim_median_shift_p7d` | `188.88` | `234.87` | `234.87` |
| `Bits 6-7` | `>> 6` | `astro_moon_elev_median_shift_p7d` | `-22.042` | `-1.2882` | `-1.2882` |
| `Bits 8-9` | `>> 8` | `astro_moon_app_mag_median_shift_p7d` | `-11.231` | `-10.805` | `-10.805` |
| `Bits 10-11` | `>> 10` | `astro_moon_surf_bright_median_shift_p7d` | `4.5122` | `4.876` | `4.876` |
| `Bits 12-13` | `>> 12` | `astro_moon_dist_median_shift_p7d` | `0.002536` | `0.002537` | `0.0026926` |
| `Bits 14-15` | `>> 14` | `astro_moon_dist_rate_median_shift_p7d` | `0.025764` | `0.23746` | `0.23746` |

### Container: `packed_astro_container_190` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_helio_dist_median_shift_p7d` | `0.99825` | `1.0066` | `1.0081` |
| `Bits 2-3` | `>> 2` | `astro_moon_helio_dist_rate_median_shift_p7d` | `-0.46557` | `-0.31839` | `0.67157` |
| `Bits 4-5` | `>> 4` | `astro_moon_phase_angle_median_shift_p7d` | `52.213` | `70.339` | `70.339` |
| `Bits 6-7` | `>> 6` | `astro_moon_elong_median_shift_p7d` | `109.53` | `109.53` | `127.66` |
| `Bits 8-9` | `>> 8` | `astro_moon_illum_frac_median_shift_p7d` | `66.824` | `66.824` | `80.404` |
| `Bits 10-11` | `>> 10` | `astro_mars_ra_icrf_median_shift_p7d` | `332.01` | `353.7` | `359.03` |
| `Bits 12-13` | `>> 12` | `astro_mars_dec_icrf_median_shift_p7d` | `-12.755` | `-4.0967` | `-1.4935` |
| `Bits 14-15` | `>> 14` | `astro_mars_ra_app_median_shift_p7d` | `0.75223` | `312.15` | `334.94` |

### Container: `packed_astro_container_191` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_dec_app_median_shift_p7d` | `-12.639` | `-3.9648` | `-1.3603` |
| `Bits 2-3` | `>> 2` | `astro_mars_azim_median_shift_p7d` | `168.12` | `177.15` | `180.6` |
| `Bits 4-5` | `>> 4` | `astro_mars_elev_median_shift_p7d` | `37.83` | `47.239` | `49.888` |
| `Bits 6-7` | `>> 6` | `astro_mars_app_mag_median_shift_p7d` | `1.179` | `1.179` | `1.2112` |
| `Bits 8-9` | `>> 8` | `astro_mars_surf_bright_median_shift_p7d` | `4.1007` | `4.1815` | `4.222` |
| `Bits 10-11` | `>> 10` | `astro_mars_dist_median_shift_p7d` | `1.9803` | `2.0124` | `2.1259` |
| `Bits 12-13` | `>> 12` | `astro_mars_dist_rate_median_shift_p7d` | `-6.703` | `-6.5563` | `-6.511` |
| `Bits 14-15` | `>> 14` | `astro_mars_helio_dist_median_shift_p7d` | `1.382` | `1.3837` | `1.3969` |

### Container: `packed_astro_container_192` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_helio_dist_rate_median_shift_p7d` | `-1.1096` | `-0.42124` | `-0.21137` |
| `Bits 2-3` | `>> 2` | `astro_mars_phase_angle_median_shift_p7d` | `22.739` | `27.171` | `28.352` |
| `Bits 4-5` | `>> 4` | `astro_mars_elong_median_shift_p7d` | `32.806` | `38.954` | `40.659` |
| `Bits 6-7` | `>> 6` | `astro_mars_illum_frac_median_shift_p7d` | `66.824` | `66.824` | `80.404` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_ra_icrf_median_shift_p7d` | `42.883` | `49.382` | `51.371` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_dec_icrf_median_shift_p7d` | `15.55` | `17.409` | `17.924` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_ra_app_median_shift_p7d` | `43.213` | `49.718` | `51.709` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_dec_app_median_shift_p7d` | `15.649` | `17.497` | `18.009` |

### Container: `packed_astro_container_193` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_azim_median_shift_p7d` | `83.351` | `96.031` | `100.03` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_elev_median_shift_p7d` | `17.038` | `35.87` | `41.105` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_app_mag_median_shift_p7d` | `-2.0905` | `-2.019` | `-2.007` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_surf_bright_median_shift_p7d` | `5.319` | `5.3225` | `5.3415` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_dist_median_shift_p7d` | `5.6862` | `5.94` | `5.9837` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_dist_rate_median_shift_p7d` | `6.9756` | `9.7811` | `18.852` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_helio_dist_median_shift_p7d` | `5.0021` | `5.0091` | `5.0111` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_helio_dist_rate_median_shift_p7d` | `0.39578` | `0.41792` | `0.425` |

### Container: `packed_astro_container_194` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_phase_angle_median_shift_p7d` | `2.7444` | `3.9465` | `7.7787` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_elong_median_shift_p7d` | `13.767` | `20.072` | `42.83` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_illum_frac_median_shift_p7d` | `66.824` | `66.824` | `80.404` |
| `Bits 6-7` | `>> 6` | `astro_saturn_ra_icrf_median_shift_p7d` | `344.22` | `347.25` | `348` |
| `Bits 8-9` | `>> 8` | `astro_saturn_dec_icrf_median_shift_p7d` | `-8.5083` | `-7.3296` | `-7.0445` |
| `Bits 10-11` | `>> 10` | `astro_saturn_ra_app_median_shift_p7d` | `344.53` | `347.56` | `348.31` |
| `Bits 12-13` | `>> 12` | `astro_saturn_dec_app_median_shift_p7d` | `-8.3816` | `-7.2002` | `-6.9142` |
| `Bits 14-15` | `>> 14` | `astro_saturn_azim_median_shift_p7d` | `151.96` | `186.18` | `196.55` |

### Container: `packed_astro_container_195` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_elev_median_shift_p7d` | `38.641` | `42.969` | `42.969` |
| `Bits 2-3` | `>> 2` | `astro_saturn_app_mag_median_shift_p7d` | `1.0385` | `1.072` | `1.072` |
| `Bits 4-5` | `>> 4` | `astro_saturn_surf_bright_median_shift_p7d` | `6.7428` | `6.832` | `6.853` |
| `Bits 6-7` | `>> 6` | `astro_saturn_dist_median_shift_p7d` | `10.267` | `10.374` | `10.643` |
| `Bits 8-9` | `>> 8` | `astro_saturn_dist_rate_median_shift_p7d` | `-23.146` | `-20.752` | `-10.079` |
| `Bits 10-11` | `>> 10` | `astro_saturn_helio_dist_median_shift_p7d` | `9.7035` | `9.7059` | `9.7145` |
| `Bits 12-13` | `>> 12` | `astro_saturn_helio_dist_rate_median_shift_p7d` | `-0.50384` | `-0.50169` | `-0.49898` |
| `Bits 14-15` | `>> 14` | `astro_saturn_phase_angle_median_shift_p7d` | `2.018` | `4.2735` | `4.7921` |

### Container: `packed_astro_container_196` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_elong_median_shift_p7d` | `20.133` | `46.138` | `53.613` |
| `Bits 2-3` | `>> 2` | `astro_saturn_illum_frac_median_shift_p7d` | `66.824` | `66.824` | `80.404` |
| `Bits 4-5` | `>> 4` | `astro_mercury_ra_icrf_median_shift_p7d` | `16.004` | `16.004` | `21.926` |
| `Bits 6-7` | `>> 6` | `astro_mercury_dec_icrf_median_shift_p7d` | `4.4509` | `4.4509` | `6.9879` |
| `Bits 8-9` | `>> 8` | `astro_mercury_ra_app_median_shift_p7d` | `16.312` | `16.312` | `22.24` |
| `Bits 10-11` | `>> 10` | `astro_mercury_dec_app_median_shift_p7d` | `4.579` | `4.579` | `7.1159` |
| `Bits 12-13` | `>> 12` | `astro_mercury_azim_median_shift_p7d` | `118.97` | `143.02` | `153.11` |
| `Bits 14-15` | `>> 14` | `astro_mercury_elev_median_shift_p7d` | `32.863` | `51.019` | `52.905` |

### Container: `packed_astro_container_197` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mercury_app_mag_median_shift_p7d` | `-0.372` | `1.087` | `1.087` |
| `Bits 2-3` | `>> 2` | `astro_mercury_surf_bright_median_shift_p7d` | `2.8585` | `4.254` | `4.254` |
| `Bits 4-5` | `>> 4` | `astro_mercury_dist_median_shift_p7d` | `0.6852` | `0.6852` | `0.95732` |
| `Bits 6-7` | `>> 6` | `astro_mercury_dist_rate_median_shift_p7d` | `-20.128` | `11.249` | `21.81` |
| `Bits 8-9` | `>> 8` | `astro_mercury_helio_dist_median_shift_p7d` | `0.37728` | `0.45341` | `0.46664` |
| `Bits 10-11` | `>> 10` | `astro_mercury_helio_dist_rate_median_shift_p7d` | `0.32913` | `0.32913` | `3.3624` |
| `Bits 12-13` | `>> 12` | `astro_mercury_phase_angle_median_shift_p7d` | `87.92` | `120.79` | `120.79` |
| `Bits 14-15` | `>> 14` | `astro_mercury_elong_median_shift_p7d` | `10.812` | `18.742` | `23.453` |

### Container: `packed_astro_container_198` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mercury_illum_frac_median_shift_p7d` | `66.824` | `66.824` | `80.404` |
| `Bits 2-3` | `>> 2` | `astro_venus_ra_icrf_median_shift_p7d` | `28.651` | `28.651` | `324.07` |
| `Bits 4-5` | `>> 4` | `astro_venus_dec_icrf_median_shift_p7d` | `-7.8721` | `6.4399` | `10.407` |
| `Bits 6-7` | `>> 6` | `astro_venus_ra_app_median_shift_p7d` | `28.968` | `28.968` | `324.39` |
| `Bits 8-9` | `>> 8` | `astro_venus_dec_app_median_shift_p7d` | `-7.7452` | `6.5657` | `10.525` |
| `Bits 10-11` | `>> 10` | `astro_venus_azim_median_shift_p7d` | `130.29` | `135.68` | `150.77` |
| `Bits 12-13` | `>> 12` | `astro_venus_elev_median_shift_p7d` | `39.014` | `49.552` | `51.992` |
| `Bits 14-15` | `>> 14` | `astro_venus_app_mag_median_shift_p7d` | `-3.885` | `-3.885` | `-3.8795` |

### Container: `packed_astro_container_199` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_surf_bright_median_shift_p7d` | `0.799` | `0.82` | `0.9045` |
| `Bits 2-3` | `>> 2` | `astro_venus_dist_median_shift_p7d` | `1.5908` | `1.6802` | `1.6989` |
| `Bits 4-5` | `>> 4` | `astro_venus_dist_rate_median_shift_p7d` | `3.2306` | `3.9242` | `6.1182` |
| `Bits 6-7` | `>> 6` | `astro_venus_helio_dist_median_shift_p7d` | `0.72535` | `0.72633` | `0.72771` |
| `Bits 8-9` | `>> 8` | `astro_venus_helio_dist_rate_median_shift_p7d` | `-0.21445` | `-0.18443` | `-0.018372` |
| `Bits 10-11` | `>> 10` | `astro_venus_phase_angle_median_shift_p7d` | `13.368` | `16.419` | `26.798` |
| `Bits 12-13` | `>> 12` | `astro_venus_elong_median_shift_p7d` | `9.5831` | `11.787` | `19.232` |
| `Bits 14-15` | `>> 14` | `astro_venus_illum_frac_median_shift_p7d` | `66.824` | `66.824` | `80.404` |

### Container: `packed_astro_container_200` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_ra_icrf_min_shift_p14d` | `36.455` | `36.455` | `36.455` |
| `Bits 2-3` | `>> 2` | `astro_sun_dec_icrf_min_shift_p14d` | `14.442` | `14.442` | `14.442` |
| `Bits 4-5` | `>> 4` | `astro_sun_ra_app_min_shift_p14d` | `36.78` | `36.78` | `36.78` |
| `Bits 6-7` | `>> 6` | `astro_sun_dec_app_min_shift_p14d` | `14.55` | `14.55` | `14.55` |
| `Bits 8-9` | `>> 8` | `astro_sun_azim_min_shift_p14d` | `115.34` | `115.34` | `115.34` |
| `Bits 10-11` | `>> 10` | `astro_sun_elev_min_shift_p14d` | `49.239` | `49.239` | `49.239` |
| `Bits 12-13` | `>> 12` | `astro_sun_app_mag_min_shift_p14d` | `-26.727` | `-26.727` | `-26.727` |
| `Bits 14-15` | `>> 14` | `astro_sun_dist_min_shift_p14d` | `1.007` | `1.007` | `1.007` |

### Container: `packed_astro_container_201` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_dist_rate_min_shift_p14d` | `0.23974` | `0.23974` | `0.23974` |
| `Bits 2-3` | `>> 2` | `astro_sun_illum_frac_min_shift_p14d` | `56.123` | `56.123` | `56.123` |
| `Bits 4-5` | `>> 4` | `astro_moon_ra_icrf_min_shift_p14d` | `277.73` | `277.73` | `277.73` |
| `Bits 6-7` | `>> 6` | `astro_moon_dec_icrf_min_shift_p14d` | `-28.981` | `-28.981` | `-28.981` |
| `Bits 8-9` | `>> 8` | `astro_moon_ra_app_min_shift_p14d` | `278.12` | `278.12` | `278.12` |
| `Bits 10-11` | `>> 10` | `astro_moon_dec_app_min_shift_p14d` | `-28.964` | `-28.964` | `-28.964` |
| `Bits 12-13` | `>> 12` | `astro_moon_azim_min_shift_p14d` | `227.79` | `227.79` | `227.79` |
| `Bits 14-15` | `>> 14` | `astro_moon_elev_min_shift_p14d` | `-11.546` | `-11.546` | `-11.546` |

### Container: `packed_astro_container_202` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_app_mag_min_shift_p14d` | `-11.149` | `-11.149` | `-11.149` |
| `Bits 2-3` | `>> 2` | `astro_moon_surf_bright_min_shift_p14d` | `4.651` | `4.651` | `4.651` |
| `Bits 4-5` | `>> 4` | `astro_moon_dist_min_shift_p14d` | `0.0025021` | `0.0025031` | `0.0025041` |
| `Bits 6-7` | `>> 6` | `astro_moon_dist_rate_min_shift_p14d` | `0.2064` | `0.20641` | `0.20641` |
| `Bits 8-9` | `>> 8` | `astro_moon_helio_dist_min_shift_p14d` | `1.0078` | `1.0078` | `1.0078` |
| `Bits 10-11` | `>> 10` | `astro_moon_helio_dist_rate_min_shift_p14d` | `-0.51557` | `-0.51556` | `-0.51556` |
| `Bits 12-13` | `>> 12` | `astro_moon_phase_angle_min_shift_p14d` | `58.02` | `58.02` | `58.02` |
| `Bits 14-15` | `>> 14` | `astro_moon_elong_min_shift_p14d` | `96.892` | `96.892` | `96.892` |

### Container: `packed_astro_container_203` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_illum_frac_min_shift_p14d` | `56.123` | `56.123` | `56.123` |
| `Bits 2-3` | `>> 2` | `astro_mars_ra_icrf_min_shift_p14d` | `0.44575` | `0.44575` | `0.44575` |
| `Bits 4-5` | `>> 4` | `astro_mars_dec_icrf_min_shift_p14d` | `-1.8007` | `-1.8007` | `-1.8007` |
| `Bits 6-7` | `>> 6` | `astro_mars_ra_app_min_shift_p14d` | `0.0452` | `0.045201` | `0.045202` |
| `Bits 8-9` | `>> 8` | `astro_mars_dec_app_min_shift_p14d` | `-1.6676` | `-1.6676` | `-1.6676` |
| `Bits 10-11` | `>> 10` | `astro_mars_azim_min_shift_p14d` | `180.16` | `180.16` | `180.16` |
| `Bits 12-13` | `>> 12` | `astro_mars_elev_min_shift_p14d` | `49.582` | `49.582` | `49.582` |
| `Bits 14-15` | `>> 14` | `astro_mars_app_mag_min_shift_p14d` | `1.172` | `1.172` | `1.172` |

### Container: `packed_astro_container_204` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_surf_bright_min_shift_p14d` | `4.219` | `4.219` | `4.219` |
| `Bits 2-3` | `>> 2` | `astro_mars_dist_min_shift_p14d` | `1.9766` | `1.9766` | `1.9766` |
| `Bits 4-5` | `>> 4` | `astro_mars_dist_rate_min_shift_p14d` | `-6.5135` | `-6.5135` | `-6.5135` |
| `Bits 6-7` | `>> 6` | `astro_mars_helio_dist_min_shift_p14d` | `1.3819` | `1.3819` | `1.3819` |
| `Bits 8-9` | `>> 8` | `astro_mars_helio_dist_rate_min_shift_p14d` | `-0.23626` | `-0.23626` | `-0.23625` |
| `Bits 10-11` | `>> 10` | `astro_mars_phase_angle_min_shift_p14d` | `28.216` | `28.216` | `28.216` |
| `Bits 12-13` | `>> 12` | `astro_mars_elong_min_shift_p14d` | `40.459` | `40.459` | `40.459` |
| `Bits 14-15` | `>> 14` | `astro_mars_illum_frac_min_shift_p14d` | `56.123` | `56.123` | `56.123` |

### Container: `packed_astro_container_205` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_ra_icrf_min_shift_p14d` | `51.134` | `51.134` | `51.134` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_dec_icrf_min_shift_p14d` | `17.864` | `17.864` | `17.864` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_ra_app_min_shift_p14d` | `51.472` | `51.472` | `51.472` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_dec_app_min_shift_p14d` | `17.949` | `17.949` | `17.949` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_azim_min_shift_p14d` | `99.539` | `99.539` | `99.539` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_elev_min_shift_p14d` | `40.494` | `40.494` | `40.494` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_app_mag_min_shift_p14d` | `-2.008` | `-2.008` | `-2.008` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_surf_bright_min_shift_p14d` | `5.319` | `5.319` | `5.319` |

### Container: `packed_astro_container_206` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_dist_min_shift_p14d` | `5.9794` | `5.9794` | `5.9794` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_dist_rate_min_shift_p14d` | `6.6384` | `6.6384` | `6.6384` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_helio_dist_min_shift_p14d` | `5.0109` | `5.0109` | `5.0109` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_helio_dist_rate_min_shift_p14d` | `0.42497` | `0.42497` | `0.42497` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_phase_angle_min_shift_p14d` | `2.6008` | `2.6008` | `2.6008` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_elong_min_shift_p14d` | `13.03` | `13.03` | `13.03` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_illum_frac_min_shift_p14d` | `56.123` | `56.123` | `56.123` |
| `Bits 14-15` | `>> 14` | `astro_saturn_ra_icrf_min_shift_p14d` | `347.91` | `347.91` | `347.91` |

### Container: `packed_astro_container_207` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_dec_icrf_min_shift_p14d` | `-7.0762` | `-7.0762` | `-7.0762` |
| `Bits 2-3` | `>> 2` | `astro_saturn_ra_app_min_shift_p14d` | `348.22` | `348.22` | `348.22` |
| `Bits 4-5` | `>> 4` | `astro_saturn_dec_app_min_shift_p14d` | `-6.946` | `-6.946` | `-6.946` |
| `Bits 6-7` | `>> 6` | `astro_saturn_azim_min_shift_p14d` | `195.35` | `195.35` | `195.35` |
| `Bits 8-9` | `>> 8` | `astro_saturn_elev_min_shift_p14d` | `42.791` | `42.791` | `42.791` |
| `Bits 10-11` | `>> 10` | `astro_saturn_app_mag_min_shift_p14d` | `1.072` | `1.072` | `1.072` |
| `Bits 12-13` | `>> 12` | `astro_saturn_surf_bright_min_shift_p14d` | `6.851` | `6.851` | `6.851` |
| `Bits 14-15` | `>> 14` | `astro_saturn_dist_min_shift_p14d` | `10.254` | `10.254` | `10.254` |

### Container: `packed_astro_container_208` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_dist_rate_min_shift_p14d` | `-23.403` | `-23.403` | `-23.403` |
| `Bits 2-3` | `>> 2` | `astro_saturn_helio_dist_min_shift_p14d` | `9.7032` | `9.7032` | `9.7032` |
| `Bits 4-5` | `>> 4` | `astro_saturn_helio_dist_rate_min_shift_p14d` | `-0.50417` | `-0.50417` | `-0.50417` |
| `Bits 6-7` | `>> 6` | `astro_saturn_phase_angle_min_shift_p14d` | `4.7356` | `4.7356` | `4.7356` |
| `Bits 8-9` | `>> 8` | `astro_saturn_elong_min_shift_p14d` | `52.731` | `52.731` | `52.731` |
| `Bits 10-11` | `>> 10` | `astro_saturn_illum_frac_min_shift_p14d` | `56.123` | `56.123` | `56.123` |
| `Bits 12-13` | `>> 12` | `astro_mercury_ra_icrf_min_shift_p14d` | `15.645` | `15.645` | `15.645` |
| `Bits 14-15` | `>> 14` | `astro_mercury_dec_icrf_min_shift_p14d` | `4.4464` | `4.4464` | `4.4464` |

### Container: `packed_astro_container_209` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mercury_ra_app_min_shift_p14d` | `15.953` | `15.953` | `15.953` |
| `Bits 2-3` | `>> 2` | `astro_mercury_dec_app_min_shift_p14d` | `4.5747` | `4.5747` | `4.5747` |
| `Bits 4-5` | `>> 4` | `astro_mercury_azim_min_shift_p14d` | `152.12` | `152.12` | `152.12` |
| `Bits 6-7` | `>> 6` | `astro_mercury_elev_min_shift_p14d` | `52.715` | `52.715` | `52.715` |
| `Bits 8-9` | `>> 8` | `astro_mercury_app_mag_min_shift_p14d` | `0.998` | `0.998` | `0.998` |
| `Bits 10-11` | `>> 10` | `astro_mercury_surf_bright_min_shift_p14d` | `4.203` | `4.203` | `4.203` |
| `Bits 12-13` | `>> 12` | `astro_mercury_dist_min_shift_p14d` | `0.67278` | `0.67279` | `0.67279` |
| `Bits 14-15` | `>> 14` | `astro_mercury_dist_rate_min_shift_p14d` | `20.977` | `20.977` | `20.977` |

### Container: `packed_astro_container_210` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mercury_helio_dist_min_shift_p14d` | `0.46631` | `0.46631` | `0.46631` |
| `Bits 2-3` | `>> 2` | `astro_mercury_helio_dist_rate_min_shift_p14d` | `-0.15454` | `-0.15454` | `-0.15454` |
| `Bits 4-5` | `>> 4` | `astro_mercury_phase_angle_min_shift_p14d` | `118.41` | `118.41` | `118.41` |
| `Bits 6-7` | `>> 6` | `astro_mercury_elong_min_shift_p14d` | `22.786` | `22.786` | `22.786` |
| `Bits 8-9` | `>> 8` | `astro_mercury_illum_frac_min_shift_p14d` | `56.123` | `56.123` | `56.123` |
| `Bits 10-11` | `>> 10` | `astro_venus_ra_icrf_min_shift_p14d` | `27.487` | `27.487` | `27.487` |
| `Bits 12-13` | `>> 12` | `astro_venus_dec_icrf_min_shift_p14d` | `9.9547` | `9.9547` | `9.9547` |
| `Bits 14-15` | `>> 14` | `astro_venus_ra_app_min_shift_p14d` | `27.803` | `27.803` | `27.803` |

### Container: `packed_astro_container_211` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_dec_app_min_shift_p14d` | `10.073` | `10.073` | `10.073` |
| `Bits 2-3` | `>> 2` | `astro_venus_azim_min_shift_p14d` | `129.61` | `129.61` | `129.61` |
| `Bits 4-5` | `>> 4` | `astro_venus_elev_min_shift_p14d` | `51.738` | `51.738` | `51.738` |
| `Bits 6-7` | `>> 6` | `astro_venus_app_mag_min_shift_p14d` | `-3.885` | `-3.885` | `-3.885` |
| `Bits 8-9` | `>> 8` | `astro_venus_surf_bright_min_shift_p14d` | `0.797` | `0.797` | `0.797` |
| `Bits 10-11` | `>> 10` | `astro_venus_dist_min_shift_p14d` | `1.6969` | `1.6969` | `1.6969` |
| `Bits 12-13` | `>> 12` | `astro_venus_dist_rate_min_shift_p14d` | `3.1446` | `3.1446` | `3.1446` |
| `Bits 14-15` | `>> 14` | `astro_venus_helio_dist_min_shift_p14d` | `0.72523` | `0.72523` | `0.72523` |

### Container: `packed_astro_container_212` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_helio_dist_rate_min_shift_p14d` | `-0.21712` | `-0.21712` | `-0.21712` |
| `Bits 2-3` | `>> 2` | `astro_venus_phase_angle_min_shift_p14d` | `13.005` | `13.005` | `13.005` |
| `Bits 4-5` | `>> 4` | `astro_venus_elong_min_shift_p14d` | `9.3214` | `9.3214` | `9.3214` |
| `Bits 6-7` | `>> 6` | `astro_venus_illum_frac_min_shift_p14d` | `56.123` | `56.123` | `56.123` |
| `Bits 8-9` | `>> 8` | `astro_sun_ra_icrf_max_shift_p14d` | `38.36` | `38.36` | `38.36` |
| `Bits 10-11` | `>> 10` | `astro_sun_dec_icrf_max_shift_p14d` | `15.056` | `15.056` | `15.056` |
| `Bits 12-13` | `>> 12` | `astro_sun_ra_app_max_shift_p14d` | `38.687` | `38.687` | `38.687` |
| `Bits 14-15` | `>> 14` | `astro_sun_dec_app_max_shift_p14d` | `15.161` | `15.161` | `15.161` |

### Container: `packed_astro_container_213` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_azim_max_shift_p14d` | `115.96` | `115.96` | `115.96` |
| `Bits 2-3` | `>> 2` | `astro_sun_elev_max_shift_p14d` | `49.703` | `49.703` | `49.703` |
| `Bits 4-5` | `>> 4` | `astro_sun_app_mag_max_shift_p14d` | `-26.726` | `-26.726` | `-26.726` |
| `Bits 6-7` | `>> 6` | `astro_sun_dist_max_shift_p14d` | `1.0075` | `1.0075` | `1.0075` |
| `Bits 8-9` | `>> 8` | `astro_sun_dist_rate_max_shift_p14d` | `0.24478` | `0.24478` | `0.24478` |
| `Bits 10-11` | `>> 10` | `astro_sun_illum_frac_max_shift_p14d` | `76.483` | `76.483` | `76.483` |
| `Bits 12-13` | `>> 12` | `astro_moon_ra_icrf_max_shift_p14d` | `307.59` | `307.59` | `307.59` |
| `Bits 14-15` | `>> 14` | `astro_moon_dec_icrf_max_shift_p14d` | `-24.633` | `-24.633` | `-24.633` |

### Container: `packed_astro_container_214` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_ra_app_max_shift_p14d` | `307.95` | `307.95` | `307.95` |
| `Bits 2-3` | `>> 2` | `astro_moon_dec_app_max_shift_p14d` | `-24.551` | `-24.551` | `-24.551` |
| `Bits 4-5` | `>> 4` | `astro_moon_azim_max_shift_p14d` | `241.98` | `241.98` | `241.98` |
| `Bits 6-7` | `>> 6` | `astro_moon_elev_max_shift_p14d` | `9.3349` | `9.3349` | `9.3349` |
| `Bits 8-9` | `>> 8` | `astro_moon_app_mag_max_shift_p14d` | `-10.415` | `-10.415` | `-10.415` |
| `Bits 10-11` | `>> 10` | `astro_moon_surf_bright_max_shift_p14d` | `5.106` | `5.106` | `5.106` |
| `Bits 12-13` | `>> 12` | `astro_moon_dist_max_shift_p14d` | `0.0025695` | `0.0025705` | `0.0025715` |
| `Bits 14-15` | `>> 14` | `astro_moon_dist_rate_max_shift_p14d` | `0.25633` | `0.25634` | `0.25634` |

### Container: `packed_astro_container_215` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_helio_dist_max_shift_p14d` | `1.0083` | `1.0083` | `1.0083` |
| `Bits 2-3` | `>> 2` | `astro_moon_helio_dist_rate_max_shift_p14d` | `-0.37549` | `-0.37549` | `-0.37549` |
| `Bits 4-5` | `>> 4` | `astro_moon_phase_angle_max_shift_p14d` | `82.967` | `82.967` | `82.967` |
| `Bits 6-7` | `>> 6` | `astro_moon_elong_max_shift_p14d` | `121.86` | `121.86` | `121.86` |
| `Bits 8-9` | `>> 8` | `astro_moon_illum_frac_max_shift_p14d` | `76.483` | `76.483` | `76.483` |
| `Bits 10-11` | `>> 10` | `astro_mars_ra_icrf_max_shift_p14d` | `359.74` | `359.74` | `359.74` |
| `Bits 12-13` | `>> 12` | `astro_mars_dec_icrf_max_shift_p14d` | `-1.1864` | `-1.1864` | `-1.1864` |
| `Bits 14-15` | `>> 14` | `astro_mars_ra_app_max_shift_p14d` | `359.34` | `359.34` | `359.34` |

### Container: `packed_astro_container_216` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_dec_app_max_shift_p14d` | `-1.0531` | `-1.0531` | `-1.0531` |
| `Bits 2-3` | `>> 2` | `astro_mars_azim_max_shift_p14d` | `181.03` | `181.03` | `181.03` |
| `Bits 4-5` | `>> 4` | `astro_mars_elev_max_shift_p14d` | `50.192` | `50.192` | `50.192` |
| `Bits 6-7` | `>> 6` | `astro_mars_app_mag_max_shift_p14d` | `1.183` | `1.183` | `1.183` |
| `Bits 8-9` | `>> 8` | `astro_mars_surf_bright_max_shift_p14d` | `4.223` | `4.223` | `4.223` |
| `Bits 10-11` | `>> 10` | `astro_mars_dist_max_shift_p14d` | `1.9841` | `1.9841` | `1.9841` |
| `Bits 12-13` | `>> 12` | `astro_mars_dist_rate_max_shift_p14d` | `-6.5092` | `-6.5092` | `-6.5092` |
| `Bits 14-15` | `>> 14` | `astro_mars_helio_dist_max_shift_p14d` | `1.3822` | `1.3822` | `1.3822` |

### Container: `packed_astro_container_217` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_helio_dist_rate_max_shift_p14d` | `-0.18645` | `-0.18645` | `-0.18644` |
| `Bits 2-3` | `>> 2` | `astro_mars_phase_angle_max_shift_p14d` | `28.489` | `28.489` | `28.489` |
| `Bits 4-5` | `>> 4` | `astro_mars_elong_max_shift_p14d` | `40.859` | `40.859` | `40.859` |
| `Bits 6-7` | `>> 6` | `astro_mars_illum_frac_max_shift_p14d` | `76.483` | `76.483` | `76.483` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_ra_icrf_max_shift_p14d` | `51.608` | `51.608` | `51.608` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_dec_icrf_max_shift_p14d` | `17.984` | `17.984` | `17.984` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_ra_app_max_shift_p14d` | `51.947` | `51.947` | `51.947` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_dec_app_max_shift_p14d` | `18.068` | `18.068` | `18.068` |

### Container: `packed_astro_container_218` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_azim_max_shift_p14d` | `100.53` | `100.53` | `100.53` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_elev_max_shift_p14d` | `41.714` | `41.714` | `41.714` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_app_mag_max_shift_p14d` | `-2.006` | `-2.006` | `-2.006` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_surf_bright_max_shift_p14d` | `5.319` | `5.319` | `5.319` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_dist_max_shift_p14d` | `5.9878` | `5.9878` | `5.9878` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_dist_rate_max_shift_p14d` | `7.3096` | `7.3096` | `7.3096` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_helio_dist_max_shift_p14d` | `5.0114` | `5.0114` | `5.0114` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_helio_dist_rate_max_shift_p14d` | `0.42614` | `0.42614` | `0.42614` |

### Container: `packed_astro_container_219` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_phase_angle_max_shift_p14d` | `2.8877` | `2.8877` | `2.8877` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_elong_max_shift_p14d` | `14.504` | `14.504` | `14.504` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_illum_frac_max_shift_p14d` | `76.483` | `76.483` | `76.483` |
| `Bits 6-7` | `>> 6` | `astro_saturn_ra_icrf_max_shift_p14d` | `348.08` | `348.08` | `348.08` |
| `Bits 8-9` | `>> 8` | `astro_saturn_dec_icrf_max_shift_p14d` | `-7.0132` | `-7.0132` | `-7.0132` |
| `Bits 10-11` | `>> 10` | `astro_saturn_ra_app_max_shift_p14d` | `348.39` | `348.39` | `348.39` |
| `Bits 12-13` | `>> 12` | `astro_saturn_dec_app_max_shift_p14d` | `-6.8828` | `-6.8828` | `-6.8828` |
| `Bits 14-15` | `>> 14` | `astro_saturn_azim_max_shift_p14d` | `197.75` | `197.75` | `197.75` |

### Container: `packed_astro_container_220` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_elev_max_shift_p14d` | `43.131` | `43.131` | `43.131` |
| `Bits 2-3` | `>> 2` | `astro_saturn_app_mag_max_shift_p14d` | `1.072` | `1.072` | `1.072` |
| `Bits 4-5` | `>> 4` | `astro_saturn_surf_bright_max_shift_p14d` | `6.856` | `6.856` | `6.856` |
| `Bits 6-7` | `>> 6` | `astro_saturn_dist_max_shift_p14d` | `10.28` | `10.28` | `10.28` |
| `Bits 8-9` | `>> 8` | `astro_saturn_dist_rate_max_shift_p14d` | `-22.885` | `-22.885` | `-22.885` |
| `Bits 10-11` | `>> 10` | `astro_saturn_helio_dist_max_shift_p14d` | `9.7037` | `9.7037` | `9.7038` |
| `Bits 12-13` | `>> 12` | `astro_saturn_helio_dist_rate_max_shift_p14d` | `-0.50336` | `-0.50336` | `-0.50336` |
| `Bits 14-15` | `>> 14` | `astro_saturn_phase_angle_max_shift_p14d` | `4.8475` | `4.8475` | `4.8475` |

### Container: `packed_astro_container_221` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_elong_max_shift_p14d` | `54.495` | `54.495` | `54.495` |
| `Bits 2-3` | `>> 2` | `astro_saturn_illum_frac_max_shift_p14d` | `76.483` | `76.483` | `76.483` |
| `Bits 4-5` | `>> 4` | `astro_mercury_ra_icrf_max_shift_p14d` | `16.427` | `16.427` | `16.427` |
| `Bits 6-7` | `>> 6` | `astro_mercury_dec_icrf_max_shift_p14d` | `4.483` | `4.483` | `4.483` |
| `Bits 8-9` | `>> 8` | `astro_mercury_ra_app_max_shift_p14d` | `16.735` | `16.735` | `16.735` |
| `Bits 10-11` | `>> 10` | `astro_mercury_dec_app_max_shift_p14d` | `4.6114` | `4.6114` | `4.6114` |
| `Bits 12-13` | `>> 12` | `astro_mercury_azim_max_shift_p14d` | `153.98` | `153.98` | `153.98` |
| `Bits 14-15` | `>> 14` | `astro_mercury_elev_max_shift_p14d` | `53.105` | `53.105` | `53.105` |

### Container: `packed_astro_container_222` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mercury_app_mag_max_shift_p14d` | `1.187` | `1.187` | `1.187` |
| `Bits 2-3` | `>> 2` | `astro_mercury_surf_bright_max_shift_p14d` | `4.31` | `4.31` | `4.31` |
| `Bits 4-5` | `>> 4` | `astro_mercury_dist_max_shift_p14d` | `0.69808` | `0.69808` | `0.69808` |
| `Bits 6-7` | `>> 6` | `astro_mercury_dist_rate_max_shift_p14d` | `22.578` | `22.578` | `22.578` |
| `Bits 8-9` | `>> 8` | `astro_mercury_helio_dist_max_shift_p14d` | `0.46669` | `0.46669` | `0.46669` |
| `Bits 10-11` | `>> 10` | `astro_mercury_helio_dist_rate_max_shift_p14d` | `0.81244` | `0.81244` | `0.81244` |
| `Bits 12-13` | `>> 12` | `astro_mercury_phase_angle_max_shift_p14d` | `123.24` | `123.24` | `123.24` |
| `Bits 14-15` | `>> 14` | `astro_mercury_elong_max_shift_p14d` | `24.043` | `24.043` | `24.043` |

### Container: `packed_astro_container_223` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mercury_illum_frac_max_shift_p14d` | `76.483` | `76.483` | `76.483` |
| `Bits 2-3` | `>> 2` | `astro_venus_ra_icrf_max_shift_p14d` | `29.818` | `29.818` | `29.818` |
| `Bits 4-5` | `>> 4` | `astro_venus_dec_icrf_max_shift_p14d` | `10.856` | `10.856` | `10.856` |
| `Bits 6-7` | `>> 6` | `astro_venus_ra_app_max_shift_p14d` | `30.136` | `30.136` | `30.136` |
| `Bits 8-9` | `>> 8` | `astro_venus_dec_app_max_shift_p14d` | `10.972` | `10.972` | `10.972` |
| `Bits 10-11` | `>> 10` | `astro_venus_azim_max_shift_p14d` | `130.96` | `130.96` | `130.96` |
| `Bits 12-13` | `>> 12` | `astro_venus_elev_max_shift_p14d` | `52.238` | `52.238` | `52.238` |
| `Bits 14-15` | `>> 14` | `astro_venus_app_mag_max_shift_p14d` | `-3.884` | `-3.884` | `-3.884` |

### Container: `packed_astro_container_224` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_surf_bright_max_shift_p14d` | `0.802` | `0.802` | `0.802` |
| `Bits 2-3` | `>> 2` | `astro_venus_dist_max_shift_p14d` | `1.7008` | `1.7008` | `1.7008` |
| `Bits 4-5` | `>> 4` | `astro_venus_dist_rate_max_shift_p14d` | `3.3157` | `3.3157` | `3.3157` |
| `Bits 6-7` | `>> 6` | `astro_venus_helio_dist_max_shift_p14d` | `0.72548` | `0.72548` | `0.72548` |
| `Bits 8-9` | `>> 8` | `astro_venus_helio_dist_rate_max_shift_p14d` | `-0.21161` | `-0.21161` | `-0.2116` |
| `Bits 10-11` | `>> 10` | `astro_venus_phase_angle_max_shift_p14d` | `13.73` | `13.73` | `13.73` |
| `Bits 12-13` | `>> 12` | `astro_venus_elong_max_shift_p14d` | `9.8445` | `9.8445` | `9.8445` |
| `Bits 14-15` | `>> 14` | `astro_venus_illum_frac_max_shift_p14d` | `76.483` | `76.483` | `76.483` |

### Container: `packed_astro_container_225` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_ra_icrf_mean_shift_p14d` | `37.407` | `37.407` | `37.407` |
| `Bits 2-3` | `>> 2` | `astro_sun_dec_icrf_mean_shift_p14d` | `14.749` | `14.749` | `14.749` |
| `Bits 4-5` | `>> 4` | `astro_sun_ra_app_mean_shift_p14d` | `37.733` | `37.733` | `37.733` |
| `Bits 6-7` | `>> 6` | `astro_sun_dec_app_mean_shift_p14d` | `14.856` | `14.856` | `14.856` |
| `Bits 8-9` | `>> 8` | `astro_sun_azim_mean_shift_p14d` | `115.65` | `115.65` | `115.65` |
| `Bits 10-11` | `>> 10` | `astro_sun_elev_mean_shift_p14d` | `49.472` | `49.472` | `49.472` |
| `Bits 12-13` | `>> 12` | `astro_sun_app_mag_mean_shift_p14d` | `-26.726` | `-26.726` | `-26.726` |
| `Bits 14-15` | `>> 14` | `astro_sun_dist_mean_shift_p14d` | `1.0073` | `1.0073` | `1.0073` |

### Container: `packed_astro_container_226` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_dist_rate_mean_shift_p14d` | `0.24236` | `0.24236` | `0.24237` |
| `Bits 2-3` | `>> 2` | `astro_sun_illum_frac_mean_shift_p14d` | `66.477` | `66.477` | `66.477` |
| `Bits 4-5` | `>> 4` | `astro_moon_ra_icrf_mean_shift_p14d` | `292.7` | `292.7` | `292.7` |
| `Bits 6-7` | `>> 6` | `astro_moon_dec_icrf_mean_shift_p14d` | `-27.077` | `-27.077` | `-27.077` |
| `Bits 8-9` | `>> 8` | `astro_moon_ra_app_mean_shift_p14d` | `293.08` | `293.08` | `293.08` |
| `Bits 10-11` | `>> 10` | `astro_moon_dec_app_mean_shift_p14d` | `-27.027` | `-27.027` | `-27.027` |
| `Bits 12-13` | `>> 12` | `astro_moon_azim_mean_shift_p14d` | `234.88` | `234.88` | `234.88` |
| `Bits 14-15` | `>> 14` | `astro_moon_elev_mean_shift_p14d` | `-1.1663` | `-1.1663` | `-1.1663` |

### Container: `packed_astro_container_227` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_app_mag_mean_shift_p14d` | `-10.79` | `-10.79` | `-10.79` |
| `Bits 2-3` | `>> 2` | `astro_moon_surf_bright_mean_shift_p14d` | `4.8777` | `4.8777` | `4.8777` |
| `Bits 4-5` | `>> 4` | `astro_moon_dist_mean_shift_p14d` | `0.0025359` | `0.0025369` | `0.0025379` |
| `Bits 6-7` | `>> 6` | `astro_moon_dist_rate_mean_shift_p14d` | `0.2334` | `0.2334` | `0.2334` |
| `Bits 8-9` | `>> 8` | `astro_moon_helio_dist_mean_shift_p14d` | `1.0081` | `1.0081` | `1.0081` |
| `Bits 10-11` | `>> 10` | `astro_moon_helio_dist_rate_mean_shift_p14d` | `-0.45221` | `-0.45221` | `-0.45221` |
| `Bits 12-13` | `>> 12` | `astro_moon_phase_angle_mean_shift_p14d` | `70.442` | `70.442` | `70.442` |
| `Bits 14-15` | `>> 14` | `astro_moon_elong_mean_shift_p14d` | `109.42` | `109.42` | `109.42` |

### Container: `packed_astro_container_228` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_illum_frac_mean_shift_p14d` | `66.477` | `66.477` | `66.477` |
| `Bits 2-3` | `>> 2` | `astro_mars_ra_icrf_mean_shift_p14d` | `239.74` | `239.74` | `239.74` |
| `Bits 4-5` | `>> 4` | `astro_mars_dec_icrf_mean_shift_p14d` | `-1.4935` | `-1.4935` | `-1.4935` |
| `Bits 6-7` | `>> 6` | `astro_mars_ra_app_mean_shift_p14d` | `120.05` | `120.05` | `120.05` |
| `Bits 8-9` | `>> 8` | `astro_mars_dec_app_mean_shift_p14d` | `-1.3604` | `-1.3603` | `-1.3603` |
| `Bits 10-11` | `>> 10` | `astro_mars_azim_mean_shift_p14d` | `180.6` | `180.6` | `180.6` |
| `Bits 12-13` | `>> 12` | `astro_mars_elev_mean_shift_p14d` | `49.888` | `49.888` | `49.888` |
| `Bits 14-15` | `>> 14` | `astro_mars_app_mag_mean_shift_p14d` | `1.178` | `1.178` | `1.178` |

### Container: `packed_astro_container_229` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_surf_bright_mean_shift_p14d` | `4.2213` | `4.2213` | `4.2213` |
| `Bits 2-3` | `>> 2` | `astro_mars_dist_mean_shift_p14d` | `1.9803` | `1.9803` | `1.9803` |
| `Bits 4-5` | `>> 4` | `astro_mars_dist_rate_mean_shift_p14d` | `-6.5112` | `-6.5112` | `-6.5112` |
| `Bits 6-7` | `>> 6` | `astro_mars_helio_dist_mean_shift_p14d` | `1.382` | `1.382` | `1.382` |
| `Bits 8-9` | `>> 8` | `astro_mars_helio_dist_rate_mean_shift_p14d` | `-0.21136` | `-0.21136` | `-0.21135` |
| `Bits 10-11` | `>> 10` | `astro_mars_phase_angle_mean_shift_p14d` | `28.352` | `28.352` | `28.352` |
| `Bits 12-13` | `>> 12` | `astro_mars_elong_mean_shift_p14d` | `40.659` | `40.659` | `40.659` |
| `Bits 14-15` | `>> 14` | `astro_mars_illum_frac_mean_shift_p14d` | `66.477` | `66.477` | `66.477` |

### Container: `packed_astro_container_230` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_ra_icrf_mean_shift_p14d` | `51.371` | `51.371` | `51.371` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_dec_icrf_mean_shift_p14d` | `17.924` | `17.924` | `17.924` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_ra_app_mean_shift_p14d` | `51.71` | `51.71` | `51.71` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_dec_app_mean_shift_p14d` | `18.008` | `18.008` | `18.008` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_azim_mean_shift_p14d` | `100.03` | `100.03` | `100.03` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_elev_mean_shift_p14d` | `41.104` | `41.104` | `41.104` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_app_mag_mean_shift_p14d` | `-2.007` | `-2.007` | `-2.007` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_surf_bright_mean_shift_p14d` | `5.319` | `5.319` | `5.319` |

### Container: `packed_astro_container_231` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_dist_mean_shift_p14d` | `5.9837` | `5.9837` | `5.9837` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_dist_rate_mean_shift_p14d` | `6.9745` | `6.9745` | `6.9745` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_helio_dist_mean_shift_p14d` | `5.0111` | `5.0111` | `5.0111` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_helio_dist_rate_mean_shift_p14d` | `0.42537` | `0.42537` | `0.42537` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_phase_angle_mean_shift_p14d` | `2.7443` | `2.7443` | `2.7443` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_elong_mean_shift_p14d` | `13.767` | `13.767` | `13.767` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_illum_frac_mean_shift_p14d` | `66.477` | `66.477` | `66.477` |
| `Bits 14-15` | `>> 14` | `astro_saturn_ra_icrf_mean_shift_p14d` | `347.99` | `347.99` | `347.99` |

### Container: `packed_astro_container_232` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_dec_icrf_mean_shift_p14d` | `-7.0446` | `-7.0446` | `-7.0446` |
| `Bits 2-3` | `>> 2` | `astro_saturn_ra_app_mean_shift_p14d` | `348.31` | `348.31` | `348.31` |
| `Bits 4-5` | `>> 4` | `astro_saturn_dec_app_mean_shift_p14d` | `-6.9143` | `-6.9143` | `-6.9143` |
| `Bits 6-7` | `>> 6` | `astro_saturn_azim_mean_shift_p14d` | `196.55` | `196.55` | `196.55` |
| `Bits 8-9` | `>> 8` | `astro_saturn_elev_mean_shift_p14d` | `42.964` | `42.964` | `42.964` |
| `Bits 10-11` | `>> 10` | `astro_saturn_app_mag_mean_shift_p14d` | `1.072` | `1.072` | `1.072` |
| `Bits 12-13` | `>> 12` | `astro_saturn_surf_bright_mean_shift_p14d` | `6.8533` | `6.8533` | `6.8533` |
| `Bits 14-15` | `>> 14` | `astro_saturn_dist_mean_shift_p14d` | `10.267` | `10.267` | `10.267` |

### Container: `packed_astro_container_233` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_dist_rate_mean_shift_p14d` | `-23.145` | `-23.145` | `-23.145` |
| `Bits 2-3` | `>> 2` | `astro_saturn_helio_dist_mean_shift_p14d` | `9.7035` | `9.7035` | `9.7035` |
| `Bits 4-5` | `>> 4` | `astro_saturn_helio_dist_rate_mean_shift_p14d` | `-0.50379` | `-0.50379` | `-0.50379` |
| `Bits 6-7` | `>> 6` | `astro_saturn_phase_angle_mean_shift_p14d` | `4.7917` | `4.7917` | `4.7917` |
| `Bits 8-9` | `>> 8` | `astro_saturn_elong_mean_shift_p14d` | `53.613` | `53.613` | `53.613` |
| `Bits 10-11` | `>> 10` | `astro_saturn_illum_frac_mean_shift_p14d` | `66.477` | `66.477` | `66.477` |
| `Bits 12-13` | `>> 12` | `astro_mercury_ra_icrf_mean_shift_p14d` | `16.025` | `16.025` | `16.025` |
| `Bits 14-15` | `>> 14` | `astro_mercury_dec_icrf_mean_shift_p14d` | `4.4601` | `4.4601` | `4.4601` |

### Container: `packed_astro_container_234` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mercury_ra_app_mean_shift_p14d` | `16.334` | `16.334` | `16.334` |
| `Bits 2-3` | `>> 2` | `astro_mercury_dec_app_mean_shift_p14d` | `4.5884` | `4.5884` | `4.5884` |
| `Bits 4-5` | `>> 4` | `astro_mercury_azim_mean_shift_p14d` | `153.07` | `153.07` | `153.07` |
| `Bits 6-7` | `>> 6` | `astro_mercury_elev_mean_shift_p14d` | `52.908` | `52.908` | `52.908` |
| `Bits 8-9` | `>> 8` | `astro_mercury_app_mag_mean_shift_p14d` | `1.0907` | `1.0907` | `1.0907` |
| `Bits 10-11` | `>> 10` | `astro_mercury_surf_bright_mean_shift_p14d` | `4.2557` | `4.2557` | `4.2557` |
| `Bits 12-13` | `>> 12` | `astro_mercury_dist_mean_shift_p14d` | `0.68535` | `0.68535` | `0.68536` |
| `Bits 14-15` | `>> 14` | `astro_mercury_dist_rate_mean_shift_p14d` | `21.788` | `21.788` | `21.788` |

### Container: `packed_astro_container_235` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mercury_helio_dist_mean_shift_p14d` | `0.46655` | `0.46655` | `0.46655` |
| `Bits 2-3` | `>> 2` | `astro_mercury_helio_dist_rate_mean_shift_p14d` | `0.32901` | `0.32901` | `0.32901` |
| `Bits 4-5` | `>> 4` | `astro_mercury_phase_angle_mean_shift_p14d` | `120.81` | `120.81` | `120.81` |
| `Bits 6-7` | `>> 6` | `astro_mercury_elong_mean_shift_p14d` | `23.427` | `23.427` | `23.427` |
| `Bits 8-9` | `>> 8` | `astro_mercury_illum_frac_mean_shift_p14d` | `66.477` | `66.477` | `66.477` |
| `Bits 10-11` | `>> 10` | `astro_venus_ra_icrf_mean_shift_p14d` | `28.652` | `28.652` | `28.652` |
| `Bits 12-13` | `>> 12` | `astro_venus_dec_icrf_mean_shift_p14d` | `10.406` | `10.406` | `10.406` |
| `Bits 14-15` | `>> 14` | `astro_venus_ra_app_mean_shift_p14d` | `28.969` | `28.969` | `28.969` |

### Container: `packed_astro_container_236` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_dec_app_mean_shift_p14d` | `10.523` | `10.523` | `10.523` |
| `Bits 2-3` | `>> 2` | `astro_venus_azim_mean_shift_p14d` | `130.28` | `130.28` | `130.28` |
| `Bits 4-5` | `>> 4` | `astro_venus_elev_mean_shift_p14d` | `51.989` | `51.989` | `51.989` |
| `Bits 6-7` | `>> 6` | `astro_venus_app_mag_mean_shift_p14d` | `-3.8847` | `-3.8847` | `-3.8847` |
| `Bits 8-9` | `>> 8` | `astro_venus_surf_bright_mean_shift_p14d` | `0.79933` | `0.79933` | `0.79934` |
| `Bits 10-11` | `>> 10` | `astro_venus_dist_mean_shift_p14d` | `1.6989` | `1.6989` | `1.6989` |
| `Bits 12-13` | `>> 12` | `astro_venus_dist_rate_mean_shift_p14d` | `3.2303` | `3.2303` | `3.2303` |
| `Bits 14-15` | `>> 14` | `astro_venus_helio_dist_mean_shift_p14d` | `0.72535` | `0.72535` | `0.72536` |

### Container: `packed_astro_container_237` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_helio_dist_rate_mean_shift_p14d` | `-0.21439` | `-0.21439` | `-0.21439` |
| `Bits 2-3` | `>> 2` | `astro_venus_phase_angle_mean_shift_p14d` | `13.367` | `13.367` | `13.367` |
| `Bits 4-5` | `>> 4` | `astro_venus_elong_mean_shift_p14d` | `9.583` | `9.583` | `9.583` |
| `Bits 6-7` | `>> 6` | `astro_venus_illum_frac_mean_shift_p14d` | `66.477` | `66.477` | `66.477` |
| `Bits 8-9` | `>> 8` | `astro_sun_ra_icrf_median_shift_p14d` | `37.406` | `37.406` | `37.406` |
| `Bits 10-11` | `>> 10` | `astro_sun_dec_icrf_median_shift_p14d` | `14.751` | `14.751` | `14.751` |
| `Bits 12-13` | `>> 12` | `astro_sun_ra_app_median_shift_p14d` | `37.732` | `37.732` | `37.732` |
| `Bits 14-15` | `>> 14` | `astro_sun_dec_app_median_shift_p14d` | `14.857` | `14.857` | `14.857` |

### Container: `packed_astro_container_238` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_azim_median_shift_p14d` | `115.65` | `115.65` | `115.65` |
| `Bits 2-3` | `>> 2` | `astro_sun_elev_median_shift_p14d` | `49.473` | `49.473` | `49.473` |
| `Bits 4-5` | `>> 4` | `astro_sun_app_mag_median_shift_p14d` | `-26.726` | `-26.726` | `-26.726` |
| `Bits 6-7` | `>> 6` | `astro_sun_dist_median_shift_p14d` | `1.0073` | `1.0073` | `1.0073` |
| `Bits 8-9` | `>> 8` | `astro_sun_dist_rate_median_shift_p14d` | `0.24257` | `0.24257` | `0.24258` |
| `Bits 10-11` | `>> 10` | `astro_sun_illum_frac_median_shift_p14d` | `66.824` | `66.824` | `66.824` |
| `Bits 12-13` | `>> 12` | `astro_moon_ra_icrf_median_shift_p14d` | `292.78` | `292.78` | `292.78` |
| `Bits 14-15` | `>> 14` | `astro_moon_dec_icrf_median_shift_p14d` | `-27.616` | `-27.616` | `-27.616` |

### Container: `packed_astro_container_239` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_ra_app_median_shift_p14d` | `293.16` | `293.16` | `293.16` |
| `Bits 2-3` | `>> 2` | `astro_moon_dec_app_median_shift_p14d` | `-27.565` | `-27.565` | `-27.565` |
| `Bits 4-5` | `>> 4` | `astro_moon_azim_median_shift_p14d` | `234.87` | `234.87` | `234.87` |
| `Bits 6-7` | `>> 6` | `astro_moon_elev_median_shift_p14d` | `-1.2882` | `-1.2882` | `-1.2882` |
| `Bits 8-9` | `>> 8` | `astro_moon_app_mag_median_shift_p14d` | `-10.805` | `-10.805` | `-10.805` |
| `Bits 10-11` | `>> 10` | `astro_moon_surf_bright_median_shift_p14d` | `4.876` | `4.876` | `4.876` |
| `Bits 12-13` | `>> 12` | `astro_moon_dist_median_shift_p14d` | `0.002536` | `0.002537` | `0.002538` |
| `Bits 14-15` | `>> 14` | `astro_moon_dist_rate_median_shift_p14d` | `0.23746` | `0.23746` | `0.23747` |

### Container: `packed_astro_container_240` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_helio_dist_median_shift_p14d` | `1.0081` | `1.0081` | `1.0081` |
| `Bits 2-3` | `>> 2` | `astro_moon_helio_dist_rate_median_shift_p14d` | `-0.46557` | `-0.46557` | `-0.46557` |
| `Bits 4-5` | `>> 4` | `astro_moon_phase_angle_median_shift_p14d` | `70.339` | `70.339` | `70.339` |
| `Bits 6-7` | `>> 6` | `astro_moon_elong_median_shift_p14d` | `109.53` | `109.53` | `109.53` |
| `Bits 8-9` | `>> 8` | `astro_moon_illum_frac_median_shift_p14d` | `66.824` | `66.824` | `66.824` |
| `Bits 10-11` | `>> 10` | `astro_mars_ra_icrf_median_shift_p14d` | `359.03` | `359.03` | `359.03` |
| `Bits 12-13` | `>> 12` | `astro_mars_dec_icrf_median_shift_p14d` | `-1.4935` | `-1.4935` | `-1.4935` |
| `Bits 14-15` | `>> 14` | `astro_mars_ra_app_median_shift_p14d` | `0.75223` | `0.75223` | `0.75223` |

### Container: `packed_astro_container_241` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_dec_app_median_shift_p14d` | `-1.3603` | `-1.3603` | `-1.3603` |
| `Bits 2-3` | `>> 2` | `astro_mars_azim_median_shift_p14d` | `180.6` | `180.6` | `180.6` |
| `Bits 4-5` | `>> 4` | `astro_mars_elev_median_shift_p14d` | `49.888` | `49.888` | `49.888` |
| `Bits 6-7` | `>> 6` | `astro_mars_app_mag_median_shift_p14d` | `1.179` | `1.179` | `1.179` |
| `Bits 8-9` | `>> 8` | `astro_mars_surf_bright_median_shift_p14d` | `4.222` | `4.222` | `4.222` |
| `Bits 10-11` | `>> 10` | `astro_mars_dist_median_shift_p14d` | `1.9803` | `1.9803` | `1.9803` |
| `Bits 12-13` | `>> 12` | `astro_mars_dist_rate_median_shift_p14d` | `-6.511` | `-6.511` | `-6.511` |
| `Bits 14-15` | `>> 14` | `astro_mars_helio_dist_median_shift_p14d` | `1.382` | `1.382` | `1.382` |

### Container: `packed_astro_container_242` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_helio_dist_rate_median_shift_p14d` | `-0.21137` | `-0.21137` | `-0.21136` |
| `Bits 2-3` | `>> 2` | `astro_mars_phase_angle_median_shift_p14d` | `28.352` | `28.353` | `28.353` |
| `Bits 4-5` | `>> 4` | `astro_mars_elong_median_shift_p14d` | `40.659` | `40.659` | `40.659` |
| `Bits 6-7` | `>> 6` | `astro_mars_illum_frac_median_shift_p14d` | `66.824` | `66.824` | `66.824` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_ra_icrf_median_shift_p14d` | `51.371` | `51.371` | `51.371` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_dec_icrf_median_shift_p14d` | `17.924` | `17.924` | `17.924` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_ra_app_median_shift_p14d` | `51.709` | `51.709` | `51.709` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_dec_app_median_shift_p14d` | `18.009` | `18.009` | `18.009` |

### Container: `packed_astro_container_243` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_azim_median_shift_p14d` | `100.03` | `100.03` | `100.03` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_elev_median_shift_p14d` | `41.105` | `41.105` | `41.105` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_app_mag_median_shift_p14d` | `-2.007` | `-2.007` | `-2.007` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_surf_bright_median_shift_p14d` | `5.319` | `5.319` | `5.319` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_dist_median_shift_p14d` | `5.9837` | `5.9837` | `5.9837` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_dist_rate_median_shift_p14d` | `6.9756` | `6.9756` | `6.9756` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_helio_dist_median_shift_p14d` | `5.0111` | `5.0111` | `5.0111` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_helio_dist_rate_median_shift_p14d` | `0.425` | `0.425` | `0.425` |

### Container: `packed_astro_container_244` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_phase_angle_median_shift_p14d` | `2.7444` | `2.7444` | `2.7444` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_elong_median_shift_p14d` | `13.767` | `13.767` | `13.767` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_illum_frac_median_shift_p14d` | `66.824` | `66.824` | `66.824` |
| `Bits 6-7` | `>> 6` | `astro_saturn_ra_icrf_median_shift_p14d` | `348` | `348` | `348` |
| `Bits 8-9` | `>> 8` | `astro_saturn_dec_icrf_median_shift_p14d` | `-7.0445` | `-7.0445` | `-7.0445` |
| `Bits 10-11` | `>> 10` | `astro_saturn_ra_app_median_shift_p14d` | `348.31` | `348.31` | `348.31` |
| `Bits 12-13` | `>> 12` | `astro_saturn_dec_app_median_shift_p14d` | `-6.9142` | `-6.9142` | `-6.9142` |
| `Bits 14-15` | `>> 14` | `astro_saturn_azim_median_shift_p14d` | `196.55` | `196.55` | `196.55` |

### Container: `packed_astro_container_245` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_elev_median_shift_p14d` | `42.969` | `42.969` | `42.969` |
| `Bits 2-3` | `>> 2` | `astro_saturn_app_mag_median_shift_p14d` | `1.072` | `1.072` | `1.072` |
| `Bits 4-5` | `>> 4` | `astro_saturn_surf_bright_median_shift_p14d` | `6.853` | `6.853` | `6.853` |
| `Bits 6-7` | `>> 6` | `astro_saturn_dist_median_shift_p14d` | `10.267` | `10.267` | `10.267` |
| `Bits 8-9` | `>> 8` | `astro_saturn_dist_rate_median_shift_p14d` | `-23.146` | `-23.146` | `-23.146` |
| `Bits 10-11` | `>> 10` | `astro_saturn_helio_dist_median_shift_p14d` | `9.7035` | `9.7035` | `9.7035` |
| `Bits 12-13` | `>> 12` | `astro_saturn_helio_dist_rate_median_shift_p14d` | `-0.50384` | `-0.50384` | `-0.50384` |
| `Bits 14-15` | `>> 14` | `astro_saturn_phase_angle_median_shift_p14d` | `4.7921` | `4.7921` | `4.7921` |

### Container: `packed_astro_container_246` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_elong_median_shift_p14d` | `53.613` | `53.613` | `53.613` |
| `Bits 2-3` | `>> 2` | `astro_saturn_illum_frac_median_shift_p14d` | `66.824` | `66.824` | `66.824` |
| `Bits 4-5` | `>> 4` | `astro_mercury_ra_icrf_median_shift_p14d` | `16.004` | `16.004` | `16.004` |
| `Bits 6-7` | `>> 6` | `astro_mercury_dec_icrf_median_shift_p14d` | `4.4509` | `4.4509` | `4.4509` |
| `Bits 8-9` | `>> 8` | `astro_mercury_ra_app_median_shift_p14d` | `16.312` | `16.312` | `16.312` |
| `Bits 10-11` | `>> 10` | `astro_mercury_dec_app_median_shift_p14d` | `4.579` | `4.579` | `4.579` |
| `Bits 12-13` | `>> 12` | `astro_mercury_azim_median_shift_p14d` | `153.11` | `153.11` | `153.11` |
| `Bits 14-15` | `>> 14` | `astro_mercury_elev_median_shift_p14d` | `52.905` | `52.905` | `52.905` |

### Container: `packed_astro_container_247` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mercury_app_mag_median_shift_p14d` | `1.087` | `1.087` | `1.087` |
| `Bits 2-3` | `>> 2` | `astro_mercury_surf_bright_median_shift_p14d` | `4.254` | `4.254` | `4.254` |
| `Bits 4-5` | `>> 4` | `astro_mercury_dist_median_shift_p14d` | `0.6852` | `0.6852` | `0.6852` |
| `Bits 6-7` | `>> 6` | `astro_mercury_dist_rate_median_shift_p14d` | `21.81` | `21.81` | `21.81` |
| `Bits 8-9` | `>> 8` | `astro_mercury_helio_dist_median_shift_p14d` | `0.46664` | `0.46664` | `0.46664` |
| `Bits 10-11` | `>> 10` | `astro_mercury_helio_dist_rate_median_shift_p14d` | `0.32913` | `0.32913` | `0.32914` |
| `Bits 12-13` | `>> 12` | `astro_mercury_phase_angle_median_shift_p14d` | `120.79` | `120.79` | `120.79` |
| `Bits 14-15` | `>> 14` | `astro_mercury_elong_median_shift_p14d` | `23.453` | `23.453` | `23.453` |

### Container: `packed_astro_container_248` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mercury_illum_frac_median_shift_p14d` | `66.824` | `66.824` | `66.824` |
| `Bits 2-3` | `>> 2` | `astro_venus_ra_icrf_median_shift_p14d` | `28.651` | `28.651` | `28.651` |
| `Bits 4-5` | `>> 4` | `astro_venus_dec_icrf_median_shift_p14d` | `10.407` | `10.407` | `10.407` |
| `Bits 6-7` | `>> 6` | `astro_venus_ra_app_median_shift_p14d` | `28.968` | `28.968` | `28.968` |
| `Bits 8-9` | `>> 8` | `astro_venus_dec_app_median_shift_p14d` | `10.525` | `10.525` | `10.525` |
| `Bits 10-11` | `>> 10` | `astro_venus_azim_median_shift_p14d` | `130.29` | `130.29` | `130.29` |
| `Bits 12-13` | `>> 12` | `astro_venus_elev_median_shift_p14d` | `51.992` | `51.992` | `51.992` |
| `Bits 14-15` | `>> 14` | `astro_venus_app_mag_median_shift_p14d` | `-3.885` | `-3.885` | `-3.885` |

### Container: `packed_astro_container_249` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_surf_bright_median_shift_p14d` | `0.799` | `0.799` | `0.799` |
| `Bits 2-3` | `>> 2` | `astro_venus_dist_median_shift_p14d` | `1.6989` | `1.6989` | `1.6989` |
| `Bits 4-5` | `>> 4` | `astro_venus_dist_rate_median_shift_p14d` | `3.2306` | `3.2306` | `3.2306` |
| `Bits 6-7` | `>> 6` | `astro_venus_helio_dist_median_shift_p14d` | `0.72535` | `0.72535` | `0.72536` |
| `Bits 8-9` | `>> 8` | `astro_venus_helio_dist_rate_median_shift_p14d` | `-0.21445` | `-0.21445` | `-0.21444` |
| `Bits 10-11` | `>> 10` | `astro_venus_phase_angle_median_shift_p14d` | `13.368` | `13.368` | `13.368` |
| `Bits 12-13` | `>> 12` | `astro_venus_elong_median_shift_p14d` | `9.5831` | `9.5831` | `9.5831` |
| `Bits 14-15` | `>> 14` | `astro_venus_illum_frac_median_shift_p14d` | `66.824` | `66.824` | `66.824` |

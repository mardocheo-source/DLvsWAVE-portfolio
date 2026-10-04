# DLVS-Wave v2.0 Master Manifest & Decodification Report: Master 7D Summarized (sample_2_italy_central)

> **Generated at**: `2026-08-27 14:11:47 UTC`  
> **Chronological Timeline**: `2024-01-01` to `2024-04-29` (`18` time steps)

## 1. Dataset Dimensions & Compression Summary

| Dimension | Raw Uncompressed | Quantized Bit-Packed (2-Bit / 16-Bit) | Reduction Ratio |
| :--- | :--- | :--- | :--- |
| **Feature Columns** | `2007` columns | `257` columns | **8.0x fewer fields** |
| **Record Count** | `18` rows | `18` rows | 1:1 Synchronized |
| **Storage Size** | `489,391 bytes` | `33,887 bytes` | **93.08% space saved** |
| **Container Type** | `Float64` | `uint16` (`2` bits/field, `4` quantiles) | Compact Binary |

## 2. Preserved Seismic Features (In Chiaro / Uncompressed)

All seismic parameters (core 3D coordinates + magnitude and historical lag shifts) are preserved uncompressed as leading columns immediately following `date` for instant inspection:

- **`seis_core_magnitude`**
- **`seis_core_latitude`**
- **`seis_core_longitude`**
- **`seis_core_depth`**
- **`seis_core_magnitude_shift_m7d`**
- **`seis_core_depth_shift_m7d`**

## 3. Tracked Astronomical Bodies & Feature Groups Catalog

| Prefix / Body Group | Fields Count | Sample Features Included |
| :--- | :--- | :--- |
| **`astro_ceres`** | 300 | `min`, `min`, `min`, `min`, ... (+296 more) |
| **`astro_jupiter`** | 300 | `min`, `min`, `min`, `min`, ... (+296 more) |
| **`astro_mars`** | 300 | `min`, `min`, `min`, `min`, ... (+296 more) |
| **`astro_moon`** | 300 | `min`, `min`, `min`, `min`, ... (+296 more) |
| **`astro_saturn`** | 300 | `min`, `min`, `min`, `min`, ... (+296 more) |
| **`astro_sun`** | 200 | `min`, `min`, `min`, `min`, ... (+196 more) |
| **`astro_venus`** | 300 | `min`, `min`, `min`, `min`, ... (+296 more) |

## 4. Container Decodification Matrix & Quantile Codebook

This matrix allows 100% exact decompression of packed integer fields into their discrete quantile bins `[0, 1, 2, 3]`.

### Container: `packed_astro_container_000` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_ra_icrf_min` | `24.968` | `292.06` | `323.03` |
| `Bits 2-3` | `>> 2` | `astro_sun_dec_icrf_min` | `-17.716` | `-7.7867` | `3.8326` |
| `Bits 4-5` | `>> 4` | `astro_sun_ra_app_min` | `25.282` | `292.41` | `323.35` |
| `Bits 6-7` | `>> 6` | `astro_sun_dec_app_min` | `-17.629` | `-7.6626` | `3.9634` |
| `Bits 8-9` | `>> 8` | `astro_sun_azim_min` | `16.354` | `16.912` | `20.292` |
| `Bits 10-11` | `>> 10` | `astro_sun_elev_min` | `-63.489` | `-53.79` | `-42.007` |
| `Bits 12-13` | `>> 12` | `astro_sun_app_mag_min` | `-26.774` | `-26.762` | `-26.745` |
| `Bits 14-15` | `>> 14` | `astro_sun_dist_min` | `0.98511` | `0.99076` | `0.99877` |

### Container: `packed_astro_container_001` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_dist_rate_min` | `0.17611` | `0.35783` | `0.39234` |
| `Bits 2-3` | `>> 2` | `astro_sun_illum_frac_min` | `1.6141` | `30.965` | `57.484` |
| `Bits 4-5` | `>> 4` | `astro_moon_ra_icrf_min` | `78.657` | `162.92` | `226.54` |
| `Bits 6-7` | `>> 6` | `astro_moon_dec_icrf_min` | `-28.567` | `-21.507` | `0.64263` |
| `Bits 8-9` | `>> 8` | `astro_moon_ra_app_min` | `79.035` | `163.24` | `226.88` |
| `Bits 10-11` | `>> 10` | `astro_moon_dec_app_min` | `-28.555` | `-21.594` | `0.57326` |
| `Bits 12-13` | `>> 12` | `astro_moon_azim_min` | `30.792` | `119.75` | `177.92` |
| `Bits 14-15` | `>> 14` | `astro_moon_elev_min` | `-47.94` | `-19.566` | `5.245` |

### Container: `packed_astro_container_002` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_app_mag_min` | `-12.25` | `-11.215` | `-10.161` |
| `Bits 2-3` | `>> 2` | `astro_moon_surf_bright_min` | `3.7283` | `4.367` | `4.8582` |
| `Bits 4-5` | `>> 4` | `astro_moon_dist_min` | `0.0024319` | `0.002546` | `0.0026072` |
| `Bits 6-7` | `>> 6` | `astro_moon_dist_rate_min` | `-0.35051` | `-0.24069` | `0.023095` |
| `Bits 8-9` | `>> 8` | `astro_moon_helio_dist_min` | `0.98497` | `0.99084` | `0.9989` |
| `Bits 10-11` | `>> 10` | `astro_moon_helio_dist_rate_min` | `-0.50816` | `-0.30062` | `0.52921` |
| `Bits 12-13` | `>> 12` | `astro_moon_phase_angle_min` | `14.644` | `56.075` | `88.61` |
| `Bits 14-15` | `>> 14` | `astro_moon_elong_min` | `12.877` | `67.107` | `98.462` |

### Container: `packed_astro_container_003` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_illum_frac_min` | `1.6141` | `30.965` | `57.484` |
| `Bits 2-3` | `>> 2` | `astro_saturn_ra_icrf_min` | `338.36` | `341.7` | `345.04` |
| `Bits 4-5` | `>> 4` | `astro_saturn_dec_icrf_min` | `-10.819` | `-9.5003` | `-8.1891` |
| `Bits 6-7` | `>> 6` | `astro_saturn_ra_app_min` | `338.67` | `342.01` | `345.35` |
| `Bits 8-9` | `>> 8` | `astro_saturn_dec_app_min` | `-10.698` | `-9.3759` | `-8.0617` |
| `Bits 10-11` | `>> 10` | `astro_saturn_azim_min` | `34.074` | `63.24` | `302.35` |
| `Bits 12-13` | `>> 12` | `astro_saturn_elev_min` | `-55.68` | `-50.557` | `-42.933` |
| `Bits 14-15` | `>> 14` | `astro_saturn_app_mag_min` | `0.97525` | `0.99` | `1.053` |

### Container: `packed_astro_container_004` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_surf_bright_min` | `6.6893` | `6.714` | `6.7672` |
| `Bits 2-3` | `>> 2` | `astro_saturn_dist_min` | `10.403` | `10.561` | `10.665` |
| `Bits 4-5` | `>> 4` | `astro_saturn_dist_rate_min` | `-15.48` | `-3.0789` | `10.095` |
| `Bits 6-7` | `>> 6` | `astro_saturn_helio_dist_min` | `9.7106` | `9.7192` | `9.7277` |
| `Bits 8-9` | `>> 8` | `astro_saturn_helio_dist_rate_min` | `-0.50083` | `-0.49719` | `-0.49408` |
| `Bits 10-11` | `>> 10` | `astro_saturn_phase_angle_min` | `1.1534` | `2.4898` | `3.6976` |
| `Bits 12-13` | `>> 12` | `astro_saturn_elong_min` | `11.418` | `25.199` | `39.035` |
| `Bits 14-15` | `>> 14` | `astro_saturn_illum_frac_min` | `1.6141` | `30.965` | `57.484` |

### Container: `packed_astro_container_005` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_ra_icrf_min` | `34.845` | `38.778` | `44.432` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_dec_icrf_min` | `12.812` | `14.224` | `16.019` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_ra_app_min` | `35.17` | `39.105` | `44.763` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_dec_app_min` | `12.922` | `14.329` | `16.115` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_azim_min` | `286.9` | `306.65` | `328.95` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_elev_min` | `-28.258` | `-20.733` | `-7.0602` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_app_mag_min` | `-2.357` | `-2.181` | `-2.068` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_surf_bright_min` | `5.3312` | `5.3545` | `5.366` |

### Container: `packed_astro_container_006` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_dist_min` | `4.9475` | `5.4036` | `5.7649` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_dist_rate_min` | `15.398` | `23.444` | `26.777` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_helio_dist_min` | `4.9908` | `4.9971` | `5.0038` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_helio_dist_rate_min` | `0.35471` | `0.37817` | `0.40206` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_phase_angle_min` | `6.1363` | `9.4492` | `10.77` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_elong_min` | `32.346` | `55.895` | `81.397` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_illum_frac_min` | `1.6141` | `30.965` | `57.484` |
| `Bits 14-15` | `>> 14` | `astro_mars_ra_icrf_min` | `285.32` | `309.44` | `332.38` |

### Container: `packed_astro_container_007` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_dec_icrf_min` | `-22.842` | `-18.135` | `-10.685` |
| `Bits 2-3` | `>> 2` | `astro_mars_ra_app_min` | `285.68` | `309.78` | `332.7` |
| `Bits 4-5` | `>> 4` | `astro_mars_dec_app_min` | `-22.796` | `-18.043` | `-10.564` |
| `Bits 6-7` | `>> 6` | `astro_mars_azim_min` | `62.397` | `62.663` | `62.789` |
| `Bits 8-9` | `>> 8` | `astro_mars_elev_min` | `-57.287` | `-50.326` | `-40.414` |
| `Bits 10-11` | `>> 10` | `astro_mars_app_mag_min` | `1.175` | `1.2425` | `1.2902` |
| `Bits 12-13` | `>> 12` | `astro_mars_surf_bright_min` | `4.0442` | `4.077` | `4.1013` |
| `Bits 14-15` | `>> 14` | `astro_mars_dist_min` | `2.0742` | `2.1887` | `2.3017` |

### Container: `packed_astro_container_008` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_dist_rate_min` | `-6.8565` | `-6.8084` | `-6.5594` |
| `Bits 2-3` | `>> 2` | `astro_mars_helio_dist_min` | `1.3894` | `1.4089` | `1.4378` |
| `Bits 4-5` | `>> 4` | `astro_mars_helio_dist_rate_min` | `-1.9709` | `-1.5425` | `-0.94567` |
| `Bits 6-7` | `>> 6` | `astro_mars_phase_angle_min` | `13.929` | `19.12` | `23.901` |
| `Bits 8-9` | `>> 8` | `astro_mars_elong_min` | `20.669` | `27.871` | `34.391` |
| `Bits 10-11` | `>> 10` | `astro_mars_illum_frac_min` | `1.6141` | `30.965` | `57.484` |
| `Bits 12-13` | `>> 12` | `astro_ceres_ra_icrf_min` | `266.56` | `277.83` | `286.89` |
| `Bits 14-15` | `>> 14` | `astro_ceres_dec_icrf_min` | `-23.542` | `-23.107` | `-22.472` |

### Container: `packed_astro_container_009` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_ceres_ra_app_min` | `266.91` | `278.19` | `287.25` |
| `Bits 2-3` | `>> 2` | `astro_ceres_dec_app_min` | `-23.502` | `-23.087` | `-22.477` |
| `Bits 4-5` | `>> 4` | `astro_ceres_azim_min` | `84.417` | `97.29` | `110.18` |
| `Bits 6-7` | `>> 6` | `astro_ceres_elev_min` | `-39.728` | `-26.948` | `-12.787` |
| `Bits 8-9` | `>> 8` | `astro_ceres_app_mag_min` | `8.7995` | `8.972` | `9.0407` |
| `Bits 10-11` | `>> 10` | `astro_ceres_surf_bright_min` | `6.7332` | `6.8915` | `6.966` |
| `Bits 12-13` | `>> 12` | `astro_ceres_dist_min` | `2.6743` | `3.0481` | `3.3656` |
| `Bits 14-15` | `>> 14` | `astro_ceres_dist_rate_min` | `-22.334` | `-20.855` | `-16.319` |

### Container: `packed_astro_container_010` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_ceres_helio_dist_min` | `2.7845` | `2.8083` | `2.8314` |
| `Bits 2-3` | `>> 2` | `astro_ceres_helio_dist_rate_min` | `1.3102` | `1.3605` | `1.396` |
| `Bits 4-5` | `>> 4` | `astro_ceres_phase_angle_min` | `14.006` | `18.281` | `19.868` |
| `Bits 6-7` | `>> 6` | `astro_ceres_elong_min` | `43.197` | `62.852` | `84.224` |
| `Bits 8-9` | `>> 8` | `astro_ceres_illum_frac_min` | `1.6141` | `30.965` | `57.484` |
| `Bits 10-11` | `>> 10` | `astro_venus_ra_icrf_min` | `80.768` | `272.49` | `311.59` |
| `Bits 12-13` | `>> 12` | `astro_venus_dec_icrf_min` | `-21.386` | `-16.78` | `-4.3558` |
| `Bits 14-15` | `>> 14` | `astro_venus_ra_app_min` | `81.09` | `272.85` | `311.93` |

### Container: `packed_astro_container_011` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_dec_app_min` | `-21.395` | `-16.684` | `-4.2248` |
| `Bits 2-3` | `>> 2` | `astro_venus_azim_min` | `37.222` | `54.088` | `71.574` |
| `Bits 4-5` | `>> 4` | `astro_venus_elev_min` | `-50.79` | `-47.418` | `-42.519` |
| `Bits 6-7` | `>> 6` | `astro_venus_app_mag_min` | `-3.9468` | `-3.894` | `-3.8807` |
| `Bits 8-9` | `>> 8` | `astro_venus_surf_bright_min` | `0.864` | `0.955` | `1.052` |
| `Bits 10-11` | `>> 10` | `astro_venus_dist_min` | `1.3555` | `1.5013` | `1.6169` |
| `Bits 12-13` | `>> 12` | `astro_venus_dist_rate_min` | `5.1797` | `7.1098` | `8.7886` |
| `Bits 14-15` | `>> 14` | `astro_venus_helio_dist_min` | `0.72431` | `0.72612` | `0.72752` |

### Container: `packed_astro_container_012` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_helio_dist_rate_min` | `-0.10271` | `0.085169` | `0.2015` |
| `Bits 2-3` | `>> 2` | `astro_venus_phase_angle_min` | `22.137` | `32.362` | `42.713` |
| `Bits 4-5` | `>> 4` | `astro_venus_elong_min` | `15.905` | `23.115` | `29.917` |
| `Bits 6-7` | `>> 6` | `astro_venus_illum_frac_min` | `1.6141` | `30.965` | `57.484` |
| `Bits 8-9` | `>> 8` | `astro_sun_ra_icrf_max` | `36.218` | `305.94` | `335.67` |
| `Bits 10-11` | `>> 10` | `astro_sun_dec_icrf_max` | `-15.993` | `-5.4876` | `6.1343` |
| `Bits 12-13` | `>> 12` | `astro_sun_ra_app_max` | `36.543` | `306.28` | `335.98` |
| `Bits 14-15` | `>> 14` | `astro_sun_dec_app_max` | `-15.896` | `-5.3598` | `6.2628` |

### Container: `packed_astro_container_013` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_azim_max` | `16.423` | `17.228` | `21.697` |
| `Bits 2-3` | `>> 2` | `astro_sun_elev_max` | `-61.871` | `-51.473` | `-39.667` |
| `Bits 4-5` | `>> 4` | `astro_sun_app_mag_max` | `-26.773` | `-26.759` | `-26.741` |
| `Bits 6-7` | `>> 6` | `astro_sun_dist_max` | `0.986` | `0.99228` | `1.0005` |
| `Bits 8-9` | `>> 8` | `astro_sun_dist_rate_max` | `0.22234` | `0.37839` | `0.39856` |
| `Bits 10-11` | `>> 10` | `astro_sun_illum_frac_max` | `51.188` | `77.905` | `98.368` |
| `Bits 12-13` | `>> 12` | `astro_moon_ra_icrf_max` | `172.85` | `248.06` | `337.05` |
| `Bits 14-15` | `>> 14` | `astro_moon_dec_icrf_max` | `-5.1515` | `10.331` | `27.457` |

### Container: `packed_astro_container_014` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_ra_app_max` | `173.16` | `248.43` | `337.36` |
| `Bits 2-3` | `>> 2` | `astro_moon_dec_app_max` | `-5.0866` | `10.202` | `27.462` |
| `Bits 4-5` | `>> 4` | `astro_moon_azim_max` | `147.05` | `276.35` | `324.41` |
| `Bits 6-7` | `>> 6` | `astro_moon_elev_max` | `-0.16134` | `31.408` | `46.746` |
| `Bits 8-9` | `>> 8` | `astro_moon_app_mag_max` | `-10.406` | `-9.1125` | `-5.3703` |
| `Bits 10-11` | `>> 10` | `astro_moon_surf_bright_max` | `5.0488` | `5.632` | `6.3355` |
| `Bits 12-13` | `>> 12` | `astro_moon_dist_max` | `0.0025786` | `0.0026265` | `0.0026821` |
| `Bits 14-15` | `>> 14` | `astro_moon_dist_rate_max` | `-0.077247` | `0.15677` | `0.34212` |

### Container: `packed_astro_container_015` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_helio_dist_max` | `0.98707` | `0.99243` | `1.0003` |
| `Bits 2-3` | `>> 2` | `astro_moon_helio_dist_rate_max` | `0.21016` | `0.7127` | `1.2544` |
| `Bits 4-5` | `>> 4` | `astro_moon_phase_angle_max` | `81.389` | `112.76` | `167.09` |
| `Bits 6-7` | `>> 6` | `astro_moon_elong_max` | `91.243` | `123.8` | `165.32` |
| `Bits 8-9` | `>> 8` | `astro_moon_illum_frac_max` | `51.188` | `77.905` | `98.368` |
| `Bits 10-11` | `>> 10` | `astro_saturn_ra_icrf_max` | `339.01` | `342.39` | `345.67` |
| `Bits 12-13` | `>> 12` | `astro_saturn_dec_icrf_max` | `-10.562` | `-9.229` | `-7.9428` |
| `Bits 14-15` | `>> 14` | `astro_saturn_ra_app_max` | `339.32` | `342.7` | `345.98` |

### Container: `packed_astro_container_016` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_dec_app_max` | `-10.44` | `-9.104` | `-7.8148` |
| `Bits 2-3` | `>> 2` | `astro_saturn_azim_max` | `48.493` | `72.745` | `316.68` |
| `Bits 4-5` | `>> 4` | `astro_saturn_elev_max` | `-54.083` | `-47.838` | `-39.527` |
| `Bits 6-7` | `>> 6` | `astro_saturn_app_mag_max` | `0.986` | `0.997` | `1.0615` |
| `Bits 8-9` | `>> 8` | `astro_saturn_surf_bright_max` | `6.6978` | `6.7225` | `6.7858` |
| `Bits 10-11` | `>> 10` | `astro_saturn_dist_max` | `10.469` | `10.607` | `10.689` |
| `Bits 12-13` | `>> 12` | `astro_saturn_dist_rate_max` | `-13.154` | `-0.40233` | `12.606` |
| `Bits 14-15` | `>> 14` | `astro_saturn_helio_dist_max` | `9.7124` | `9.7209` | `9.7294` |

### Container: `packed_astro_container_017` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_helio_dist_rate_max` | `-0.49877` | `-0.4958` | `-0.49197` |
| `Bits 2-3` | `>> 2` | `astro_saturn_phase_angle_max` | `1.6737` | `2.9705` | `4.1079` |
| `Bits 4-5` | `>> 4` | `astro_saturn_elong_max` | `16.646` | `30.514` | `44.347` |
| `Bits 6-7` | `>> 6` | `astro_saturn_illum_frac_max` | `51.188` | `77.905` | `98.368` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_ra_icrf_max` | `35.462` | `39.803` | `45.719` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_dec_icrf_max` | `13.047` | `14.567` | `16.397` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_ra_app_max` | `35.787` | `40.131` | `46.052` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_dec_app_max` | `13.157` | `14.67` | `16.491` |

### Container: `packed_astro_container_018` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_azim_max` | `295.3` | `316.04` | `339.5` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_elev_max` | `-27.293` | `-18.432` | `-3.6607` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_app_mag_max` | `-2.3165` | `-2.153` | `-2.0515` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_surf_bright_max` | `5.3355` | `5.3595` | `5.3685` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_dist_max` | `5.0435` | `5.4863` | `5.821` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_dist_rate_max` | `17.215` | `24.685` | `27.534` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_helio_dist_max` | `4.992` | `4.9984` | `5.0052` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_helio_dist_rate_max` | `0.36101` | `0.38458` | `0.40823` |

### Container: `packed_astro_container_019` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_phase_angle_max` | `6.8901` | `9.9591` | `11.081` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_elong_max` | `36.97` | `60.86` | `86.839` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_illum_frac_max` | `51.188` | `77.905` | `98.368` |
| `Bits 6-7` | `>> 6` | `astro_mars_ra_icrf_max` | `295.96` | `319.64` | `341.99` |
| `Bits 8-9` | `>> 8` | `astro_mars_dec_icrf_max` | `-22.167` | `-16.814` | `-8.9625` |
| `Bits 10-11` | `>> 10` | `astro_mars_ra_app_max` | `296.31` | `319.97` | `342.3` |
| `Bits 12-13` | `>> 12` | `astro_mars_dec_app_max` | `-22.111` | `-16.715` | `-8.8371` |
| `Bits 14-15` | `>> 14` | `astro_mars_azim_max` | `62.634` | `62.716` | `62.938` |

### Container: `packed_astro_container_020` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_elev_max` | `-56.137` | `-48.545` | `-38.132` |
| `Bits 2-3` | `>> 2` | `astro_mars_app_mag_max` | `1.1935` | `1.288` | `1.3213` |
| `Bits 4-5` | `>> 4` | `astro_mars_surf_bright_max` | `4.0953` | `4.1135` | `4.1677` |
| `Bits 6-7` | `>> 6` | `astro_mars_dist_max` | `2.0971` | `2.2117` | `2.3236` |
| `Bits 8-9` | `>> 8` | `astro_mars_dist_rate_max` | `-6.8449` | `-6.781` | `-6.4272` |
| `Bits 10-11` | `>> 10` | `astro_mars_helio_dist_max` | `1.3925` | `1.4141` | `1.4445` |
| `Bits 12-13` | `>> 12` | `astro_mars_helio_dist_rate_max` | `-1.8998` | `-1.4343` | `-0.80923` |
| `Bits 14-15` | `>> 14` | `astro_mars_phase_angle_max` | `15.005` | `20.12` | `24.81` |

### Container: `packed_astro_container_021` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_elong_max` | `22.181` | `29.236` | `35.64` |
| `Bits 2-3` | `>> 2` | `astro_mars_illum_frac_max` | `51.188` | `77.905` | `98.368` |
| `Bits 4-5` | `>> 4` | `astro_ceres_ra_icrf_max` | `268.96` | `279.87` | `288.34` |
| `Bits 6-7` | `>> 6` | `astro_ceres_dec_icrf_max` | `-23.437` | `-23.016` | `-22.267` |
| `Bits 8-9` | `>> 8` | `astro_ceres_ra_app_max` | `269.32` | `280.23` | `288.71` |
| `Bits 10-11` | `>> 10` | `astro_ceres_dec_app_max` | `-23.4` | `-23` | `-22.276` |
| `Bits 12-13` | `>> 12` | `astro_ceres_azim_max` | `87.157` | `99.794` | `113.05` |
| `Bits 14-15` | `>> 14` | `astro_ceres_elev_max` | `-37.279` | `-24.191` | `-9.811` |

### Container: `packed_astro_container_022` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_ceres_app_mag_max` | `8.8545` | `9.003` | `9.0555` |
| `Bits 2-3` | `>> 2` | `astro_ceres_surf_bright_max` | `6.7705` | `6.9155` | `6.976` |
| `Bits 4-5` | `>> 4` | `astro_ceres_dist_max` | `2.7519` | `3.1181` | `3.4193` |
| `Bits 6-7` | `>> 6` | `astro_ceres_dist_rate_max` | `-21.901` | `-20.106` | `-15.17` |
| `Bits 8-9` | `>> 8` | `astro_ceres_helio_dist_max` | `2.7893` | `2.813` | `2.836` |
| `Bits 10-11` | `>> 10` | `astro_ceres_helio_dist_rate_max` | `1.3215` | `1.3689` | `1.4012` |
| `Bits 12-13` | `>> 12` | `astro_ceres_phase_angle_max` | `14.988` | `18.931` | `20.264` |
| `Bits 14-15` | `>> 14` | `astro_ceres_elong_max` | `47.056` | `66.997` | `88.832` |

### Container: `packed_astro_container_023` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_ceres_illum_frac_max` | `51.188` | `77.905` | `98.368` |
| `Bits 2-3` | `>> 2` | `astro_venus_ra_icrf_max` | `250.48` | `289.8` | `327.73` |
| `Bits 4-5` | `>> 4` | `astro_venus_dec_icrf_max` | `-20.287` | `-14.674` | `-1.4553` |
| `Bits 6-7` | `>> 6` | `astro_venus_ra_app_max` | `250.83` | `290.15` | `328.05` |
| `Bits 8-9` | `>> 8` | `astro_venus_dec_app_max` | `-20.305` | `-14.567` | `-1.3232` |
| `Bits 10-11` | `>> 10` | `astro_venus_azim_max` | `40.176` | `57.963` | `73.993` |
| `Bits 12-13` | `>> 12` | `astro_venus_elev_max` | `-49.739` | `-45.627` | `-40.36` |
| `Bits 14-15` | `>> 14` | `astro_venus_app_mag_max` | `-3.9325` | `-3.8875` | `-3.8782` |

### Container: `packed_astro_container_024` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_surf_bright_max` | `0.88225` | `0.974` | `1.072` |
| `Bits 2-3` | `>> 2` | `astro_venus_dist_max` | `1.3872` | `1.5272` | `1.6361` |
| `Bits 4-5` | `>> 4` | `astro_venus_dist_rate_max` | `5.6033` | `7.4679` | `9.1146` |
| `Bits 6-7` | `>> 6` | `astro_venus_helio_dist_max` | `0.72502` | `0.72675` | `0.72787` |
| `Bits 8-9` | `>> 8` | `astro_venus_helio_dist_rate_max` | `-0.066316` | `0.12019` | `0.21915` |
| `Bits 10-11` | `>> 10` | `astro_venus_phase_angle_max` | `24.215` | `34.421` | `44.868` |
| `Bits 12-13` | `>> 12` | `astro_venus_elong_max` | `17.394` | `24.519` | `31.239` |
| `Bits 14-15` | `>> 14` | `astro_venus_illum_frac_max` | `51.188` | `77.905` | `98.368` |

### Container: `packed_astro_container_025` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_ra_icrf_mean` | `33.856` | `295.3` | `325.99` |
| `Bits 2-3` | `>> 2` | `astro_sun_dec_icrf_mean` | `-16.867` | `-6.6411` | `4.9871` |
| `Bits 4-5` | `>> 4` | `astro_sun_ra_app_mean` | `34.179` | `295.65` | `326.31` |
| `Bits 6-7` | `>> 6` | `astro_sun_dec_app_mean` | `-16.775` | `-6.5151` | `5.1168` |
| `Bits 8-9` | `>> 8` | `astro_sun_azim_mean` | `16.389` | `17.061` | `20.975` |
| `Bits 10-11` | `>> 10` | `astro_sun_elev_mean` | `-62.695` | `-52.636` | `-40.833` |
| `Bits 12-13` | `>> 12` | `astro_sun_app_mag_mean` | `-26.774` | `-26.761` | `-26.743` |
| `Bits 14-15` | `>> 14` | `astro_sun_dist_mean` | `0.98555` | `0.99151` | `0.99964` |

### Container: `packed_astro_container_026` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_dist_rate_mean` | `0.20035` | `0.36869` | `0.39467` |
| `Bits 2-3` | `>> 2` | `astro_sun_illum_frac_mean` | `23.183` | `57.977` | `81.162` |
| `Bits 4-5` | `>> 4` | `astro_moon_ra_icrf_mean` | `125.79` | `195.49` | `269.89` |
| `Bits 6-7` | `>> 6` | `astro_moon_dec_icrf_mean` | `-20.136` | `-6.0115` | `15.878` |
| `Bits 8-9` | `>> 8` | `astro_moon_ra_app_mean` | `126.12` | `195.81` | `270.24` |
| `Bits 10-11` | `>> 10` | `astro_moon_dec_app_mean` | `-20.101` | `-6.1313` | `15.826` |
| `Bits 12-13` | `>> 12` | `astro_moon_azim_mean` | `123.93` | `175.04` | `254.74` |
| `Bits 14-15` | `>> 14` | `astro_moon_elev_mean` | `-22.954` | `3.1919` | `25.087` |

### Container: `packed_astro_container_027` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_app_mag_mean` | `-11.363` | `-10.369` | `-8.1673` |
| `Bits 2-3` | `>> 2` | `astro_moon_surf_bright_mean` | `4.4088` | `5.0424` | `5.7436` |
| `Bits 4-5` | `>> 4` | `astro_moon_dist_mean` | `0.0024968` | `0.0025813` | `0.0026558` |
| `Bits 6-7` | `>> 6` | `astro_moon_dist_rate_mean` | `-0.25044` | `-0.059315` | `0.20613` |
| `Bits 8-9` | `>> 8` | `astro_moon_helio_dist_mean` | `0.98632` | `0.99171` | `0.99998` |
| `Bits 10-11` | `>> 10` | `astro_moon_helio_dist_rate_mean` | `-0.20385` | `0.15494` | `0.95732` |
| `Bits 12-13` | `>> 12` | `astro_moon_phase_angle_mean` | `47.73` | `80.55` | `127` |
| `Bits 14-15` | `>> 14` | `astro_moon_elong_mean` | `52.894` | `99.311` | `132.17` |

### Container: `packed_astro_container_028` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_illum_frac_mean` | `23.183` | `57.977` | `81.162` |
| `Bits 2-3` | `>> 2` | `astro_saturn_ra_icrf_mean` | `338.68` | `342.05` | `345.35` |
| `Bits 4-5` | `>> 4` | `astro_saturn_dec_icrf_mean` | `-10.691` | `-9.3646` | `-8.0653` |
| `Bits 6-7` | `>> 6` | `astro_saturn_ra_app_mean` | `338.99` | `342.36` | `345.66` |
| `Bits 8-9` | `>> 8` | `astro_saturn_dec_app_mean` | `-10.569` | `-9.2399` | `-7.9376` |
| `Bits 10-11` | `>> 10` | `astro_saturn_azim_mean` | `45.396` | `70.647` | `306.36` |
| `Bits 12-13` | `>> 12` | `astro_saturn_elev_mean` | `-54.918` | `-49.221` | `-41.244` |
| `Bits 14-15` | `>> 14` | `astro_saturn_app_mag_mean` | `0.98296` | `0.99064` | `1.0575` |

### Container: `packed_astro_container_029` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_surf_bright_mean` | `6.6928` | `6.7169` | `6.7765` |
| `Bits 2-3` | `>> 2` | `astro_saturn_dist_mean` | `10.437` | `10.585` | `10.678` |
| `Bits 4-5` | `>> 4` | `astro_saturn_dist_rate_mean` | `-14.324` | `-1.741` | `11.358` |
| `Bits 6-7` | `>> 6` | `astro_saturn_helio_dist_mean` | `9.7115` | `9.72` | `9.7286` |
| `Bits 8-9` | `>> 8` | `astro_saturn_helio_dist_rate_mean` | `-0.49975` | `-0.49644` | `-0.49314` |
| `Bits 10-11` | `>> 10` | `astro_saturn_phase_angle_mean` | `1.4141` | `2.7317` | `3.905` |
| `Bits 12-13` | `>> 12` | `astro_saturn_elong_mean` | `14.036` | `27.855` | `41.69` |
| `Bits 14-15` | `>> 14` | `astro_saturn_illum_frac_mean` | `23.183` | `57.977` | `81.162` |

### Container: `packed_astro_container_030` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_ra_icrf_mean` | `35.147` | `39.286` | `45.073` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_dec_icrf_mean` | `12.927` | `14.395` | `16.208` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_ra_app_mean` | `35.472` | `39.613` | `45.405` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_dec_app_mean` | `13.037` | `14.499` | `16.303` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_azim_mean` | `288.82` | `308.77` | `331.36` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_elev_mean` | `-27.795` | `-19.6` | `-5.3741` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_app_mag_mean` | `-2.3365` | `-2.1667` | `-2.0596` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_surf_bright_mean` | `5.3336` | `5.357` | `5.3674` |

### Container: `packed_astro_container_031` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_dist_mean` | `4.9956` | `5.4453` | `5.7934` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_dist_rate_mean` | `16.312` | `24.076` | `27.176` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_helio_dist_mean` | `4.9914` | `4.9977` | `5.0045` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_helio_dist_rate_mean` | `0.35754` | `0.38137` | `0.40427` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_phase_angle_mean` | `6.5156` | `9.7086` | `10.933` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_elong_mean` | `34.655` | `58.372` | `84.11` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_illum_frac_mean` | `23.183` | `57.977` | `81.162` |
| `Bits 14-15` | `>> 14` | `astro_mars_ra_icrf_mean` | `287.78` | `311.81` | `334.62` |

### Container: `packed_astro_container_032` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_dec_icrf_mean` | `-22.515` | `-17.482` | `-9.8275` |
| `Bits 2-3` | `>> 2` | `astro_mars_ra_app_mean` | `288.14` | `312.15` | `334.94` |
| `Bits 4-5` | `>> 4` | `astro_mars_dec_app_mean` | `-22.464` | `-17.387` | `-9.7039` |
| `Bits 6-7` | `>> 6` | `astro_mars_azim_mean` | `62.549` | `62.688` | `62.857` |
| `Bits 8-9` | `>> 8` | `astro_mars_elev_mean` | `-56.721` | `-49.444` | `-39.278` |
| `Bits 10-11` | `>> 10` | `astro_mars_app_mag_mean` | `1.1834` | `1.2656` | `1.3031` |
| `Bits 12-13` | `>> 12` | `astro_mars_surf_bright_mean` | `4.0625` | `4.1007` | `4.1345` |
| `Bits 14-15` | `>> 14` | `astro_mars_dist_mean` | `2.0857` | `2.2002` | `2.3127` |

### Container: `packed_astro_container_033` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_dist_rate_mean` | `-6.8486` | `-6.7931` | `-6.4941` |
| `Bits 2-3` | `>> 2` | `astro_mars_helio_dist_mean` | `1.3909` | `1.4115` | `1.4411` |
| `Bits 4-5` | `>> 4` | `astro_mars_helio_dist_rate_mean` | `-1.9359` | `-1.4889` | `-0.87775` |
| `Bits 6-7` | `>> 6` | `astro_mars_phase_angle_mean` | `14.468` | `19.621` | `24.357` |
| `Bits 8-9` | `>> 8` | `astro_mars_elong_mean` | `21.427` | `28.555` | `35.017` |
| `Bits 10-11` | `>> 10` | `astro_mars_illum_frac_mean` | `23.183` | `57.977` | `81.162` |
| `Bits 12-13` | `>> 12` | `astro_ceres_ra_icrf_mean` | `267.76` | `278.85` | `287.63` |
| `Bits 14-15` | `>> 14` | `astro_ceres_dec_icrf_mean` | `-23.488` | `-23.063` | `-22.372` |

### Container: `packed_astro_container_034` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_ceres_ra_app_mean` | `268.12` | `279.22` | `287.99` |
| `Bits 2-3` | `>> 2` | `astro_ceres_dec_app_mean` | `-23.449` | `-23.044` | `-22.379` |
| `Bits 4-5` | `>> 4` | `astro_ceres_azim_mean` | `85.795` | `98.541` | `111.6` |
| `Bits 6-7` | `>> 6` | `astro_ceres_elev_mean` | `-38.508` | `-25.574` | `-11.301` |
| `Bits 8-9` | `>> 8` | `astro_ceres_app_mag_mean` | `8.8272` | `8.988` | `9.0485` |
| `Bits 10-11` | `>> 10` | `astro_ceres_surf_bright_mean` | `6.7522` | `6.9037` | `6.9714` |
| `Bits 12-13` | `>> 12` | `astro_ceres_dist_mean` | `2.7131` | `3.0833` | `3.3927` |
| `Bits 14-15` | `>> 14` | `astro_ceres_dist_rate_mean` | `-22.127` | `-20.487` | `-15.748` |

### Container: `packed_astro_container_035` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_ceres_helio_dist_mean` | `2.7869` | `2.8107` | `2.8337` |
| `Bits 2-3` | `>> 2` | `astro_ceres_helio_dist_rate_mean` | `1.3159` | `1.3648` | `1.3986` |
| `Bits 4-5` | `>> 4` | `astro_ceres_phase_angle_mean` | `14.5` | `18.612` | `20.075` |
| `Bits 6-7` | `>> 6` | `astro_ceres_elong_mean` | `45.123` | `64.919` | `86.52` |
| `Bits 8-9` | `>> 8` | `astro_ceres_illum_frac_mean` | `23.183` | `57.977` | `81.162` |
| `Bits 10-11` | `>> 10` | `astro_venus_ra_icrf_mean` | `214.61` | `276.49` | `315.37` |
| `Bits 12-13` | `>> 12` | `astro_venus_dec_icrf_mean` | `-20.861` | `-15.746` | `-2.9093` |
| `Bits 14-15` | `>> 14` | `astro_venus_ra_app_mean` | `214.92` | `276.84` | `315.7` |

### Container: `packed_astro_container_036` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_dec_app_mean` | `-20.874` | `-15.643` | `-2.7777` |
| `Bits 2-3` | `>> 2` | `astro_venus_azim_mean` | `38.683` | `56.025` | `72.821` |
| `Bits 4-5` | `>> 4` | `astro_venus_elev_mean` | `-50.29` | `-46.538` | `-41.446` |
| `Bits 6-7` | `>> 6` | `astro_venus_app_mag_mean` | `-3.9396` | `-3.8906` | `-3.8796` |
| `Bits 8-9` | `>> 8` | `astro_venus_surf_bright_mean` | `0.87307` | `0.96464` | `1.062` |
| `Bits 10-11` | `>> 10` | `astro_venus_dist_mean` | `1.3714` | `1.5144` | `1.6266` |
| `Bits 12-13` | `>> 12` | `astro_venus_dist_rate_mean` | `5.3937` | `7.2903` | `8.9526` |
| `Bits 14-15` | `>> 14` | `astro_venus_helio_dist_mean` | `0.72469` | `0.72644` | `0.7277` |

### Container: `packed_astro_container_037` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_helio_dist_rate_mean` | `-0.084672` | `0.10287` | `0.21074` |
| `Bits 2-3` | `>> 2` | `astro_venus_phase_angle_mean` | `23.177` | `33.391` | `43.788` |
| `Bits 4-5` | `>> 4` | `astro_venus_elong_mean` | `16.651` | `23.818` | `30.579` |
| `Bits 6-7` | `>> 6` | `astro_venus_illum_frac_mean` | `23.183` | `57.977` | `81.162` |
| `Bits 8-9` | `>> 8` | `astro_sun_ra_icrf_median` | `27.758` | `295.31` | `325.99` |
| `Bits 10-11` | `>> 10` | `astro_sun_dec_icrf_median` | `-16.877` | `-6.6443` | `4.99` |
| `Bits 12-13` | `>> 12` | `astro_sun_ra_app_median` | `28.075` | `295.66` | `326.31` |
| `Bits 14-15` | `>> 14` | `astro_sun_dec_app_median` | `-16.785` | `-6.5182` | `5.1198` |

### Container: `packed_astro_container_038` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_azim_median` | `16.39` | `17.054` | `20.96` |
| `Bits 2-3` | `>> 2` | `astro_sun_elev_median` | `-62.707` | `-52.64` | `-40.83` |
| `Bits 4-5` | `>> 4` | `astro_sun_app_mag_median` | `-26.773` | `-26.761` | `-26.743` |
| `Bits 6-7` | `>> 6` | `astro_sun_dist_median` | `0.98554` | `0.99151` | `0.99964` |
| `Bits 8-9` | `>> 8` | `astro_sun_dist_rate_median` | `0.20127` | `0.36922` | `0.39401` |
| `Bits 10-11` | `>> 10` | `astro_sun_illum_frac_median` | `20.617` | `58.276` | `83.77` |
| `Bits 12-13` | `>> 12` | `astro_moon_ra_icrf_median` | `120.92` | `194.79` | `269.55` |
| `Bits 14-15` | `>> 14` | `astro_moon_dec_icrf_median` | `-22.576` | `-6.3342` | `17.518` |

### Container: `packed_astro_container_039` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_ra_app_median` | `121.28` | `195.11` | `269.91` |
| `Bits 2-3` | `>> 2` | `astro_moon_dec_app_median` | `-22.534` | `-6.4637` | `17.568` |
| `Bits 4-5` | `>> 4` | `astro_moon_azim_median` | `107.94` | `173.27` | `269.68` |
| `Bits 6-7` | `>> 6` | `astro_moon_elev_median` | `-24.167` | `3.3341` | `26.709` |
| `Bits 8-9` | `>> 8` | `astro_moon_app_mag_median` | `-11.389` | `-10.433` | `-8.4887` |
| `Bits 10-11` | `>> 10` | `astro_moon_surf_bright_median` | `4.4257` | `5.033` | `5.7308` |
| `Bits 12-13` | `>> 12` | `astro_moon_dist_median` | `0.0024904` | `0.0025823` | `0.002665` |
| `Bits 14-15` | `>> 14` | `astro_moon_dist_rate_median` | `-0.27879` | `-0.060578` | `0.23225` |

### Container: `packed_astro_container_040` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_helio_dist_median` | `0.98635` | `0.99186` | `0.9998` |
| `Bits 2-3` | `>> 2` | `astro_moon_helio_dist_rate_median` | `-0.25854` | `0.13619` | `0.99541` |
| `Bits 4-5` | `>> 4` | `astro_moon_phase_angle_median` | `47.507` | `80.361` | `126.28` |
| `Bits 6-7` | `>> 6` | `astro_moon_elong_median` | `53.607` | `99.492` | `132.38` |
| `Bits 8-9` | `>> 8` | `astro_moon_illum_frac_median` | `20.617` | `58.276` | `83.77` |
| `Bits 10-11` | `>> 10` | `astro_saturn_ra_icrf_median` | `338.68` | `342.05` | `345.35` |
| `Bits 12-13` | `>> 12` | `astro_saturn_dec_icrf_median` | `-10.692` | `-9.3646` | `-8.0648` |
| `Bits 14-15` | `>> 14` | `astro_saturn_ra_app_median` | `338.99` | `342.36` | `345.66` |

### Container: `packed_astro_container_041` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_dec_app_median` | `-10.57` | `-9.2399` | `-7.9371` |
| `Bits 2-3` | `>> 2` | `astro_saturn_azim_median` | `45.43` | `70.66` | `313.1` |
| `Bits 4-5` | `>> 4` | `astro_saturn_elev_median` | `-54.947` | `-49.24` | `-41.255` |
| `Bits 6-7` | `>> 6` | `astro_saturn_app_mag_median` | `0.983` | `0.991` | `1.0573` |
| `Bits 8-9` | `>> 8` | `astro_saturn_surf_bright_median` | `6.693` | `6.717` | `6.7765` |
| `Bits 10-11` | `>> 10` | `astro_saturn_dist_median` | `10.437` | `10.585` | `10.678` |
| `Bits 12-13` | `>> 12` | `astro_saturn_dist_rate_median` | `-14.33` | `-1.7413` | `11.364` |
| `Bits 14-15` | `>> 14` | `astro_saturn_helio_dist_median` | `9.7115` | `9.72` | `9.7286` |

### Container: `packed_astro_container_042` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_helio_dist_rate_median` | `-0.49984` | `-0.49638` | `-0.49331` |
| `Bits 2-3` | `>> 2` | `astro_saturn_phase_angle_median` | `1.4145` | `2.7328` | `3.9068` |
| `Bits 4-5` | `>> 4` | `astro_saturn_elong_median` | `14.034` | `27.854` | `41.689` |
| `Bits 6-7` | `>> 6` | `astro_saturn_illum_frac_median` | `20.617` | `58.276` | `83.77` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_ra_icrf_median` | `35.142` | `39.282` | `45.07` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_dec_icrf_median` | `12.926` | `14.394` | `16.208` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_ra_app_median` | `35.466` | `39.609` | `45.402` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_dec_app_median` | `13.036` | `14.498` | `16.303` |

### Container: `packed_astro_container_043` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_azim_median` | `293.34` | `313.82` | `337.04` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_elev_median` | `-27.811` | `-19.613` | `-5.385` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_app_mag_median` | `-2.3362` | `-2.1665` | `-2.0598` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_surf_bright_median` | `5.3332` | `5.357` | `5.3673` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_dist_median` | `4.9956` | `5.4455` | `5.7937` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_dist_rate_median` | `16.316` | `24.084` | `27.193` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_helio_dist_median` | `4.9914` | `4.9977` | `5.0045` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_helio_dist_rate_median` | `0.35784` | `0.38064` | `0.40335` |

### Container: `packed_astro_container_044` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_phase_angle_median` | `6.5176` | `9.7122` | `10.94` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_elong_median` | `34.652` | `58.367` | `84.104` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_illum_frac_median` | `20.617` | `58.276` | `83.77` |
| `Bits 6-7` | `>> 6` | `astro_mars_ra_icrf_median` | `293.51` | `317.31` | `339.79` |
| `Bits 8-9` | `>> 8` | `astro_mars_dec_icrf_median` | `-22.523` | `-17.488` | `-9.8304` |
| `Bits 10-11` | `>> 10` | `astro_mars_ra_app_median` | `288.14` | `312.15` | `334.94` |
| `Bits 12-13` | `>> 12` | `astro_mars_dec_app_median` | `-22.472` | `-17.393` | `-9.7068` |
| `Bits 14-15` | `>> 14` | `astro_mars_azim_median` | `62.556` | `62.687` | `62.862` |

### Container: `packed_astro_container_045` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_elev_median` | `-56.728` | `-49.451` | `-39.282` |
| `Bits 2-3` | `>> 2` | `astro_mars_app_mag_median` | `1.1835` | `1.2645` | `1.3022` |
| `Bits 4-5` | `>> 4` | `astro_mars_surf_bright_median` | `4.0572` | `4.0985` | `4.1345` |
| `Bits 6-7` | `>> 6` | `astro_mars_dist_median` | `2.0857` | `2.2002` | `2.3127` |
| `Bits 8-9` | `>> 8` | `astro_mars_dist_rate_median` | `-6.8484` | `-6.7931` | `-6.4948` |
| `Bits 10-11` | `>> 10` | `astro_mars_helio_dist_median` | `1.3909` | `1.4115` | `1.4411` |
| `Bits 12-13` | `>> 12` | `astro_mars_helio_dist_rate_median` | `-1.9363` | `-1.4893` | `-0.87799` |
| `Bits 14-15` | `>> 14` | `astro_mars_phase_angle_median` | `14.469` | `19.622` | `24.358` |

### Container: `packed_astro_container_046` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_elong_median` | `21.428` | `28.557` | `35.018` |
| `Bits 2-3` | `>> 2` | `astro_mars_illum_frac_median` | `20.617` | `58.276` | `83.77` |
| `Bits 4-5` | `>> 4` | `astro_ceres_ra_icrf_median` | `267.76` | `278.86` | `287.63` |
| `Bits 6-7` | `>> 6` | `astro_ceres_dec_icrf_median` | `-23.487` | `-23.063` | `-22.374` |
| `Bits 8-9` | `>> 8` | `astro_ceres_ra_app_median` | `268.12` | `279.22` | `288` |
| `Bits 10-11` | `>> 10` | `astro_ceres_dec_app_median` | `-23.448` | `-23.045` | `-22.381` |
| `Bits 12-13` | `>> 12` | `astro_ceres_azim_median` | `85.801` | `98.54` | `111.59` |
| `Bits 14-15` | `>> 14` | `astro_ceres_elev_median` | `-38.512` | `-25.577` | `-11.302` |

### Container: `packed_astro_container_047` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_ceres_app_mag_median` | `8.8275` | `8.9885` | `9.0488` |
| `Bits 2-3` | `>> 2` | `astro_ceres_surf_bright_median` | `6.7525` | `6.904` | `6.9713` |
| `Bits 4-5` | `>> 4` | `astro_ceres_dist_median` | `2.7131` | `3.0834` | `3.3929` |
| `Bits 6-7` | `>> 6` | `astro_ceres_dist_rate_median` | `-22.134` | `-20.493` | `-15.751` |
| `Bits 8-9` | `>> 8` | `astro_ceres_helio_dist_median` | `2.7869` | `2.8107` | `2.8337` |
| `Bits 10-11` | `>> 10` | `astro_ceres_helio_dist_rate_median` | `1.316` | `1.3648` | `1.3986` |
| `Bits 12-13` | `>> 12` | `astro_ceres_phase_angle_median` | `14.503` | `18.617` | `20.082` |
| `Bits 14-15` | `>> 14` | `astro_ceres_elong_median` | `45.121` | `64.915` | `86.513` |

### Container: `packed_astro_container_048` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_ceres_illum_frac_median` | `20.617` | `58.276` | `83.77` |
| `Bits 2-3` | `>> 2` | `astro_venus_ra_icrf_median` | `246.63` | `285.82` | `324.07` |
| `Bits 4-5` | `>> 4` | `astro_venus_dec_icrf_median` | `-20.88` | `-15.76` | `-2.9124` |
| `Bits 6-7` | `>> 6` | `astro_venus_ra_app_median` | `246.98` | `286.17` | `324.4` |
| `Bits 8-9` | `>> 8` | `astro_venus_dec_app_median` | `-20.894` | `-15.658` | `-2.7806` |
| `Bits 10-11` | `>> 10` | `astro_venus_azim_median` | `38.671` | `56.024` | `72.85` |
| `Bits 12-13` | `>> 12` | `astro_venus_elev_median` | `-50.31` | `-46.551` | `-41.451` |
| `Bits 14-15` | `>> 14` | `astro_venus_app_mag_median` | `-3.9392` | `-3.8905` | `-3.8795` |

### Container: `packed_astro_container_049` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_surf_bright_median` | `0.873` | `0.965` | `1.062` |
| `Bits 2-3` | `>> 2` | `astro_venus_dist_median` | `1.3715` | `1.5144` | `1.6267` |
| `Bits 4-5` | `>> 4` | `astro_venus_dist_rate_median` | `5.3955` | `7.2915` | `8.9535` |
| `Bits 6-7` | `>> 6` | `astro_venus_helio_dist_median` | `0.7247` | `0.72645` | `0.72771` |
| `Bits 8-9` | `>> 8` | `astro_venus_helio_dist_rate_median` | `-0.0848` | `0.10303` | `0.21106` |
| `Bits 10-11` | `>> 10` | `astro_venus_phase_angle_median` | `23.178` | `33.39` | `43.786` |
| `Bits 12-13` | `>> 12` | `astro_venus_elong_median` | `16.652` | `23.819` | `30.58` |
| `Bits 14-15` | `>> 14` | `astro_venus_illum_frac_median` | `20.617` | `58.276` | `83.77` |

### Container: `packed_astro_container_050` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_ra_icrf_min_shift_m14d` | `280.57` | `280.57` | `280.57` |
| `Bits 2-3` | `>> 2` | `astro_sun_dec_icrf_min_shift_m14d` | `-23.081` | `-23.081` | `-23.081` |
| `Bits 4-5` | `>> 4` | `astro_sun_ra_app_min_shift_m14d` | `280.92` | `280.92` | `280.92` |
| `Bits 6-7` | `>> 6` | `astro_sun_dec_app_min_shift_m14d` | `-23.059` | `-23.059` | `-23.059` |
| `Bits 8-9` | `>> 8` | `astro_sun_azim_min_shift_m14d` | `29.525` | `29.525` | `29.525` |
| `Bits 10-11` | `>> 10` | `astro_sun_elev_min_shift_m14d` | `-67.753` | `-67.753` | `-67.753` |
| `Bits 12-13` | `>> 12` | `astro_sun_app_mag_min_shift_m14d` | `-26.779` | `-26.779` | `-26.779` |
| `Bits 14-15` | `>> 14` | `astro_sun_dist_min_shift_m14d` | `0.98335` | `0.98335` | `0.98335` |

### Container: `packed_astro_container_051` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_dist_rate_min_shift_m14d` | `-0.087413` | `-0.087412` | `-0.087411` |
| `Bits 2-3` | `>> 2` | `astro_sun_illum_frac_min_shift_m14d` | `22.786` | `22.786` | `22.786` |
| `Bits 4-5` | `>> 4` | `astro_moon_ra_icrf_min_shift_m14d` | `159.29` | `159.29` | `159.29` |
| `Bits 6-7` | `>> 6` | `astro_moon_dec_icrf_min_shift_m14d` | `-20.017` | `-20.017` | `-20.017` |
| `Bits 8-9` | `>> 8` | `astro_moon_ra_app_min_shift_m14d` | `159.61` | `159.61` | `159.61` |
| `Bits 10-11` | `>> 10` | `astro_moon_dec_app_min_shift_m14d` | `-20.11` | `-20.11` | `-20.11` |
| `Bits 12-13` | `>> 12` | `astro_moon_azim_min_shift_m14d` | `94.369` | `94.369` | `94.369` |
| `Bits 14-15` | `>> 14` | `astro_moon_elev_min_shift_m14d` | `-25.607` | `-25.607` | `-25.607` |

### Container: `packed_astro_container_052` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_app_mag_min_shift_m14d` | `-11.154` | `-11.154` | `-11.154` |
| `Bits 2-3` | `>> 2` | `astro_moon_surf_bright_min_shift_m14d` | `4.571` | `4.571` | `4.571` |
| `Bits 4-5` | `>> 4` | `astro_moon_dist_min_shift_m14d` | `0.0026113` | `0.0026123` | `0.0026133` |
| `Bits 6-7` | `>> 6` | `astro_moon_dist_rate_min_shift_m14d` | `-0.37172` | `-0.37172` | `-0.37172` |
| `Bits 8-9` | `>> 8` | `astro_moon_helio_dist_min_shift_m14d` | `0.98196` | `0.98196` | `0.98196` |
| `Bits 10-11` | `>> 10` | `astro_moon_helio_dist_rate_min_shift_m14d` | `-0.87805` | `-0.87805` | `-0.87805` |
| `Bits 12-13` | `>> 12` | `astro_moon_phase_angle_min_shift_m14d` | `56.517` | `56.518` | `56.518` |
| `Bits 14-15` | `>> 14` | `astro_moon_elong_min_shift_m14d` | `56.9` | `56.9` | `56.9` |

### Container: `packed_astro_container_053` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_illum_frac_min_shift_m14d` | `22.786` | `22.786` | `22.786` |
| `Bits 2-3` | `>> 2` | `astro_saturn_ra_icrf_min_shift_m14d` | `335.46` | `335.46` | `335.46` |
| `Bits 4-5` | `>> 4` | `astro_saturn_dec_icrf_min_shift_m14d` | `-11.958` | `-11.958` | `-11.958` |
| `Bits 6-7` | `>> 6` | `astro_saturn_ra_app_min_shift_m14d` | `335.78` | `335.78` | `335.78` |
| `Bits 8-9` | `>> 8` | `astro_saturn_dec_app_min_shift_m14d` | `-11.839` | `-11.839` | `-11.839` |
| `Bits 10-11` | `>> 10` | `astro_saturn_azim_min_shift_m14d` | `297.28` | `297.28` | `297.28` |
| `Bits 12-13` | `>> 12` | `astro_saturn_elev_min_shift_m14d` | `-45.349` | `-45.349` | `-45.349` |
| `Bits 14-15` | `>> 14` | `astro_saturn_app_mag_min_shift_m14d` | `0.955` | `0.955` | `0.955` |

### Container: `packed_astro_container_054` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_surf_bright_min_shift_m14d` | `6.723` | `6.723` | `6.723` |
| `Bits 2-3` | `>> 2` | `astro_saturn_dist_min_shift_m14d` | `10.295` | `10.295` | `10.295` |
| `Bits 4-5` | `>> 4` | `astro_saturn_dist_rate_min_shift_m14d` | `21.404` | `21.404` | `21.404` |
| `Bits 6-7` | `>> 6` | `astro_saturn_helio_dist_min_shift_m14d` | `9.7361` | `9.7361` | `9.7362` |
| `Bits 8-9` | `>> 8` | `astro_saturn_helio_dist_rate_min_shift_m14d` | `-0.49018` | `-0.49018` | `-0.49018` |
| `Bits 10-11` | `>> 10` | `astro_saturn_phase_angle_min_shift_m14d` | `4.2836` | `4.2836` | `4.2836` |
| `Bits 12-13` | `>> 12` | `astro_saturn_elong_min_shift_m14d` | `47.66` | `47.661` | `47.661` |
| `Bits 14-15` | `>> 14` | `astro_saturn_illum_frac_min_shift_m14d` | `22.786` | `22.786` | `22.786` |

### Container: `packed_astro_container_055` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_ra_icrf_min_shift_m14d` | `33.361` | `33.361` | `33.361` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_dec_icrf_min_shift_m14d` | `12.151` | `12.151` | `12.151` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_ra_app_min_shift_m14d` | `33.685` | `33.685` | `33.685` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_dec_app_min_shift_m14d` | `12.264` | `12.264` | `12.264` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_azim_min_shift_m14d` | `272.24` | `272.24` | `272.24` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_elev_min_shift_m14d` | `11.557` | `11.557` | `11.557` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_app_mag_min_shift_m14d` | `-2.589` | `-2.589` | `-2.589` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_surf_bright_min_shift_m14d` | `5.357` | `5.357` | `5.357` |

### Container: `packed_astro_container_056` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_dist_min_shift_m14d` | `4.4815` | `4.4815` | `4.4815` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_dist_rate_min_shift_m14d` | `25.552` | `25.552` | `25.552` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_helio_dist_min_shift_m14d` | `4.9849` | `4.9849` | `4.9849` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_helio_dist_rate_min_shift_m14d` | `0.32902` | `0.32902` | `0.32902` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_phase_angle_min_shift_m14d` | `10.249` | `10.249` | `10.249` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_elong_min_shift_m14d` | `109.5` | `109.5` | `109.5` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_illum_frac_min_shift_m14d` | `22.786` | `22.786` | `22.786` |
| `Bits 14-15` | `>> 14` | `astro_mars_ra_icrf_min_shift_m14d` | `266.7` | `266.7` | `266.7` |

### Container: `packed_astro_container_057` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_dec_icrf_min_shift_m14d` | `-24.037` | `-24.037` | `-24.037` |
| `Bits 2-3` | `>> 2` | `astro_mars_ra_app_min_shift_m14d` | `267.05` | `267.05` | `267.05` |
| `Bits 4-5` | `>> 4` | `astro_mars_dec_app_min_shift_m14d` | `-24.035` | `-24.035` | `-24.035` |
| `Bits 6-7` | `>> 6` | `astro_mars_azim_min_shift_m14d` | `57.573` | `57.573` | `57.573` |
| `Bits 8-9` | `>> 8` | `astro_mars_elev_min_shift_m14d` | `-61.284` | `-61.284` | `-61.284` |
| `Bits 10-11` | `>> 10` | `astro_mars_app_mag_min_shift_m14d` | `1.411` | `1.411` | `1.411` |
| `Bits 12-13` | `>> 12` | `astro_mars_surf_bright_min_shift_m14d` | `4.085` | `4.085` | `4.085` |
| `Bits 14-15` | `>> 14` | `astro_mars_dist_min_shift_m14d` | `2.4052` | `2.4052` | `2.4052` |

### Container: `packed_astro_container_058` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_dist_rate_min_shift_m14d` | `-5.666` | `-5.666` | `-5.666` |
| `Bits 2-3` | `>> 2` | `astro_mars_helio_dist_min_shift_m14d` | `1.4731` | `1.4731` | `1.4731` |
| `Bits 4-5` | `>> 4` | `astro_mars_helio_dist_rate_min_shift_m14d` | `-2.208` | `-2.208` | `-2.208` |
| `Bits 6-7` | `>> 6` | `astro_mars_phase_angle_min_shift_m14d` | `8.4223` | `8.4223` | `8.4223` |
| `Bits 8-9` | `>> 8` | `astro_mars_elong_min_shift_m14d` | `12.742` | `12.742` | `12.742` |
| `Bits 10-11` | `>> 10` | `astro_mars_illum_frac_min_shift_m14d` | `22.786` | `22.786` | `22.786` |
| `Bits 12-13` | `>> 12` | `astro_ceres_ra_icrf_min_shift_m14d` | `254.07` | `254.07` | `254.07` |
| `Bits 14-15` | `>> 14` | `astro_ceres_dec_icrf_min_shift_m14d` | `-21.093` | `-21.093` | `-21.093` |

### Container: `packed_astro_container_059` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_ceres_ra_app_min_shift_m14d` | `254.42` | `254.42` | `254.42` |
| `Bits 2-3` | `>> 2` | `astro_ceres_dec_app_min_shift_m14d` | `-21.125` | `-21.125` | `-21.125` |
| `Bits 4-5` | `>> 4` | `astro_ceres_azim_min_shift_m14d` | `68.346` | `68.346` | `68.346` |
| `Bits 6-7` | `>> 6` | `astro_ceres_elev_min_shift_m14d` | `-50.727` | `-50.727` | `-50.727` |
| `Bits 8-9` | `>> 8` | `astro_ceres_app_mag_min_shift_m14d` | `8.95` | `8.95` | `8.95` |
| `Bits 10-11` | `>> 10` | `astro_ceres_surf_bright_min_shift_m14d` | `6.504` | `6.504` | `6.504` |
| `Bits 12-13` | `>> 12` | `astro_ceres_dist_min_shift_m14d` | `3.5911` | `3.5911` | `3.5911` |
| `Bits 14-15` | `>> 14` | `astro_ceres_dist_rate_min_shift_m14d` | `-10.144` | `-10.144` | `-10.144` |

### Container: `packed_astro_container_060` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_ceres_helio_dist_min_shift_m14d` | `2.7602` | `2.7602` | `2.7602` |
| `Bits 2-3` | `>> 2` | `astro_ceres_helio_dist_rate_min_shift_m14d` | `1.4152` | `1.4152` | `1.4152` |
| `Bits 4-5` | `>> 4` | `astro_ceres_phase_angle_min_shift_m14d` | `8.5488` | `8.5488` | `8.5488` |
| `Bits 6-7` | `>> 6` | `astro_ceres_elong_min_shift_m14d` | `24.667` | `24.667` | `24.667` |
| `Bits 8-9` | `>> 8` | `astro_ceres_illum_frac_min_shift_m14d` | `22.786` | `22.786` | `22.786` |
| `Bits 10-11` | `>> 10` | `astro_venus_ra_icrf_min_shift_m14d` | `240.61` | `240.61` | `240.61` |
| `Bits 12-13` | `>> 12` | `astro_venus_dec_icrf_min_shift_m14d` | `-20.155` | `-20.155` | `-20.155` |
| `Bits 14-15` | `>> 14` | `astro_venus_ra_app_min_shift_m14d` | `240.95` | `240.95` | `240.95` |

### Container: `packed_astro_container_061` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_dec_app_min_shift_m14d` | `-20.205` | `-20.205` | `-20.205` |
| `Bits 2-3` | `>> 2` | `astro_venus_azim_min_shift_m14d` | `78.303` | `78.303` | `78.303` |
| `Bits 4-5` | `>> 4` | `astro_venus_elev_min_shift_m14d` | `-42.098` | `-42.098` | `-42.098` |
| `Bits 6-7` | `>> 6` | `astro_venus_app_mag_min_shift_m14d` | `-4.039` | `-4.039` | `-4.039` |
| `Bits 8-9` | `>> 8` | `astro_venus_surf_bright_min_shift_m14d` | `1.155` | `1.155` | `1.155` |
| `Bits 10-11` | `>> 10` | `astro_venus_dist_min_shift_m14d` | `1.1819` | `1.1819` | `1.1819` |
| `Bits 12-13` | `>> 12` | `astro_venus_dist_rate_min_shift_m14d` | `10.33` | `10.33` | `10.33` |
| `Bits 14-15` | `>> 14` | `astro_venus_helio_dist_min_shift_m14d` | `0.72045` | `0.72045` | `0.72045` |

### Container: `packed_astro_container_062` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_helio_dist_rate_min_shift_m14d` | `0.19155` | `0.19155` | `0.19155` |
| `Bits 2-3` | `>> 2` | `astro_venus_phase_angle_min_shift_m14d` | `53.77` | `53.77` | `53.77` |
| `Bits 4-5` | `>> 4` | `astro_venus_elong_min_shift_m14d` | `36.265` | `36.265` | `36.265` |
| `Bits 6-7` | `>> 6` | `astro_venus_illum_frac_min_shift_m14d` | `22.786` | `22.786` | `22.786` |
| `Bits 8-9` | `>> 8` | `astro_sun_ra_icrf_max_shift_m14d` | `287.17` | `287.17` | `287.17` |
| `Bits 10-11` | `>> 10` | `astro_sun_dec_icrf_max_shift_m14d` | `-22.499` | `-22.499` | `-22.499` |
| `Bits 12-13` | `>> 12` | `astro_sun_ra_app_max_shift_m14d` | `287.52` | `287.52` | `287.52` |
| `Bits 14-15` | `>> 14` | `astro_sun_dec_app_max_shift_m14d` | `-22.462` | `-22.462` | `-22.462` |

### Container: `packed_astro_container_063` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_azim_max_shift_m14d` | `31.68` | `31.68` | `31.68` |
| `Bits 2-3` | `>> 2` | `astro_sun_elev_max_shift_m14d` | `-67.464` | `-67.464` | `-67.464` |
| `Bits 4-5` | `>> 4` | `astro_sun_app_mag_max_shift_m14d` | `-26.779` | `-26.779` | `-26.779` |
| `Bits 6-7` | `>> 6` | `astro_sun_dist_max_shift_m14d` | `0.98339` | `0.98339` | `0.98339` |
| `Bits 8-9` | `>> 8` | `astro_sun_dist_rate_max_shift_m14d` | `-0.030764` | `-0.030763` | `-0.030762` |
| `Bits 10-11` | `>> 10` | `astro_sun_illum_frac_max_shift_m14d` | `77.587` | `77.587` | `77.587` |
| `Bits 12-13` | `>> 12` | `astro_moon_ra_icrf_max_shift_m14d` | `225.73` | `225.73` | `225.73` |
| `Bits 14-15` | `>> 14` | `astro_moon_dec_icrf_max_shift_m14d` | `12.253` | `12.253` | `12.253` |

### Container: `packed_astro_container_064` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_ra_app_max_shift_m14d` | `226.07` | `226.07` | `226.07` |
| `Bits 2-3` | `>> 2` | `astro_moon_dec_app_max_shift_m14d` | `12.128` | `12.128` | `12.128` |
| `Bits 4-5` | `>> 4` | `astro_moon_azim_max_shift_m14d` | `113.37` | `113.37` | `113.37` |
| `Bits 6-7` | `>> 6` | `astro_moon_elev_max_shift_m14d` | `39.751` | `39.751` | `39.751` |
| `Bits 8-9` | `>> 8` | `astro_moon_app_mag_max_shift_m14d` | `-8.613` | `-8.613` | `-8.613` |
| `Bits 10-11` | `>> 10` | `astro_moon_surf_bright_max_shift_m14d` | `5.837` | `5.837` | `5.837` |
| `Bits 12-13` | `>> 12` | `astro_moon_dist_max_shift_m14d` | `0.002685` | `0.002686` | `0.002687` |
| `Bits 14-15` | `>> 14` | `astro_moon_dist_rate_max_shift_m14d` | `-0.22195` | `-0.22195` | `-0.22195` |

### Container: `packed_astro_container_065` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_helio_dist_max_shift_m14d` | `0.98483` | `0.98483` | `0.98483` |
| `Bits 2-3` | `>> 2` | `astro_moon_helio_dist_rate_max_shift_m14d` | `-0.71371` | `-0.71371` | `-0.71371` |
| `Bits 4-5` | `>> 4` | `astro_moon_phase_angle_max_shift_m14d` | `122.97` | `122.97` | `122.97` |
| `Bits 6-7` | `>> 6` | `astro_moon_elong_max_shift_m14d` | `123.35` | `123.35` | `123.35` |
| `Bits 8-9` | `>> 8` | `astro_moon_illum_frac_max_shift_m14d` | `77.587` | `77.587` | `77.587` |
| `Bits 10-11` | `>> 10` | `astro_saturn_ra_icrf_max_shift_m14d` | `335.99` | `335.99` | `335.99` |
| `Bits 12-13` | `>> 12` | `astro_saturn_dec_icrf_max_shift_m14d` | `-11.752` | `-11.752` | `-11.752` |
| `Bits 14-15` | `>> 14` | `astro_saturn_ra_app_max_shift_m14d` | `336.3` | `336.3` | `336.3` |

### Container: `packed_astro_container_066` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_dec_app_max_shift_m14d` | `-11.633` | `-11.633` | `-11.633` |
| `Bits 2-3` | `>> 2` | `astro_saturn_azim_max_shift_m14d` | `303.03` | `303.03` | `303.03` |
| `Bits 4-5` | `>> 4` | `astro_saturn_elev_max_shift_m14d` | `-42.082` | `-42.082` | `-42.082` |
| `Bits 6-7` | `>> 6` | `astro_saturn_app_mag_max_shift_m14d` | `0.967` | `0.967` | `0.967` |
| `Bits 8-9` | `>> 8` | `astro_saturn_surf_bright_max_shift_m14d` | `6.727` | `6.727` | `6.727` |
| `Bits 10-11` | `>> 10` | `astro_saturn_dist_max_shift_m14d` | `10.371` | `10.371` | `10.371` |
| `Bits 12-13` | `>> 12` | `astro_saturn_dist_rate_max_shift_m14d` | `23.199` | `23.199` | `23.199` |
| `Bits 14-15` | `>> 14` | `astro_saturn_helio_dist_max_shift_m14d` | `9.7378` | `9.7378` | `9.7378` |

### Container: `packed_astro_container_067` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_helio_dist_rate_max_shift_m14d` | `-0.48811` | `-0.48811` | `-0.48811` |
| `Bits 2-3` | `>> 2` | `astro_saturn_phase_angle_max_shift_m14d` | `4.6409` | `4.6409` | `4.6409` |
| `Bits 4-5` | `>> 4` | `astro_saturn_elong_max_shift_m14d` | `53.221` | `53.222` | `53.222` |
| `Bits 6-7` | `>> 6` | `astro_saturn_illum_frac_max_shift_m14d` | `77.587` | `77.587` | `77.587` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_ra_icrf_max_shift_m14d` | `33.429` | `33.429` | `33.429` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_dec_icrf_max_shift_m14d` | `12.207` | `12.207` | `12.207` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_ra_app_max_shift_m14d` | `33.753` | `33.753` | `33.753` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_dec_app_max_shift_m14d` | `12.319` | `12.319` | `12.319` |

### Container: `packed_astro_container_068` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_azim_max_shift_m14d` | `276.17` | `276.17` | `276.17` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_elev_max_shift_m14d` | `15.8` | `15.8` | `15.8` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_app_mag_max_shift_m14d` | `-2.539` | `-2.539` | `-2.539` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_surf_bright_max_shift_m14d` | `5.362` | `5.362` | `5.362` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_dist_max_shift_m14d` | `4.5709` | `4.5709` | `4.5709` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_dist_rate_max_shift_m14d` | `26.669` | `26.669` | `26.669` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_helio_dist_max_shift_m14d` | `4.986` | `4.986` | `4.986` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_helio_dist_rate_max_shift_m14d` | `0.33541` | `0.33541` | `0.33541` |

### Container: `packed_astro_container_069` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_phase_angle_max_shift_m14d` | `10.71` | `10.71` | `10.71` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_elong_max_shift_m14d` | `115.54` | `115.54` | `115.54` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_illum_frac_max_shift_m14d` | `77.587` | `77.587` | `77.587` |
| `Bits 6-7` | `>> 6` | `astro_mars_ra_icrf_max_shift_m14d` | `271.58` | `271.58` | `271.58` |
| `Bits 8-9` | `>> 8` | `astro_mars_dec_icrf_max_shift_m14d` | `-23.952` | `-23.952` | `-23.952` |
| `Bits 10-11` | `>> 10` | `astro_mars_ra_app_max_shift_m14d` | `271.94` | `271.94` | `271.94` |
| `Bits 12-13` | `>> 12` | `astro_mars_dec_app_max_shift_m14d` | `-23.962` | `-23.962` | `-23.962` |
| `Bits 14-15` | `>> 14` | `astro_mars_azim_max_shift_m14d` | `59.092` | `59.092` | `59.092` |

### Container: `packed_astro_container_070` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_elev_max_shift_m14d` | `-60.694` | `-60.694` | `-60.694` |
| `Bits 2-3` | `>> 2` | `astro_mars_app_mag_max_shift_m14d` | `1.44` | `1.44` | `1.44` |
| `Bits 4-5` | `>> 4` | `astro_mars_surf_bright_max_shift_m14d` | `4.112` | `4.112` | `4.112` |
| `Bits 6-7` | `>> 6` | `astro_mars_dist_max_shift_m14d` | `2.4238` | `2.4238` | `2.4238` |
| `Bits 8-9` | `>> 8` | `astro_mars_dist_rate_max_shift_m14d` | `-5.4012` | `-5.4012` | `-5.4012` |
| `Bits 10-11` | `>> 10` | `astro_mars_helio_dist_max_shift_m14d` | `1.4807` | `1.4807` | `1.4807` |
| `Bits 12-13` | `>> 12` | `astro_mars_helio_dist_rate_max_shift_m14d` | `-2.176` | `-2.176` | `-2.176` |
| `Bits 14-15` | `>> 14` | `astro_mars_phase_angle_max_shift_m14d` | `9.5532` | `9.5532` | `9.5532` |

### Container: `packed_astro_container_071` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_elong_max_shift_m14d` | `14.396` | `14.396` | `14.396` |
| `Bits 2-3` | `>> 2` | `astro_mars_illum_frac_max_shift_m14d` | `77.587` | `77.587` | `77.587` |
| `Bits 4-5` | `>> 4` | `astro_ceres_ra_icrf_max_shift_m14d` | `256.65` | `256.65` | `256.65` |
| `Bits 6-7` | `>> 6` | `astro_ceres_dec_icrf_max_shift_m14d` | `-20.692` | `-20.692` | `-20.692` |
| `Bits 8-9` | `>> 8` | `astro_ceres_ra_app_max_shift_m14d` | `257` | `257` | `257` |
| `Bits 10-11` | `>> 10` | `astro_ceres_dec_app_max_shift_m14d` | `-20.73` | `-20.73` | `-20.73` |
| `Bits 12-13` | `>> 12` | `astro_ceres_azim_max_shift_m14d` | `72.041` | `72.041` | `72.041` |
| `Bits 14-15` | `>> 14` | `astro_ceres_elev_max_shift_m14d` | `-48.688` | `-48.688` | `-48.688` |

### Container: `packed_astro_container_072` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_ceres_app_mag_max_shift_m14d` | `8.985` | `8.985` | `8.985` |
| `Bits 2-3` | `>> 2` | `astro_ceres_surf_bright_max_shift_m14d` | `6.557` | `6.557` | `6.557` |
| `Bits 4-5` | `>> 4` | `astro_ceres_dist_max_shift_m14d` | `3.6232` | `3.6232` | `3.6232` |
| `Bits 6-7` | `>> 6` | `astro_ceres_dist_rate_max_shift_m14d` | `-8.7694` | `-8.7694` | `-8.7694` |
| `Bits 8-9` | `>> 8` | `astro_ceres_helio_dist_max_shift_m14d` | `2.7651` | `2.7651` | `2.7651` |
| `Bits 10-11` | `>> 10` | `astro_ceres_helio_dist_rate_max_shift_m14d` | `1.417` | `1.417` | `1.417` |
| `Bits 12-13` | `>> 12` | `astro_ceres_phase_angle_max_shift_m14d` | `9.7133` | `9.7133` | `9.7133` |
| `Bits 14-15` | `>> 14` | `astro_ceres_elong_max_shift_m14d` | `28.326` | `28.326` | `28.326` |

### Container: `packed_astro_container_073` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_ceres_illum_frac_max_shift_m14d` | `77.587` | `77.587` | `77.587` |
| `Bits 2-3` | `>> 2` | `astro_venus_ra_icrf_max_shift_m14d` | `248.21` | `248.21` | `248.21` |
| `Bits 4-5` | `>> 4` | `astro_venus_dec_icrf_max_shift_m14d` | `-18.704` | `-18.704` | `-18.704` |
| `Bits 6-7` | `>> 6` | `astro_venus_ra_app_max_shift_m14d` | `248.56` | `248.56` | `248.56` |
| `Bits 8-9` | `>> 8` | `astro_venus_dec_app_max_shift_m14d` | `-18.77` | `-18.77` | `-18.77` |
| `Bits 10-11` | `>> 10` | `astro_venus_azim_max_shift_m14d` | `78.404` | `78.404` | `78.404` |
| `Bits 12-13` | `>> 12` | `astro_venus_elev_max_shift_m14d` | `-39.953` | `-39.953` | `-39.953` |
| `Bits 14-15` | `>> 14` | `astro_venus_app_mag_max_shift_m14d` | `-4.016` | `-4.016` | `-4.016` |

### Container: `packed_astro_container_074` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_surf_bright_max_shift_m14d` | `1.176` | `1.176` | `1.176` |
| `Bits 2-3` | `>> 2` | `astro_venus_dist_max_shift_m14d` | `1.2191` | `1.2191` | `1.2191` |
| `Bits 4-5` | `>> 4` | `astro_venus_dist_rate_max_shift_m14d` | `10.63` | `10.63` | `10.63` |
| `Bits 6-7` | `>> 6` | `astro_venus_helio_dist_max_shift_m14d` | `0.72115` | `0.72115` | `0.72116` |
| `Bits 8-9` | `>> 8` | `astro_venus_helio_dist_rate_max_shift_m14d` | `0.21206` | `0.21206` | `0.21206` |
| `Bits 10-11` | `>> 10` | `astro_venus_phase_angle_max_shift_m14d` | `56.136` | `56.136` | `56.136` |
| `Bits 12-13` | `>> 12` | `astro_venus_elong_max_shift_m14d` | `37.469` | `37.469` | `37.469` |
| `Bits 14-15` | `>> 14` | `astro_venus_illum_frac_max_shift_m14d` | `77.587` | `77.587` | `77.587` |

### Container: `packed_astro_container_075` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_ra_icrf_mean_shift_m14d` | `283.87` | `283.87` | `283.87` |
| `Bits 2-3` | `>> 2` | `astro_sun_dec_icrf_mean_shift_m14d` | `-22.809` | `-22.809` | `-22.809` |
| `Bits 4-5` | `>> 4` | `astro_sun_ra_app_mean_shift_m14d` | `284.23` | `284.23` | `284.23` |
| `Bits 6-7` | `>> 6` | `astro_sun_dec_app_mean_shift_m14d` | `-22.78` | `-22.78` | `-22.78` |
| `Bits 8-9` | `>> 8` | `astro_sun_azim_mean_shift_m14d` | `30.611` | `30.611` | `30.611` |
| `Bits 10-11` | `>> 10` | `astro_sun_elev_mean_shift_m14d` | `-67.629` | `-67.629` | `-67.629` |
| `Bits 12-13` | `>> 12` | `astro_sun_app_mag_mean_shift_m14d` | `-26.779` | `-26.779` | `-26.779` |
| `Bits 14-15` | `>> 14` | `astro_sun_dist_mean_shift_m14d` | `0.98336` | `0.98336` | `0.98336` |

### Container: `packed_astro_container_076` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_dist_rate_mean_shift_m14d` | `-0.058043` | `-0.058042` | `-0.058041` |
| `Bits 2-3` | `>> 2` | `astro_sun_illum_frac_mean_shift_m14d` | `50.516` | `50.516` | `50.516` |
| `Bits 4-5` | `>> 4` | `astro_moon_ra_icrf_mean_shift_m14d` | `191.8` | `191.8` | `191.8` |
| `Bits 6-7` | `>> 6` | `astro_moon_dec_icrf_mean_shift_m14d` | `-4.1098` | `-4.1098` | `-4.1098` |
| `Bits 8-9` | `>> 8` | `astro_moon_ra_app_mean_shift_m14d` | `192.12` | `192.12` | `192.12` |
| `Bits 10-11` | `>> 10` | `astro_moon_dec_app_mean_shift_m14d` | `-4.2311` | `-4.2311` | `-4.2311` |
| `Bits 12-13` | `>> 12` | `astro_moon_azim_mean_shift_m14d` | `103.59` | `103.59` | `103.59` |
| `Bits 14-15` | `>> 14` | `astro_moon_elev_mean_shift_m14d` | `7.4548` | `7.4548` | `7.4548` |

### Container: `packed_astro_container_077` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_app_mag_mean_shift_m14d` | `-10.005` | `-10.005` | `-10.005` |
| `Bits 2-3` | `>> 2` | `astro_moon_surf_bright_mean_shift_m14d` | `5.1834` | `5.1834` | `5.1834` |
| `Bits 4-5` | `>> 4` | `astro_moon_dist_mean_shift_m14d` | `0.0026624` | `0.0026634` | `0.0026644` |
| `Bits 6-7` | `>> 6` | `astro_moon_dist_rate_mean_shift_m14d` | `-0.32296` | `-0.32296` | `-0.32296` |
| `Bits 8-9` | `>> 8` | `astro_moon_helio_dist_mean_shift_m14d` | `0.98339` | `0.98339` | `0.98339` |
| `Bits 10-11` | `>> 10` | `astro_moon_helio_dist_rate_mean_shift_m14d` | `-0.81159` | `-0.81159` | `-0.81159` |
| `Bits 12-13` | `>> 12` | `astro_moon_phase_angle_mean_shift_m14d` | `89.379` | `89.379` | `89.379` |
| `Bits 14-15` | `>> 14` | `astro_moon_elong_mean_shift_m14d` | `90.477` | `90.477` | `90.477` |

### Container: `packed_astro_container_078` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_illum_frac_mean_shift_m14d` | `50.516` | `50.516` | `50.516` |
| `Bits 2-3` | `>> 2` | `astro_saturn_ra_icrf_mean_shift_m14d` | `335.72` | `335.72` | `335.72` |
| `Bits 4-5` | `>> 4` | `astro_saturn_dec_icrf_mean_shift_m14d` | `-11.856` | `-11.856` | `-11.856` |
| `Bits 6-7` | `>> 6` | `astro_saturn_ra_app_mean_shift_m14d` | `336.04` | `336.04` | `336.04` |
| `Bits 8-9` | `>> 8` | `astro_saturn_dec_app_mean_shift_m14d` | `-11.737` | `-11.737` | `-11.737` |
| `Bits 10-11` | `>> 10` | `astro_saturn_azim_mean_shift_m14d` | `300.11` | `300.11` | `300.11` |
| `Bits 12-13` | `>> 12` | `astro_saturn_elev_mean_shift_m14d` | `-43.732` | `-43.732` | `-43.732` |
| `Bits 14-15` | `>> 14` | `astro_saturn_app_mag_mean_shift_m14d` | `0.961` | `0.961` | `0.961` |

### Container: `packed_astro_container_079` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_surf_bright_mean_shift_m14d` | `6.7253` | `6.7253` | `6.7253` |
| `Bits 2-3` | `>> 2` | `astro_saturn_dist_mean_shift_m14d` | `10.333` | `10.333` | `10.333` |
| `Bits 4-5` | `>> 4` | `astro_saturn_dist_rate_mean_shift_m14d` | `22.316` | `22.316` | `22.316` |
| `Bits 6-7` | `>> 6` | `astro_saturn_helio_dist_mean_shift_m14d` | `9.737` | `9.737` | `9.737` |
| `Bits 8-9` | `>> 8` | `astro_saturn_helio_dist_rate_mean_shift_m14d` | `-0.48885` | `-0.48885` | `-0.48885` |
| `Bits 10-11` | `>> 10` | `astro_saturn_phase_angle_mean_shift_m14d` | `4.4649` | `4.4649` | `4.4649` |
| `Bits 12-13` | `>> 12` | `astro_saturn_elong_mean_shift_m14d` | `50.438` | `50.438` | `50.438` |
| `Bits 14-15` | `>> 14` | `astro_saturn_illum_frac_mean_shift_m14d` | `50.516` | `50.516` | `50.516` |

### Container: `packed_astro_container_080` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_ra_icrf_mean_shift_m14d` | `33.387` | `33.387` | `33.387` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_dec_icrf_mean_shift_m14d` | `12.176` | `12.176` | `12.176` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_ra_app_mean_shift_m14d` | `33.71` | `33.71` | `33.711` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_dec_app_mean_shift_m14d` | `12.289` | `12.289` | `12.289` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_azim_mean_shift_m14d` | `274.21` | `274.21` | `274.21` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_elev_mean_shift_m14d` | `13.669` | `13.669` | `13.669` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_app_mag_mean_shift_m14d` | `-2.564` | `-2.564` | `-2.564` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_surf_bright_mean_shift_m14d` | `5.3599` | `5.3599` | `5.3599` |

### Container: `packed_astro_container_081` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_dist_mean_shift_m14d` | `4.5259` | `4.5259` | `4.5259` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_dist_rate_mean_shift_m14d` | `26.132` | `26.132` | `26.132` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_helio_dist_mean_shift_m14d` | `4.9855` | `4.9855` | `4.9855` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_helio_dist_rate_mean_shift_m14d` | `0.33256` | `0.33256` | `0.33256` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_phase_angle_mean_shift_m14d` | `10.488` | `10.488` | `10.488` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_elong_mean_shift_m14d` | `112.51` | `112.51` | `112.51` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_illum_frac_mean_shift_m14d` | `50.516` | `50.516` | `50.516` |
| `Bits 14-15` | `>> 14` | `astro_mars_ra_icrf_mean_shift_m14d` | `269.14` | `269.14` | `269.14` |

### Container: `packed_astro_container_082` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_dec_icrf_mean_shift_m14d` | `-24.005` | `-24.005` | `-24.005` |
| `Bits 2-3` | `>> 2` | `astro_mars_ra_app_mean_shift_m14d` | `269.49` | `269.49` | `269.49` |
| `Bits 4-5` | `>> 4` | `astro_mars_dec_app_mean_shift_m14d` | `-24.009` | `-24.009` | `-24.009` |
| `Bits 6-7` | `>> 6` | `astro_mars_azim_mean_shift_m14d` | `58.354` | `58.354` | `58.354` |
| `Bits 8-9` | `>> 8` | `astro_mars_elev_mean_shift_m14d` | `-60.996` | `-60.996` | `-60.996` |
| `Bits 10-11` | `>> 10` | `astro_mars_app_mag_mean_shift_m14d` | `1.426` | `1.426` | `1.426` |
| `Bits 12-13` | `>> 12` | `astro_mars_surf_bright_mean_shift_m14d` | `4.1006` | `4.1006` | `4.1006` |
| `Bits 14-15` | `>> 14` | `astro_mars_dist_mean_shift_m14d` | `2.4146` | `2.4146` | `2.4146` |

### Container: `packed_astro_container_083` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_dist_rate_mean_shift_m14d` | `-5.5345` | `-5.5345` | `-5.5345` |
| `Bits 2-3` | `>> 2` | `astro_mars_helio_dist_mean_shift_m14d` | `1.4769` | `1.4769` | `1.4769` |
| `Bits 4-5` | `>> 4` | `astro_mars_helio_dist_rate_mean_shift_m14d` | `-2.1925` | `-2.1925` | `-2.1925` |
| `Bits 6-7` | `>> 6` | `astro_mars_phase_angle_mean_shift_m14d` | `8.9883` | `8.9883` | `8.9883` |
| `Bits 8-9` | `>> 8` | `astro_mars_elong_mean_shift_m14d` | `13.571` | `13.571` | `13.571` |
| `Bits 10-11` | `>> 10` | `astro_mars_illum_frac_mean_shift_m14d` | `50.516` | `50.516` | `50.516` |
| `Bits 12-13` | `>> 12` | `astro_ceres_ra_icrf_mean_shift_m14d` | `255.36` | `255.36` | `255.36` |
| `Bits 14-15` | `>> 14` | `astro_ceres_dec_icrf_mean_shift_m14d` | `-20.895` | `-20.895` | `-20.895` |

### Container: `packed_astro_container_084` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_ceres_ra_app_mean_shift_m14d` | `255.71` | `255.71` | `255.71` |
| `Bits 2-3` | `>> 2` | `astro_ceres_dec_app_mean_shift_m14d` | `-20.93` | `-20.93` | `-20.93` |
| `Bits 4-5` | `>> 4` | `astro_ceres_azim_mean_shift_m14d` | `70.214` | `70.214` | `70.214` |
| `Bits 6-7` | `>> 6` | `astro_ceres_elev_mean_shift_m14d` | `-49.715` | `-49.715` | `-49.715` |
| `Bits 8-9` | `>> 8` | `astro_ceres_app_mag_mean_shift_m14d` | `8.9679` | `8.9679` | `8.9679` |
| `Bits 10-11` | `>> 10` | `astro_ceres_surf_bright_mean_shift_m14d` | `6.5309` | `6.5309` | `6.5309` |
| `Bits 12-13` | `>> 12` | `astro_ceres_dist_mean_shift_m14d` | `3.6075` | `3.6075` | `3.6075` |
| `Bits 14-15` | `>> 14` | `astro_ceres_dist_rate_mean_shift_m14d` | `-9.4577` | `-9.4577` | `-9.4577` |

### Container: `packed_astro_container_085` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_ceres_helio_dist_mean_shift_m14d` | `2.7627` | `2.7627` | `2.7627` |
| `Bits 2-3` | `>> 2` | `astro_ceres_helio_dist_rate_mean_shift_m14d` | `1.4162` | `1.4162` | `1.4162` |
| `Bits 4-5` | `>> 4` | `astro_ceres_phase_angle_mean_shift_m14d` | `9.1326` | `9.1326` | `9.1326` |
| `Bits 6-7` | `>> 6` | `astro_ceres_elong_mean_shift_m14d` | `26.494` | `26.494` | `26.494` |
| `Bits 8-9` | `>> 8` | `astro_ceres_illum_frac_mean_shift_m14d` | `50.516` | `50.516` | `50.516` |
| `Bits 10-11` | `>> 10` | `astro_venus_ra_icrf_mean_shift_m14d` | `244.4` | `244.4` | `244.4` |
| `Bits 12-13` | `>> 12` | `astro_venus_dec_icrf_mean_shift_m14d` | `-19.45` | `-19.45` | `-19.45` |
| `Bits 14-15` | `>> 14` | `astro_venus_ra_app_mean_shift_m14d` | `244.74` | `244.74` | `244.74` |

### Container: `packed_astro_container_086` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_dec_app_mean_shift_m14d` | `-19.509` | `-19.509` | `-19.509` |
| `Bits 2-3` | `>> 2` | `astro_venus_azim_mean_shift_m14d` | `78.373` | `78.373` | `78.373` |
| `Bits 4-5` | `>> 4` | `astro_venus_elev_mean_shift_m14d` | `-41.031` | `-41.031` | `-41.031` |
| `Bits 6-7` | `>> 6` | `astro_venus_app_mag_mean_shift_m14d` | `-4.0274` | `-4.0274` | `-4.0274` |
| `Bits 8-9` | `>> 8` | `astro_venus_surf_bright_mean_shift_m14d` | `1.1656` | `1.1656` | `1.1656` |
| `Bits 10-11` | `>> 10` | `astro_venus_dist_mean_shift_m14d` | `1.2006` | `1.2006` | `1.2006` |
| `Bits 12-13` | `>> 12` | `astro_venus_dist_rate_mean_shift_m14d` | `10.482` | `10.482` | `10.482` |
| `Bits 14-15` | `>> 14` | `astro_venus_helio_dist_mean_shift_m14d` | `0.7208` | `0.7208` | `0.7208` |

### Container: `packed_astro_container_087` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_helio_dist_rate_mean_shift_m14d` | `0.20221` | `0.20221` | `0.20221` |
| `Bits 2-3` | `>> 2` | `astro_venus_phase_angle_mean_shift_m14d` | `54.949` | `54.949` | `54.949` |
| `Bits 4-5` | `>> 4` | `astro_venus_elong_mean_shift_m14d` | `36.869` | `36.869` | `36.869` |
| `Bits 6-7` | `>> 6` | `astro_venus_illum_frac_mean_shift_m14d` | `50.516` | `50.516` | `50.516` |
| `Bits 8-9` | `>> 8` | `astro_sun_ra_icrf_median_shift_m14d` | `283.87` | `283.87` | `283.87` |
| `Bits 10-11` | `>> 10` | `astro_sun_dec_icrf_median_shift_m14d` | `-22.824` | `-22.824` | `-22.824` |
| `Bits 12-13` | `>> 12` | `astro_sun_ra_app_median_shift_m14d` | `284.23` | `284.23` | `284.23` |
| `Bits 14-15` | `>> 14` | `astro_sun_dec_app_median_shift_m14d` | `-22.795` | `-22.795` | `-22.795` |

### Container: `packed_astro_container_088` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_azim_median_shift_m14d` | `30.618` | `30.618` | `30.618` |
| `Bits 2-3` | `>> 2` | `astro_sun_elev_median_shift_m14d` | `-67.645` | `-67.645` | `-67.645` |
| `Bits 4-5` | `>> 4` | `astro_sun_app_mag_median_shift_m14d` | `-26.779` | `-26.779` | `-26.779` |
| `Bits 6-7` | `>> 6` | `astro_sun_dist_median_shift_m14d` | `0.98336` | `0.98336` | `0.98336` |
| `Bits 8-9` | `>> 8` | `astro_sun_dist_rate_median_shift_m14d` | `-0.057205` | `-0.057204` | `-0.057203` |
| `Bits 10-11` | `>> 10` | `astro_sun_illum_frac_median_shift_m14d` | `50.799` | `50.799` | `50.799` |
| `Bits 12-13` | `>> 12` | `astro_moon_ra_icrf_median_shift_m14d` | `191.24` | `191.24` | `191.24` |
| `Bits 14-15` | `>> 14` | `astro_moon_dec_icrf_median_shift_m14d` | `-4.2772` | `-4.2772` | `-4.2772` |

### Container: `packed_astro_container_089` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_ra_app_median_shift_m14d` | `191.55` | `191.55` | `191.55` |
| `Bits 2-3` | `>> 2` | `astro_moon_dec_app_median_shift_m14d` | `-4.4082` | `-4.4082` | `-4.4082` |
| `Bits 4-5` | `>> 4` | `astro_moon_azim_median_shift_m14d` | `103.39` | `103.39` | `103.39` |
| `Bits 6-7` | `>> 6` | `astro_moon_elev_median_shift_m14d` | `7.7593` | `7.7593` | `7.7593` |
| `Bits 8-9` | `>> 8` | `astro_moon_app_mag_median_shift_m14d` | `-10.1` | `-10.1` | `-10.1` |
| `Bits 10-11` | `>> 10` | `astro_moon_surf_bright_median_shift_m14d` | `5.166` | `5.166` | `5.166` |
| `Bits 12-13` | `>> 12` | `astro_moon_dist_median_shift_m14d` | `0.0026772` | `0.0026782` | `0.0026792` |
| `Bits 14-15` | `>> 14` | `astro_moon_dist_rate_median_shift_m14d` | `-0.34912` | `-0.34912` | `-0.34912` |

### Container: `packed_astro_container_090` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_helio_dist_median_shift_m14d` | `0.98339` | `0.98339` | `0.98339` |
| `Bits 2-3` | `>> 2` | `astro_moon_helio_dist_rate_median_shift_m14d` | `-0.81843` | `-0.81843` | `-0.81843` |
| `Bits 4-5` | `>> 4` | `astro_moon_phase_angle_median_shift_m14d` | `89.085` | `89.085` | `89.085` |
| `Bits 6-7` | `>> 6` | `astro_moon_elong_median_shift_m14d` | `90.759` | `90.759` | `90.759` |
| `Bits 8-9` | `>> 8` | `astro_moon_illum_frac_median_shift_m14d` | `50.799` | `50.799` | `50.799` |
| `Bits 10-11` | `>> 10` | `astro_saturn_ra_icrf_median_shift_m14d` | `335.72` | `335.72` | `335.72` |
| `Bits 12-13` | `>> 12` | `astro_saturn_dec_icrf_median_shift_m14d` | `-11.857` | `-11.857` | `-11.857` |
| `Bits 14-15` | `>> 14` | `astro_saturn_ra_app_median_shift_m14d` | `336.03` | `336.03` | `336.03` |

### Container: `packed_astro_container_091` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_dec_app_median_shift_m14d` | `-11.738` | `-11.738` | `-11.738` |
| `Bits 2-3` | `>> 2` | `astro_saturn_azim_median_shift_m14d` | `300.09` | `300.09` | `300.09` |
| `Bits 4-5` | `>> 4` | `astro_saturn_elev_median_shift_m14d` | `-43.746` | `-43.746` | `-43.746` |
| `Bits 6-7` | `>> 6` | `astro_saturn_app_mag_median_shift_m14d` | `0.961` | `0.961` | `0.961` |
| `Bits 8-9` | `>> 8` | `astro_saturn_surf_bright_median_shift_m14d` | `6.725` | `6.725` | `6.725` |
| `Bits 10-11` | `>> 10` | `astro_saturn_dist_median_shift_m14d` | `10.334` | `10.334` | `10.334` |
| `Bits 12-13` | `>> 12` | `astro_saturn_dist_rate_median_shift_m14d` | `22.328` | `22.328` | `22.328` |
| `Bits 14-15` | `>> 14` | `astro_saturn_helio_dist_median_shift_m14d` | `9.737` | `9.737` | `9.737` |

### Container: `packed_astro_container_092` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_helio_dist_rate_median_shift_m14d` | `-0.4886` | `-0.4886` | `-0.4886` |
| `Bits 2-3` | `>> 2` | `astro_saturn_phase_angle_median_shift_m14d` | `4.4671` | `4.4671` | `4.4671` |
| `Bits 4-5` | `>> 4` | `astro_saturn_elong_median_shift_m14d` | `50.436` | `50.436` | `50.436` |
| `Bits 6-7` | `>> 6` | `astro_saturn_illum_frac_median_shift_m14d` | `50.799` | `50.799` | `50.799` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_ra_icrf_median_shift_m14d` | `33.38` | `33.38` | `33.38` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_dec_icrf_median_shift_m14d` | `12.174` | `12.174` | `12.174` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_ra_app_median_shift_m14d` | `33.704` | `33.704` | `33.704` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_dec_app_median_shift_m14d` | `12.286` | `12.286` | `12.286` |

### Container: `packed_astro_container_093` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_azim_median_shift_m14d` | `274.22` | `274.22` | `274.22` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_elev_median_shift_m14d` | `13.661` | `13.661` | `13.661` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_app_mag_median_shift_m14d` | `-2.564` | `-2.564` | `-2.564` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_surf_bright_median_shift_m14d` | `5.36` | `5.36` | `5.36` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_dist_median_shift_m14d` | `4.5257` | `4.5257` | `4.5257` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_dist_rate_median_shift_m14d` | `26.149` | `26.149` | `26.149` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_helio_dist_median_shift_m14d` | `4.9855` | `4.9855` | `4.9855` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_helio_dist_rate_median_shift_m14d` | `0.3332` | `0.3332` | `0.3332` |

### Container: `packed_astro_container_094` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_phase_angle_median_shift_m14d` | `10.495` | `10.495` | `10.495` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_elong_median_shift_m14d` | `112.51` | `112.51` | `112.51` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_illum_frac_median_shift_m14d` | `50.799` | `50.799` | `50.799` |
| `Bits 6-7` | `>> 6` | `astro_mars_ra_icrf_median_shift_m14d` | `269.13` | `269.13` | `269.13` |
| `Bits 8-9` | `>> 8` | `astro_mars_dec_icrf_median_shift_m14d` | `-24.014` | `-24.014` | `-24.014` |
| `Bits 10-11` | `>> 10` | `astro_mars_ra_app_median_shift_m14d` | `269.49` | `269.49` | `269.49` |
| `Bits 12-13` | `>> 12` | `astro_mars_dec_app_median_shift_m14d` | `-24.018` | `-24.018` | `-24.018` |
| `Bits 14-15` | `>> 14` | `astro_mars_azim_median_shift_m14d` | `58.371` | `58.371` | `58.371` |

### Container: `packed_astro_container_095` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_elev_median_shift_m14d` | `-61.002` | `-61.002` | `-61.002` |
| `Bits 2-3` | `>> 2` | `astro_mars_app_mag_median_shift_m14d` | `1.429` | `1.429` | `1.429` |
| `Bits 4-5` | `>> 4` | `astro_mars_surf_bright_median_shift_m14d` | `4.099` | `4.099` | `4.099` |
| `Bits 6-7` | `>> 6` | `astro_mars_dist_median_shift_m14d` | `2.4146` | `2.4146` | `2.4146` |
| `Bits 8-9` | `>> 8` | `astro_mars_dist_rate_median_shift_m14d` | `-5.5352` | `-5.5352` | `-5.5352` |
| `Bits 10-11` | `>> 10` | `astro_mars_helio_dist_median_shift_m14d` | `1.4769` | `1.4769` | `1.4769` |
| `Bits 12-13` | `>> 12` | `astro_mars_helio_dist_rate_median_shift_m14d` | `-2.1929` | `-2.1929` | `-2.1929` |
| `Bits 14-15` | `>> 14` | `astro_mars_phase_angle_median_shift_m14d` | `8.9887` | `8.9887` | `8.9887` |

### Container: `packed_astro_container_096` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_elong_median_shift_m14d` | `13.572` | `13.572` | `13.572` |
| `Bits 2-3` | `>> 2` | `astro_mars_illum_frac_median_shift_m14d` | `50.799` | `50.799` | `50.799` |
| `Bits 4-5` | `>> 4` | `astro_ceres_ra_icrf_median_shift_m14d` | `255.36` | `255.36` | `255.36` |
| `Bits 6-7` | `>> 6` | `astro_ceres_dec_icrf_median_shift_m14d` | `-20.898` | `-20.898` | `-20.898` |
| `Bits 8-9` | `>> 8` | `astro_ceres_ra_app_median_shift_m14d` | `255.71` | `255.71` | `255.71` |
| `Bits 10-11` | `>> 10` | `astro_ceres_dec_app_median_shift_m14d` | `-20.933` | `-20.933` | `-20.933` |
| `Bits 12-13` | `>> 12` | `astro_ceres_azim_median_shift_m14d` | `70.229` | `70.229` | `70.229` |
| `Bits 14-15` | `>> 14` | `astro_ceres_elev_median_shift_m14d` | `-49.721` | `-49.721` | `-49.721` |

### Container: `packed_astro_container_097` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_ceres_app_mag_median_shift_m14d` | `8.968` | `8.968` | `8.968` |
| `Bits 2-3` | `>> 2` | `astro_ceres_surf_bright_median_shift_m14d` | `6.531` | `6.531` | `6.531` |
| `Bits 4-5` | `>> 4` | `astro_ceres_dist_median_shift_m14d` | `3.6077` | `3.6077` | `3.6077` |
| `Bits 6-7` | `>> 6` | `astro_ceres_dist_rate_median_shift_m14d` | `-9.4584` | `-9.4584` | `-9.4584` |
| `Bits 8-9` | `>> 8` | `astro_ceres_helio_dist_median_shift_m14d` | `2.7627` | `2.7627` | `2.7627` |
| `Bits 10-11` | `>> 10` | `astro_ceres_helio_dist_rate_median_shift_m14d` | `1.4162` | `1.4162` | `1.4162` |
| `Bits 12-13` | `>> 12` | `astro_ceres_phase_angle_median_shift_m14d` | `9.1339` | `9.1339` | `9.1339` |
| `Bits 14-15` | `>> 14` | `astro_ceres_elong_median_shift_m14d` | `26.491` | `26.491` | `26.491` |

### Container: `packed_astro_container_098` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_ceres_illum_frac_median_shift_m14d` | `50.799` | `50.799` | `50.799` |
| `Bits 2-3` | `>> 2` | `astro_venus_ra_icrf_median_shift_m14d` | `244.39` | `244.39` | `244.39` |
| `Bits 4-5` | `>> 4` | `astro_venus_dec_icrf_median_shift_m14d` | `-19.467` | `-19.467` | `-19.467` |
| `Bits 6-7` | `>> 6` | `astro_venus_ra_app_median_shift_m14d` | `244.73` | `244.73` | `244.73` |
| `Bits 8-9` | `>> 8` | `astro_venus_dec_app_median_shift_m14d` | `-19.526` | `-19.526` | `-19.526` |
| `Bits 10-11` | `>> 10` | `astro_venus_azim_median_shift_m14d` | `78.387` | `78.387` | `78.387` |
| `Bits 12-13` | `>> 12` | `astro_venus_elev_median_shift_m14d` | `-41.036` | `-41.036` | `-41.036` |
| `Bits 14-15` | `>> 14` | `astro_venus_app_mag_median_shift_m14d` | `-4.027` | `-4.027` | `-4.027` |

### Container: `packed_astro_container_099` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_surf_bright_median_shift_m14d` | `1.166` | `1.166` | `1.166` |
| `Bits 2-3` | `>> 2` | `astro_venus_dist_median_shift_m14d` | `1.2007` | `1.2007` | `1.2007` |
| `Bits 4-5` | `>> 4` | `astro_venus_dist_rate_median_shift_m14d` | `10.483` | `10.483` | `10.483` |
| `Bits 6-7` | `>> 6` | `astro_venus_helio_dist_median_shift_m14d` | `0.72079` | `0.7208` | `0.7208` |
| `Bits 8-9` | `>> 8` | `astro_venus_helio_dist_rate_median_shift_m14d` | `0.20253` | `0.20253` | `0.20253` |
| `Bits 10-11` | `>> 10` | `astro_venus_phase_angle_median_shift_m14d` | `54.946` | `54.946` | `54.946` |
| `Bits 12-13` | `>> 12` | `astro_venus_elong_median_shift_m14d` | `36.871` | `36.871` | `36.871` |
| `Bits 14-15` | `>> 14` | `astro_venus_illum_frac_median_shift_m14d` | `50.799` | `50.799` | `50.799` |

### Container: `packed_astro_container_100` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_ra_icrf_min_shift_m7d` | `280.57` | `292.06` | `323.03` |
| `Bits 2-3` | `>> 2` | `astro_sun_dec_icrf_min_shift_m7d` | `-23.081` | `-21.843` | `-14.589` |
| `Bits 4-5` | `>> 4` | `astro_sun_ra_app_min_shift_m7d` | `280.92` | `292.41` | `323.35` |
| `Bits 6-7` | `>> 6` | `astro_sun_dec_app_min_shift_m7d` | `-23.059` | `-21.795` | `-14.486` |
| `Bits 8-9` | `>> 8` | `astro_sun_azim_min_shift_m7d` | `18.491` | `25.74` | `29.525` |
| `Bits 10-11` | `>> 10` | `astro_sun_elev_min_shift_m7d` | `-67.753` | `-67.004` | `-60.523` |
| `Bits 12-13` | `>> 12` | `astro_sun_app_mag_min_shift_m7d` | `-26.779` | `-26.778` | `-26.771` |
| `Bits 14-15` | `>> 14` | `astro_sun_dist_min_shift_m7d` | `0.98335` | `0.98354` | `0.98676` |

### Container: `packed_astro_container_101` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_dist_rate_min_shift_m7d` | `-0.087413` | `0.0011805` | `0.24541` |
| `Bits 2-3` | `>> 2` | `astro_sun_illum_frac_min_shift_m7d` | `8.6922` | `22.786` | `22.786` |
| `Bits 4-5` | `>> 4` | `astro_moon_ra_icrf_min_shift_m7d` | `104.95` | `159.29` | `164.74` |
| `Bits 6-7` | `>> 6` | `astro_moon_dec_icrf_min_shift_m7d` | `-22.252` | `-20.017` | `-12.746` |
| `Bits 8-9` | `>> 8` | `astro_moon_ra_app_min_shift_m7d` | `105.32` | `159.61` | `165.06` |
| `Bits 10-11` | `>> 10` | `astro_moon_dec_app_min_shift_m7d` | `-22.336` | `-20.11` | `-12.674` |
| `Bits 12-13` | `>> 12` | `astro_moon_azim_min_shift_m7d` | `94.369` | `94.369` | `119.33` |
| `Bits 14-15` | `>> 14` | `astro_moon_elev_min_shift_m7d` | `-47.94` | `-25.607` | `-25.607` |

### Container: `packed_astro_container_102` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_app_mag_min_shift_m7d` | `-11.245` | `-11.154` | `-10.808` |
| `Bits 2-3` | `>> 2` | `astro_moon_surf_bright_min_shift_m7d` | `4.5598` | `4.571` | `4.688` |
| `Bits 4-5` | `>> 4` | `astro_moon_dist_min_shift_m7d` | `0.0024596` | `0.0026089` | `0.0026113` |
| `Bits 6-7` | `>> 6` | `astro_moon_dist_rate_min_shift_m7d` | `-0.37172` | `-0.3632` | `-0.13613` |
| `Bits 8-9` | `>> 8` | `astro_moon_helio_dist_min_shift_m7d` | `0.98196` | `0.98199` | `0.98578` |
| `Bits 10-11` | `>> 10` | `astro_moon_helio_dist_rate_min_shift_m7d` | `-0.87805` | `-0.6153` | `-0.23252` |
| `Bits 12-13` | `>> 12` | `astro_moon_phase_angle_min_shift_m7d` | `55.854` | `56.517` | `69.643` |
| `Bits 14-15` | `>> 14` | `astro_moon_elong_min_shift_m7d` | `33.342` | `56.9` | `56.9` |

### Container: `packed_astro_container_103` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_illum_frac_min_shift_m7d` | `8.6922` | `22.786` | `22.786` |
| `Bits 2-3` | `>> 2` | `astro_saturn_ra_icrf_min_shift_m7d` | `335.46` | `336.41` | `339.51` |
| `Bits 4-5` | `>> 4` | `astro_saturn_dec_icrf_min_shift_m7d` | `-11.958` | `-11.587` | `-10.365` |
| `Bits 6-7` | `>> 6` | `astro_saturn_ra_app_min_shift_m7d` | `335.78` | `336.72` | `339.82` |
| `Bits 8-9` | `>> 8` | `astro_saturn_dec_app_min_shift_m7d` | `-11.839` | `-11.467` | `-10.242` |
| `Bits 10-11` | `>> 10` | `astro_saturn_azim_min_shift_m7d` | `98.306` | `297.28` | `302.35` |
| `Bits 12-13` | `>> 12` | `astro_saturn_elev_min_shift_m7d` | `-55.68` | `-50.328` | `-45.349` |
| `Bits 14-15` | `>> 14` | `astro_saturn_app_mag_min_shift_m7d` | `0.955` | `0.9595` | `0.98125` |

### Container: `packed_astro_container_104` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_surf_bright_min_shift_m7d` | `6.6893` | `6.714` | `6.723` |
| `Bits 2-3` | `>> 2` | `astro_saturn_dist_min_shift_m7d` | `10.295` | `10.423` | `10.665` |
| `Bits 4-5` | `>> 4` | `astro_saturn_dist_rate_min_shift_m7d` | `5.5007` | `17.763` | `21.404` |
| `Bits 6-7` | `>> 6` | `astro_saturn_helio_dist_min_shift_m7d` | `9.7247` | `9.7332` | `9.7361` |
| `Bits 8-9` | `>> 8` | `astro_saturn_helio_dist_rate_min_shift_m7d` | `-0.49543` | `-0.49132` | `-0.49018` |
| `Bits 10-11` | `>> 10` | `astro_saturn_phase_angle_min_shift_m7d` | `1.1534` | `3.567` | `4.2836` |
| `Bits 12-13` | `>> 12` | `astro_saturn_elong_min_shift_m7d` | `11.418` | `38.025` | `47.66` |
| `Bits 14-15` | `>> 14` | `astro_saturn_illum_frac_min_shift_m7d` | `8.6922` | `22.786` | `22.786` |

### Container: `packed_astro_container_105` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_ra_icrf_min_shift_m7d` | `33.361` | `33.578` | `35.988` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_dec_icrf_min_shift_m7d` | `12.151` | `12.282` | `13.242` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_ra_app_min_shift_m7d` | `33.685` | `33.902` | `36.313` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_dec_app_min_shift_m7d` | `12.264` | `12.394` | `13.351` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_azim_min_shift_m7d` | `272.24` | `279.07` | `298.27` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_elev_min_shift_m7d` | `-12.518` | `4.5178` | `11.557` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_app_mag_min_shift_m7d` | `-2.589` | `-2.503` | `-2.2872` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_surf_bright_min_shift_m7d` | `5.357` | `5.357` | `5.366` |

### Container: `packed_astro_container_106` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_dist_min_shift_m7d` | `4.4815` | `4.6407` | `5.1148` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_dist_rate_min_shift_m7d` | `25.552` | `25.552` | `26.777` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_helio_dist_min_shift_m7d` | `4.9849` | `4.9869` | `4.993` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_helio_dist_rate_min_shift_m7d` | `0.32902` | `0.33788` | `0.36269` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_phase_angle_min_shift_m7d` | `10.249` | `10.249` | `10.77` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_elong_min_shift_m7d` | `72.126` | `99.263` | `109.5` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_illum_frac_min_shift_m7d` | `8.6922` | `22.786` | `22.786` |
| `Bits 14-15` | `>> 14` | `astro_mars_ra_icrf_min_shift_m7d` | `266.7` | `275.27` | `299.62` |

### Container: `packed_astro_container_107` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_dec_icrf_min_shift_m7d` | `-24.037` | `-23.974` | `-21.565` |
| `Bits 2-3` | `>> 2` | `astro_mars_ra_app_min_shift_m7d` | `267.05` | `275.62` | `299.96` |
| `Bits 4-5` | `>> 4` | `astro_mars_dec_app_min_shift_m7d` | `-24.035` | `-23.964` | `-21.502` |
| `Bits 6-7` | `>> 6` | `astro_mars_azim_min_shift_m7d` | `57.573` | `59.985` | `62.789` |
| `Bits 8-9` | `>> 8` | `astro_mars_elev_min_shift_m7d` | `-61.284` | `-60.167` | `-55.193` |
| `Bits 10-11` | `>> 10` | `astro_mars_app_mag_min_shift_m7d` | `1.2617` | `1.3525` | `1.411` |
| `Bits 12-13` | `>> 12` | `astro_mars_surf_bright_min_shift_m7d` | `4.054` | `4.085` | `4.085` |
| `Bits 14-15` | `>> 14` | `astro_mars_dist_min_shift_m7d` | `2.2624` | `2.3703` | `2.4052` |

### Container: `packed_astro_container_108` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_dist_rate_min_shift_m7d` | `-6.7406` | `-6.0683` | `-5.666` |
| `Bits 2-3` | `>> 2` | `astro_mars_helio_dist_min_shift_m7d` | `1.4267` | `1.4601` | `1.4731` |
| `Bits 4-5` | `>> 4` | `astro_mars_helio_dist_rate_min_shift_m7d` | `-2.208` | `-2.1455` | `-1.8412` |
| `Bits 6-7` | `>> 6` | `astro_mars_phase_angle_min_shift_m7d` | `8.4223` | `10.394` | `15.804` |
| `Bits 8-9` | `>> 8` | `astro_mars_elong_min_shift_m7d` | `12.742` | `15.616` | `23.296` |
| `Bits 10-11` | `>> 10` | `astro_mars_illum_frac_min_shift_m7d` | `8.6922` | `22.786` | `22.786` |
| `Bits 12-13` | `>> 12` | `astro_ceres_ra_icrf_min_shift_m7d` | `254.07` | `258.56` | `270.72` |
| `Bits 14-15` | `>> 14` | `astro_ceres_dec_icrf_min_shift_m7d` | `-22.759` | `-21.684` | `-21.093` |

### Container: `packed_astro_container_109` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_ceres_ra_app_min_shift_m7d` | `254.42` | `258.91` | `271.08` |
| `Bits 2-3` | `>> 2` | `astro_ceres_dec_app_min_shift_m7d` | `-22.754` | `-21.706` | `-21.125` |
| `Bits 4-5` | `>> 4` | `astro_ceres_azim_min_shift_m7d` | `68.346` | `74.597` | `89.144` |
| `Bits 6-7` | `>> 6` | `astro_ceres_elev_min_shift_m7d` | `-50.727` | `-47.079` | `-35.399` |
| `Bits 8-9` | `>> 8` | `astro_ceres_app_mag_min_shift_m7d` | `8.95` | `8.972` | `9.0407` |
| `Bits 10-11` | `>> 10` | `astro_ceres_surf_bright_min_shift_m7d` | `6.504` | `6.5935` | `6.797` |
| `Bits 12-13` | `>> 12` | `astro_ceres_dist_min_shift_m7d` | `3.2626` | `3.5231` | `3.5911` |
| `Bits 14-15` | `>> 14` | `astro_ceres_dist_rate_min_shift_m7d` | `-18.162` | `-12.464` | `-10.144` |

### Container: `packed_astro_container_110` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_ceres_helio_dist_min_shift_m7d` | `2.7602` | `2.7688` | `2.7929` |
| `Bits 2-3` | `>> 2` | `astro_ceres_helio_dist_rate_min_shift_m7d` | `1.3853` | `1.4103` | `1.4152` |
| `Bits 4-5` | `>> 4` | `astro_ceres_phase_angle_min_shift_m7d` | `8.5488` | `10.565` | `15.69` |
| `Bits 6-7` | `>> 6` | `astro_ceres_elong_min_shift_m7d` | `24.667` | `31.103` | `49.984` |
| `Bits 8-9` | `>> 8` | `astro_ceres_illum_frac_min_shift_m7d` | `8.6922` | `22.786` | `22.786` |
| `Bits 10-11` | `>> 10` | `astro_venus_ra_icrf_min_shift_m7d` | `240.61` | `254.04` | `293.44` |
| `Bits 12-13` | `>> 12` | `astro_venus_dec_icrf_min_shift_m7d` | `-21.386` | `-20.155` | `-20.155` |
| `Bits 14-15` | `>> 14` | `astro_venus_ra_app_min_shift_m7d` | `240.95` | `254.39` | `293.79` |

### Container: `packed_astro_container_111` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_dec_app_min_shift_m7d` | `-21.395` | `-20.205` | `-20.205` |
| `Bits 2-3` | `>> 2` | `astro_venus_azim_min_shift_m7d` | `66.168` | `77.386` | `78.303` |
| `Bits 4-5` | `>> 4` | `astro_venus_elev_min_shift_m7d` | `-50.79` | `-45.543` | `-42.098` |
| `Bits 6-7` | `>> 6` | `astro_venus_app_mag_min_shift_m7d` | `-4.039` | `-4.0015` | `-3.9235` |
| `Bits 8-9` | `>> 8` | `astro_venus_surf_bright_min_shift_m7d` | `1.0168` | `1.1175` | `1.155` |
| `Bits 10-11` | `>> 10` | `astro_venus_dist_min_shift_m7d` | `1.1819` | `1.2461` | `1.4103` |
| `Bits 12-13` | `>> 12` | `astro_venus_dist_rate_min_shift_m7d` | `8.203` | `9.7893` | `10.33` |
| `Bits 14-15` | `>> 14` | `astro_venus_helio_dist_min_shift_m7d` | `0.72045` | `0.72173` | `0.72564` |

### Container: `packed_astro_container_112` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_helio_dist_rate_min_shift_m7d` | `0.18157` | `0.19155` | `0.2015` |
| `Bits 2-3` | `>> 2` | `astro_venus_phase_angle_min_shift_m7d` | `39.01` | `49.758` | `53.77` |
| `Bits 4-5` | `>> 4` | `astro_venus_elong_min_shift_m7d` | `27.564` | `34.086` | `36.265` |
| `Bits 6-7` | `>> 6` | `astro_venus_illum_frac_min_shift_m7d` | `8.6922` | `22.786` | `22.786` |
| `Bits 8-9` | `>> 8` | `astro_sun_ra_icrf_max_shift_m7d` | `287.17` | `298.53` | `328.93` |
| `Bits 10-11` | `>> 10` | `astro_sun_dec_icrf_max_shift_m7d` | `-22.499` | `-20.807` | `-12.592` |
| `Bits 12-13` | `>> 12` | `astro_sun_ra_app_max_shift_m7d` | `287.52` | `298.88` | `329.24` |
| `Bits 14-15` | `>> 14` | `astro_sun_dec_app_max_shift_m7d` | `-22.462` | `-20.746` | `-12.481` |

### Container: `packed_astro_container_113` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_azim_max_shift_m7d` | `19.421` | `27.875` | `31.68` |
| `Bits 2-3` | `>> 2` | `astro_sun_elev_max_shift_m7d` | `-67.464` | `-66.204` | `-58.574` |
| `Bits 4-5` | `>> 4` | `astro_sun_app_mag_max_shift_m7d` | `-26.779` | `-26.777` | `-26.769` |
| `Bits 6-7` | `>> 6` | `astro_sun_dist_max_shift_m7d` | `0.98339` | `0.98383` | `0.98786` |
| `Bits 8-9` | `>> 8` | `astro_sun_dist_rate_max_shift_m7d` | `-0.030764` | `0.048109` | `0.27729` |
| `Bits 10-11` | `>> 10` | `astro_sun_illum_frac_max_shift_m7d` | `67.22` | `77.587` | `78.064` |
| `Bits 12-13` | `>> 12` | `astro_moon_ra_icrf_max_shift_m7d` | `225.73` | `225.73` | `308.83` |
| `Bits 14-15` | `>> 14` | `astro_moon_dec_icrf_max_shift_m7d` | `9.3694` | `12.253` | `21.23` |

### Container: `packed_astro_container_114` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_ra_app_max_shift_m7d` | `226.07` | `226.07` | `309.17` |
| `Bits 2-3` | `>> 2` | `astro_moon_dec_app_max_shift_m7d` | `9.2395` | `12.128` | `21.248` |
| `Bits 4-5` | `>> 4` | `astro_moon_azim_max_shift_m7d` | `113.37` | `127.65` | `298.33` |
| `Bits 6-7` | `>> 6` | `astro_moon_elev_max_shift_m7d` | `21.781` | `39.751` | `39.751` |
| `Bits 8-9` | `>> 8` | `astro_moon_app_mag_max_shift_m7d` | `-8.613` | `-8.613` | `-7.174` |
| `Bits 10-11` | `>> 10` | `astro_moon_surf_bright_max_shift_m7d` | `5.837` | `5.837` | `6.2488` |
| `Bits 12-13` | `>> 12` | `astro_moon_dist_max_shift_m7d` | `0.0025805` | `0.0026831` | `0.002685` |
| `Bits 14-15` | `>> 14` | `astro_moon_dist_rate_max_shift_m7d` | `-0.22195` | `-0.11416` | `0.2508` |

### Container: `packed_astro_container_115` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_helio_dist_max_shift_m7d` | `0.98483` | `0.98483` | `0.98847` |
| `Bits 2-3` | `>> 2` | `astro_moon_helio_dist_rate_max_shift_m7d` | `-0.71371` | `-0.065935` | `0.76477` |
| `Bits 4-5` | `>> 4` | `astro_moon_phase_angle_max_shift_m7d` | `122.97` | `122.97` | `146.58` |
| `Bits 6-7` | `>> 6` | `astro_moon_elong_max_shift_m7d` | `110.22` | `123.35` | `124.02` |
| `Bits 8-9` | `>> 8` | `astro_moon_illum_frac_max_shift_m7d` | `67.22` | `77.587` | `78.064` |
| `Bits 10-11` | `>> 10` | `astro_saturn_ra_icrf_max_shift_m7d` | `335.99` | `336.98` | `340.19` |
| `Bits 12-13` | `>> 12` | `astro_saturn_dec_icrf_max_shift_m7d` | `-11.752` | `-11.359` | `-10.098` |
| `Bits 14-15` | `>> 14` | `astro_saturn_ra_app_max_shift_m7d` | `336.3` | `337.3` | `340.5` |

### Container: `packed_astro_container_116` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_dec_app_max_shift_m7d` | `-11.633` | `-11.238` | `-9.9751` |
| `Bits 2-3` | `>> 2` | `astro_saturn_azim_max_shift_m7d` | `303.03` | `303.03` | `316.68` |
| `Bits 4-5` | `>> 4` | `astro_saturn_elev_max_shift_m7d` | `-54.083` | `-47.575` | `-42.082` |
| `Bits 6-7` | `>> 6` | `astro_saturn_app_mag_max_shift_m7d` | `0.967` | `0.9725` | `0.98975` |
| `Bits 8-9` | `>> 8` | `astro_saturn_surf_bright_max_shift_m7d` | `6.6978` | `6.7225` | `6.727` |
| `Bits 10-11` | `>> 10` | `astro_saturn_dist_max_shift_m7d` | `10.371` | `10.488` | `10.689` |
| `Bits 12-13` | `>> 12` | `astro_saturn_dist_rate_max_shift_m7d` | `8.1453` | `19.89` | `23.199` |
| `Bits 14-15` | `>> 14` | `astro_saturn_helio_dist_max_shift_m7d` | `9.7264` | `9.7349` | `9.7378` |

### Container: `packed_astro_container_117` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_helio_dist_rate_max_shift_m7d` | `-0.49337` | `-0.49039` | `-0.48811` |
| `Bits 2-3` | `>> 2` | `astro_saturn_phase_angle_max_shift_m7d` | `1.6737` | `3.9854` | `4.6409` |
| `Bits 4-5` | `>> 4` | `astro_saturn_elong_max_shift_m7d` | `16.667` | `43.52` | `53.221` |
| `Bits 6-7` | `>> 6` | `astro_saturn_illum_frac_max_shift_m7d` | `67.22` | `77.587` | `78.064` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_ra_icrf_max_shift_m7d` | `33.429` | `33.852` | `36.768` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_dec_icrf_max_shift_m7d` | `12.207` | `12.408` | `13.525` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_ra_app_max_shift_m7d` | `33.753` | `34.176` | `37.093` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_dec_app_max_shift_m7d` | `12.319` | `12.52` | `13.633` |

### Container: `packed_astro_container_118` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_azim_max_shift_m7d` | `276.17` | `282.91` | `302.32` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_elev_max_shift_m7d` | `-9.4783` | `8.4951` | `15.8` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_app_mag_max_shift_m7d` | `-2.539` | `-2.4555` | `-2.2513` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_surf_bright_max_shift_m7d` | `5.362` | `5.362` | `5.3685` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_dist_max_shift_m7d` | `4.5709` | `4.735` | `5.2081` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_dist_rate_max_shift_m7d` | `26.669` | `26.669` | `27.534` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_helio_dist_max_shift_m7d` | `4.986` | `4.9881` | `4.9942` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_helio_dist_rate_max_shift_m7d` | `0.33541` | `0.34494` | `0.36919` |

### Container: `packed_astro_container_119` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_phase_angle_max_shift_m7d` | `10.71` | `10.71` | `11.081` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_elong_max_shift_m7d` | `77.385` | `105.08` | `115.54` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_illum_frac_max_shift_m7d` | `67.22` | `77.587` | `78.064` |
| `Bits 6-7` | `>> 6` | `astro_mars_ra_icrf_max_shift_m7d` | `271.58` | `280.19` | `304.45` |
| `Bits 8-9` | `>> 8` | `astro_mars_dec_icrf_max_shift_m7d` | `-23.952` | `-23.789` | `-20.641` |
| `Bits 10-11` | `>> 10` | `astro_mars_ra_app_max_shift_m7d` | `271.94` | `280.55` | `304.8` |
| `Bits 12-13` | `>> 12` | `astro_mars_dec_app_max_shift_m7d` | `-23.962` | `-23.768` | `-20.568` |
| `Bits 14-15` | `>> 14` | `astro_mars_azim_max_shift_m7d` | `59.092` | `61.004` | `62.938` |

### Container: `packed_astro_container_120` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_elev_max_shift_m7d` | `-60.694` | `-59.393` | `-53.82` |
| `Bits 2-3` | `>> 2` | `astro_mars_app_mag_max_shift_m7d` | `1.3153` | `1.4095` | `1.44` |
| `Bits 4-5` | `>> 4` | `astro_mars_surf_bright_max_shift_m7d` | `4.1013` | `4.112` | `4.112` |
| `Bits 6-7` | `>> 6` | `astro_mars_dist_max_shift_m7d` | `2.285` | `2.3904` | `2.4238` |
| `Bits 8-9` | `>> 8` | `astro_mars_dist_rate_max_shift_m7d` | `-6.65` | `-5.8496` | `-5.4012` |
| `Bits 10-11` | `>> 10` | `astro_mars_helio_dist_max_shift_m7d` | `1.4329` | `1.4675` | `1.4807` |
| `Bits 12-13` | `>> 12` | `astro_mars_helio_dist_rate_max_shift_m7d` | `-2.176` | `-2.0997` | `-1.7565` |
| `Bits 14-15` | `>> 14` | `astro_mars_phase_angle_max_shift_m7d` | `9.5532` | `11.509` | `16.856` |

### Container: `packed_astro_container_121` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_elong_max_shift_m7d` | `14.396` | `17.223` | `24.756` |
| `Bits 2-3` | `>> 2` | `astro_mars_illum_frac_max_shift_m7d` | `67.22` | `77.587` | `78.064` |
| `Bits 4-5` | `>> 4` | `astro_ceres_ra_icrf_max_shift_m7d` | `256.65` | `261.09` | `273.02` |
| `Bits 6-7` | `>> 6` | `astro_ceres_dec_icrf_max_shift_m7d` | `-22.606` | `-21.357` | `-20.692` |
| `Bits 8-9` | `>> 8` | `astro_ceres_ra_app_max_shift_m7d` | `257` | `261.45` | `273.38` |
| `Bits 10-11` | `>> 10` | `astro_ceres_dec_app_max_shift_m7d` | `-22.606` | `-21.385` | `-20.73` |
| `Bits 12-13` | `>> 12` | `astro_ceres_azim_max_shift_m7d` | `72.041` | `77.86` | `91.73` |
| `Bits 14-15` | `>> 14` | `astro_ceres_elev_max_shift_m7d` | `-48.688` | `-44.875` | `-32.834` |

### Container: `packed_astro_container_122` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_ceres_app_mag_max_shift_m7d` | `8.985` | `9.003` | `9.0555` |
| `Bits 2-3` | `>> 2` | `astro_ceres_surf_bright_max_shift_m7d` | `6.557` | `6.6405` | `6.8298` |
| `Bits 4-5` | `>> 4` | `astro_ceres_dist_max_shift_m7d` | `3.3228` | `3.5632` | `3.6232` |
| `Bits 6-7` | `>> 6` | `astro_ceres_dist_rate_max_shift_m7d` | `-17.143` | `-11.154` | `-8.7694` |
| `Bits 8-9` | `>> 8` | `astro_ceres_helio_dist_max_shift_m7d` | `2.7651` | `2.7737` | `2.7977` |
| `Bits 10-11` | `>> 10` | `astro_ceres_helio_dist_rate_max_shift_m7d` | `1.3916` | `1.4133` | `1.417` |
| `Bits 12-13` | `>> 12` | `astro_ceres_phase_angle_max_shift_m7d` | `9.7133` | `11.678` | `16.574` |
| `Bits 14-15` | `>> 14` | `astro_ceres_elong_max_shift_m7d` | `28.326` | `34.83` | `53.931` |

### Container: `packed_astro_container_123` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_ceres_illum_frac_max_shift_m7d` | `67.22` | `77.587` | `78.064` |
| `Bits 2-3` | `>> 2` | `astro_venus_ra_icrf_max_shift_m7d` | `248.21` | `261.89` | `301.3` |
| `Bits 4-5` | `>> 4` | `astro_venus_dec_icrf_max_shift_m7d` | `-20.287` | `-18.704` | `-18.704` |
| `Bits 6-7` | `>> 6` | `astro_venus_ra_app_max_shift_m7d` | `248.56` | `262.24` | `301.65` |
| `Bits 8-9` | `>> 8` | `astro_venus_dec_app_max_shift_m7d` | `-20.305` | `-18.77` | `-18.77` |
| `Bits 10-11` | `>> 10` | `astro_venus_azim_max_shift_m7d` | `69.421` | `78.093` | `78.404` |
| `Bits 12-13` | `>> 12` | `astro_venus_elev_max_shift_m7d` | `-49.739` | `-43.616` | `-39.953` |
| `Bits 14-15` | `>> 14` | `astro_venus_app_mag_max_shift_m7d` | `-4.016` | `-3.9825` | `-3.9122` |

### Container: `packed_astro_container_124` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_surf_bright_max_shift_m7d` | `1.0368` | `1.1385` | `1.176` |
| `Bits 2-3` | `>> 2` | `astro_venus_dist_max_shift_m7d` | `1.2191` | `1.2814` | `1.44` |
| `Bits 4-5` | `>> 4` | `astro_venus_dist_rate_max_shift_m7d` | `8.5351` | `10.096` | `10.63` |
| `Bits 6-7` | `>> 6` | `astro_venus_helio_dist_max_shift_m7d` | `0.72115` | `0.72252` | `0.72632` |
| `Bits 8-9` | `>> 8` | `astro_venus_helio_dist_rate_max_shift_m7d` | `0.20412` | `0.21206` | `0.21915` |
| `Bits 10-11` | `>> 10` | `astro_venus_phase_angle_max_shift_m7d` | `41.117` | `52.038` | `56.136` |
| `Bits 12-13` | `>> 12` | `astro_venus_elong_max_shift_m7d` | `28.915` | `35.338` | `37.469` |
| `Bits 14-15` | `>> 14` | `astro_venus_illum_frac_max_shift_m7d` | `67.22` | `77.587` | `78.064` |

### Container: `packed_astro_container_125` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_ra_icrf_mean_shift_m7d` | `283.87` | `295.3` | `325.99` |
| `Bits 2-3` | `>> 2` | `astro_sun_dec_icrf_mean_shift_m7d` | `-22.809` | `-21.342` | `-13.6` |
| `Bits 4-5` | `>> 4` | `astro_sun_ra_app_mean_shift_m7d` | `284.23` | `295.65` | `326.31` |
| `Bits 6-7` | `>> 6` | `astro_sun_dec_app_mean_shift_m7d` | `-22.78` | `-21.288` | `-13.492` |
| `Bits 8-9` | `>> 8` | `astro_sun_azim_mean_shift_m7d` | `18.939` | `26.8` | `30.611` |
| `Bits 10-11` | `>> 10` | `astro_sun_elev_mean_shift_m7d` | `-67.629` | `-66.624` | `-59.56` |
| `Bits 12-13` | `>> 12` | `astro_sun_app_mag_mean_shift_m7d` | `-26.779` | `-26.778` | `-26.77` |
| `Bits 14-15` | `>> 14` | `astro_sun_dist_mean_shift_m7d` | `0.98336` | `0.98367` | `0.9873` |

### Container: `packed_astro_container_126` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_dist_rate_mean_shift_m7d` | `-0.058043` | `0.024212` | `0.26083` |
| `Bits 2-3` | `>> 2` | `astro_sun_illum_frac_mean_shift_m7d` | `36.787` | `50.516` | `50.516` |
| `Bits 4-5` | `>> 4` | `astro_moon_ra_icrf_mean_shift_m7d` | `142.97` | `191.8` | `197.33` |
| `Bits 6-7` | `>> 6` | `astro_moon_dec_icrf_mean_shift_m7d` | `-6.9624` | `-4.1098` | `5.2201` |
| `Bits 8-9` | `>> 8` | `astro_moon_ra_app_mean_shift_m7d` | `143.32` | `192.12` | `197.65` |
| `Bits 10-11` | `>> 10` | `astro_moon_dec_app_mean_shift_m7d` | `-7.0814` | `-4.2311` | `5.2735` |
| `Bits 12-13` | `>> 12` | `astro_moon_azim_mean_shift_m7d` | `103.59` | `107.52` | `199.03` |
| `Bits 14-15` | `>> 14` | `astro_moon_elev_mean_shift_m7d` | `-12.909` | `7.4548` | `7.4548` |

### Container: `packed_astro_container_127` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_app_mag_mean_shift_m7d` | `-10.005` | `-10.005` | `-9.2864` |
| `Bits 2-3` | `>> 2` | `astro_moon_surf_bright_mean_shift_m7d` | `5.1834` | `5.1834` | `5.53` |
| `Bits 4-5` | `>> 4` | `astro_moon_dist_mean_shift_m7d` | `0.0025052` | `0.0026594` | `0.0026624` |
| `Bits 6-7` | `>> 6` | `astro_moon_dist_rate_mean_shift_m7d` | `-0.32296` | `-0.27166` | `0.059093` |
| `Bits 8-9` | `>> 8` | `astro_moon_helio_dist_mean_shift_m7d` | `0.98339` | `0.98356` | `0.9868` |
| `Bits 10-11` | `>> 10` | `astro_moon_helio_dist_rate_mean_shift_m7d` | `-0.81159` | `-0.37403` | `0.25273` |
| `Bits 12-13` | `>> 12` | `astro_moon_phase_angle_mean_shift_m7d` | `89.379` | `89.379` | `107.24` |
| `Bits 14-15` | `>> 14` | `astro_moon_elong_mean_shift_m7d` | `72.638` | `90.477` | `90.477` |

### Container: `packed_astro_container_128` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_illum_frac_mean_shift_m7d` | `36.787` | `50.516` | `50.516` |
| `Bits 2-3` | `>> 2` | `astro_saturn_ra_icrf_mean_shift_m7d` | `335.72` | `336.69` | `339.85` |
| `Bits 4-5` | `>> 4` | `astro_saturn_dec_icrf_mean_shift_m7d` | `-11.856` | `-11.473` | `-10.232` |
| `Bits 6-7` | `>> 6` | `astro_saturn_ra_app_mean_shift_m7d` | `336.04` | `337.01` | `340.16` |
| `Bits 8-9` | `>> 8` | `astro_saturn_dec_app_mean_shift_m7d` | `-11.737` | `-11.353` | `-10.109` |
| `Bits 10-11` | `>> 10` | `astro_saturn_azim_mean_shift_m7d` | `300.11` | `300.11` | `306.36` |
| `Bits 12-13` | `>> 12` | `astro_saturn_elev_mean_shift_m7d` | `-54.918` | `-48.976` | `-43.732` |
| `Bits 14-15` | `>> 14` | `astro_saturn_app_mag_mean_shift_m7d` | `0.961` | `0.967` | `0.98746` |

### Container: `packed_astro_container_129` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_surf_bright_mean_shift_m7d` | `6.6928` | `6.7169` | `6.7253` |
| `Bits 2-3` | `>> 2` | `astro_saturn_dist_mean_shift_m7d` | `10.333` | `10.456` | `10.678` |
| `Bits 4-5` | `>> 4` | `astro_saturn_dist_rate_mean_shift_m7d` | `6.8255` | `18.838` | `22.316` |
| `Bits 6-7` | `>> 6` | `astro_saturn_helio_dist_mean_shift_m7d` | `9.7256` | `9.734` | `9.737` |
| `Bits 8-9` | `>> 8` | `astro_saturn_helio_dist_rate_mean_shift_m7d` | `-0.4945` | `-0.49088` | `-0.48885` |
| `Bits 10-11` | `>> 10` | `astro_saturn_phase_angle_mean_shift_m7d` | `1.4141` | `3.7783` | `4.4649` |
| `Bits 12-13` | `>> 12` | `astro_saturn_elong_mean_shift_m7d` | `14.04` | `40.77` | `50.438` |
| `Bits 14-15` | `>> 14` | `astro_saturn_illum_frac_mean_shift_m7d` | `36.787` | `50.516` | `50.516` |

### Container: `packed_astro_container_130` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_ra_icrf_mean_shift_m7d` | `33.387` | `33.707` | `36.372` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_dec_icrf_mean_shift_m7d` | `12.176` | `12.342` | `13.382` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_ra_app_mean_shift_m7d` | `33.71` | `34.031` | `36.697` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_dec_app_mean_shift_m7d` | `12.289` | `12.454` | `13.49` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_azim_mean_shift_m7d` | `274.21` | `280.99` | `300.29` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_elev_mean_shift_m7d` | `-11.013` | `6.4951` | `13.669` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_app_mag_mean_shift_m7d` | `-2.564` | `-2.4792` | `-2.269` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_surf_bright_mean_shift_m7d` | `5.3599` | `5.3599` | `5.3674` |

### Container: `packed_astro_container_131` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_dist_mean_shift_m7d` | `4.5259` | `4.6877` | `5.1616` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_dist_rate_mean_shift_m7d` | `26.132` | `26.132` | `27.176` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_helio_dist_mean_shift_m7d` | `4.9855` | `4.9875` | `4.9936` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_helio_dist_rate_mean_shift_m7d` | `0.33256` | `0.34145` | `0.36589` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_phase_angle_mean_shift_m7d` | `10.488` | `10.488` | `10.933` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_elong_mean_shift_m7d` | `74.748` | `102.16` | `112.51` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_illum_frac_mean_shift_m7d` | `36.787` | `50.516` | `50.516` |
| `Bits 14-15` | `>> 14` | `astro_mars_ra_icrf_mean_shift_m7d` | `269.14` | `277.73` | `302.04` |

### Container: `packed_astro_container_132` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_dec_icrf_mean_shift_m7d` | `-24.005` | `-23.892` | `-21.112` |
| `Bits 2-3` | `>> 2` | `astro_mars_ra_app_mean_shift_m7d` | `269.49` | `278.09` | `302.38` |
| `Bits 4-5` | `>> 4` | `astro_mars_dec_app_mean_shift_m7d` | `-24.009` | `-23.877` | `-21.044` |
| `Bits 6-7` | `>> 6` | `astro_mars_azim_mean_shift_m7d` | `58.354` | `60.513` | `62.857` |
| `Bits 8-9` | `>> 8` | `astro_mars_elev_mean_shift_m7d` | `-60.996` | `-59.788` | `-54.516` |
| `Bits 10-11` | `>> 10` | `astro_mars_app_mag_mean_shift_m7d` | `1.2876` | `1.3838` | `1.426` |
| `Bits 12-13` | `>> 12` | `astro_mars_surf_bright_mean_shift_m7d` | `4.0744` | `4.1006` | `4.1006` |
| `Bits 14-15` | `>> 14` | `astro_mars_dist_mean_shift_m7d` | `2.2737` | `2.3804` | `2.4146` |

### Container: `packed_astro_container_133` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_dist_rate_mean_shift_m7d` | `-6.6979` | `-5.9616` | `-5.5345` |
| `Bits 2-3` | `>> 2` | `astro_mars_helio_dist_mean_shift_m7d` | `1.4298` | `1.4638` | `1.4769` |
| `Bits 4-5` | `>> 4` | `astro_mars_helio_dist_rate_mean_shift_m7d` | `-2.1925` | `-2.1231` | `-1.7994` |
| `Bits 6-7` | `>> 6` | `astro_mars_phase_angle_mean_shift_m7d` | `8.9883` | `10.952` | `16.331` |
| `Bits 8-9` | `>> 8` | `astro_mars_elong_mean_shift_m7d` | `13.571` | `16.421` | `24.028` |
| `Bits 10-11` | `>> 10` | `astro_mars_illum_frac_mean_shift_m7d` | `36.787` | `50.516` | `50.516` |
| `Bits 12-13` | `>> 12` | `astro_ceres_ra_icrf_mean_shift_m7d` | `255.36` | `259.83` | `271.88` |
| `Bits 14-15` | `>> 14` | `astro_ceres_dec_icrf_mean_shift_m7d` | `-22.684` | `-21.523` | `-20.895` |

### Container: `packed_astro_container_134` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_ceres_ra_app_mean_shift_m7d` | `255.71` | `260.18` | `272.24` |
| `Bits 2-3` | `>> 2` | `astro_ceres_dec_app_mean_shift_m7d` | `-22.682` | `-21.548` | `-20.93` |
| `Bits 4-5` | `>> 4` | `astro_ceres_azim_mean_shift_m7d` | `70.214` | `76.244` | `90.441` |
| `Bits 6-7` | `>> 6` | `astro_ceres_elev_mean_shift_m7d` | `-49.715` | `-45.983` | `-34.121` |
| `Bits 8-9` | `>> 8` | `astro_ceres_app_mag_mean_shift_m7d` | `8.9679` | `8.988` | `9.0485` |
| `Bits 10-11` | `>> 10` | `astro_ceres_surf_bright_mean_shift_m7d` | `6.5309` | `6.6173` | `6.8136` |
| `Bits 12-13` | `>> 12` | `astro_ceres_dist_mean_shift_m7d` | `3.293` | `3.5435` | `3.6075` |
| `Bits 14-15` | `>> 14` | `astro_ceres_dist_rate_mean_shift_m7d` | `-17.659` | `-11.812` | `-9.4577` |

### Container: `packed_astro_container_135` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_ceres_helio_dist_mean_shift_m7d` | `2.7627` | `2.7713` | `2.7953` |
| `Bits 2-3` | `>> 2` | `astro_ceres_helio_dist_rate_mean_shift_m7d` | `1.3885` | `1.4118` | `1.4162` |
| `Bits 4-5` | `>> 4` | `astro_ceres_phase_angle_mean_shift_m7d` | `9.1326` | `11.124` | `16.136` |
| `Bits 6-7` | `>> 6` | `astro_ceres_elong_mean_shift_m7d` | `26.494` | `32.964` | `51.954` |
| `Bits 8-9` | `>> 8` | `astro_ceres_illum_frac_mean_shift_m7d` | `36.787` | `50.516` | `50.516` |
| `Bits 10-11` | `>> 10` | `astro_venus_ra_icrf_mean_shift_m7d` | `244.4` | `257.95` | `297.38` |
| `Bits 12-13` | `>> 12` | `astro_venus_dec_icrf_mean_shift_m7d` | `-20.861` | `-19.45` | `-19.45` |
| `Bits 14-15` | `>> 14` | `astro_venus_ra_app_mean_shift_m7d` | `244.74` | `258.31` | `297.73` |

### Container: `packed_astro_container_136` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_dec_app_mean_shift_m7d` | `-20.874` | `-19.509` | `-19.509` |
| `Bits 2-3` | `>> 2` | `astro_venus_azim_mean_shift_m7d` | `67.822` | `77.773` | `78.373` |
| `Bits 4-5` | `>> 4` | `astro_venus_elev_mean_shift_m7d` | `-50.29` | `-44.591` | `-41.031` |
| `Bits 6-7` | `>> 6` | `astro_venus_app_mag_mean_shift_m7d` | `-4.0274` | `-3.9919` | `-3.9178` |
| `Bits 8-9` | `>> 8` | `astro_venus_surf_bright_mean_shift_m7d` | `1.027` | `1.1281` | `1.1656` |
| `Bits 10-11` | `>> 10` | `astro_venus_dist_mean_shift_m7d` | `1.2006` | `1.2638` | `1.4252` |
| `Bits 12-13` | `>> 12` | `astro_venus_dist_rate_mean_shift_m7d` | `8.3685` | `9.9424` | `10.482` |
| `Bits 14-15` | `>> 14` | `astro_venus_helio_dist_mean_shift_m7d` | `0.7208` | `0.72212` | `0.72599` |

### Container: `packed_astro_container_137` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_helio_dist_rate_mean_shift_m7d` | `0.19322` | `0.20221` | `0.21074` |
| `Bits 2-3` | `>> 2` | `astro_venus_phase_angle_mean_shift_m7d` | `40.062` | `50.895` | `54.949` |
| `Bits 4-5` | `>> 4` | `astro_venus_elong_mean_shift_m7d` | `28.241` | `34.714` | `36.869` |
| `Bits 6-7` | `>> 6` | `astro_venus_illum_frac_mean_shift_m7d` | `36.787` | `50.516` | `50.516` |
| `Bits 8-9` | `>> 8` | `astro_sun_ra_icrf_median_shift_m7d` | `283.87` | `295.31` | `325.99` |
| `Bits 10-11` | `>> 10` | `astro_sun_dec_icrf_median_shift_m7d` | `-22.824` | `-21.356` | `-13.608` |
| `Bits 12-13` | `>> 12` | `astro_sun_ra_app_median_shift_m7d` | `284.23` | `295.66` | `326.31` |
| `Bits 14-15` | `>> 14` | `astro_sun_dec_app_median_shift_m7d` | `-22.795` | `-21.301` | `-13.5` |

### Container: `packed_astro_container_138` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_azim_median_shift_m7d` | `18.924` | `26.793` | `30.618` |
| `Bits 2-3` | `>> 2` | `astro_sun_elev_median_shift_m7d` | `-67.645` | `-66.64` | `-59.569` |
| `Bits 4-5` | `>> 4` | `astro_sun_app_mag_median_shift_m7d` | `-26.779` | `-26.778` | `-26.77` |
| `Bits 6-7` | `>> 6` | `astro_sun_dist_median_shift_m7d` | `0.98336` | `0.98366` | `0.9873` |
| `Bits 8-9` | `>> 8` | `astro_sun_dist_rate_median_shift_m7d` | `-0.057205` | `0.023865` | `0.2604` |
| `Bits 10-11` | `>> 10` | `astro_sun_illum_frac_median_shift_m7d` | `35.826` | `50.799` | `50.799` |
| `Bits 12-13` | `>> 12` | `astro_moon_ra_icrf_median_shift_m7d` | `143.86` | `191.24` | `196.57` |
| `Bits 14-15` | `>> 14` | `astro_moon_dec_icrf_median_shift_m7d` | `-7.3627` | `-4.2772` | `6.0176` |

### Container: `packed_astro_container_139` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_ra_app_median_shift_m7d` | `144.21` | `191.55` | `196.89` |
| `Bits 2-3` | `>> 2` | `astro_moon_dec_app_median_shift_m7d` | `-7.4915` | `-4.4082` | `6.078` |
| `Bits 4-5` | `>> 4` | `astro_moon_azim_median_shift_m7d` | `103.39` | `103.39` | `205.39` |
| `Bits 6-7` | `>> 6` | `astro_moon_elev_median_shift_m7d` | `-12.538` | `7.7593` | `7.7593` |
| `Bits 8-9` | `>> 8` | `astro_moon_app_mag_median_shift_m7d` | `-10.101` | `-10.1` | `-9.5075` |
| `Bits 10-11` | `>> 10` | `astro_moon_surf_bright_median_shift_m7d` | `5.166` | `5.166` | `5.5122` |
| `Bits 12-13` | `>> 12` | `astro_moon_dist_median_shift_m7d` | `0.0024982` | `0.0026712` | `0.0026772` |
| `Bits 14-15` | `>> 14` | `astro_moon_dist_rate_median_shift_m7d` | `-0.34912` | `-0.30004` | `0.060246` |

### Container: `packed_astro_container_140` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_helio_dist_median_shift_m7d` | `0.98339` | `0.98355` | `0.98692` |
| `Bits 2-3` | `>> 2` | `astro_moon_helio_dist_rate_median_shift_m7d` | `-0.81843` | `-0.42658` | `0.25188` |
| `Bits 4-5` | `>> 4` | `astro_moon_phase_angle_median_shift_m7d` | `89.085` | `89.085` | `106.6` |
| `Bits 6-7` | `>> 6` | `astro_moon_elong_median_shift_m7d` | `73.258` | `90.759` | `90.759` |
| `Bits 8-9` | `>> 8` | `astro_moon_illum_frac_median_shift_m7d` | `35.826` | `50.799` | `50.799` |
| `Bits 10-11` | `>> 10` | `astro_saturn_ra_icrf_median_shift_m7d` | `335.72` | `336.69` | `339.85` |
| `Bits 12-13` | `>> 12` | `astro_saturn_dec_icrf_median_shift_m7d` | `-11.857` | `-11.474` | `-10.232` |
| `Bits 14-15` | `>> 14` | `astro_saturn_ra_app_median_shift_m7d` | `336.03` | `337` | `340.16` |

### Container: `packed_astro_container_141` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_dec_app_median_shift_m7d` | `-11.738` | `-11.354` | `-10.109` |
| `Bits 2-3` | `>> 2` | `astro_saturn_azim_median_shift_m7d` | `300.09` | `300.09` | `313.1` |
| `Bits 4-5` | `>> 4` | `astro_saturn_elev_median_shift_m7d` | `-54.947` | `-48.995` | `-43.746` |
| `Bits 6-7` | `>> 6` | `astro_saturn_app_mag_median_shift_m7d` | `0.961` | `0.967` | `0.9875` |
| `Bits 8-9` | `>> 8` | `astro_saturn_surf_bright_median_shift_m7d` | `6.693` | `6.717` | `6.725` |
| `Bits 10-11` | `>> 10` | `astro_saturn_dist_median_shift_m7d` | `10.334` | `10.457` | `10.678` |
| `Bits 12-13` | `>> 12` | `astro_saturn_dist_rate_median_shift_m7d` | `6.8274` | `18.847` | `22.328` |
| `Bits 14-15` | `>> 14` | `astro_saturn_helio_dist_median_shift_m7d` | `9.7256` | `9.734` | `9.737` |

### Container: `packed_astro_container_142` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_helio_dist_rate_median_shift_m7d` | `-0.49447` | `-0.49088` | `-0.4886` |
| `Bits 2-3` | `>> 2` | `astro_saturn_phase_angle_median_shift_m7d` | `1.4145` | `3.7801` | `4.4671` |
| `Bits 4-5` | `>> 4` | `astro_saturn_elong_median_shift_m7d` | `14.039` | `40.768` | `50.436` |
| `Bits 6-7` | `>> 6` | `astro_saturn_illum_frac_median_shift_m7d` | `35.826` | `50.799` | `50.799` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_ra_icrf_median_shift_m7d` | `33.38` | `33.701` | `36.367` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_dec_icrf_median_shift_m7d` | `12.174` | `12.34` | `13.381` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_ra_app_median_shift_m7d` | `33.704` | `34.025` | `36.692` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_dec_app_median_shift_m7d` | `12.286` | `12.452` | `13.489` |

### Container: `packed_astro_container_143` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_azim_median_shift_m7d` | `274.22` | `280.99` | `300.29` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_elev_median_shift_m7d` | `-11.025` | `6.4861` | `13.661` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_app_mag_median_shift_m7d` | `-2.564` | `-2.479` | `-2.2687` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_surf_bright_median_shift_m7d` | `5.36` | `5.36` | `5.3673` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_dist_median_shift_m7d` | `4.5257` | `4.6876` | `5.1617` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_dist_rate_median_shift_m7d` | `26.149` | `26.149` | `27.193` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_helio_dist_median_shift_m7d` | `4.9855` | `4.9875` | `4.9936` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_helio_dist_rate_median_shift_m7d` | `0.3332` | `0.34203` | `0.3657` |

### Container: `packed_astro_container_144` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_phase_angle_median_shift_m7d` | `10.495` | `10.495` | `10.94` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_elong_median_shift_m7d` | `74.743` | `102.16` | `112.51` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_illum_frac_median_shift_m7d` | `35.826` | `50.799` | `50.799` |
| `Bits 6-7` | `>> 6` | `astro_mars_ra_icrf_median_shift_m7d` | `269.13` | `277.73` | `302.04` |
| `Bits 8-9` | `>> 8` | `astro_mars_dec_icrf_median_shift_m7d` | `-24.014` | `-23.901` | `-21.12` |
| `Bits 10-11` | `>> 10` | `astro_mars_ra_app_median_shift_m7d` | `269.49` | `278.08` | `302.39` |
| `Bits 12-13` | `>> 12` | `astro_mars_dec_app_median_shift_m7d` | `-24.018` | `-23.885` | `-21.052` |
| `Bits 14-15` | `>> 14` | `astro_mars_azim_median_shift_m7d` | `58.371` | `60.528` | `62.862` |

### Container: `packed_astro_container_145` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_elev_median_shift_m7d` | `-61.002` | `-59.794` | `-54.523` |
| `Bits 2-3` | `>> 2` | `astro_mars_app_mag_median_shift_m7d` | `1.2843` | `1.383` | `1.429` |
| `Bits 4-5` | `>> 4` | `astro_mars_surf_bright_median_shift_m7d` | `4.0753` | `4.099` | `4.099` |
| `Bits 6-7` | `>> 6` | `astro_mars_dist_median_shift_m7d` | `2.2737` | `2.3804` | `2.4146` |
| `Bits 8-9` | `>> 8` | `astro_mars_dist_rate_median_shift_m7d` | `-6.6999` | `-5.9637` | `-5.5352` |
| `Bits 10-11` | `>> 10` | `astro_mars_helio_dist_median_shift_m7d` | `1.4298` | `1.4638` | `1.4769` |
| `Bits 12-13` | `>> 12` | `astro_mars_helio_dist_rate_median_shift_m7d` | `-2.1929` | `-2.1236` | `-1.7998` |
| `Bits 14-15` | `>> 14` | `astro_mars_phase_angle_median_shift_m7d` | `8.9887` | `10.953` | `16.332` |

### Container: `packed_astro_container_146` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_elong_median_shift_m7d` | `13.572` | `16.423` | `24.03` |
| `Bits 2-3` | `>> 2` | `astro_mars_illum_frac_median_shift_m7d` | `35.826` | `50.799` | `50.799` |
| `Bits 4-5` | `>> 4` | `astro_ceres_ra_icrf_median_shift_m7d` | `255.36` | `259.83` | `271.88` |
| `Bits 6-7` | `>> 6` | `astro_ceres_dec_icrf_median_shift_m7d` | `-22.686` | `-21.526` | `-20.898` |
| `Bits 8-9` | `>> 8` | `astro_ceres_ra_app_median_shift_m7d` | `255.71` | `260.18` | `272.24` |
| `Bits 10-11` | `>> 10` | `astro_ceres_dec_app_median_shift_m7d` | `-22.683` | `-21.551` | `-20.933` |
| `Bits 12-13` | `>> 12` | `astro_ceres_azim_median_shift_m7d` | `70.229` | `76.256` | `90.445` |
| `Bits 14-15` | `>> 14` | `astro_ceres_elev_median_shift_m7d` | `-49.721` | `-45.988` | `-34.124` |

### Container: `packed_astro_container_147` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_ceres_app_mag_median_shift_m7d` | `8.968` | `8.9885` | `9.0488` |
| `Bits 2-3` | `>> 2` | `astro_ceres_surf_bright_median_shift_m7d` | `6.531` | `6.6175` | `6.8133` |
| `Bits 4-5` | `>> 4` | `astro_ceres_dist_median_shift_m7d` | `3.2932` | `3.5437` | `3.6077` |
| `Bits 6-7` | `>> 6` | `astro_ceres_dist_rate_median_shift_m7d` | `-17.664` | `-11.815` | `-9.4584` |
| `Bits 8-9` | `>> 8` | `astro_ceres_helio_dist_median_shift_m7d` | `2.7627` | `2.7713` | `2.7953` |
| `Bits 10-11` | `>> 10` | `astro_ceres_helio_dist_rate_median_shift_m7d` | `1.3885` | `1.4119` | `1.4162` |
| `Bits 12-13` | `>> 12` | `astro_ceres_phase_angle_median_shift_m7d` | `9.1339` | `11.126` | `16.139` |
| `Bits 14-15` | `>> 14` | `astro_ceres_elong_median_shift_m7d` | `26.491` | `32.961` | `51.951` |

### Container: `packed_astro_container_148` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_ceres_illum_frac_median_shift_m7d` | `35.826` | `50.799` | `50.799` |
| `Bits 2-3` | `>> 2` | `astro_venus_ra_icrf_median_shift_m7d` | `244.39` | `257.95` | `297.39` |
| `Bits 4-5` | `>> 4` | `astro_venus_dec_icrf_median_shift_m7d` | `-20.88` | `-19.467` | `-19.467` |
| `Bits 6-7` | `>> 6` | `astro_venus_ra_app_median_shift_m7d` | `244.73` | `258.3` | `297.73` |
| `Bits 8-9` | `>> 8` | `astro_venus_dec_app_median_shift_m7d` | `-20.894` | `-19.526` | `-19.526` |
| `Bits 10-11` | `>> 10` | `astro_venus_azim_median_shift_m7d` | `67.845` | `77.801` | `78.387` |
| `Bits 12-13` | `>> 12` | `astro_venus_elev_median_shift_m7d` | `-50.31` | `-44.6` | `-41.036` |
| `Bits 14-15` | `>> 14` | `astro_venus_app_mag_median_shift_m7d` | `-4.027` | `-3.992` | `-3.9175` |

### Container: `packed_astro_container_149` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_surf_bright_median_shift_m7d` | `1.0267` | `1.128` | `1.166` |
| `Bits 2-3` | `>> 2` | `astro_venus_dist_median_shift_m7d` | `1.2007` | `1.2639` | `1.4253` |
| `Bits 4-5` | `>> 4` | `astro_venus_dist_rate_median_shift_m7d` | `8.368` | `9.942` | `10.483` |
| `Bits 6-7` | `>> 6` | `astro_venus_helio_dist_median_shift_m7d` | `0.72079` | `0.72212` | `0.72599` |
| `Bits 8-9` | `>> 8` | `astro_venus_helio_dist_rate_median_shift_m7d` | `0.19352` | `0.20253` | `0.21106` |
| `Bits 10-11` | `>> 10` | `astro_venus_phase_angle_median_shift_m7d` | `40.061` | `50.893` | `54.946` |
| `Bits 12-13` | `>> 12` | `astro_venus_elong_median_shift_m7d` | `28.241` | `34.715` | `36.871` |
| `Bits 14-15` | `>> 14` | `astro_venus_illum_frac_median_shift_m7d` | `35.826` | `50.799` | `50.799` |

### Container: `packed_astro_container_150` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_ra_icrf_min_shift_p7d` | `24.968` | `36.454` | `36.454` |
| `Bits 2-3` | `>> 2` | `astro_sun_dec_icrf_min_shift_p7d` | `-0.28488` | `10.958` | `14.441` |
| `Bits 4-5` | `>> 4` | `astro_sun_ra_app_min_shift_p7d` | `25.282` | `36.779` | `36.779` |
| `Bits 6-7` | `>> 6` | `astro_sun_dec_app_min_shift_p7d` | `-0.15304` | `11.077` | `14.549` |
| `Bits 8-9` | `>> 8` | `astro_sun_azim_min_shift_p7d` | `15.729` | `15.951` | `16.47` |
| `Bits 10-11` | `>> 10` | `astro_sun_elev_min_shift_p7d` | `-46.197` | `-34.786` | `-31.292` |
| `Bits 12-13` | `>> 12` | `astro_sun_app_mag_min_shift_p7d` | `-26.751` | `-26.733` | `-26.727` |
| `Bits 14-15` | `>> 14` | `astro_sun_dist_min_shift_p7d` | `0.9958` | `1.0042` | `1.007` |

### Container: `packed_astro_container_151` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_dist_rate_min_shift_p7d` | `0.37185` | `0.37185` | `0.39234` |
| `Bits 2-3` | `>> 2` | `astro_sun_illum_frac_min_shift_p7d` | `44.976` | `55.013` | `55.801` |
| `Bits 4-5` | `>> 4` | `astro_moon_ra_icrf_min_shift_p7d` | `123.95` | `262.47` | `279.17` |
| `Bits 6-7` | `>> 6` | `astro_moon_dec_icrf_min_shift_p7d` | `-29.197` | `-29.106` | `-8.0731` |
| `Bits 8-9` | `>> 8` | `astro_moon_ra_app_min_shift_p7d` | `124.31` | `262.85` | `279.56` |
| `Bits 10-11` | `>> 10` | `astro_moon_dec_app_min_shift_p7d` | `-29.176` | `-29.117` | `-7.9897` |
| `Bits 12-13` | `>> 12` | `astro_moon_azim_min_shift_p7d` | `116.74` | `116.74` | `132.73` |
| `Bits 14-15` | `>> 14` | `astro_moon_elev_min_shift_p7d` | `-7.3342` | `-7.3342` | `2.9656` |

### Container: `packed_astro_container_152` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_app_mag_min_shift_p7d` | `-12.101` | `-11.123` | `-11.123` |
| `Bits 2-3` | `>> 2` | `astro_moon_surf_bright_min_shift_p7d` | `3.8337` | `4.674` | `4.674` |
| `Bits 4-5` | `>> 4` | `astro_moon_dist_min_shift_p7d` | `0.0025145` | `0.0025155` | `0.0025946` |
| `Bits 6-7` | `>> 6` | `astro_moon_dist_rate_min_shift_p7d` | `-0.33895` | `-0.33895` | `-0.14512` |
| `Bits 8-9` | `>> 8` | `astro_moon_helio_dist_min_shift_p7d` | `0.9965` | `1.0052` | `1.0078` |
| `Bits 10-11` | `>> 10` | `astro_moon_helio_dist_rate_min_shift_p7d` | `-0.51557` | `-0.4839` | `0.16185` |
| `Bits 12-13` | `>> 12` | `astro_moon_phase_angle_min_shift_p7d` | `20.495` | `59.276` | `59.276` |
| `Bits 14-15` | `>> 14` | `astro_moon_elong_min_shift_p7d` | `84.065` | `95.611` | `96.514` |

### Container: `packed_astro_container_153` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_illum_frac_min_shift_p7d` | `44.976` | `55.013` | `55.801` |
| `Bits 2-3` | `>> 2` | `astro_saturn_ra_icrf_min_shift_p7d` | `343.89` | `346.97` | `347.91` |
| `Bits 4-5` | `>> 4` | `astro_saturn_dec_icrf_min_shift_p7d` | `-8.6388` | `-7.4361` | `-7.0762` |
| `Bits 6-7` | `>> 6` | `astro_saturn_ra_app_min_shift_p7d` | `344.2` | `347.28` | `348.22` |
| `Bits 8-9` | `>> 8` | `astro_saturn_dec_app_min_shift_p7d` | `-8.5124` | `-7.3069` | `-6.946` |
| `Bits 10-11` | `>> 10` | `astro_saturn_azim_min_shift_p7d` | `42.215` | `68.516` | `75.807` |
| `Bits 12-13` | `>> 12` | `astro_saturn_elev_min_shift_p7d` | `-48.429` | `-31.586` | `-24.771` |
| `Bits 14-15` | `>> 14` | `astro_saturn_app_mag_min_shift_p7d` | `1.032` | `1.0715` | `1.072` |

### Container: `packed_astro_container_154` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_surf_bright_min_shift_p7d` | `6.732` | `6.8235` | `6.851` |
| `Bits 2-3` | `>> 2` | `astro_saturn_dist_min_shift_p7d` | `10.254` | `10.337` | `10.625` |
| `Bits 4-5` | `>> 4` | `astro_saturn_dist_rate_min_shift_p7d` | `-23.79` | `-21.958` | `-11.345` |
| `Bits 6-7` | `>> 6` | `astro_saturn_helio_dist_min_shift_p7d` | `9.7032` | `9.7051` | `9.7137` |
| `Bits 8-9` | `>> 8` | `astro_saturn_helio_dist_rate_min_shift_p7d` | `-0.50417` | `-0.50269` | `-0.49946` |
| `Bits 10-11` | `>> 10` | `astro_saturn_phase_angle_min_shift_p7d` | `1.7625` | `4.0762` | `4.7357` |
| `Bits 12-13` | `>> 12` | `astro_saturn_elong_min_shift_p7d` | `17.517` | `43.504` | `52.73` |
| `Bits 14-15` | `>> 14` | `astro_saturn_illum_frac_min_shift_p7d` | `44.976` | `55.013` | `55.801` |

### Container: `packed_astro_container_155` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_ra_icrf_min_shift_p7d` | `42.283` | `48.69` | `51.134` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_dec_icrf_min_shift_p7d` | `15.364` | `17.224` | `17.864` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_ra_app_min_shift_p7d` | `42.613` | `49.025` | `51.472` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_dec_app_min_shift_p7d` | `15.464` | `17.313` | `17.949` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_azim_min_shift_p7d` | `0.78204` | `306.65` | `328.95` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_elev_min_shift_p7d` | `-29.297` | `-29.297` | `-26.381` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_app_mag_min_shift_p7d` | `-2.101` | `-2.024` | `-2.008` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_surf_bright_min_shift_p7d` | `5.319` | `5.321` | `5.3395` |

### Container: `packed_astro_container_156` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_dist_min_shift_p7d` | `5.6523` | `5.9217` | `5.9795` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_dist_rate_min_shift_p7d` | `6.9007` | `9.1056` | `18.519` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_helio_dist_min_shift_p7d` | `5.0014` | `5.0083` | `5.0109` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_helio_dist_rate_min_shift_p7d` | `0.39378` | `0.41709` | `0.42497` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_phase_angle_min_shift_p7d` | `2.6012` | `3.5255` | `7.4314` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_elong_min_shift_p7d` | `13.031` | `17.841` | `40.475` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_illum_frac_min_shift_p7d` | `44.976` | `55.013` | `55.801` |
| `Bits 14-15` | `>> 14` | `astro_mars_ra_icrf_min_shift_p7d` | `0.44647` | `309.44` | `332.38` |

### Container: `packed_astro_container_157` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_dec_icrf_min_shift_p7d` | `-13.552` | `-5.0096` | `-1.8007` |
| `Bits 2-3` | `>> 2` | `astro_mars_ra_app_min_shift_p7d` | `0.04581` | `309.78` | `332.7` |
| `Bits 4-5` | `>> 4` | `astro_mars_dec_app_min_shift_p7d` | `-13.439` | `-4.8785` | `-1.6676` |
| `Bits 6-7` | `>> 6` | `astro_mars_azim_min_shift_p7d` | `62.681` | `62.734` | `62.734` |
| `Bits 8-9` | `>> 8` | `astro_mars_elev_min_shift_p7d` | `-44.207` | `-32.87` | `-28.564` |
| `Bits 10-11` | `>> 10` | `astro_mars_app_mag_min_shift_p7d` | `1.172` | `1.172` | `1.184` |
| `Bits 12-13` | `>> 12` | `astro_mars_surf_bright_min_shift_p7d` | `4.068` | `4.1675` | `4.219` |
| `Bits 14-15` | `>> 14` | `astro_mars_dist_min_shift_p7d` | `1.9766` | `2.0011` | `2.1144` |

### Container: `packed_astro_container_158` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_dist_rate_min_shift_p7d` | `-6.8565` | `-6.8084` | `-6.782` |
| `Bits 2-3` | `>> 2` | `astro_mars_helio_dist_min_shift_p7d` | `1.3819` | `1.383` | `1.3951` |
| `Bits 4-5` | `>> 4` | `astro_mars_helio_dist_rate_min_shift_p7d` | `-1.1729` | `-0.49445` | `-0.23626` |
| `Bits 6-7` | `>> 6` | `astro_mars_phase_angle_min_shift_p7d` | `22.267` | `26.747` | `28.216` |
| `Bits 8-9` | `>> 8` | `astro_mars_elong_min_shift_p7d` | `32.16` | `38.348` | `40.457` |
| `Bits 10-11` | `>> 10` | `astro_mars_illum_frac_min_shift_p7d` | `44.976` | `55.013` | `55.801` |
| `Bits 12-13` | `>> 12` | `astro_ceres_ra_icrf_min_shift_p7d` | `284.02` | `290.98` | `292.48` |
| `Bits 14-15` | `>> 14` | `astro_ceres_dec_icrf_min_shift_p7d` | `-24.316` | `-24.063` | `-23.368` |

### Container: `packed_astro_container_159` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_ceres_ra_app_min_shift_p7d` | `284.38` | `291.34` | `292.85` |
| `Bits 2-3` | `>> 2` | `astro_ceres_dec_app_min_shift_p7d` | `-24.266` | `-24.014` | `-23.334` |
| `Bits 4-5` | `>> 4` | `astro_ceres_azim_min_shift_p7d` | `105.44` | `119.98` | `126.18` |
| `Bits 6-7` | `>> 6` | `astro_ceres_elev_min_shift_p7d` | `-17.917` | `-3.1937` | `1.9973` |
| `Bits 8-9` | `>> 8` | `astro_ceres_app_mag_min_shift_p7d` | `8.488` | `8.5765` | `8.8918` |
| `Bits 10-11` | `>> 10` | `astro_ceres_surf_bright_min_shift_p7d` | `6.9548` | `6.96` | `6.966` |
| `Bits 12-13` | `>> 12` | `astro_ceres_dist_min_shift_p7d` | `2.3466` | `2.4272` | `2.8097` |
| `Bits 14-15` | `>> 14` | `astro_ceres_dist_rate_min_shift_p7d` | `-22.334` | `-21.535` | `-21.535` |

### Container: `packed_astro_container_160` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_ceres_helio_dist_min_shift_p7d` | `2.8234` | `2.8459` | `2.8536` |
| `Bits 2-3` | `>> 2` | `astro_ceres_helio_dist_rate_min_shift_p7d` | `1.2556` | `1.2703` | `1.3296` |
| `Bits 4-5` | `>> 4` | `astro_ceres_phase_angle_min_shift_p7d` | `19.352` | `19.352` | `19.868` |
| `Bits 6-7` | `>> 6` | `astro_ceres_elong_min_shift_p7d` | `76.429` | `99.476` | `108.39` |
| `Bits 8-9` | `>> 8` | `astro_ceres_illum_frac_min_shift_p7d` | `44.976` | `55.013` | `55.801` |
| `Bits 10-11` | `>> 10` | `astro_venus_ra_icrf_min_shift_p7d` | `27.487` | `27.487` | `311.59` |
| `Bits 12-13` | `>> 12` | `astro_venus_dec_icrf_min_shift_p7d` | `-9.2259` | `5.0025` | `9.9542` |
| `Bits 14-15` | `>> 14` | `astro_venus_ra_app_min_shift_p7d` | `27.802` | `27.802` | `311.93` |

### Container: `packed_astro_container_161` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_dec_app_min_shift_p7d` | `-9.1015` | `5.1305` | `10.073` |
| `Bits 2-3` | `>> 2` | `astro_venus_azim_min_shift_p7d` | `26.474` | `28.988` | `42.543` |
| `Bits 4-5` | `>> 4` | `astro_venus_elev_min_shift_p7d` | `-47.699` | `-37.165` | `-33.185` |
| `Bits 6-7` | `>> 6` | `astro_venus_app_mag_min_shift_p7d` | `-3.885` | `-3.885` | `-3.8807` |
| `Bits 8-9` | `>> 8` | `astro_venus_surf_bright_min_shift_p7d` | `0.797` | `0.8125` | `0.8955` |
| `Bits 10-11` | `>> 10` | `astro_venus_dist_min_shift_p7d` | `1.5798` | `1.673` | `1.697` |
| `Bits 12-13` | `>> 12` | `astro_venus_dist_rate_min_shift_p7d` | `3.187` | `3.7136` | `5.9009` |
| `Bits 14-15` | `>> 14` | `astro_venus_helio_dist_min_shift_p7d` | `0.72523` | `0.726` | `0.72752` |

### Container: `packed_astro_container_162` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_helio_dist_rate_min_shift_p7d` | `-0.21712` | `-0.19592` | `-0.037737` |
| `Bits 2-3` | `>> 2` | `astro_venus_phase_angle_min_shift_p7d` | `13.005` | `15.346` | `25.766` |
| `Bits 4-5` | `>> 4` | `astro_venus_elong_min_shift_p7d` | `9.3206` | `11.011` | `18.499` |
| `Bits 6-7` | `>> 6` | `astro_venus_illum_frac_min_shift_p7d` | `44.976` | `55.013` | `55.801` |
| `Bits 8-9` | `>> 8` | `astro_sun_ra_icrf_max_shift_p7d` | `36.218` | `38.36` | `262.6` |
| `Bits 10-11` | `>> 10` | `astro_sun_dec_icrf_max_shift_p7d` | `2.0768` | `12.982` | `15.055` |
| `Bits 12-13` | `>> 12` | `astro_sun_ra_app_max_shift_p7d` | `36.543` | `38.686` | `262.91` |
| `Bits 14-15` | `>> 14` | `astro_sun_dec_app_max_shift_p7d` | `2.2085` | `13.095` | `15.16` |

### Container: `packed_astro_container_163` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_azim_max_shift_p7d` | `15.806` | `16.116` | `16.547` |
| `Bits 2-3` | `>> 2` | `astro_sun_elev_max_shift_p7d` | `-43.794` | `-32.752` | `-30.681` |
| `Bits 4-5` | `>> 4` | `astro_sun_app_mag_max_shift_p7d` | `-26.748` | `-26.73` | `-26.726` |
| `Bits 6-7` | `>> 6` | `astro_sun_dist_max_shift_p7d` | `0.99747` | `1.0058` | `1.0076` |
| `Bits 8-9` | `>> 8` | `astro_sun_dist_rate_max_shift_p7d` | `0.37793` | `0.37839` | `0.39856` |
| `Bits 10-11` | `>> 10` | `astro_sun_illum_frac_max_shift_p7d` | `75.547` | `75.547` | `96.469` |
| `Bits 12-13` | `>> 12` | `astro_moon_ra_icrf_max_shift_p7d` | `194.56` | `309.02` | `309.02` |
| `Bits 14-15` | `>> 14` | `astro_moon_dec_icrf_max_shift_p7d` | `-24.563` | `-7.3842` | `21.371` |

### Container: `packed_astro_container_164` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_ra_app_max_shift_p7d` | `194.88` | `309.38` | `309.38` |
| `Bits 2-3` | `>> 2` | `astro_moon_dec_app_max_shift_p7d` | `-24.479` | `-7.2544` | `21.309` |
| `Bits 4-5` | `>> 4` | `astro_moon_azim_max_shift_p7d` | `138.67` | `138.67` | `267.21` |
| `Bits 6-7` | `>> 6` | `astro_moon_elev_max_shift_p7d` | `5.2124` | `5.2124` | `33.421` |
| `Bits 8-9` | `>> 8` | `astro_moon_app_mag_max_shift_p7d` | `-10.359` | `-10.359` | `-9.859` |
| `Bits 10-11` | `>> 10` | `astro_moon_surf_bright_max_shift_p7d` | `5.0865` | `5.13` | `5.3392` |
| `Bits 12-13` | `>> 12` | `astro_moon_dist_max_shift_p7d` | `0.002557` | `0.0025771` | `0.0026788` |
| `Bits 14-15` | `>> 14` | `astro_moon_dist_rate_max_shift_p7d` | `-0.26051` | `-0.14919` | `0.27889` |

### Container: `packed_astro_container_165` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_helio_dist_max_shift_p7d` | `0.99965` | `1.0077` | `1.0083` |
| `Bits 2-3` | `>> 2` | `astro_moon_helio_dist_rate_max_shift_p7d` | `-0.37549` | `0.12081` | `1.0805` |
| `Bits 4-5` | `>> 4` | `astro_moon_phase_angle_max_shift_p7d` | `83.338` | `84.246` | `95.789` |
| `Bits 6-7` | `>> 6` | `astro_moon_elong_max_shift_p7d` | `120.6` | `120.6` | `159.45` |
| `Bits 8-9` | `>> 8` | `astro_moon_illum_frac_max_shift_p7d` | `75.547` | `75.547` | `96.469` |
| `Bits 10-11` | `>> 10` | `astro_saturn_ra_icrf_max_shift_p7d` | `344.55` | `347.52` | `348.08` |
| `Bits 12-13` | `>> 12` | `astro_saturn_dec_icrf_max_shift_p7d` | `-8.3793` | `-7.2266` | `-7.0132` |
| `Bits 14-15` | `>> 14` | `astro_saturn_ra_app_max_shift_p7d` | `344.86` | `347.83` | `348.39` |

### Container: `packed_astro_container_166` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_dec_app_max_shift_p7d` | `-8.2523` | `-7.0968` | `-6.8828` |
| `Bits 2-3` | `>> 2` | `astro_saturn_azim_max_shift_p7d` | `48.493` | `72.745` | `77.121` |
| `Bits 4-5` | `>> 4` | `astro_saturn_elev_max_shift_p7d` | `-45.466` | `-27.72` | `-23.439` |
| `Bits 6-7` | `>> 6` | `astro_saturn_app_mag_max_shift_p7d` | `1.045` | `1.073` | `1.073` |
| `Bits 8-9` | `>> 8` | `astro_saturn_surf_bright_max_shift_p7d` | `6.7527` | `6.84` | `6.856` |
| `Bits 10-11` | `>> 10` | `astro_saturn_dist_max_shift_p7d` | `10.28` | `10.409` | `10.659` |
| `Bits 12-13` | `>> 12` | `astro_saturn_dist_rate_max_shift_p7d` | `-23.256` | `-20.12` | `-8.8576` |
| `Bits 14-15` | `>> 14` | `astro_saturn_helio_dist_max_shift_p7d` | `9.7037` | `9.7068` | `9.7154` |

### Container: `packed_astro_container_167` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_helio_dist_rate_max_shift_p7d` | `-0.50336` | `-0.50084` | `-0.49773` |
| `Bits 2-3` | `>> 2` | `astro_saturn_phase_angle_max_shift_p7d` | `2.2698` | `4.4625` | `4.8476` |
| `Bits 4-5` | `>> 4` | `astro_saturn_elong_max_shift_p7d` | `22.747` | `48.772` | `54.494` |
| `Bits 6-7` | `>> 6` | `astro_saturn_illum_frac_max_shift_p7d` | `75.547` | `75.547` | `96.469` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_ra_icrf_max_shift_p7d` | `43.493` | `50.08` | `51.608` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_dec_icrf_max_shift_p7d` | `15.737` | `17.592` | `17.983` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_ra_app_max_shift_p7d` | `43.824` | `50.417` | `51.946` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_dec_app_max_shift_p7d` | `15.835` | `17.678` | `18.067` |

### Container: `packed_astro_container_168` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_azim_max_shift_p7d` | `330.95` | `355.44` | `359.97` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_elev_max_shift_p7d` | `-29.179` | `-29.179` | `-24.921` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_app_mag_max_shift_p7d` | `-2.0808` | `-2.0145` | `-2.006` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_surf_bright_max_shift_p7d` | `5.319` | `5.3235` | `5.3438` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_dist_max_shift_p7d` | `5.7188` | `5.9567` | `5.9879` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_dist_rate_max_shift_p7d` | `7.5862` | `11.11` | `20.178` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_helio_dist_max_shift_p7d` | `5.0028` | `5.0098` | `5.0114` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_helio_dist_rate_max_shift_p7d` | `0.40019` | `0.4225` | `0.42614` |

### Container: `packed_astro_container_169` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_phase_angle_max_shift_p7d` | `2.8881` | `4.3638` | `8.1161` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_elong_max_shift_p7d` | `14.505` | `22.314` | `45.202` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_illum_frac_max_shift_p7d` | `75.547` | `75.547` | `96.469` |
| `Bits 6-7` | `>> 6` | `astro_mars_ra_icrf_max_shift_p7d` | `334.25` | `355.84` | `359.74` |
| `Bits 8-9` | `>> 8` | `astro_mars_dec_icrf_max_shift_p7d` | `-11.94` | `-3.1798` | `-1.1864` |
| `Bits 10-11` | `>> 10` | `astro_mars_ra_app_max_shift_p7d` | `334.57` | `356.14` | `359.34` |
| `Bits 12-13` | `>> 12` | `astro_mars_dec_app_max_shift_p7d` | `-11.821` | `-3.0474` | `-1.0532` |
| `Bits 14-15` | `>> 14` | `astro_mars_azim_max_shift_p7d` | `62.732` | `62.757` | `62.781` |

### Container: `packed_astro_container_170` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_elev_max_shift_p7d` | `-42.074` | `-30.418` | `-27.735` |
| `Bits 2-3` | `>> 2` | `astro_mars_app_mag_max_shift_p7d` | `1.184` | `1.184` | `1.24` |
| `Bits 4-5` | `>> 4` | `astro_mars_surf_bright_max_shift_p7d` | `4.1303` | `4.19` | `4.223` |
| `Bits 6-7` | `>> 6` | `astro_mars_dist_max_shift_p7d` | `1.9841` | `2.0238` | `2.1375` |
| `Bits 8-9` | `>> 8` | `astro_mars_dist_rate_max_shift_p7d` | `-6.8449` | `-6.781` | `-6.7807` |
| `Bits 10-11` | `>> 10` | `astro_mars_helio_dist_max_shift_p7d` | `1.3822` | `1.3845` | `1.3989` |
| `Bits 12-13` | `>> 12` | `astro_mars_helio_dist_rate_max_shift_p7d` | `-1.045` | `-0.34749` | `-0.18645` |
| `Bits 14-15` | `>> 14` | `astro_mars_phase_angle_max_shift_p7d` | `23.207` | `27.592` | `28.489` |

### Container: `packed_astro_container_171` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_elong_max_shift_p7d` | `33.443` | `39.555` | `40.857` |
| `Bits 2-3` | `>> 2` | `astro_mars_illum_frac_max_shift_p7d` | `75.547` | `75.547` | `96.469` |
| `Bits 4-5` | `>> 4` | `astro_ceres_ra_icrf_max_shift_p7d` | `285.71` | `291.89` | `292.69` |
| `Bits 6-7` | `>> 6` | `astro_ceres_dec_icrf_max_shift_p7d` | `-24.231` | `-23.864` | `-23.285` |
| `Bits 8-9` | `>> 8` | `astro_ceres_ra_app_max_shift_p7d` | `286.07` | `292.26` | `293.06` |
| `Bits 10-11` | `>> 10` | `astro_ceres_dec_app_max_shift_p7d` | `-24.181` | `-23.818` | `-23.255` |
| `Bits 12-13` | `>> 12` | `astro_ceres_azim_max_shift_p7d` | `108.11` | `123.46` | `127.47` |
| `Bits 14-15` | `>> 14` | `astro_ceres_elev_max_shift_p7d` | `-15` | `-0.2174` | `2.9664` |

### Container: `packed_astro_container_172` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_ceres_app_mag_max_shift_p7d` | `8.516` | `8.6535` | `8.9347` |
| `Bits 2-3` | `>> 2` | `astro_ceres_surf_bright_max_shift_p7d` | `6.966` | `6.966` | `6.976` |
| `Bits 4-5` | `>> 4` | `astro_ceres_dist_max_shift_p7d` | `2.3711` | `2.5032` | `2.8859` |
| `Bits 6-7` | `>> 6` | `astro_ceres_dist_rate_max_shift_p7d` | `-21.901` | `-21.294` | `-21.294` |
| `Bits 8-9` | `>> 8` | `astro_ceres_helio_dist_max_shift_p7d` | `2.828` | `2.8503` | `2.8551` |
| `Bits 10-11` | `>> 10` | `astro_ceres_helio_dist_rate_max_shift_p7d` | `1.2602` | `1.2833` | `1.3399` |
| `Bits 12-13` | `>> 12` | `astro_ceres_phase_angle_max_shift_p7d` | `19.569` | `19.569` | `20.264` |
| `Bits 14-15` | `>> 14` | `astro_ceres_elong_max_shift_p7d` | `80.845` | `104.53` | `110.15` |

### Container: `packed_astro_container_173` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_ceres_illum_frac_max_shift_p7d` | `75.547` | `75.547` | `96.469` |
| `Bits 2-3` | `>> 2` | `astro_venus_ra_icrf_max_shift_p7d` | `29.818` | `29.818` | `327.73` |
| `Bits 4-5` | `>> 4` | `astro_venus_dec_icrf_max_shift_p7d` | `-6.4857` | `7.8563` | `10.856` |
| `Bits 6-7` | `>> 6` | `astro_venus_ra_app_max_shift_p7d` | `30.136` | `30.136` | `328.05` |
| `Bits 8-9` | `>> 8` | `astro_venus_dec_app_max_shift_p7d` | `-6.3569` | `7.9794` | `10.972` |
| `Bits 10-11` | `>> 10` | `astro_venus_azim_max_shift_p7d` | `27.233` | `31.395` | `45.911` |
| `Bits 12-13` | `>> 12` | `astro_venus_elev_max_shift_p7d` | `-45.885` | `-34.875` | `-32.459` |
| `Bits 14-15` | `>> 14` | `astro_venus_app_mag_max_shift_p7d` | `-3.884` | `-3.884` | `-3.8782` |

### Container: `packed_astro_container_174` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_surf_bright_max_shift_p7d` | `0.802` | `0.8275` | `0.91375` |
| `Bits 2-3` | `>> 2` | `astro_venus_dist_max_shift_p7d` | `1.6015` | `1.6871` | `1.7009` |
| `Bits 4-5` | `>> 4` | `astro_venus_dist_rate_max_shift_p7d` | `3.3543` | `4.1814` | `6.2821` |
| `Bits 6-7` | `>> 6` | `astro_venus_helio_dist_max_shift_p7d` | `0.72548` | `0.72663` | `0.72787` |
| `Bits 8-9` | `>> 8` | `astro_venus_helio_dist_rate_max_shift_p7d` | `-0.21161` | `-0.17166` | `0.0011154` |
| `Bits 10-11` | `>> 10` | `astro_venus_phase_angle_max_shift_p7d` | `13.729` | `17.486` | `27.827` |
| `Bits 12-13` | `>> 12` | `astro_venus_elong_max_shift_p7d` | `9.8437` | `12.556` | `19.957` |
| `Bits 14-15` | `>> 14` | `astro_venus_illum_frac_max_shift_p7d` | `75.547` | `75.547` | `96.469` |

### Container: `packed_astro_container_175` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_ra_icrf_mean_shift_p7d` | `33.856` | `37.406` | `125.43` |
| `Bits 2-3` | `>> 2` | `astro_sun_dec_icrf_mean_shift_p7d` | `0.89714` | `11.978` | `14.748` |
| `Bits 4-5` | `>> 4` | `astro_sun_ra_app_mean_shift_p7d` | `34.179` | `37.732` | `125.74` |
| `Bits 6-7` | `>> 6` | `astro_sun_dec_app_mean_shift_p7d` | `1.029` | `12.095` | `14.855` |
| `Bits 8-9` | `>> 8` | `astro_sun_azim_mean_shift_p7d` | `15.768` | `16.036` | `16.507` |
| `Bits 10-11` | `>> 10` | `astro_sun_elev_mean_shift_p7d` | `-44.994` | `-33.76` | `-30.986` |
| `Bits 12-13` | `>> 12` | `astro_sun_app_mag_mean_shift_p7d` | `-26.749` | `-26.731` | `-26.726` |
| `Bits 14-15` | `>> 14` | `astro_sun_dist_mean_shift_p7d` | `0.99663` | `1.005` | `1.0073` |

### Container: `packed_astro_container_176` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_dist_rate_mean_shift_p7d` | `0.37499` | `0.37499` | `0.39467` |
| `Bits 2-3` | `>> 2` | `astro_sun_illum_frac_mean_shift_p7d` | `65.438` | `65.438` | `77.36` |
| `Bits 4-5` | `>> 4` | `astro_moon_ra_icrf_mean_shift_p7d` | `160.12` | `294.15` | `294.15` |
| `Bits 6-7` | `>> 6` | `astro_moon_dec_icrf_mean_shift_p7d` | `-27.146` | `-21.59` | `8.5882` |
| `Bits 8-9` | `>> 8` | `astro_moon_ra_app_mean_shift_p7d` | `160.45` | `294.53` | `294.53` |
| `Bits 10-11` | `>> 10` | `astro_moon_dec_app_mean_shift_p7d` | `-27.093` | `-21.521` | `8.6282` |
| `Bits 12-13` | `>> 12` | `astro_moon_azim_mean_shift_p7d` | `127.76` | `127.76` | `227.5` |
| `Bits 14-15` | `>> 14` | `astro_moon_elev_mean_shift_p7d` | `-1.071` | `-1.071` | `24.092` |

### Container: `packed_astro_container_177` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_app_mag_mean_shift_p7d` | `-11.191` | `-10.749` | `-10.749` |
| `Bits 2-3` | `>> 2` | `astro_moon_surf_bright_mean_shift_p7d` | `4.5201` | `4.9013` | `4.9013` |
| `Bits 4-5` | `>> 4` | `astro_moon_dist_mean_shift_p7d` | `0.0025358` | `0.0025368` | `0.0026438` |
| `Bits 6-7` | `>> 6` | `astro_moon_dist_rate_mean_shift_p7d` | `-0.30191` | `-0.28471` | `0.085489` |
| `Bits 8-9` | `>> 8` | `astro_moon_helio_dist_mean_shift_p7d` | `0.99817` | `1.0066` | `1.0081` |
| `Bits 10-11` | `>> 10` | `astro_moon_helio_dist_rate_mean_shift_p7d` | `-0.45221` | `-0.2493` | `0.65312` |
| `Bits 12-13` | `>> 12` | `astro_moon_phase_angle_mean_shift_p7d` | `53.505` | `71.72` | `71.72` |
| `Bits 14-15` | `>> 14` | `astro_moon_elong_mean_shift_p7d` | `108.15` | `108.15` | `126.38` |

### Container: `packed_astro_container_178` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_illum_frac_mean_shift_p7d` | `65.438` | `65.438` | `77.36` |
| `Bits 2-3` | `>> 2` | `astro_saturn_ra_icrf_mean_shift_p7d` | `344.22` | `347.25` | `347.99` |
| `Bits 4-5` | `>> 4` | `astro_saturn_dec_icrf_mean_shift_p7d` | `-8.5086` | `-7.3304` | `-7.0446` |
| `Bits 6-7` | `>> 6` | `astro_saturn_ra_app_mean_shift_p7d` | `344.53` | `347.56` | `348.31` |
| `Bits 8-9` | `>> 8` | `astro_saturn_dec_app_mean_shift_p7d` | `-8.3819` | `-7.2009` | `-6.9143` |
| `Bits 10-11` | `>> 10` | `astro_saturn_azim_mean_shift_p7d` | `45.396` | `70.647` | `76.465` |
| `Bits 12-13` | `>> 12` | `astro_saturn_elev_mean_shift_p7d` | `-46.968` | `-29.66` | `-24.106` |
| `Bits 14-15` | `>> 14` | `astro_saturn_app_mag_mean_shift_p7d` | `1.0385` | `1.0723` | `1.0723` |

### Container: `packed_astro_container_179` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_surf_bright_mean_shift_p7d` | `6.7425` | `6.8319` | `6.8533` |
| `Bits 2-3` | `>> 2` | `astro_saturn_dist_mean_shift_p7d` | `10.267` | `10.374` | `10.643` |
| `Bits 4-5` | `>> 4` | `astro_saturn_dist_rate_mean_shift_p7d` | `-23.524` | `-21.051` | `-10.107` |
| `Bits 6-7` | `>> 6` | `astro_saturn_helio_dist_mean_shift_p7d` | `9.7035` | `9.7059` | `9.7145` |
| `Bits 8-9` | `>> 8` | `astro_saturn_helio_dist_rate_mean_shift_p7d` | `-0.50379` | `-0.50172` | `-0.49888` |
| `Bits 10-11` | `>> 10` | `astro_saturn_phase_angle_mean_shift_p7d` | `2.0171` | `4.2717` | `4.7918` |
| `Bits 12-13` | `>> 12` | `astro_saturn_elong_mean_shift_p7d` | `20.132` | `46.137` | `53.612` |
| `Bits 14-15` | `>> 14` | `astro_saturn_illum_frac_mean_shift_p7d` | `65.438` | `65.438` | `77.36` |

### Container: `packed_astro_container_180` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_ra_icrf_mean_shift_p7d` | `42.885` | `49.383` | `51.371` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_dec_icrf_mean_shift_p7d` | `15.55` | `17.408` | `17.924` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_ra_app_mean_shift_p7d` | `43.215` | `49.719` | `51.709` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_dec_app_mean_shift_p7d` | `15.649` | `17.496` | `18.008` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_azim_mean_shift_p7d` | `239.97` | `308.77` | `331.36` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_elev_mean_shift_p7d` | `-29.239` | `-29.239` | `-25.67` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_app_mag_mean_shift_p7d` | `-2.0908` | `-2.0191` | `-2.007` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_surf_bright_mean_shift_p7d` | `5.319` | `5.3222` | `5.3416` |

### Container: `packed_astro_container_181` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_dist_mean_shift_p7d` | `5.6859` | `5.9397` | `5.9837` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_dist_rate_mean_shift_p7d` | `7.244` | `10.109` | `19.353` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_helio_dist_mean_shift_p7d` | `5.0021` | `5.0091` | `5.0111` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_helio_dist_rate_mean_shift_p7d` | `0.3965` | `0.41878` | `0.42537` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_phase_angle_mean_shift_p7d` | `2.7447` | `3.9459` | `7.7768` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_elong_mean_shift_p7d` | `13.768` | `20.074` | `42.834` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_illum_frac_mean_shift_p7d` | `65.438` | `65.438` | `77.36` |
| `Bits 14-15` | `>> 14` | `astro_mars_ra_icrf_mean_shift_p7d` | `239.74` | `311.81` | `334.62` |

### Container: `packed_astro_container_182` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_dec_icrf_mean_shift_p7d` | `-12.751` | `-4.0958` | `-1.4936` |
| `Bits 2-3` | `>> 2` | `astro_mars_ra_app_mean_shift_p7d` | `120.05` | `312.15` | `334.94` |
| `Bits 4-5` | `>> 4` | `astro_mars_dec_app_mean_shift_p7d` | `-12.635` | `-3.964` | `-1.3604` |
| `Bits 6-7` | `>> 6` | `astro_mars_azim_mean_shift_p7d` | `62.708` | `62.746` | `62.751` |
| `Bits 8-9` | `>> 8` | `astro_mars_elev_mean_shift_p7d` | `-43.147` | `-31.646` | `-28.15` |
| `Bits 10-11` | `>> 10` | `astro_mars_app_mag_mean_shift_p7d` | `1.1783` | `1.1783` | `1.215` |
| `Bits 12-13` | `>> 12` | `astro_mars_surf_bright_mean_shift_p7d` | `4.1036` | `4.1802` | `4.2213` |
| `Bits 14-15` | `>> 14` | `astro_mars_dist_mean_shift_p7d` | `1.9804` | `2.0124` | `2.1259` |

### Container: `packed_astro_container_183` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_dist_rate_mean_shift_p7d` | `-6.8486` | `-6.7931` | `-6.7812` |
| `Bits 2-3` | `>> 2` | `astro_mars_helio_dist_mean_shift_p7d` | `1.382` | `1.3837` | `1.397` |
| `Bits 4-5` | `>> 4` | `astro_mars_helio_dist_rate_mean_shift_p7d` | `-1.1093` | `-0.42112` | `-0.21136` |
| `Bits 6-7` | `>> 6` | `astro_mars_phase_angle_mean_shift_p7d` | `22.738` | `27.171` | `28.353` |
| `Bits 8-9` | `>> 8` | `astro_mars_elong_mean_shift_p7d` | `32.803` | `38.952` | `40.657` |
| `Bits 10-11` | `>> 10` | `astro_mars_illum_frac_mean_shift_p7d` | `65.438` | `65.438` | `77.36` |
| `Bits 12-13` | `>> 12` | `astro_ceres_ra_icrf_mean_shift_p7d` | `284.87` | `291.44` | `292.59` |
| `Bits 14-15` | `>> 14` | `astro_ceres_dec_icrf_mean_shift_p7d` | `-24.273` | `-23.961` | `-23.326` |

### Container: `packed_astro_container_184` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_ceres_ra_app_mean_shift_p7d` | `285.24` | `291.81` | `292.95` |
| `Bits 2-3` | `>> 2` | `astro_ceres_dec_app_mean_shift_p7d` | `-24.223` | `-23.913` | `-23.294` |
| `Bits 4-5` | `>> 4` | `astro_ceres_azim_mean_shift_p7d` | `106.77` | `121.7` | `126.82` |
| `Bits 6-7` | `>> 6` | `astro_ceres_elev_mean_shift_p7d` | `-16.461` | `-1.7033` | `2.4822` |
| `Bits 8-9` | `>> 8` | `astro_ceres_app_mag_mean_shift_p7d` | `8.502` | `8.6156` | `8.9136` |
| `Bits 10-11` | `>> 10` | `astro_ceres_surf_bright_mean_shift_p7d` | `6.9607` | `6.963` | `6.9714` |
| `Bits 12-13` | `>> 12` | `astro_ceres_dist_mean_shift_p7d` | `2.3588` | `2.4651` | `2.8479` |
| `Bits 14-15` | `>> 14` | `astro_ceres_dist_rate_mean_shift_p7d` | `-22.127` | `-21.415` | `-21.415` |

### Container: `packed_astro_container_185` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_ceres_helio_dist_mean_shift_p7d` | `2.8257` | `2.8481` | `2.8544` |
| `Bits 2-3` | `>> 2` | `astro_ceres_helio_dist_rate_mean_shift_p7d` | `1.2579` | `1.2768` | `1.3348` |
| `Bits 4-5` | `>> 4` | `astro_ceres_phase_angle_mean_shift_p7d` | `19.461` | `19.461` | `20.075` |
| `Bits 6-7` | `>> 6` | `astro_ceres_elong_mean_shift_p7d` | `78.63` | `101.99` | `109.27` |
| `Bits 8-9` | `>> 8` | `astro_ceres_illum_frac_mean_shift_p7d` | `65.438` | `65.438` | `77.36` |
| `Bits 10-11` | `>> 10` | `astro_venus_ra_icrf_mean_shift_p7d` | `28.652` | `28.652` | `315.37` |
| `Bits 12-13` | `>> 12` | `astro_venus_dec_icrf_mean_shift_p7d` | `-7.8647` | `6.4351` | `10.406` |
| `Bits 14-15` | `>> 14` | `astro_venus_ra_app_mean_shift_p7d` | `28.969` | `28.969` | `315.7` |

### Container: `packed_astro_container_186` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_dec_app_mean_shift_p7d` | `-7.738` | `6.5608` | `10.523` |
| `Bits 2-3` | `>> 2` | `astro_venus_azim_mean_shift_p7d` | `26.853` | `30.184` | `44.21` |
| `Bits 4-5` | `>> 4` | `astro_venus_elev_mean_shift_p7d` | `-46.809` | `-36.017` | `-32.821` |
| `Bits 6-7` | `>> 6` | `astro_venus_app_mag_mean_shift_p7d` | `-3.8847` | `-3.8847` | `-3.8796` |
| `Bits 8-9` | `>> 8` | `astro_venus_surf_bright_mean_shift_p7d` | `0.79933` | `0.81986` | `0.90457` |
| `Bits 10-11` | `>> 10` | `astro_venus_dist_mean_shift_p7d` | `1.5907` | `1.6802` | `1.6989` |
| `Bits 12-13` | `>> 12` | `astro_venus_dist_rate_mean_shift_p7d` | `3.2708` | `3.9486` | `6.0924` |
| `Bits 14-15` | `>> 14` | `astro_venus_helio_dist_mean_shift_p7d` | `0.72535` | `0.72632` | `0.7277` |

### Container: `packed_astro_container_187` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_helio_dist_rate_mean_shift_p7d` | `-0.21439` | `-0.18414` | `-0.018345` |
| `Bits 2-3` | `>> 2` | `astro_venus_phase_angle_mean_shift_p7d` | `13.367` | `16.418` | `26.797` |
| `Bits 4-5` | `>> 4` | `astro_venus_elong_mean_shift_p7d` | `9.5822` | `11.785` | `19.23` |
| `Bits 6-7` | `>> 6` | `astro_venus_illum_frac_mean_shift_p7d` | `65.438` | `65.438` | `77.36` |
| `Bits 8-9` | `>> 8` | `astro_sun_ra_icrf_median_shift_p7d` | `27.758` | `37.406` | `37.406` |
| `Bits 10-11` | `>> 10` | `astro_sun_dec_icrf_median_shift_p7d` | `0.89807` | `11.985` | `14.75` |
| `Bits 12-13` | `>> 12` | `astro_sun_ra_app_median_shift_p7d` | `28.075` | `37.732` | `37.732` |
| `Bits 14-15` | `>> 14` | `astro_sun_dec_app_median_shift_p7d` | `1.03` | `12.101` | `14.856` |

### Container: `packed_astro_container_188` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_azim_median_shift_p7d` | `15.769` | `16.039` | `16.505` |
| `Bits 2-3` | `>> 2` | `astro_sun_elev_median_shift_p7d` | `-44.994` | `-33.753` | `-30.985` |
| `Bits 4-5` | `>> 4` | `astro_sun_app_mag_median_shift_p7d` | `-26.75` | `-26.731` | `-26.726` |
| `Bits 6-7` | `>> 6` | `astro_sun_dist_median_shift_p7d` | `0.99663` | `1.005` | `1.0073` |
| `Bits 8-9` | `>> 8` | `astro_sun_dist_rate_median_shift_p7d` | `0.37519` | `0.37519` | `0.39401` |
| `Bits 10-11` | `>> 10` | `astro_sun_illum_frac_median_shift_p7d` | `65.753` | `65.753` | `79.697` |
| `Bits 12-13` | `>> 12` | `astro_moon_ra_icrf_median_shift_p7d` | `160.83` | `294.27` | `294.27` |
| `Bits 14-15` | `>> 14` | `astro_moon_dec_icrf_median_shift_p7d` | `-27.678` | `-24.538` | `9.9146` |

### Container: `packed_astro_container_189` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_ra_app_median_shift_p7d` | `161.17` | `294.65` | `294.65` |
| `Bits 2-3` | `>> 2` | `astro_moon_dec_app_median_shift_p7d` | `-27.624` | `-24.457` | `9.801` |
| `Bits 4-5` | `>> 4` | `astro_moon_azim_median_shift_p7d` | `127.87` | `127.87` | `232.39` |
| `Bits 6-7` | `>> 6` | `astro_moon_elev_median_shift_p7d` | `-1.0911` | `-1.0911` | `25.39` |
| `Bits 8-9` | `>> 8` | `astro_moon_app_mag_median_shift_p7d` | `-11.226` | `-10.764` | `-10.764` |
| `Bits 10-11` | `>> 10` | `astro_moon_surf_bright_median_shift_p7d` | `4.5315` | `4.9` | `4.9` |
| `Bits 12-13` | `>> 12` | `astro_moon_dist_median_shift_p7d` | `0.0025358` | `0.0025368` | `0.0026488` |
| `Bits 14-15` | `>> 14` | `astro_moon_dist_rate_median_shift_p7d` | `-0.30627` | `-0.30543` | `0.10123` |

### Container: `packed_astro_container_190` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_helio_dist_median_shift_p7d` | `0.99825` | `1.0066` | `1.0081` |
| `Bits 2-3` | `>> 2` | `astro_moon_helio_dist_rate_median_shift_p7d` | `-0.46557` | `-0.31839` | `0.67157` |
| `Bits 4-5` | `>> 4` | `astro_moon_phase_angle_median_shift_p7d` | `53.246` | `71.638` | `71.638` |
| `Bits 6-7` | `>> 6` | `astro_moon_elong_median_shift_p7d` | `108.23` | `108.23` | `126.63` |
| `Bits 8-9` | `>> 8` | `astro_moon_illum_frac_median_shift_p7d` | `65.753` | `65.753` | `79.697` |
| `Bits 10-11` | `>> 10` | `astro_saturn_ra_icrf_median_shift_p7d` | `344.22` | `347.25` | `348` |
| `Bits 12-13` | `>> 12` | `astro_saturn_dec_icrf_median_shift_p7d` | `-8.5082` | `-7.3296` | `-7.0445` |
| `Bits 14-15` | `>> 14` | `astro_saturn_ra_app_median_shift_p7d` | `344.53` | `347.56` | `348.31` |

### Container: `packed_astro_container_191` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_dec_app_median_shift_p7d` | `-8.3816` | `-7.2001` | `-6.9142` |
| `Bits 2-3` | `>> 2` | `astro_saturn_azim_median_shift_p7d` | `45.43` | `70.66` | `76.466` |
| `Bits 4-5` | `>> 4` | `astro_saturn_elev_median_shift_p7d` | `-46.984` | `-29.666` | `-24.106` |
| `Bits 6-7` | `>> 6` | `astro_saturn_app_mag_median_shift_p7d` | `1.0385` | `1.072` | `1.072` |
| `Bits 8-9` | `>> 8` | `astro_saturn_surf_bright_median_shift_p7d` | `6.7428` | `6.832` | `6.853` |
| `Bits 10-11` | `>> 10` | `astro_saturn_dist_median_shift_p7d` | `10.267` | `10.374` | `10.643` |
| `Bits 12-13` | `>> 12` | `astro_saturn_dist_rate_median_shift_p7d` | `-23.526` | `-21.06` | `-10.112` |
| `Bits 14-15` | `>> 14` | `astro_saturn_helio_dist_median_shift_p7d` | `9.7035` | `9.7059` | `9.7145` |

### Container: `packed_astro_container_192` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_helio_dist_rate_median_shift_p7d` | `-0.50384` | `-0.50169` | `-0.49898` |
| `Bits 2-3` | `>> 2` | `astro_saturn_phase_angle_median_shift_p7d` | `2.0179` | `4.2736` | `4.7922` |
| `Bits 4-5` | `>> 4` | `astro_saturn_elong_median_shift_p7d` | `20.132` | `46.136` | `53.612` |
| `Bits 6-7` | `>> 6` | `astro_saturn_illum_frac_median_shift_p7d` | `65.753` | `65.753` | `79.697` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_ra_icrf_median_shift_p7d` | `42.882` | `49.382` | `51.371` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_dec_icrf_median_shift_p7d` | `15.55` | `17.409` | `17.924` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_ra_app_median_shift_p7d` | `43.212` | `49.718` | `51.709` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_dec_app_median_shift_p7d` | `15.649` | `17.497` | `18.008` |

### Container: `packed_astro_container_193` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_azim_median_shift_p7d` | `328.55` | `352.97` | `359.15` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_elev_median_shift_p7d` | `-29.242` | `-29.242` | `-25.685` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_app_mag_median_shift_p7d` | `-2.0905` | `-2.019` | `-2.007` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_surf_bright_median_shift_p7d` | `5.319` | `5.3225` | `5.3415` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_dist_median_shift_p7d` | `5.6863` | `5.9401` | `5.9838` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_dist_rate_median_shift_p7d` | `7.2451` | `10.11` | `19.357` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_helio_dist_median_shift_p7d` | `5.0021` | `5.0091` | `5.0111` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_helio_dist_rate_median_shift_p7d` | `0.39578` | `0.41792` | `0.425` |

### Container: `packed_astro_container_194` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_phase_angle_median_shift_p7d` | `2.7448` | `3.947` | `7.7793` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_elong_median_shift_p7d` | `13.767` | `20.072` | `42.83` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_illum_frac_median_shift_p7d` | `65.753` | `65.753` | `79.697` |
| `Bits 6-7` | `>> 6` | `astro_mars_ra_icrf_median_shift_p7d` | `332.01` | `353.7` | `359.03` |
| `Bits 8-9` | `>> 8` | `astro_mars_dec_icrf_median_shift_p7d` | `-12.755` | `-4.0966` | `-1.4936` |
| `Bits 10-11` | `>> 10` | `astro_mars_ra_app_median_shift_p7d` | `0.75284` | `312.15` | `334.94` |
| `Bits 12-13` | `>> 12` | `astro_mars_dec_app_median_shift_p7d` | `-12.639` | `-3.9648` | `-1.3604` |
| `Bits 14-15` | `>> 14` | `astro_mars_azim_median_shift_p7d` | `62.707` | `62.746` | `62.75` |

### Container: `packed_astro_container_195` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_elev_median_shift_p7d` | `-43.152` | `-31.648` | `-28.15` |
| `Bits 2-3` | `>> 2` | `astro_mars_app_mag_median_shift_p7d` | `1.179` | `1.179` | `1.212` |
| `Bits 4-5` | `>> 4` | `astro_mars_surf_bright_median_shift_p7d` | `4.1007` | `4.1815` | `4.222` |
| `Bits 6-7` | `>> 6` | `astro_mars_dist_median_shift_p7d` | `1.9804` | `2.0124` | `2.1259` |
| `Bits 8-9` | `>> 8` | `astro_mars_dist_rate_median_shift_p7d` | `-6.8484` | `-6.7931` | `-6.7809` |
| `Bits 10-11` | `>> 10` | `astro_mars_helio_dist_median_shift_p7d` | `1.382` | `1.3837` | `1.3969` |
| `Bits 12-13` | `>> 12` | `astro_mars_helio_dist_rate_median_shift_p7d` | `-1.1096` | `-0.42124` | `-0.21137` |
| `Bits 14-15` | `>> 14` | `astro_mars_phase_angle_median_shift_p7d` | `22.739` | `27.172` | `28.353` |

### Container: `packed_astro_container_196` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_elong_median_shift_p7d` | `32.804` | `38.953` | `40.657` |
| `Bits 2-3` | `>> 2` | `astro_mars_illum_frac_median_shift_p7d` | `65.753` | `65.753` | `79.697` |
| `Bits 4-5` | `>> 4` | `astro_ceres_ra_icrf_median_shift_p7d` | `284.88` | `291.46` | `292.59` |
| `Bits 6-7` | `>> 6` | `astro_ceres_dec_icrf_median_shift_p7d` | `-24.273` | `-23.959` | `-23.326` |
| `Bits 8-9` | `>> 8` | `astro_ceres_ra_app_median_shift_p7d` | `285.24` | `291.82` | `292.96` |
| `Bits 10-11` | `>> 10` | `astro_ceres_dec_app_median_shift_p7d` | `-24.223` | `-23.911` | `-23.293` |
| `Bits 12-13` | `>> 12` | `astro_ceres_azim_median_shift_p7d` | `106.77` | `121.69` | `126.82` |
| `Bits 14-15` | `>> 14` | `astro_ceres_elev_median_shift_p7d` | `-16.463` | `-1.7014` | `2.4829` |

### Container: `packed_astro_container_197` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_ceres_app_mag_median_shift_p7d` | `8.502` | `8.616` | `8.9138` |
| `Bits 2-3` | `>> 2` | `astro_ceres_surf_bright_median_shift_p7d` | `6.9607` | `6.963` | `6.9713` |
| `Bits 4-5` | `>> 4` | `astro_ceres_dist_median_shift_p7d` | `2.3588` | `2.465` | `2.8479` |
| `Bits 6-7` | `>> 6` | `astro_ceres_dist_rate_median_shift_p7d` | `-22.134` | `-21.417` | `-21.417` |
| `Bits 8-9` | `>> 8` | `astro_ceres_helio_dist_median_shift_p7d` | `2.8257` | `2.8481` | `2.8544` |
| `Bits 10-11` | `>> 10` | `astro_ceres_helio_dist_rate_median_shift_p7d` | `1.2579` | `1.2768` | `1.3349` |
| `Bits 12-13` | `>> 12` | `astro_ceres_phase_angle_median_shift_p7d` | `19.463` | `19.463` | `20.082` |
| `Bits 14-15` | `>> 14` | `astro_ceres_elong_median_shift_p7d` | `78.625` | `101.98` | `109.27` |

### Container: `packed_astro_container_198` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_ceres_illum_frac_median_shift_p7d` | `65.753` | `65.753` | `79.697` |
| `Bits 2-3` | `>> 2` | `astro_venus_ra_icrf_median_shift_p7d` | `28.651` | `28.651` | `324.07` |
| `Bits 4-5` | `>> 4` | `astro_venus_dec_icrf_median_shift_p7d` | `-7.8719` | `6.4396` | `10.407` |
| `Bits 6-7` | `>> 6` | `astro_venus_ra_app_median_shift_p7d` | `28.967` | `28.967` | `324.4` |
| `Bits 8-9` | `>> 8` | `astro_venus_dec_app_median_shift_p7d` | `-7.745` | `6.5654` | `10.524` |
| `Bits 10-11` | `>> 10` | `astro_venus_azim_median_shift_p7d` | `26.853` | `30.177` | `44.197` |
| `Bits 12-13` | `>> 12` | `astro_venus_elev_median_shift_p7d` | `-46.823` | `-36.014` | `-32.82` |
| `Bits 14-15` | `>> 14` | `astro_venus_app_mag_median_shift_p7d` | `-3.885` | `-3.885` | `-3.8795` |

### Container: `packed_astro_container_199` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_surf_bright_median_shift_p7d` | `0.799` | `0.82` | `0.9045` |
| `Bits 2-3` | `>> 2` | `astro_venus_dist_median_shift_p7d` | `1.5908` | `1.6803` | `1.699` |
| `Bits 4-5` | `>> 4` | `astro_venus_dist_rate_median_shift_p7d` | `3.2711` | `3.9495` | `6.0931` |
| `Bits 6-7` | `>> 6` | `astro_venus_helio_dist_median_shift_p7d` | `0.72535` | `0.72633` | `0.72771` |
| `Bits 8-9` | `>> 8` | `astro_venus_helio_dist_rate_median_shift_p7d` | `-0.21445` | `-0.18443` | `-0.018372` |
| `Bits 10-11` | `>> 10` | `astro_venus_phase_angle_median_shift_p7d` | `13.367` | `16.419` | `26.798` |
| `Bits 12-13` | `>> 12` | `astro_venus_elong_median_shift_p7d` | `9.5824` | `11.786` | `19.231` |
| `Bits 14-15` | `>> 14` | `astro_venus_illum_frac_median_shift_p7d` | `65.753` | `65.753` | `79.697` |

### Container: `packed_astro_container_200` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_ra_icrf_min_shift_p14d` | `36.454` | `36.454` | `36.454` |
| `Bits 2-3` | `>> 2` | `astro_sun_dec_icrf_min_shift_p14d` | `14.441` | `14.441` | `14.441` |
| `Bits 4-5` | `>> 4` | `astro_sun_ra_app_min_shift_p14d` | `36.779` | `36.779` | `36.779` |
| `Bits 6-7` | `>> 6` | `astro_sun_dec_app_min_shift_p14d` | `14.549` | `14.549` | `14.549` |
| `Bits 8-9` | `>> 8` | `astro_sun_azim_min_shift_p14d` | `15.729` | `15.729` | `15.729` |
| `Bits 10-11` | `>> 10` | `astro_sun_elev_min_shift_p14d` | `-31.292` | `-31.292` | `-31.292` |
| `Bits 12-13` | `>> 12` | `astro_sun_app_mag_min_shift_p14d` | `-26.727` | `-26.727` | `-26.727` |
| `Bits 14-15` | `>> 14` | `astro_sun_dist_min_shift_p14d` | `1.007` | `1.007` | `1.007` |

### Container: `packed_astro_container_201` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_dist_rate_min_shift_p14d` | `0.37185` | `0.37185` | `0.37185` |
| `Bits 2-3` | `>> 2` | `astro_sun_illum_frac_min_shift_p14d` | `55.013` | `55.013` | `55.013` |
| `Bits 4-5` | `>> 4` | `astro_moon_ra_icrf_min_shift_p14d` | `279.17` | `279.17` | `279.17` |
| `Bits 6-7` | `>> 6` | `astro_moon_dec_icrf_min_shift_p14d` | `-29.197` | `-29.197` | `-29.197` |
| `Bits 8-9` | `>> 8` | `astro_moon_ra_app_min_shift_p14d` | `279.56` | `279.56` | `279.56` |
| `Bits 10-11` | `>> 10` | `astro_moon_dec_app_min_shift_p14d` | `-29.176` | `-29.176` | `-29.176` |
| `Bits 12-13` | `>> 12` | `astro_moon_azim_min_shift_p14d` | `116.74` | `116.74` | `116.74` |
| `Bits 14-15` | `>> 14` | `astro_moon_elev_min_shift_p14d` | `-7.3342` | `-7.3342` | `-7.3342` |

### Container: `packed_astro_container_202` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_app_mag_min_shift_p14d` | `-11.123` | `-11.123` | `-11.123` |
| `Bits 2-3` | `>> 2` | `astro_moon_surf_bright_min_shift_p14d` | `4.674` | `4.674` | `4.674` |
| `Bits 4-5` | `>> 4` | `astro_moon_dist_min_shift_p14d` | `0.0025145` | `0.0025155` | `0.0025165` |
| `Bits 6-7` | `>> 6` | `astro_moon_dist_rate_min_shift_p14d` | `-0.33895` | `-0.33895` | `-0.33895` |
| `Bits 8-9` | `>> 8` | `astro_moon_helio_dist_min_shift_p14d` | `1.0078` | `1.0078` | `1.0078` |
| `Bits 10-11` | `>> 10` | `astro_moon_helio_dist_rate_min_shift_p14d` | `-0.51557` | `-0.51556` | `-0.51556` |
| `Bits 12-13` | `>> 12` | `astro_moon_phase_angle_min_shift_p14d` | `59.276` | `59.276` | `59.276` |
| `Bits 14-15` | `>> 14` | `astro_moon_elong_min_shift_p14d` | `95.611` | `95.611` | `95.611` |

### Container: `packed_astro_container_203` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_illum_frac_min_shift_p14d` | `55.013` | `55.013` | `55.013` |
| `Bits 2-3` | `>> 2` | `astro_saturn_ra_icrf_min_shift_p14d` | `347.91` | `347.91` | `347.91` |
| `Bits 4-5` | `>> 4` | `astro_saturn_dec_icrf_min_shift_p14d` | `-7.0762` | `-7.0762` | `-7.0762` |
| `Bits 6-7` | `>> 6` | `astro_saturn_ra_app_min_shift_p14d` | `348.22` | `348.22` | `348.22` |
| `Bits 8-9` | `>> 8` | `astro_saturn_dec_app_min_shift_p14d` | `-6.946` | `-6.946` | `-6.946` |
| `Bits 10-11` | `>> 10` | `astro_saturn_azim_min_shift_p14d` | `75.807` | `75.807` | `75.807` |
| `Bits 12-13` | `>> 12` | `astro_saturn_elev_min_shift_p14d` | `-24.771` | `-24.771` | `-24.771` |
| `Bits 14-15` | `>> 14` | `astro_saturn_app_mag_min_shift_p14d` | `1.072` | `1.072` | `1.072` |

### Container: `packed_astro_container_204` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_surf_bright_min_shift_p14d` | `6.851` | `6.851` | `6.851` |
| `Bits 2-3` | `>> 2` | `astro_saturn_dist_min_shift_p14d` | `10.254` | `10.254` | `10.254` |
| `Bits 4-5` | `>> 4` | `astro_saturn_dist_rate_min_shift_p14d` | `-23.79` | `-23.79` | `-23.79` |
| `Bits 6-7` | `>> 6` | `astro_saturn_helio_dist_min_shift_p14d` | `9.7032` | `9.7032` | `9.7032` |
| `Bits 8-9` | `>> 8` | `astro_saturn_helio_dist_rate_min_shift_p14d` | `-0.50417` | `-0.50417` | `-0.50417` |
| `Bits 10-11` | `>> 10` | `astro_saturn_phase_angle_min_shift_p14d` | `4.7357` | `4.7357` | `4.7357` |
| `Bits 12-13` | `>> 12` | `astro_saturn_elong_min_shift_p14d` | `52.73` | `52.73` | `52.73` |
| `Bits 14-15` | `>> 14` | `astro_saturn_illum_frac_min_shift_p14d` | `55.013` | `55.013` | `55.013` |

### Container: `packed_astro_container_205` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_ra_icrf_min_shift_p14d` | `51.134` | `51.134` | `51.134` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_dec_icrf_min_shift_p14d` | `17.864` | `17.864` | `17.864` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_ra_app_min_shift_p14d` | `51.472` | `51.472` | `51.472` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_dec_app_min_shift_p14d` | `17.949` | `17.949` | `17.949` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_azim_min_shift_p14d` | `0.78204` | `0.78204` | `0.78204` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_elev_min_shift_p14d` | `-29.297` | `-29.297` | `-29.297` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_app_mag_min_shift_p14d` | `-2.008` | `-2.008` | `-2.008` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_surf_bright_min_shift_p14d` | `5.319` | `5.319` | `5.319` |

### Container: `packed_astro_container_206` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_dist_min_shift_p14d` | `5.9795` | `5.9795` | `5.9795` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_dist_rate_min_shift_p14d` | `6.9007` | `6.9007` | `6.9007` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_helio_dist_min_shift_p14d` | `5.0109` | `5.0109` | `5.0109` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_helio_dist_rate_min_shift_p14d` | `0.42497` | `0.42497` | `0.42497` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_phase_angle_min_shift_p14d` | `2.6012` | `2.6012` | `2.6012` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_elong_min_shift_p14d` | `13.031` | `13.031` | `13.031` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_illum_frac_min_shift_p14d` | `55.013` | `55.013` | `55.013` |
| `Bits 14-15` | `>> 14` | `astro_mars_ra_icrf_min_shift_p14d` | `0.44647` | `0.44647` | `0.44647` |

### Container: `packed_astro_container_207` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_dec_icrf_min_shift_p14d` | `-1.8007` | `-1.8007` | `-1.8007` |
| `Bits 2-3` | `>> 2` | `astro_mars_ra_app_min_shift_p14d` | `0.04581` | `0.045811` | `0.045812` |
| `Bits 4-5` | `>> 4` | `astro_mars_dec_app_min_shift_p14d` | `-1.6676` | `-1.6676` | `-1.6676` |
| `Bits 6-7` | `>> 6` | `astro_mars_azim_min_shift_p14d` | `62.734` | `62.734` | `62.734` |
| `Bits 8-9` | `>> 8` | `astro_mars_elev_min_shift_p14d` | `-28.564` | `-28.564` | `-28.564` |
| `Bits 10-11` | `>> 10` | `astro_mars_app_mag_min_shift_p14d` | `1.172` | `1.172` | `1.172` |
| `Bits 12-13` | `>> 12` | `astro_mars_surf_bright_min_shift_p14d` | `4.219` | `4.219` | `4.219` |
| `Bits 14-15` | `>> 14` | `astro_mars_dist_min_shift_p14d` | `1.9766` | `1.9766` | `1.9766` |

### Container: `packed_astro_container_208` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_dist_rate_min_shift_p14d` | `-6.782` | `-6.782` | `-6.782` |
| `Bits 2-3` | `>> 2` | `astro_mars_helio_dist_min_shift_p14d` | `1.3819` | `1.3819` | `1.3819` |
| `Bits 4-5` | `>> 4` | `astro_mars_helio_dist_rate_min_shift_p14d` | `-0.23626` | `-0.23626` | `-0.23625` |
| `Bits 6-7` | `>> 6` | `astro_mars_phase_angle_min_shift_p14d` | `28.216` | `28.216` | `28.216` |
| `Bits 8-9` | `>> 8` | `astro_mars_elong_min_shift_p14d` | `40.457` | `40.457` | `40.457` |
| `Bits 10-11` | `>> 10` | `astro_mars_illum_frac_min_shift_p14d` | `55.013` | `55.013` | `55.013` |
| `Bits 12-13` | `>> 12` | `astro_ceres_ra_icrf_min_shift_p14d` | `292.48` | `292.48` | `292.48` |
| `Bits 14-15` | `>> 14` | `astro_ceres_dec_icrf_min_shift_p14d` | `-24.316` | `-24.316` | `-24.316` |

### Container: `packed_astro_container_209` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_ceres_ra_app_min_shift_p14d` | `292.85` | `292.85` | `292.85` |
| `Bits 2-3` | `>> 2` | `astro_ceres_dec_app_min_shift_p14d` | `-24.266` | `-24.266` | `-24.266` |
| `Bits 4-5` | `>> 4` | `astro_ceres_azim_min_shift_p14d` | `126.18` | `126.18` | `126.18` |
| `Bits 6-7` | `>> 6` | `astro_ceres_elev_min_shift_p14d` | `1.9973` | `1.9973` | `1.9973` |
| `Bits 8-9` | `>> 8` | `astro_ceres_app_mag_min_shift_p14d` | `8.488` | `8.488` | `8.488` |
| `Bits 10-11` | `>> 10` | `astro_ceres_surf_bright_min_shift_p14d` | `6.96` | `6.96` | `6.96` |
| `Bits 12-13` | `>> 12` | `astro_ceres_dist_min_shift_p14d` | `2.3466` | `2.3466` | `2.3466` |
| `Bits 14-15` | `>> 14` | `astro_ceres_dist_rate_min_shift_p14d` | `-21.535` | `-21.535` | `-21.535` |

### Container: `packed_astro_container_210` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_ceres_helio_dist_min_shift_p14d` | `2.8536` | `2.8536` | `2.8536` |
| `Bits 2-3` | `>> 2` | `astro_ceres_helio_dist_rate_min_shift_p14d` | `1.2556` | `1.2556` | `1.2556` |
| `Bits 4-5` | `>> 4` | `astro_ceres_phase_angle_min_shift_p14d` | `19.352` | `19.352` | `19.352` |
| `Bits 6-7` | `>> 6` | `astro_ceres_elong_min_shift_p14d` | `108.39` | `108.39` | `108.39` |
| `Bits 8-9` | `>> 8` | `astro_ceres_illum_frac_min_shift_p14d` | `55.013` | `55.013` | `55.013` |
| `Bits 10-11` | `>> 10` | `astro_venus_ra_icrf_min_shift_p14d` | `27.487` | `27.487` | `27.487` |
| `Bits 12-13` | `>> 12` | `astro_venus_dec_icrf_min_shift_p14d` | `9.9542` | `9.9542` | `9.9542` |
| `Bits 14-15` | `>> 14` | `astro_venus_ra_app_min_shift_p14d` | `27.802` | `27.802` | `27.802` |

### Container: `packed_astro_container_211` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_dec_app_min_shift_p14d` | `10.073` | `10.073` | `10.073` |
| `Bits 2-3` | `>> 2` | `astro_venus_azim_min_shift_p14d` | `26.474` | `26.474` | `26.474` |
| `Bits 4-5` | `>> 4` | `astro_venus_elev_min_shift_p14d` | `-33.185` | `-33.185` | `-33.185` |
| `Bits 6-7` | `>> 6` | `astro_venus_app_mag_min_shift_p14d` | `-3.885` | `-3.885` | `-3.885` |
| `Bits 8-9` | `>> 8` | `astro_venus_surf_bright_min_shift_p14d` | `0.797` | `0.797` | `0.797` |
| `Bits 10-11` | `>> 10` | `astro_venus_dist_min_shift_p14d` | `1.697` | `1.697` | `1.697` |
| `Bits 12-13` | `>> 12` | `astro_venus_dist_rate_min_shift_p14d` | `3.187` | `3.187` | `3.187` |
| `Bits 14-15` | `>> 14` | `astro_venus_helio_dist_min_shift_p14d` | `0.72523` | `0.72523` | `0.72523` |

### Container: `packed_astro_container_212` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_helio_dist_rate_min_shift_p14d` | `-0.21712` | `-0.21712` | `-0.21712` |
| `Bits 2-3` | `>> 2` | `astro_venus_phase_angle_min_shift_p14d` | `13.005` | `13.005` | `13.005` |
| `Bits 4-5` | `>> 4` | `astro_venus_elong_min_shift_p14d` | `9.3206` | `9.3206` | `9.3206` |
| `Bits 6-7` | `>> 6` | `astro_venus_illum_frac_min_shift_p14d` | `55.013` | `55.013` | `55.013` |
| `Bits 8-9` | `>> 8` | `astro_sun_ra_icrf_max_shift_p14d` | `38.36` | `38.36` | `38.36` |
| `Bits 10-11` | `>> 10` | `astro_sun_dec_icrf_max_shift_p14d` | `15.055` | `15.055` | `15.055` |
| `Bits 12-13` | `>> 12` | `astro_sun_ra_app_max_shift_p14d` | `38.686` | `38.686` | `38.686` |
| `Bits 14-15` | `>> 14` | `astro_sun_dec_app_max_shift_p14d` | `15.16` | `15.16` | `15.16` |

### Container: `packed_astro_container_213` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_azim_max_shift_p14d` | `15.806` | `15.806` | `15.806` |
| `Bits 2-3` | `>> 2` | `astro_sun_elev_max_shift_p14d` | `-30.681` | `-30.681` | `-30.681` |
| `Bits 4-5` | `>> 4` | `astro_sun_app_mag_max_shift_p14d` | `-26.726` | `-26.726` | `-26.726` |
| `Bits 6-7` | `>> 6` | `astro_sun_dist_max_shift_p14d` | `1.0076` | `1.0076` | `1.0076` |
| `Bits 8-9` | `>> 8` | `astro_sun_dist_rate_max_shift_p14d` | `0.37793` | `0.37793` | `0.37793` |
| `Bits 10-11` | `>> 10` | `astro_sun_illum_frac_max_shift_p14d` | `75.547` | `75.547` | `75.547` |
| `Bits 12-13` | `>> 12` | `astro_moon_ra_icrf_max_shift_p14d` | `309.02` | `309.02` | `309.02` |
| `Bits 14-15` | `>> 14` | `astro_moon_dec_icrf_max_shift_p14d` | `-24.563` | `-24.563` | `-24.563` |

### Container: `packed_astro_container_214` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_ra_app_max_shift_p14d` | `309.38` | `309.38` | `309.38` |
| `Bits 2-3` | `>> 2` | `astro_moon_dec_app_max_shift_p14d` | `-24.479` | `-24.479` | `-24.479` |
| `Bits 4-5` | `>> 4` | `astro_moon_azim_max_shift_p14d` | `138.67` | `138.67` | `138.67` |
| `Bits 6-7` | `>> 6` | `astro_moon_elev_max_shift_p14d` | `5.2124` | `5.2124` | `5.2124` |
| `Bits 8-9` | `>> 8` | `astro_moon_app_mag_max_shift_p14d` | `-10.359` | `-10.359` | `-10.359` |
| `Bits 10-11` | `>> 10` | `astro_moon_surf_bright_max_shift_p14d` | `5.13` | `5.13` | `5.13` |
| `Bits 12-13` | `>> 12` | `astro_moon_dist_max_shift_p14d` | `0.002557` | `0.002558` | `0.002559` |
| `Bits 14-15` | `>> 14` | `astro_moon_dist_rate_max_shift_p14d` | `-0.26051` | `-0.26051` | `-0.26051` |

### Container: `packed_astro_container_215` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_helio_dist_max_shift_p14d` | `1.0083` | `1.0083` | `1.0083` |
| `Bits 2-3` | `>> 2` | `astro_moon_helio_dist_rate_max_shift_p14d` | `-0.37549` | `-0.37549` | `-0.37549` |
| `Bits 4-5` | `>> 4` | `astro_moon_phase_angle_max_shift_p14d` | `84.246` | `84.246` | `84.246` |
| `Bits 6-7` | `>> 6` | `astro_moon_elong_max_shift_p14d` | `120.6` | `120.6` | `120.6` |
| `Bits 8-9` | `>> 8` | `astro_moon_illum_frac_max_shift_p14d` | `75.547` | `75.547` | `75.547` |
| `Bits 10-11` | `>> 10` | `astro_saturn_ra_icrf_max_shift_p14d` | `348.08` | `348.08` | `348.08` |
| `Bits 12-13` | `>> 12` | `astro_saturn_dec_icrf_max_shift_p14d` | `-7.0132` | `-7.0132` | `-7.0132` |
| `Bits 14-15` | `>> 14` | `astro_saturn_ra_app_max_shift_p14d` | `348.39` | `348.39` | `348.39` |

### Container: `packed_astro_container_216` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_dec_app_max_shift_p14d` | `-6.8828` | `-6.8828` | `-6.8828` |
| `Bits 2-3` | `>> 2` | `astro_saturn_azim_max_shift_p14d` | `77.121` | `77.121` | `77.121` |
| `Bits 4-5` | `>> 4` | `astro_saturn_elev_max_shift_p14d` | `-23.439` | `-23.439` | `-23.439` |
| `Bits 6-7` | `>> 6` | `astro_saturn_app_mag_max_shift_p14d` | `1.073` | `1.073` | `1.073` |
| `Bits 8-9` | `>> 8` | `astro_saturn_surf_bright_max_shift_p14d` | `6.856` | `6.856` | `6.856` |
| `Bits 10-11` | `>> 10` | `astro_saturn_dist_max_shift_p14d` | `10.28` | `10.28` | `10.28` |
| `Bits 12-13` | `>> 12` | `astro_saturn_dist_rate_max_shift_p14d` | `-23.256` | `-23.256` | `-23.256` |
| `Bits 14-15` | `>> 14` | `astro_saturn_helio_dist_max_shift_p14d` | `9.7037` | `9.7037` | `9.7038` |

### Container: `packed_astro_container_217` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_helio_dist_rate_max_shift_p14d` | `-0.50336` | `-0.50336` | `-0.50336` |
| `Bits 2-3` | `>> 2` | `astro_saturn_phase_angle_max_shift_p14d` | `4.8476` | `4.8476` | `4.8476` |
| `Bits 4-5` | `>> 4` | `astro_saturn_elong_max_shift_p14d` | `54.494` | `54.494` | `54.494` |
| `Bits 6-7` | `>> 6` | `astro_saturn_illum_frac_max_shift_p14d` | `75.547` | `75.547` | `75.547` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_ra_icrf_max_shift_p14d` | `51.608` | `51.608` | `51.608` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_dec_icrf_max_shift_p14d` | `17.983` | `17.983` | `17.983` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_ra_app_max_shift_p14d` | `51.946` | `51.946` | `51.946` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_dec_app_max_shift_p14d` | `18.067` | `18.067` | `18.067` |

### Container: `packed_astro_container_218` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_azim_max_shift_p14d` | `359.97` | `359.97` | `359.97` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_elev_max_shift_p14d` | `-29.179` | `-29.179` | `-29.179` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_app_mag_max_shift_p14d` | `-2.006` | `-2.006` | `-2.006` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_surf_bright_max_shift_p14d` | `5.319` | `5.319` | `5.319` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_dist_max_shift_p14d` | `5.9879` | `5.9879` | `5.9879` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_dist_rate_max_shift_p14d` | `7.5862` | `7.5862` | `7.5862` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_helio_dist_max_shift_p14d` | `5.0114` | `5.0114` | `5.0114` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_helio_dist_rate_max_shift_p14d` | `0.42614` | `0.42614` | `0.42614` |

### Container: `packed_astro_container_219` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_phase_angle_max_shift_p14d` | `2.8881` | `2.8881` | `2.8881` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_elong_max_shift_p14d` | `14.505` | `14.505` | `14.505` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_illum_frac_max_shift_p14d` | `75.547` | `75.547` | `75.547` |
| `Bits 6-7` | `>> 6` | `astro_mars_ra_icrf_max_shift_p14d` | `359.74` | `359.74` | `359.74` |
| `Bits 8-9` | `>> 8` | `astro_mars_dec_icrf_max_shift_p14d` | `-1.1864` | `-1.1864` | `-1.1864` |
| `Bits 10-11` | `>> 10` | `astro_mars_ra_app_max_shift_p14d` | `359.34` | `359.34` | `359.34` |
| `Bits 12-13` | `>> 12` | `astro_mars_dec_app_max_shift_p14d` | `-1.0532` | `-1.0532` | `-1.0532` |
| `Bits 14-15` | `>> 14` | `astro_mars_azim_max_shift_p14d` | `62.757` | `62.757` | `62.757` |

### Container: `packed_astro_container_220` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_elev_max_shift_p14d` | `-27.735` | `-27.735` | `-27.735` |
| `Bits 2-3` | `>> 2` | `astro_mars_app_mag_max_shift_p14d` | `1.184` | `1.184` | `1.184` |
| `Bits 4-5` | `>> 4` | `astro_mars_surf_bright_max_shift_p14d` | `4.223` | `4.223` | `4.223` |
| `Bits 6-7` | `>> 6` | `astro_mars_dist_max_shift_p14d` | `1.9841` | `1.9841` | `1.9841` |
| `Bits 8-9` | `>> 8` | `astro_mars_dist_rate_max_shift_p14d` | `-6.7807` | `-6.7807` | `-6.7807` |
| `Bits 10-11` | `>> 10` | `astro_mars_helio_dist_max_shift_p14d` | `1.3822` | `1.3822` | `1.3822` |
| `Bits 12-13` | `>> 12` | `astro_mars_helio_dist_rate_max_shift_p14d` | `-0.18645` | `-0.18645` | `-0.18644` |
| `Bits 14-15` | `>> 14` | `astro_mars_phase_angle_max_shift_p14d` | `28.489` | `28.489` | `28.489` |

### Container: `packed_astro_container_221` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_elong_max_shift_p14d` | `40.857` | `40.857` | `40.857` |
| `Bits 2-3` | `>> 2` | `astro_mars_illum_frac_max_shift_p14d` | `75.547` | `75.547` | `75.547` |
| `Bits 4-5` | `>> 4` | `astro_ceres_ra_icrf_max_shift_p14d` | `292.69` | `292.69` | `292.69` |
| `Bits 6-7` | `>> 6` | `astro_ceres_dec_icrf_max_shift_p14d` | `-24.231` | `-24.231` | `-24.231` |
| `Bits 8-9` | `>> 8` | `astro_ceres_ra_app_max_shift_p14d` | `293.06` | `293.06` | `293.06` |
| `Bits 10-11` | `>> 10` | `astro_ceres_dec_app_max_shift_p14d` | `-24.181` | `-24.181` | `-24.181` |
| `Bits 12-13` | `>> 12` | `astro_ceres_azim_max_shift_p14d` | `127.47` | `127.47` | `127.47` |
| `Bits 14-15` | `>> 14` | `astro_ceres_elev_max_shift_p14d` | `2.9664` | `2.9664` | `2.9664` |

### Container: `packed_astro_container_222` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_ceres_app_mag_max_shift_p14d` | `8.516` | `8.516` | `8.516` |
| `Bits 2-3` | `>> 2` | `astro_ceres_surf_bright_max_shift_p14d` | `6.966` | `6.966` | `6.966` |
| `Bits 4-5` | `>> 4` | `astro_ceres_dist_max_shift_p14d` | `2.3711` | `2.3711` | `2.3711` |
| `Bits 6-7` | `>> 6` | `astro_ceres_dist_rate_max_shift_p14d` | `-21.294` | `-21.294` | `-21.294` |
| `Bits 8-9` | `>> 8` | `astro_ceres_helio_dist_max_shift_p14d` | `2.8551` | `2.8551` | `2.8551` |
| `Bits 10-11` | `>> 10` | `astro_ceres_helio_dist_rate_max_shift_p14d` | `1.2602` | `1.2602` | `1.2602` |
| `Bits 12-13` | `>> 12` | `astro_ceres_phase_angle_max_shift_p14d` | `19.569` | `19.569` | `19.569` |
| `Bits 14-15` | `>> 14` | `astro_ceres_elong_max_shift_p14d` | `110.15` | `110.15` | `110.15` |

### Container: `packed_astro_container_223` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_ceres_illum_frac_max_shift_p14d` | `75.547` | `75.547` | `75.547` |
| `Bits 2-3` | `>> 2` | `astro_venus_ra_icrf_max_shift_p14d` | `29.818` | `29.818` | `29.818` |
| `Bits 4-5` | `>> 4` | `astro_venus_dec_icrf_max_shift_p14d` | `10.856` | `10.856` | `10.856` |
| `Bits 6-7` | `>> 6` | `astro_venus_ra_app_max_shift_p14d` | `30.136` | `30.136` | `30.136` |
| `Bits 8-9` | `>> 8` | `astro_venus_dec_app_max_shift_p14d` | `10.972` | `10.972` | `10.972` |
| `Bits 10-11` | `>> 10` | `astro_venus_azim_max_shift_p14d` | `27.233` | `27.233` | `27.233` |
| `Bits 12-13` | `>> 12` | `astro_venus_elev_max_shift_p14d` | `-32.459` | `-32.459` | `-32.459` |
| `Bits 14-15` | `>> 14` | `astro_venus_app_mag_max_shift_p14d` | `-3.884` | `-3.884` | `-3.884` |

### Container: `packed_astro_container_224` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_surf_bright_max_shift_p14d` | `0.802` | `0.802` | `0.802` |
| `Bits 2-3` | `>> 2` | `astro_venus_dist_max_shift_p14d` | `1.7009` | `1.7009` | `1.7009` |
| `Bits 4-5` | `>> 4` | `astro_venus_dist_rate_max_shift_p14d` | `3.3543` | `3.3543` | `3.3543` |
| `Bits 6-7` | `>> 6` | `astro_venus_helio_dist_max_shift_p14d` | `0.72548` | `0.72548` | `0.72548` |
| `Bits 8-9` | `>> 8` | `astro_venus_helio_dist_rate_max_shift_p14d` | `-0.21161` | `-0.21161` | `-0.2116` |
| `Bits 10-11` | `>> 10` | `astro_venus_phase_angle_max_shift_p14d` | `13.729` | `13.729` | `13.729` |
| `Bits 12-13` | `>> 12` | `astro_venus_elong_max_shift_p14d` | `9.8437` | `9.8437` | `9.8437` |
| `Bits 14-15` | `>> 14` | `astro_venus_illum_frac_max_shift_p14d` | `75.547` | `75.547` | `75.547` |

### Container: `packed_astro_container_225` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_ra_icrf_mean_shift_p14d` | `37.406` | `37.406` | `37.406` |
| `Bits 2-3` | `>> 2` | `astro_sun_dec_icrf_mean_shift_p14d` | `14.748` | `14.748` | `14.748` |
| `Bits 4-5` | `>> 4` | `astro_sun_ra_app_mean_shift_p14d` | `37.732` | `37.732` | `37.732` |
| `Bits 6-7` | `>> 6` | `astro_sun_dec_app_mean_shift_p14d` | `14.855` | `14.855` | `14.855` |
| `Bits 8-9` | `>> 8` | `astro_sun_azim_mean_shift_p14d` | `15.768` | `15.768` | `15.768` |
| `Bits 10-11` | `>> 10` | `astro_sun_elev_mean_shift_p14d` | `-30.986` | `-30.986` | `-30.986` |
| `Bits 12-13` | `>> 12` | `astro_sun_app_mag_mean_shift_p14d` | `-26.726` | `-26.726` | `-26.726` |
| `Bits 14-15` | `>> 14` | `astro_sun_dist_mean_shift_p14d` | `1.0073` | `1.0073` | `1.0073` |

### Container: `packed_astro_container_226` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_dist_rate_mean_shift_p14d` | `0.37499` | `0.37499` | `0.37499` |
| `Bits 2-3` | `>> 2` | `astro_sun_illum_frac_mean_shift_p14d` | `65.438` | `65.438` | `65.438` |
| `Bits 4-5` | `>> 4` | `astro_moon_ra_icrf_mean_shift_p14d` | `294.15` | `294.15` | `294.15` |
| `Bits 6-7` | `>> 6` | `astro_moon_dec_icrf_mean_shift_p14d` | `-27.146` | `-27.146` | `-27.146` |
| `Bits 8-9` | `>> 8` | `astro_moon_ra_app_mean_shift_p14d` | `294.53` | `294.53` | `294.53` |
| `Bits 10-11` | `>> 10` | `astro_moon_dec_app_mean_shift_p14d` | `-27.093` | `-27.093` | `-27.093` |
| `Bits 12-13` | `>> 12` | `astro_moon_azim_mean_shift_p14d` | `127.76` | `127.76` | `127.76` |
| `Bits 14-15` | `>> 14` | `astro_moon_elev_mean_shift_p14d` | `-1.071` | `-1.071` | `-1.071` |

### Container: `packed_astro_container_227` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_app_mag_mean_shift_p14d` | `-10.749` | `-10.749` | `-10.749` |
| `Bits 2-3` | `>> 2` | `astro_moon_surf_bright_mean_shift_p14d` | `4.9013` | `4.9013` | `4.9013` |
| `Bits 4-5` | `>> 4` | `astro_moon_dist_mean_shift_p14d` | `0.0025358` | `0.0025368` | `0.0025378` |
| `Bits 6-7` | `>> 6` | `astro_moon_dist_rate_mean_shift_p14d` | `-0.30191` | `-0.30191` | `-0.30191` |
| `Bits 8-9` | `>> 8` | `astro_moon_helio_dist_mean_shift_p14d` | `1.0081` | `1.0081` | `1.0081` |
| `Bits 10-11` | `>> 10` | `astro_moon_helio_dist_rate_mean_shift_p14d` | `-0.45221` | `-0.45221` | `-0.45221` |
| `Bits 12-13` | `>> 12` | `astro_moon_phase_angle_mean_shift_p14d` | `71.72` | `71.72` | `71.72` |
| `Bits 14-15` | `>> 14` | `astro_moon_elong_mean_shift_p14d` | `108.15` | `108.15` | `108.15` |

### Container: `packed_astro_container_228` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_illum_frac_mean_shift_p14d` | `65.438` | `65.438` | `65.438` |
| `Bits 2-3` | `>> 2` | `astro_saturn_ra_icrf_mean_shift_p14d` | `347.99` | `347.99` | `347.99` |
| `Bits 4-5` | `>> 4` | `astro_saturn_dec_icrf_mean_shift_p14d` | `-7.0446` | `-7.0446` | `-7.0446` |
| `Bits 6-7` | `>> 6` | `astro_saturn_ra_app_mean_shift_p14d` | `348.31` | `348.31` | `348.31` |
| `Bits 8-9` | `>> 8` | `astro_saturn_dec_app_mean_shift_p14d` | `-6.9143` | `-6.9143` | `-6.9143` |
| `Bits 10-11` | `>> 10` | `astro_saturn_azim_mean_shift_p14d` | `76.465` | `76.465` | `76.465` |
| `Bits 12-13` | `>> 12` | `astro_saturn_elev_mean_shift_p14d` | `-24.106` | `-24.106` | `-24.106` |
| `Bits 14-15` | `>> 14` | `astro_saturn_app_mag_mean_shift_p14d` | `1.0723` | `1.0723` | `1.0723` |

### Container: `packed_astro_container_229` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_surf_bright_mean_shift_p14d` | `6.8533` | `6.8533` | `6.8533` |
| `Bits 2-3` | `>> 2` | `astro_saturn_dist_mean_shift_p14d` | `10.267` | `10.267` | `10.267` |
| `Bits 4-5` | `>> 4` | `astro_saturn_dist_rate_mean_shift_p14d` | `-23.524` | `-23.524` | `-23.524` |
| `Bits 6-7` | `>> 6` | `astro_saturn_helio_dist_mean_shift_p14d` | `9.7035` | `9.7035` | `9.7035` |
| `Bits 8-9` | `>> 8` | `astro_saturn_helio_dist_rate_mean_shift_p14d` | `-0.50379` | `-0.50379` | `-0.50379` |
| `Bits 10-11` | `>> 10` | `astro_saturn_phase_angle_mean_shift_p14d` | `4.7918` | `4.7918` | `4.7918` |
| `Bits 12-13` | `>> 12` | `astro_saturn_elong_mean_shift_p14d` | `53.612` | `53.612` | `53.612` |
| `Bits 14-15` | `>> 14` | `astro_saturn_illum_frac_mean_shift_p14d` | `65.438` | `65.438` | `65.438` |

### Container: `packed_astro_container_230` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_ra_icrf_mean_shift_p14d` | `51.371` | `51.371` | `51.371` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_dec_icrf_mean_shift_p14d` | `17.924` | `17.924` | `17.924` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_ra_app_mean_shift_p14d` | `51.709` | `51.709` | `51.709` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_dec_app_mean_shift_p14d` | `18.008` | `18.008` | `18.008` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_azim_mean_shift_p14d` | `239.97` | `239.97` | `239.97` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_elev_mean_shift_p14d` | `-29.239` | `-29.239` | `-29.239` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_app_mag_mean_shift_p14d` | `-2.007` | `-2.007` | `-2.007` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_surf_bright_mean_shift_p14d` | `5.319` | `5.319` | `5.319` |

### Container: `packed_astro_container_231` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_dist_mean_shift_p14d` | `5.9837` | `5.9837` | `5.9837` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_dist_rate_mean_shift_p14d` | `7.244` | `7.244` | `7.244` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_helio_dist_mean_shift_p14d` | `5.0111` | `5.0111` | `5.0111` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_helio_dist_rate_mean_shift_p14d` | `0.42537` | `0.42537` | `0.42537` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_phase_angle_mean_shift_p14d` | `2.7447` | `2.7447` | `2.7447` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_elong_mean_shift_p14d` | `13.768` | `13.768` | `13.768` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_illum_frac_mean_shift_p14d` | `65.438` | `65.438` | `65.438` |
| `Bits 14-15` | `>> 14` | `astro_mars_ra_icrf_mean_shift_p14d` | `239.74` | `239.74` | `239.74` |

### Container: `packed_astro_container_232` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_dec_icrf_mean_shift_p14d` | `-1.4936` | `-1.4936` | `-1.4936` |
| `Bits 2-3` | `>> 2` | `astro_mars_ra_app_mean_shift_p14d` | `120.05` | `120.05` | `120.05` |
| `Bits 4-5` | `>> 4` | `astro_mars_dec_app_mean_shift_p14d` | `-1.3604` | `-1.3604` | `-1.3604` |
| `Bits 6-7` | `>> 6` | `astro_mars_azim_mean_shift_p14d` | `62.746` | `62.746` | `62.746` |
| `Bits 8-9` | `>> 8` | `astro_mars_elev_mean_shift_p14d` | `-28.15` | `-28.15` | `-28.15` |
| `Bits 10-11` | `>> 10` | `astro_mars_app_mag_mean_shift_p14d` | `1.1783` | `1.1783` | `1.1783` |
| `Bits 12-13` | `>> 12` | `astro_mars_surf_bright_mean_shift_p14d` | `4.2213` | `4.2213` | `4.2213` |
| `Bits 14-15` | `>> 14` | `astro_mars_dist_mean_shift_p14d` | `1.9804` | `1.9804` | `1.9804` |

### Container: `packed_astro_container_233` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_dist_rate_mean_shift_p14d` | `-6.7812` | `-6.7812` | `-6.7812` |
| `Bits 2-3` | `>> 2` | `astro_mars_helio_dist_mean_shift_p14d` | `1.382` | `1.382` | `1.382` |
| `Bits 4-5` | `>> 4` | `astro_mars_helio_dist_rate_mean_shift_p14d` | `-0.21136` | `-0.21136` | `-0.21135` |
| `Bits 6-7` | `>> 6` | `astro_mars_phase_angle_mean_shift_p14d` | `28.353` | `28.353` | `28.353` |
| `Bits 8-9` | `>> 8` | `astro_mars_elong_mean_shift_p14d` | `40.657` | `40.657` | `40.657` |
| `Bits 10-11` | `>> 10` | `astro_mars_illum_frac_mean_shift_p14d` | `65.438` | `65.438` | `65.438` |
| `Bits 12-13` | `>> 12` | `astro_ceres_ra_icrf_mean_shift_p14d` | `292.59` | `292.59` | `292.59` |
| `Bits 14-15` | `>> 14` | `astro_ceres_dec_icrf_mean_shift_p14d` | `-24.273` | `-24.273` | `-24.273` |

### Container: `packed_astro_container_234` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_ceres_ra_app_mean_shift_p14d` | `292.95` | `292.95` | `292.95` |
| `Bits 2-3` | `>> 2` | `astro_ceres_dec_app_mean_shift_p14d` | `-24.223` | `-24.223` | `-24.223` |
| `Bits 4-5` | `>> 4` | `astro_ceres_azim_mean_shift_p14d` | `126.82` | `126.82` | `126.82` |
| `Bits 6-7` | `>> 6` | `astro_ceres_elev_mean_shift_p14d` | `2.4822` | `2.4822` | `2.4822` |
| `Bits 8-9` | `>> 8` | `astro_ceres_app_mag_mean_shift_p14d` | `8.502` | `8.502` | `8.502` |
| `Bits 10-11` | `>> 10` | `astro_ceres_surf_bright_mean_shift_p14d` | `6.963` | `6.963` | `6.963` |
| `Bits 12-13` | `>> 12` | `astro_ceres_dist_mean_shift_p14d` | `2.3588` | `2.3588` | `2.3588` |
| `Bits 14-15` | `>> 14` | `astro_ceres_dist_rate_mean_shift_p14d` | `-21.415` | `-21.415` | `-21.415` |

### Container: `packed_astro_container_235` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_ceres_helio_dist_mean_shift_p14d` | `2.8544` | `2.8544` | `2.8544` |
| `Bits 2-3` | `>> 2` | `astro_ceres_helio_dist_rate_mean_shift_p14d` | `1.2579` | `1.2579` | `1.2579` |
| `Bits 4-5` | `>> 4` | `astro_ceres_phase_angle_mean_shift_p14d` | `19.461` | `19.461` | `19.461` |
| `Bits 6-7` | `>> 6` | `astro_ceres_elong_mean_shift_p14d` | `109.27` | `109.27` | `109.27` |
| `Bits 8-9` | `>> 8` | `astro_ceres_illum_frac_mean_shift_p14d` | `65.438` | `65.438` | `65.438` |
| `Bits 10-11` | `>> 10` | `astro_venus_ra_icrf_mean_shift_p14d` | `28.652` | `28.652` | `28.652` |
| `Bits 12-13` | `>> 12` | `astro_venus_dec_icrf_mean_shift_p14d` | `10.406` | `10.406` | `10.406` |
| `Bits 14-15` | `>> 14` | `astro_venus_ra_app_mean_shift_p14d` | `28.969` | `28.969` | `28.969` |

### Container: `packed_astro_container_236` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_dec_app_mean_shift_p14d` | `10.523` | `10.523` | `10.523` |
| `Bits 2-3` | `>> 2` | `astro_venus_azim_mean_shift_p14d` | `26.853` | `26.853` | `26.853` |
| `Bits 4-5` | `>> 4` | `astro_venus_elev_mean_shift_p14d` | `-32.821` | `-32.821` | `-32.821` |
| `Bits 6-7` | `>> 6` | `astro_venus_app_mag_mean_shift_p14d` | `-3.8847` | `-3.8847` | `-3.8847` |
| `Bits 8-9` | `>> 8` | `astro_venus_surf_bright_mean_shift_p14d` | `0.79933` | `0.79933` | `0.79934` |
| `Bits 10-11` | `>> 10` | `astro_venus_dist_mean_shift_p14d` | `1.6989` | `1.6989` | `1.6989` |
| `Bits 12-13` | `>> 12` | `astro_venus_dist_rate_mean_shift_p14d` | `3.2708` | `3.2708` | `3.2708` |
| `Bits 14-15` | `>> 14` | `astro_venus_helio_dist_mean_shift_p14d` | `0.72535` | `0.72535` | `0.72536` |

### Container: `packed_astro_container_237` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_helio_dist_rate_mean_shift_p14d` | `-0.21439` | `-0.21439` | `-0.21439` |
| `Bits 2-3` | `>> 2` | `astro_venus_phase_angle_mean_shift_p14d` | `13.367` | `13.367` | `13.367` |
| `Bits 4-5` | `>> 4` | `astro_venus_elong_mean_shift_p14d` | `9.5822` | `9.5822` | `9.5822` |
| `Bits 6-7` | `>> 6` | `astro_venus_illum_frac_mean_shift_p14d` | `65.438` | `65.438` | `65.438` |
| `Bits 8-9` | `>> 8` | `astro_sun_ra_icrf_median_shift_p14d` | `37.406` | `37.406` | `37.406` |
| `Bits 10-11` | `>> 10` | `astro_sun_dec_icrf_median_shift_p14d` | `14.75` | `14.75` | `14.75` |
| `Bits 12-13` | `>> 12` | `astro_sun_ra_app_median_shift_p14d` | `37.732` | `37.732` | `37.732` |
| `Bits 14-15` | `>> 14` | `astro_sun_dec_app_median_shift_p14d` | `14.856` | `14.856` | `14.856` |

### Container: `packed_astro_container_238` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_azim_median_shift_p14d` | `15.769` | `15.769` | `15.769` |
| `Bits 2-3` | `>> 2` | `astro_sun_elev_median_shift_p14d` | `-30.985` | `-30.985` | `-30.985` |
| `Bits 4-5` | `>> 4` | `astro_sun_app_mag_median_shift_p14d` | `-26.726` | `-26.726` | `-26.726` |
| `Bits 6-7` | `>> 6` | `astro_sun_dist_median_shift_p14d` | `1.0073` | `1.0073` | `1.0073` |
| `Bits 8-9` | `>> 8` | `astro_sun_dist_rate_median_shift_p14d` | `0.37519` | `0.37519` | `0.37519` |
| `Bits 10-11` | `>> 10` | `astro_sun_illum_frac_median_shift_p14d` | `65.753` | `65.753` | `65.753` |
| `Bits 12-13` | `>> 12` | `astro_moon_ra_icrf_median_shift_p14d` | `294.27` | `294.27` | `294.27` |
| `Bits 14-15` | `>> 14` | `astro_moon_dec_icrf_median_shift_p14d` | `-27.678` | `-27.678` | `-27.678` |

### Container: `packed_astro_container_239` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_ra_app_median_shift_p14d` | `294.65` | `294.65` | `294.65` |
| `Bits 2-3` | `>> 2` | `astro_moon_dec_app_median_shift_p14d` | `-27.624` | `-27.624` | `-27.624` |
| `Bits 4-5` | `>> 4` | `astro_moon_azim_median_shift_p14d` | `127.87` | `127.87` | `127.87` |
| `Bits 6-7` | `>> 6` | `astro_moon_elev_median_shift_p14d` | `-1.0911` | `-1.0911` | `-1.0911` |
| `Bits 8-9` | `>> 8` | `astro_moon_app_mag_median_shift_p14d` | `-10.764` | `-10.764` | `-10.764` |
| `Bits 10-11` | `>> 10` | `astro_moon_surf_bright_median_shift_p14d` | `4.9` | `4.9` | `4.9` |
| `Bits 12-13` | `>> 12` | `astro_moon_dist_median_shift_p14d` | `0.0025358` | `0.0025368` | `0.0025378` |
| `Bits 14-15` | `>> 14` | `astro_moon_dist_rate_median_shift_p14d` | `-0.30627` | `-0.30626` | `-0.30626` |

### Container: `packed_astro_container_240` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_helio_dist_median_shift_p14d` | `1.0081` | `1.0081` | `1.0081` |
| `Bits 2-3` | `>> 2` | `astro_moon_helio_dist_rate_median_shift_p14d` | `-0.46557` | `-0.46557` | `-0.46557` |
| `Bits 4-5` | `>> 4` | `astro_moon_phase_angle_median_shift_p14d` | `71.638` | `71.638` | `71.638` |
| `Bits 6-7` | `>> 6` | `astro_moon_elong_median_shift_p14d` | `108.23` | `108.23` | `108.23` |
| `Bits 8-9` | `>> 8` | `astro_moon_illum_frac_median_shift_p14d` | `65.753` | `65.753` | `65.753` |
| `Bits 10-11` | `>> 10` | `astro_saturn_ra_icrf_median_shift_p14d` | `348` | `348` | `348` |
| `Bits 12-13` | `>> 12` | `astro_saturn_dec_icrf_median_shift_p14d` | `-7.0445` | `-7.0444` | `-7.0444` |
| `Bits 14-15` | `>> 14` | `astro_saturn_ra_app_median_shift_p14d` | `348.31` | `348.31` | `348.31` |

### Container: `packed_astro_container_241` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_dec_app_median_shift_p14d` | `-6.9142` | `-6.9142` | `-6.9142` |
| `Bits 2-3` | `>> 2` | `astro_saturn_azim_median_shift_p14d` | `76.466` | `76.466` | `76.466` |
| `Bits 4-5` | `>> 4` | `astro_saturn_elev_median_shift_p14d` | `-24.106` | `-24.106` | `-24.106` |
| `Bits 6-7` | `>> 6` | `astro_saturn_app_mag_median_shift_p14d` | `1.072` | `1.072` | `1.072` |
| `Bits 8-9` | `>> 8` | `astro_saturn_surf_bright_median_shift_p14d` | `6.853` | `6.853` | `6.853` |
| `Bits 10-11` | `>> 10` | `astro_saturn_dist_median_shift_p14d` | `10.267` | `10.267` | `10.267` |
| `Bits 12-13` | `>> 12` | `astro_saturn_dist_rate_median_shift_p14d` | `-23.526` | `-23.526` | `-23.526` |
| `Bits 14-15` | `>> 14` | `astro_saturn_helio_dist_median_shift_p14d` | `9.7035` | `9.7035` | `9.7035` |

### Container: `packed_astro_container_242` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_helio_dist_rate_median_shift_p14d` | `-0.50384` | `-0.50384` | `-0.50384` |
| `Bits 2-3` | `>> 2` | `astro_saturn_phase_angle_median_shift_p14d` | `4.7922` | `4.7922` | `4.7922` |
| `Bits 4-5` | `>> 4` | `astro_saturn_elong_median_shift_p14d` | `53.612` | `53.612` | `53.612` |
| `Bits 6-7` | `>> 6` | `astro_saturn_illum_frac_median_shift_p14d` | `65.753` | `65.753` | `65.753` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_ra_icrf_median_shift_p14d` | `51.371` | `51.371` | `51.371` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_dec_icrf_median_shift_p14d` | `17.924` | `17.924` | `17.924` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_ra_app_median_shift_p14d` | `51.709` | `51.709` | `51.709` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_dec_app_median_shift_p14d` | `18.008` | `18.008` | `18.008` |

### Container: `packed_astro_container_243` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_azim_median_shift_p14d` | `359.15` | `359.15` | `359.15` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_elev_median_shift_p14d` | `-29.242` | `-29.242` | `-29.242` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_app_mag_median_shift_p14d` | `-2.007` | `-2.007` | `-2.007` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_surf_bright_median_shift_p14d` | `5.319` | `5.319` | `5.319` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_dist_median_shift_p14d` | `5.9838` | `5.9838` | `5.9838` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_dist_rate_median_shift_p14d` | `7.2451` | `7.2451` | `7.2451` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_helio_dist_median_shift_p14d` | `5.0111` | `5.0111` | `5.0111` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_helio_dist_rate_median_shift_p14d` | `0.425` | `0.425` | `0.425` |

### Container: `packed_astro_container_244` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_phase_angle_median_shift_p14d` | `2.7448` | `2.7448` | `2.7448` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_elong_median_shift_p14d` | `13.767` | `13.767` | `13.767` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_illum_frac_median_shift_p14d` | `65.753` | `65.753` | `65.753` |
| `Bits 6-7` | `>> 6` | `astro_mars_ra_icrf_median_shift_p14d` | `359.03` | `359.03` | `359.03` |
| `Bits 8-9` | `>> 8` | `astro_mars_dec_icrf_median_shift_p14d` | `-1.4936` | `-1.4936` | `-1.4936` |
| `Bits 10-11` | `>> 10` | `astro_mars_ra_app_median_shift_p14d` | `0.75284` | `0.75284` | `0.75284` |
| `Bits 12-13` | `>> 12` | `astro_mars_dec_app_median_shift_p14d` | `-1.3604` | `-1.3604` | `-1.3604` |
| `Bits 14-15` | `>> 14` | `astro_mars_azim_median_shift_p14d` | `62.746` | `62.746` | `62.746` |

### Container: `packed_astro_container_245` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_elev_median_shift_p14d` | `-28.15` | `-28.15` | `-28.15` |
| `Bits 2-3` | `>> 2` | `astro_mars_app_mag_median_shift_p14d` | `1.179` | `1.179` | `1.179` |
| `Bits 4-5` | `>> 4` | `astro_mars_surf_bright_median_shift_p14d` | `4.222` | `4.222` | `4.222` |
| `Bits 6-7` | `>> 6` | `astro_mars_dist_median_shift_p14d` | `1.9804` | `1.9804` | `1.9804` |
| `Bits 8-9` | `>> 8` | `astro_mars_dist_rate_median_shift_p14d` | `-6.7809` | `-6.7809` | `-6.7809` |
| `Bits 10-11` | `>> 10` | `astro_mars_helio_dist_median_shift_p14d` | `1.382` | `1.382` | `1.382` |
| `Bits 12-13` | `>> 12` | `astro_mars_helio_dist_rate_median_shift_p14d` | `-0.21137` | `-0.21137` | `-0.21136` |
| `Bits 14-15` | `>> 14` | `astro_mars_phase_angle_median_shift_p14d` | `28.353` | `28.353` | `28.353` |

### Container: `packed_astro_container_246` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_elong_median_shift_p14d` | `40.657` | `40.657` | `40.657` |
| `Bits 2-3` | `>> 2` | `astro_mars_illum_frac_median_shift_p14d` | `65.753` | `65.753` | `65.753` |
| `Bits 4-5` | `>> 4` | `astro_ceres_ra_icrf_median_shift_p14d` | `292.59` | `292.59` | `292.59` |
| `Bits 6-7` | `>> 6` | `astro_ceres_dec_icrf_median_shift_p14d` | `-24.273` | `-24.273` | `-24.273` |
| `Bits 8-9` | `>> 8` | `astro_ceres_ra_app_median_shift_p14d` | `292.96` | `292.96` | `292.96` |
| `Bits 10-11` | `>> 10` | `astro_ceres_dec_app_median_shift_p14d` | `-24.223` | `-24.223` | `-24.223` |
| `Bits 12-13` | `>> 12` | `astro_ceres_azim_median_shift_p14d` | `126.82` | `126.82` | `126.82` |
| `Bits 14-15` | `>> 14` | `astro_ceres_elev_median_shift_p14d` | `2.4829` | `2.4829` | `2.4829` |

### Container: `packed_astro_container_247` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_ceres_app_mag_median_shift_p14d` | `8.502` | `8.502` | `8.502` |
| `Bits 2-3` | `>> 2` | `astro_ceres_surf_bright_median_shift_p14d` | `6.963` | `6.963` | `6.963` |
| `Bits 4-5` | `>> 4` | `astro_ceres_dist_median_shift_p14d` | `2.3588` | `2.3588` | `2.3588` |
| `Bits 6-7` | `>> 6` | `astro_ceres_dist_rate_median_shift_p14d` | `-21.417` | `-21.417` | `-21.417` |
| `Bits 8-9` | `>> 8` | `astro_ceres_helio_dist_median_shift_p14d` | `2.8544` | `2.8544` | `2.8544` |
| `Bits 10-11` | `>> 10` | `astro_ceres_helio_dist_rate_median_shift_p14d` | `1.2579` | `1.2579` | `1.2579` |
| `Bits 12-13` | `>> 12` | `astro_ceres_phase_angle_median_shift_p14d` | `19.463` | `19.463` | `19.463` |
| `Bits 14-15` | `>> 14` | `astro_ceres_elong_median_shift_p14d` | `109.27` | `109.27` | `109.27` |

### Container: `packed_astro_container_248` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_ceres_illum_frac_median_shift_p14d` | `65.753` | `65.753` | `65.753` |
| `Bits 2-3` | `>> 2` | `astro_venus_ra_icrf_median_shift_p14d` | `28.651` | `28.651` | `28.651` |
| `Bits 4-5` | `>> 4` | `astro_venus_dec_icrf_median_shift_p14d` | `10.407` | `10.407` | `10.407` |
| `Bits 6-7` | `>> 6` | `astro_venus_ra_app_median_shift_p14d` | `28.967` | `28.967` | `28.967` |
| `Bits 8-9` | `>> 8` | `astro_venus_dec_app_median_shift_p14d` | `10.524` | `10.524` | `10.524` |
| `Bits 10-11` | `>> 10` | `astro_venus_azim_median_shift_p14d` | `26.853` | `26.853` | `26.853` |
| `Bits 12-13` | `>> 12` | `astro_venus_elev_median_shift_p14d` | `-32.82` | `-32.82` | `-32.82` |
| `Bits 14-15` | `>> 14` | `astro_venus_app_mag_median_shift_p14d` | `-3.885` | `-3.885` | `-3.885` |

### Container: `packed_astro_container_249` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_surf_bright_median_shift_p14d` | `0.799` | `0.799` | `0.799` |
| `Bits 2-3` | `>> 2` | `astro_venus_dist_median_shift_p14d` | `1.699` | `1.699` | `1.699` |
| `Bits 4-5` | `>> 4` | `astro_venus_dist_rate_median_shift_p14d` | `3.2711` | `3.2711` | `3.2711` |
| `Bits 6-7` | `>> 6` | `astro_venus_helio_dist_median_shift_p14d` | `0.72535` | `0.72535` | `0.72536` |
| `Bits 8-9` | `>> 8` | `astro_venus_helio_dist_rate_median_shift_p14d` | `-0.21445` | `-0.21445` | `-0.21444` |
| `Bits 10-11` | `>> 10` | `astro_venus_phase_angle_median_shift_p14d` | `13.367` | `13.367` | `13.367` |
| `Bits 12-13` | `>> 12` | `astro_venus_elong_median_shift_p14d` | `9.5824` | `9.5824` | `9.5824` |
| `Bits 14-15` | `>> 14` | `astro_venus_illum_frac_median_shift_p14d` | `65.753` | `65.753` | `65.753` |

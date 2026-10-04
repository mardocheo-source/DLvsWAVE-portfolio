# DLVS-Wave v2.0 Master Manifest & Decodification Report: Master 30D Summarized (sample_2_italy_central)

> **Generated at**: `2026-08-27 14:11:44 UTC`  
> **Chronological Timeline**: `2024-01-01` to `2024-04-30` (`5` time steps)

## 1. Dataset Dimensions & Compression Summary

| Dimension | Raw Uncompressed | Quantized Bit-Packed (2-Bit / 16-Bit) | Reduction Ratio |
| :--- | :--- | :--- | :--- |
| **Feature Columns** | `405` columns | `55` columns | **8.0x fewer fields** |
| **Record Count** | `5` rows | `5` rows | 1:1 Synchronized |
| **Storage Size** | `34,890 bytes` | `3,029 bytes` | **91.32% space saved** |
| **Container Type** | `Float64` | `uint16` (`2` bits/field, `4` quantiles) | Compact Binary |

## 2. Preserved Seismic Features (In Chiaro / Uncompressed)

All seismic parameters (core 3D coordinates + magnitude and historical lag shifts) are preserved uncompressed as leading columns immediately following `date` for instant inspection:

- **`seis_core_magnitude`**
- **`seis_core_latitude`**
- **`seis_core_longitude`**
- **`seis_core_depth`**

## 3. Tracked Astronomical Bodies & Feature Groups Catalog

| Prefix / Body Group | Fields Count | Sample Features Included |
| :--- | :--- | :--- |
| **`astro_ceres`** | 60 | `min`, `min`, `min`, `min`, ... (+56 more) |
| **`astro_jupiter`** | 60 | `min`, `min`, `min`, `min`, ... (+56 more) |
| **`astro_mars`** | 60 | `min`, `min`, `min`, `min`, ... (+56 more) |
| **`astro_moon`** | 60 | `min`, `min`, `min`, `min`, ... (+56 more) |
| **`astro_saturn`** | 60 | `min`, `min`, `min`, `min`, ... (+56 more) |
| **`astro_sun`** | 40 | `min`, `min`, `min`, `min`, ... (+36 more) |
| **`astro_venus`** | 60 | `min`, `min`, `min`, `min`, ... (+56 more) |

## 4. Container Decodification Matrix & Quantile Codebook

This matrix allows 100% exact decompression of packed integer fields into their discrete quantile bins `[0, 1, 2, 3]`.

### Container: `packed_astro_container_000` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_ra_icrf_min` | `9.5902` | `37.406` | `280.57` |
| `Bits 2-3` | `>> 2` | `astro_sun_dec_icrf_min` | `-17.672` | `-7.6088` | `4.1282` |
| `Bits 4-5` | `>> 4` | `astro_sun_ra_app_min` | `9.8956` | `37.732` | `280.92` |
| `Bits 6-7` | `>> 6` | `astro_sun_dec_app_min` | `-17.584` | `-7.4841` | `4.2588` |
| `Bits 8-9` | `>> 8` | `astro_sun_azim_min` | `15.806` | `16.425` | `17.235` |
| `Bits 10-11` | `>> 10` | `astro_sun_elev_min` | `-63.454` | `-53.613` | `-41.706` |
| `Bits 12-13` | `>> 12` | `astro_sun_app_mag_min` | `-26.775` | `-26.762` | `-26.744` |
| `Bits 14-15` | `>> 14` | `astro_sun_dist_min` | `0.98513` | `0.99087` | `0.99898` |

### Container: `packed_astro_container_001` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_dist_rate_min` | `0.18049` | `0.36896` | `0.37185` |
| `Bits 2-3` | `>> 2` | `astro_sun_illum_frac_min` | `0.1666` | `0.306` | `0.5401` |
| `Bits 4-5` | `>> 4` | `astro_moon_ra_icrf_min` | `5.6757` | `7.5189` | `9.7892` |
| `Bits 6-7` | `>> 6` | `astro_moon_dec_icrf_min` | `-29.025` | `-28.626` | `-28.387` |
| `Bits 8-9` | `>> 8` | `astro_moon_ra_app_min` | `5.9799` | `7.8237` | `10.096` |
| `Bits 10-11` | `>> 10` | `astro_moon_dec_app_min` | `-29.022` | `-28.609` | `-28.391` |
| `Bits 12-13` | `>> 12` | `astro_moon_azim_min` | `8.7589` | `12.396` | `17.355` |
| `Bits 14-15` | `>> 14` | `astro_moon_elev_min` | `-65.194` | `-54.343` | `-41.836` |

### Container: `packed_astro_container_002` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_app_mag_min` | `-12.551` | `-12.547` | `-12.494` |
| `Bits 2-3` | `>> 2` | `astro_moon_surf_bright_min` | `3.452` | `3.475` | `3.503` |
| `Bits 4-5` | `>> 4` | `astro_moon_dist_min` | `0.002427` | `0.0024307` | `0.0024586` |
| `Bits 6-7` | `>> 6` | `astro_moon_dist_rate_min` | `-0.36641` | `-0.35547` | `-0.35436` |
| `Bits 8-9` | `>> 8` | `astro_moon_helio_dist_min` | `0.98416` | `0.99062` | `0.99882` |
| `Bits 10-11` | `>> 10` | `astro_moon_helio_dist_rate_min` | `-0.64447` | `-0.51557` | `-0.48595` |
| `Bits 12-13` | `>> 12` | `astro_moon_phase_angle_min` | `3.1339` | `5.2248` | `5.875` |
| `Bits 14-15` | `>> 14` | `astro_moon_elong_min` | `4.6657` | `6.331` | `8.4124` |

### Container: `packed_astro_container_003` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_illum_frac_min` | `0.1666` | `0.306` | `0.5401` |
| `Bits 2-3` | `>> 2` | `astro_saturn_ra_icrf_min` | `338.38` | `341.76` | `345.12` |
| `Bits 4-5` | `>> 4` | `astro_saturn_dec_icrf_min` | `-10.81` | `-9.4776` | `-8.1568` |
| `Bits 6-7` | `>> 6` | `astro_saturn_ra_app_min` | `338.69` | `342.07` | `345.43` |
| `Bits 8-9` | `>> 8` | `astro_saturn_dec_app_min` | `-10.688` | `-9.3532` | `-8.0294` |
| `Bits 10-11` | `>> 10` | `astro_saturn_azim_min` | `18.388` | `53.576` | `76.466` |
| `Bits 12-13` | `>> 12` | `astro_saturn_elev_min` | `-55.368` | `-54.865` | `-42.684` |
| `Bits 14-15` | `>> 14` | `astro_saturn_app_mag_min` | `0.955` | `0.956` | `1.054` |

### Container: `packed_astro_container_004` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_surf_bright_min` | `6.646` | `6.701` | `6.77` |
| `Bits 2-3` | `>> 2` | `astro_saturn_dist_min` | `10.28` | `10.295` | `10.596` |
| `Bits 4-5` | `>> 4` | `astro_saturn_dist_rate_min` | `-23.256` | `-13.067` | `-0.17951` |
| `Bits 6-7` | `>> 6` | `astro_saturn_helio_dist_min` | `9.7037` | `9.7124` | `9.7211` |
| `Bits 8-9` | `>> 8` | `astro_saturn_helio_dist_rate_min` | `-0.50336` | `-0.5007` | `-0.49735` |
| `Bits 10-11` | `>> 10` | `astro_saturn_phase_angle_min` | `0.1906` | `2.6095` | `2.703` |
| `Bits 12-13` | `>> 12` | `astro_saturn_elong_min` | `1.8914` | `26.689` | `27.325` |
| `Bits 14-15` | `>> 14` | `astro_saturn_illum_frac_min` | `0.1666` | `0.306` | `0.5401` |

### Container: `packed_astro_container_005` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_ra_icrf_min` | `34.856` | `38.849` | `44.585` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_dec_icrf_min` | `12.817` | `14.249` | `16.066` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_ra_app_min` | `35.181` | `39.176` | `44.916` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_dec_app_min` | `12.928` | `14.354` | `16.162` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_azim_min` | `272.24` | `291.55` | `311.97` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_elev_min` | `-29.242` | `-27.282` | `-18.27` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_app_mag_min` | `-2.355` | `-2.178` | `-2.065` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_surf_bright_min` | `5.319` | `5.336` | `5.357` |

### Container: `packed_astro_container_006` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_dist_min` | `4.9516` | `5.4114` | `5.773` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_dist_rate_min` | `7.5862` | `17.299` | `24.807` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_helio_dist_min` | `4.9908` | `4.9972` | `5.004` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_helio_dist_rate_min` | `0.35485` | `0.37899` | `0.4033` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_phase_angle_min` | `2.8881` | `6.9257` | `10.01` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_elong_min` | `14.505` | `37.157` | `61.263` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_illum_frac_min` | `0.1666` | `0.306` | `0.5401` |
| `Bits 14-15` | `>> 14` | `astro_mars_ra_icrf_min` | `266.7` | `291.27` | `315.36` |

### Container: `packed_astro_container_007` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_dec_icrf_min` | `-22.836` | `-18.048` | `-10.48` |
| `Bits 2-3` | `>> 2` | `astro_mars_ra_app_min` | `267.05` | `291.62` | `315.7` |
| `Bits 4-5` | `>> 4` | `astro_mars_dec_app_min` | `-22.79` | `-17.956` | `-10.358` |
| `Bits 6-7` | `>> 6` | `astro_mars_azim_min` | `62.468` | `62.623` | `62.665` |
| `Bits 8-9` | `>> 8` | `astro_mars_elev_min` | `-57.257` | `-50.203` | `-40.143` |
| `Bits 10-11` | `>> 10` | `astro_mars_app_mag_min` | `1.172` | `1.184` | `1.217` |
| `Bits 12-13` | `>> 12` | `astro_mars_surf_bright_min` | `4.013` | `4.027` | `4.044` |
| `Bits 14-15` | `>> 14` | `astro_mars_dist_min` | `1.9841` | `2.0981` | `2.2137` |

### Container: `packed_astro_container_008` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_dist_rate_min` | `-6.8569` | `-6.8409` | `-6.782` |
| `Bits 2-3` | `>> 2` | `astro_mars_helio_dist_min` | `1.3822` | `1.3926` | `1.4145` |
| `Bits 4-5` | `>> 4` | `astro_mars_helio_dist_rate_min` | `-1.9691` | `-1.5349` | `-0.92946` |
| `Bits 6-7` | `>> 6` | `astro_mars_phase_angle_min` | `13.976` | `19.207` | `24.018` |
| `Bits 8-9` | `>> 8` | `astro_mars_elong_min` | `20.736` | `27.99` | `34.551` |
| `Bits 10-11` | `>> 10` | `astro_mars_illum_frac_min` | `0.1666` | `0.306` | `0.5401` |
| `Bits 12-13` | `>> 12` | `astro_ceres_ra_icrf_min` | `266.66` | `278.02` | `287.1` |
| `Bits 14-15` | `>> 14` | `astro_ceres_dec_icrf_min` | `-24.231` | `-23.431` | `-23.011` |

### Container: `packed_astro_container_009` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_ceres_ra_app_min` | `267.02` | `278.38` | `287.46` |
| `Bits 2-3` | `>> 2` | `astro_ceres_dec_app_min` | `-24.181` | `-23.394` | `-22.995` |
| `Bits 4-5` | `>> 4` | `astro_ceres_azim_min` | `84.549` | `97.497` | `110.51` |
| `Bits 6-7` | `>> 6` | `astro_ceres_elev_min` | `-39.636` | `-26.73` | `-12.42` |
| `Bits 8-9` | `>> 8` | `astro_ceres_app_mag_min` | `8.516` | `8.857` | `8.95` |
| `Bits 10-11` | `>> 10` | `astro_ceres_surf_bright_min` | `6.735` | `6.894` | `6.96` |
| `Bits 12-13` | `>> 12` | `astro_ceres_dist_min` | `2.3711` | `2.7552` | `3.1243` |
| `Bits 14-15` | `>> 14` | `astro_ceres_dist_rate_min` | `-22.649` | `-21.417` | `-20.054` |

### Container: `packed_astro_container_010` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_ceres_helio_dist_min` | `2.7847` | `2.8087` | `2.832` |
| `Bits 2-3` | `>> 2` | `astro_ceres_helio_dist_rate_min` | `1.2602` | `1.3221` | `1.3697` |
| `Bits 4-5` | `>> 4` | `astro_ceres_phase_angle_min` | `14.054` | `18.352` | `19.352` |
| `Bits 6-7` | `>> 6` | `astro_ceres_elong_min` | `43.351` | `63.183` | `84.779` |
| `Bits 8-9` | `>> 8` | `astro_ceres_illum_frac_min` | `0.1666` | `0.306` | `0.5401` |
| `Bits 10-11` | `>> 10` | `astro_venus_ra_icrf_min` | `28.651` | `240.61` | `279.82` |
| `Bits 12-13` | `>> 12` | `astro_venus_dec_icrf_min` | `-22.441` | `-16.663` | `-4.0065` |
| `Bits 14-15` | `>> 14` | `astro_venus_ra_app_min` | `28.967` | `240.95` | `280.18` |

### Container: `packed_astro_container_011` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_dec_app_min` | `-22.421` | `-16.565` | `-3.8751` |
| `Bits 2-3` | `>> 2` | `astro_venus_azim_min` | `27.233` | `40.274` | `58.295` |
| `Bits 4-5` | `>> 4` | `astro_venus_elev_min` | `-51.382` | `-48.977` | `-44.136` |
| `Bits 6-7` | `>> 6` | `astro_venus_app_mag_min` | `-3.946` | `-3.893` | `-3.885` |
| `Bits 8-9` | `>> 8` | `astro_venus_surf_bright_min` | `0.802` | `0.882` | `0.976` |
| `Bits 10-11` | `>> 10` | `astro_venus_dist_min` | `1.357` | `1.5037` | `1.6195` |
| `Bits 12-13` | `>> 12` | `astro_venus_dist_rate_min` | `3.3543` | `5.6237` | `7.5005` |
| `Bits 14-15` | `>> 14` | `astro_venus_helio_dist_min` | `0.72434` | `0.72523` | `0.72548` |

### Container: `packed_astro_container_012` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_helio_dist_rate_min` | `-0.21161` | `-0.064952` | `0.12354` |
| `Bits 2-3` | `>> 2` | `astro_venus_phase_angle_min` | `13.729` | `24.303` | `34.591` |
| `Bits 4-5` | `>> 4` | `astro_venus_elong_min` | `9.8437` | `17.458` | `24.638` |
| `Bits 6-7` | `>> 6` | `astro_venus_illum_frac_min` | `0.1666` | `0.306` | `0.5401` |
| `Bits 8-9` | `>> 8` | `astro_sun_ra_icrf_max` | `38.36` | `311.67` | `341.12` |
| `Bits 10-11` | `>> 10` | `astro_sun_dec_icrf_max` | `-7.9876` | `3.7404` | `14.441` |
| `Bits 12-13` | `>> 12` | `astro_sun_ra_app_max` | `38.686` | `312.01` | `341.43` |
| `Bits 14-15` | `>> 14` | `astro_sun_dec_app_max` | `-7.8636` | `3.8714` | `14.549` |

### Container: `packed_astro_container_013` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_azim_max` | `16.415` | `17.173` | `21.597` |
| `Bits 2-3` | `>> 2` | `astro_sun_elev_max` | `-53.994` | `-42.101` | `-31.292` |
| `Bits 4-5` | `>> 4` | `astro_sun_app_mag_max` | `-26.763` | `-26.745` | `-26.727` |
| `Bits 6-7` | `>> 6` | `astro_sun_dist_max` | `0.99062` | `0.99869` | `1.007` |
| `Bits 8-9` | `>> 8` | `astro_sun_dist_rate_max` | `0.36325` | `0.37519` | `0.43321` |
| `Bits 10-11` | `>> 10` | `astro_sun_illum_frac_max` | `99.738` | `99.793` | `99.925` |
| `Bits 12-13` | `>> 12` | `astro_moon_ra_icrf_max` | `346.71` | `352.64` | `354.36` |
| `Bits 14-15` | `>> 14` | `astro_moon_dec_icrf_max` | `27.815` | `27.826` | `27.873` |

### Container: `packed_astro_container_014` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_ra_app_max` | `347.02` | `352.95` | `354.67` |
| `Bits 2-3` | `>> 2` | `astro_moon_dec_app_max` | `27.822` | `27.824` | `27.862` |
| `Bits 4-5` | `>> 4` | `astro_moon_azim_max` | `331.96` | `346.38` | `349.11` |
| `Bits 6-7` | `>> 6` | `astro_moon_elev_max` | `33.561` | `47.243` | `59.593` |
| `Bits 8-9` | `>> 8` | `astro_moon_app_mag_max` | `-4.902` | `-4.717` | `-4.533` |
| `Bits 10-11` | `>> 10` | `astro_moon_surf_bright_max` | `6.323` | `6.344` | `6.36` |
| `Bits 12-13` | `>> 12` | `astro_moon_dist_max` | `0.0026823` | `0.0026842` | `0.002685` |
| `Bits 14-15` | `>> 14` | `astro_moon_dist_rate_max` | `0.34887` | `0.3513` | `0.35439` |

### Container: `packed_astro_container_015` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_helio_dist_max` | `0.99252` | `1.0004` | `1.0081` |
| `Bits 2-3` | `>> 2` | `astro_moon_helio_dist_rate_max` | `1.0717` | `1.2794` | `1.3811` |
| `Bits 4-5` | `>> 4` | `astro_moon_phase_angle_max` | `171.57` | `173.65` | `175.32` |
| `Bits 6-7` | `>> 6` | `astro_moon_elong_max` | `174.11` | `174.76` | `176.86` |
| `Bits 8-9` | `>> 8` | `astro_moon_illum_frac_max` | `99.738` | `99.793` | `99.925` |
| `Bits 10-11` | `>> 10` | `astro_saturn_ra_icrf_max` | `341.65` | `345.01` | `347.91` |
| `Bits 12-13` | `>> 12` | `astro_saturn_dec_icrf_max` | `-9.5229` | `-8.1985` | `-7.0762` |
| `Bits 14-15` | `>> 14` | `astro_saturn_ra_app_max` | `341.96` | `345.32` | `348.22` |

### Container: `packed_astro_container_016` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_dec_app_max` | `-9.3987` | `-8.0712` | `-6.946` |
| `Bits 2-3` | `>> 2` | `astro_saturn_azim_max` | `75.807` | `77.121` | `330.81` |
| `Bits 4-5` | `>> 4` | `astro_saturn_elev_max` | `-43.234` | `-42.082` | `-24.771` |
| `Bits 6-7` | `>> 6` | `astro_saturn_app_mag_max` | `0.991` | `1.053` | `1.072` |
| `Bits 8-9` | `>> 8` | `astro_saturn_surf_bright_max` | `6.727` | `6.766` | `6.851` |
| `Bits 10-11` | `>> 10` | `astro_saturn_dist_max` | `10.589` | `10.6` | `10.711` |
| `Bits 12-13` | `>> 12` | `astro_saturn_dist_rate_max` | `-13.462` | `-0.62568` | `12.518` |
| `Bits 14-15` | `>> 14` | `astro_saturn_helio_dist_max` | `9.7121` | `9.7208` | `9.7293` |

### Container: `packed_astro_container_017` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_helio_dist_rate_max` | `-0.49896` | `-0.49544` | `-0.49184` |
| `Bits 2-3` | `>> 2` | `astro_saturn_phase_angle_max` | `2.622` | `4.6409` | `4.7357` |
| `Bits 4-5` | `>> 4` | `astro_saturn_elong_max` | `26.453` | `52.73` | `53.221` |
| `Bits 6-7` | `>> 6` | `astro_saturn_illum_frac_max` | `99.738` | `99.793` | `99.925` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_ra_icrf_max` | `38.684` | `44.373` | `51.134` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_dec_icrf_max` | `14.193` | `16.003` | `17.864` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_ra_app_max` | `39.01` | `44.705` | `51.472` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_dec_app_max` | `14.299` | `16.099` | `17.949` |

### Container: `packed_astro_container_018` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_azim_max` | `311.25` | `334.38` | `359.15` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_elev_max` | `-27.465` | `-18.674` | `-3.831` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_app_mag_max` | `-2.183` | `-2.068` | `-2.008` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_surf_bright_max` | `5.335` | `5.359` | `5.372` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_dist_max` | `5.3972` | `5.7632` | `5.9795` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_dist_rate_max` | `17.005` | `24.614` | `28.166` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_helio_dist_max` | `4.997` | `5.0037` | `5.0109` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_helio_dist_rate_max` | `0.37741` | `0.40126` | `0.42527` |

### Container: `packed_astro_container_019` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_phase_angle_max` | `6.8027` | `9.9306` | `11.361` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_elong_max` | `36.382` | `60.429` | `86.596` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_illum_frac_max` | `99.738` | `99.793` | `99.925` |
| `Bits 6-7` | `>> 6` | `astro_mars_ra_icrf_max` | `314.58` | `337.41` | `359.03` |
| `Bits 8-9` | `>> 8` | `astro_mars_dec_icrf_max` | `-18.259` | `-10.764` | `-1.8007` |
| `Bits 10-11` | `>> 10` | `astro_mars_ra_app_max` | `290.81` | `314.92` | `337.72` |
| `Bits 12-13` | `>> 12` | `astro_mars_dec_app_max` | `-18.168` | `-10.642` | `-1.6676` |
| `Bits 14-15` | `>> 14` | `astro_mars_azim_max` | `62.734` | `62.757` | `63.018` |

### Container: `packed_astro_container_020` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_elev_max` | `-50.49` | `-40.518` | `-28.564` |
| `Bits 2-3` | `>> 2` | `astro_mars_app_mag_max` | `1.184` | `1.29` | `1.332` |
| `Bits 4-5` | `>> 4` | `astro_mars_surf_bright_max` | `4.125` | `4.187` | `4.222` |
| `Bits 6-7` | `>> 6` | `astro_mars_dist_max` | `2.0943` | `2.2098` | `2.3228` |
| `Bits 8-9` | `>> 8` | `astro_mars_dist_rate_max` | `-6.7809` | `-6.7807` | `-6.4341` |
| `Bits 10-11` | `>> 10` | `astro_mars_helio_dist_max` | `1.392` | `1.4136` | `1.4442` |
| `Bits 12-13` | `>> 12` | `astro_mars_helio_dist_rate_max` | `-1.5524` | `-0.95187` | `-0.23626` |
| `Bits 14-15` | `>> 14` | `astro_mars_phase_angle_max` | `19.039` | `23.865` | `28.216` |

### Container: `packed_astro_container_021` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_elong_max` | `27.761` | `34.342` | `40.457` |
| `Bits 2-3` | `>> 2` | `astro_mars_illum_frac_max` | `99.738` | `99.793` | `99.925` |
| `Bits 4-5` | `>> 4` | `astro_ceres_ra_icrf_max` | `277.67` | `286.84` | `292.48` |
| `Bits 6-7` | `>> 6` | `astro_ceres_dec_icrf_max` | `-23.447` | `-23.027` | `-22.28` |
| `Bits 8-9` | `>> 8` | `astro_ceres_ra_app_max` | `278.03` | `287.21` | `292.85` |
| `Bits 10-11` | `>> 10` | `astro_ceres_dec_app_max` | `-23.409` | `-23.01` | `-22.29` |
| `Bits 12-13` | `>> 12` | `astro_ceres_azim_max` | `97.082` | `110.05` | `126.18` |
| `Bits 14-15` | `>> 14` | `astro_ceres_elev_max` | `-27.185` | `-12.914` | `1.9973` |

### Container: `packed_astro_container_022` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_ceres_app_mag_max` | `8.849` | `9.032` | `9.063` |
| `Bits 2-3` | `>> 2` | `astro_ceres_surf_bright_max` | `6.89` | `6.963` | `6.977` |
| `Bits 4-5` | `>> 4` | `astro_ceres_dist_max` | `2.7423` | `3.1128` | `3.4176` |
| `Bits 6-7` | `>> 6` | `astro_ceres_dist_rate_max` | `-21.294` | `-20.186` | `-15.224` |
| `Bits 8-9` | `>> 8` | `astro_ceres_helio_dist_max` | `2.8079` | `2.8312` | `2.8536` |
| `Bits 10-11` | `>> 10` | `astro_ceres_helio_dist_rate_max` | `1.3202` | `1.3684` | `1.401` |
| `Bits 12-13` | `>> 12` | `astro_ceres_phase_angle_max` | `18.237` | `19.463` | `20.54` |
| `Bits 14-15` | `>> 14` | `astro_ceres_elong_max` | `62.498` | `84.021` | `108.39` |

### Container: `packed_astro_container_023` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_ceres_illum_frac_max` | `99.738` | `99.793` | `99.925` |
| `Bits 2-3` | `>> 2` | `astro_venus_ra_icrf_max` | `278.49` | `317.59` | `353.27` |
| `Bits 4-5` | `>> 4` | `astro_venus_dec_icrf_max` | `-16.993` | `-4.4862` | `9.9542` |
| `Bits 6-7` | `>> 6` | `astro_venus_ra_app_max` | `278.84` | `317.92` | `353.57` |
| `Bits 8-9` | `>> 8` | `astro_venus_dec_app_max` | `-16.897` | `-4.3551` | `10.073` |
| `Bits 10-11` | `>> 10` | `astro_venus_azim_max` | `39.764` | `57.646` | `73.973` |
| `Bits 12-13` | `>> 12` | `astro_venus_elev_max` | `-44.485` | `-39.953` | `-33.185` |
| `Bits 14-15` | `>> 14` | `astro_venus_app_mag_max` | `-3.894` | `-3.885` | `-3.876` |

### Container: `packed_astro_container_024` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_surf_bright_max` | `0.879` | `0.973` | `1.071` |
| `Bits 2-3` | `>> 2` | `astro_venus_dist_max` | `1.4993` | `1.6162` | `1.697` |
| `Bits 4-5` | `>> 4` | `astro_venus_dist_rate_max` | `5.5558` | `7.4428` | `9.1037` |
| `Bits 6-7` | `>> 6` | `astro_venus_helio_dist_max` | `0.72535` | `0.72748` | `0.72798` |
| `Bits 8-9` | `>> 8` | `astro_venus_helio_dist_rate_max` | `-0.071205` | `0.11793` | `0.23077` |
| `Bits 10-11` | `>> 10` | `astro_venus_phase_angle_max` | `23.958` | `34.247` | `44.773` |
| `Bits 12-13` | `>> 12` | `astro_venus_elong_max` | `17.211` | `24.405` | `31.187` |
| `Bits 14-15` | `>> 14` | `astro_venus_illum_frac_max` | `99.738` | `99.793` | `99.925` |

### Container: `packed_astro_container_025` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_ra_icrf_mean` | `37.883` | `235.43` | `296.3` |
| `Bits 2-3` | `>> 2` | `astro_sun_dec_icrf_mean` | `-13.072` | `-1.9533` | `9.4638` |
| `Bits 4-5` | `>> 4` | `astro_sun_ra_app_mean` | `38.209` | `235.74` | `296.65` |
| `Bits 6-7` | `>> 6` | `astro_sun_dec_app_mean` | `-12.964` | `-1.8232` | `9.5853` |
| `Bits 8-9` | `>> 8` | `astro_sun_azim_mean` | `16.174` | `16.683` | `18.96` |
| `Bits 10-11` | `>> 10` | `astro_sun_elev_mean` | `-59.018` | `-47.887` | `-36.301` |
| `Bits 12-13` | `>> 12` | `astro_sun_app_mag_mean` | `-26.769` | `-26.754` | `-26.735` |
| `Bits 14-15` | `>> 14` | `astro_sun_dist_mean` | `0.98764` | `0.99469` | `1.0031` |

### Container: `packed_astro_container_026` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_dist_rate_mean` | `0.27139` | `0.37352` | `0.40163` |
| `Bits 2-3` | `>> 2` | `astro_sun_illum_frac_mean` | `52.959` | `53.155` | `53.417` |
| `Bits 4-5` | `>> 4` | `astro_moon_ra_icrf_mean` | `177.91` | `179.35` | `188.17` |
| `Bits 6-7` | `>> 6` | `astro_moon_dec_icrf_mean` | `-3.1406` | `-2.0965` | `-0.46965` |
| `Bits 8-9` | `>> 8` | `astro_moon_ra_app_mean` | `178.25` | `179.68` | `188.52` |
| `Bits 10-11` | `>> 10` | `astro_moon_dec_app_mean` | `-3.1494` | `-2.1128` | `-0.4885` |
| `Bits 12-13` | `>> 12` | `astro_moon_azim_mean` | `183.14` | `190.09` | `194.1` |
| `Bits 14-15` | `>> 14` | `astro_moon_elev_mean` | `-0.29514` | `1.3853` | `2.7629` |

### Container: `packed_astro_container_027` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_app_mag_mean` | `-9.7817` | `-9.7806` | `-9.7355` |
| `Bits 2-3` | `>> 2` | `astro_moon_surf_bright_mean` | `5.015` | `5.0154` | `5.017` |
| `Bits 4-5` | `>> 4` | `astro_moon_dist_mean` | `0.002571` | `0.0025772` | `0.0025811` |
| `Bits 6-7` | `>> 6` | `astro_moon_dist_rate_mean` | `-0.012183` | `-0.0054826` | `0.0026413` |
| `Bits 8-9` | `>> 8` | `astro_moon_helio_dist_mean` | `0.98786` | `0.99493` | `1.0033` |
| `Bits 10-11` | `>> 10` | `astro_moon_helio_dist_rate_mean` | `0.095482` | `0.32244` | `0.45621` |
| `Bits 12-13` | `>> 12` | `astro_moon_phase_angle_mean` | `85.049` | `85.423` | `85.838` |
| `Bits 14-15` | `>> 14` | `astro_moon_elong_mean` | `94.066` | `94.48` | `94.855` |

### Container: `packed_astro_container_028` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_illum_frac_mean` | `52.959` | `53.155` | `53.417` |
| `Bits 2-3` | `>> 2` | `astro_saturn_ra_icrf_mean` | `340` | `343.41` | `346.57` |
| `Bits 4-5` | `>> 4` | `astro_saturn_dec_icrf_mean` | `-10.173` | `-8.8299` | `-7.5937` |
| `Bits 6-7` | `>> 6` | `astro_saturn_ra_app_mean` | `340.31` | `343.72` | `346.88` |
| `Bits 8-9` | `>> 8` | `astro_saturn_dec_app_mean` | `-10.05` | `-8.704` | `-7.4649` |
| `Bits 10-11` | `>> 10` | `astro_saturn_azim_mean` | `65.281` | `76.793` | `210.52` |
| `Bits 12-13` | `>> 12` | `astro_saturn_elev_mean` | `-49.998` | `-49.141` | `-33.982` |
| `Bits 14-15` | `>> 14` | `astro_saturn_app_mag_mean` | `0.98073` | `1.0154` | `1.0681` |

### Container: `packed_astro_container_029` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_surf_bright_mean` | `6.7137` | `6.7156` | `6.8121` |
| `Bits 2-3` | `>> 2` | `astro_saturn_dist_mean` | `10.448` | `10.461` | `10.67` |
| `Bits 4-5` | `>> 4` | `astro_saturn_dist_rate_mean` | `-18.658` | `-6.9738` | `6.2443` |
| `Bits 6-7` | `>> 6` | `astro_saturn_helio_dist_mean` | `9.7079` | `9.7166` | `9.7252` |
| `Bits 8-9` | `>> 8` | `astro_saturn_helio_dist_rate_mean` | `-0.50102` | `-0.49776` | `-0.49444` |
| `Bits 10-11` | `>> 10` | `astro_saturn_phase_angle_mean` | `1.3936` | `3.6831` | `3.7749` |
| `Bits 12-13` | `>> 12` | `astro_saturn_elong_mean` | `13.879` | `39.885` | `40.008` |
| `Bits 14-15` | `>> 14` | `astro_saturn_illum_frac_mean` | `52.959` | `53.155` | `53.417` |

### Container: `packed_astro_container_030` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_ra_icrf_mean` | `36.609` | `41.507` | `47.803` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_dec_icrf_mean` | `13.461` | `15.111` | `16.973` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_ra_app_mean` | `36.935` | `41.836` | `48.138` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_dec_app_mean` | `13.569` | `15.212` | `17.063` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_azim_mean` | `281.61` | `301.22` | `322.97` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_elev_mean` | `-28.92` | `-23.478` | `-11.456` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_app_mag_mean` | `-2.2638` | `-2.1185` | `-2.0331` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_surf_bright_mean` | `5.3261` | `5.3475` | `5.3668` |

### Container: `packed_astro_container_031` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_dist_mean` | `5.1789` | `5.5971` | `5.8888` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_dist_rate_mean` | `12.389` | `21.186` | `26.878` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_helio_dist_mean` | `4.9939` | `5.0004` | `5.0074` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_helio_dist_rate_mean` | `0.36691` | `0.39077` | `0.41365` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_phase_angle_mean` | `4.8907` | `8.5256` | `10.847` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_elong_mean` | `25.358` | `48.657` | `73.741` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_illum_frac_mean` | `52.959` | `53.155` | `53.417` |
| `Bits 14-15` | `>> 14` | `astro_mars_ra_icrf_mean` | `278.55` | `303.01` | `326.49` |

### Container: `packed_astro_container_032` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_dec_icrf_mean` | `-20.801` | `-14.568` | `-6.194` |
| `Bits 2-3` | `>> 2` | `astro_mars_ra_app_mean` | `278.91` | `303.35` | `326.82` |
| `Bits 4-5` | `>> 4` | `astro_mars_dec_app_mean` | `-20.732` | `-14.46` | `-6.065` |
| `Bits 6-7` | `>> 6` | `astro_mars_azim_mean` | `62.653` | `62.752` | `62.83` |
| `Bits 8-9` | `>> 8` | `astro_mars_elev_mean` | `-54.116` | `-45.561` | `-34.443` |
| `Bits 10-11` | `>> 10` | `astro_mars_app_mag_mean` | `1.1755` | `1.2379` | `1.2897` |
| `Bits 12-13` | `>> 12` | `astro_mars_surf_bright_mean` | `4.083` | `4.1041` | `4.1275` |
| `Bits 14-15` | `>> 14` | `astro_mars_dist_mean` | `2.039` | `2.1539` | `2.2687` |

### Container: `packed_astro_container_033` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_dist_rate_mean` | `-6.8242` | `-6.7815` | `-6.6886` |
| `Bits 2-3` | `>> 2` | `astro_mars_helio_dist_mean` | `1.3861` | `1.4023` | `1.4288` |
| `Bits 4-5` | `>> 4` | `astro_mars_helio_dist_rate_mean` | `-1.775` | `-1.2546` | `-0.58847` |
| `Bits 6-7` | `>> 6` | `astro_mars_phase_angle_mean` | `16.536` | `21.571` | `26.155` |
| `Bits 8-9` | `>> 8` | `astro_mars_elong_mean` | `24.306` | `31.213` | `37.526` |
| `Bits 10-11` | `>> 10` | `astro_mars_illum_frac_mean` | `52.959` | `53.155` | `53.417` |
| `Bits 12-13` | `>> 12` | `astro_ceres_ra_icrf_mean` | `272.29` | `282.64` | `290.11` |
| `Bits 14-15` | `>> 14` | `astro_ceres_dec_icrf_mean` | `-23.78` | `-23.229` | `-22.694` |

### Container: `packed_astro_container_034` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_ceres_ra_app_mean` | `272.65` | `283.01` | `290.48` |
| `Bits 2-3` | `>> 2` | `astro_ceres_dec_app_mean` | `-23.735` | `-23.202` | `-22.69` |
| `Bits 4-5` | `>> 4` | `astro_ceres_azim_mean` | `90.928` | `103.66` | `117.97` |
| `Bits 6-7` | `>> 6` | `astro_ceres_elev_mean` | `-33.53` | `-19.912` | `-5.1968` |
| `Bits 8-9` | `>> 8` | `astro_ceres_app_mag_mean` | `8.695` | `8.9565` | `9.0177` |
| `Bits 10-11` | `>> 10` | `astro_ceres_surf_bright_mean` | `6.8179` | `6.9421` | `6.9615` |
| `Bits 12-13` | `>> 12` | `astro_ceres_dist_mean` | `2.5552` | `2.9373` | `3.2774` |
| `Bits 14-15` | `>> 14` | `astro_ceres_dist_rate_mean` | `-21.652` | `-21.355` | `-17.794` |

### Container: `packed_astro_container_035` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_ceres_helio_dist_mean` | `2.7963` | `2.82` | `2.8429` |
| `Bits 2-3` | `>> 2` | `astro_ceres_helio_dist_rate_mean` | `1.2912` | `1.3463` | `1.3866` |
| `Bits 4-5` | `>> 4` | `astro_ceres_phase_angle_mean` | `16.264` | `19.408` | `19.643` |
| `Bits 6-7` | `>> 6` | `astro_ceres_elong_mean` | `52.823` | `73.437` | `96.317` |
| `Bits 8-9` | `>> 8` | `astro_ceres_illum_frac_mean` | `52.959` | `53.155` | `53.417` |
| `Bits 10-11` | `>> 10` | `astro_venus_ra_icrf_mean` | `70.899` | `259.35` | `298.92` |
| `Bits 12-13` | `>> 12` | `astro_venus_dec_icrf_mean` | `-20.402` | `-10.913` | `3.0351` |
| `Bits 14-15` | `>> 14` | `astro_venus_ra_app_mean` | `71.206` | `259.7` | `299.26` |

### Container: `packed_astro_container_036` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_dec_app_mean` | `-20.341` | `-10.795` | `3.1636` |
| `Bits 2-3` | `>> 2` | `astro_venus_azim_mean` | `33.207` | `48.612` | `66.821` |
| `Bits 4-5` | `>> 4` | `astro_venus_elev_mean` | `-48.527` | `-44.775` | `-38.693` |
| `Bits 6-7` | `>> 6` | `astro_venus_app_mag_mean` | `-3.9169` | `-3.885` | `-3.8818` |
| `Bits 8-9` | `>> 8` | `astro_venus_surf_bright_mean` | `0.83897` | `0.9271` | `1.0231` |
| `Bits 10-11` | `>> 10` | `astro_venus_dist_mean` | `1.4304` | `1.5625` | `1.6612` |
| `Bits 12-13` | `>> 12` | `astro_venus_dist_rate_mean` | `4.479` | `6.5461` | `8.3027` |
| `Bits 14-15` | `>> 14` | `astro_venus_helio_dist_mean` | `0.72529` | `0.72606` | `0.72692` |

### Container: `packed_astro_container_037` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_helio_dist_rate_mean` | `-0.14919` | `0.027941` | `0.18696` |
| `Bits 2-3` | `>> 2` | `astro_venus_phase_angle_mean` | `18.882` | `29.28` | `39.642` |
| `Bits 4-5` | `>> 4` | `astro_venus_elong_mean` | `13.561` | `20.964` | `27.944` |
| `Bits 6-7` | `>> 6` | `astro_venus_illum_frac_mean` | `52.959` | `53.155` | `53.417` |
| `Bits 8-9` | `>> 8` | `astro_sun_ra_icrf_median` | `37.883` | `296.4` | `327.23` |
| `Bits 10-11` | `>> 10` | `astro_sun_dec_icrf_median` | `-13.205` | `-1.9634` | `9.5632` |
| `Bits 12-13` | `>> 12` | `astro_sun_ra_app_median` | `38.209` | `296.75` | `327.55` |
| `Bits 14-15` | `>> 14` | `astro_sun_dec_app_median` | `-13.096` | `-1.832` | `9.6859` |

### Container: `packed_astro_container_038` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_azim_median` | `16.209` | `16.619` | `18.704` |
| `Bits 2-3` | `>> 2` | `astro_sun_elev_median` | `-59.179` | `-47.904` | `-36.192` |
| `Bits 4-5` | `>> 4` | `astro_sun_app_mag_median` | `-26.77` | `-26.754` | `-26.736` |
| `Bits 6-7` | `>> 6` | `astro_sun_dist_median` | `0.98751` | `0.99465` | `1.0031` |
| `Bits 8-9` | `>> 8` | `astro_sun_dist_rate_median` | `0.26564` | `0.37352` | `0.39641` |
| `Bits 10-11` | `>> 10` | `astro_sun_illum_frac_median` | `56.16` | `56.497` | `57.011` |
| `Bits 12-13` | `>> 12` | `astro_moon_ra_icrf_median` | `186.13` | `186.85` | `194.37` |
| `Bits 14-15` | `>> 14` | `astro_moon_dec_icrf_median` | `-4.8166` | `-3.9513` | `-2.1027` |

### Container: `packed_astro_container_039` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_ra_app_median` | `186.44` | `187.17` | `194.69` |
| `Bits 2-3` | `>> 2` | `astro_moon_dec_app_median` | `-4.8185` | `-3.9524` | `-2.2376` |
| `Bits 4-5` | `>> 4` | `astro_moon_azim_median` | `159.04` | `179.03` | `180.01` |
| `Bits 6-7` | `>> 6` | `astro_moon_elev_median` | `5.1166` | `6.9819` | `7.6072` |
| `Bits 8-9` | `>> 8` | `astro_moon_app_mag_median` | `-10.389` | `-10.373` | `-10.338` |
| `Bits 10-11` | `>> 10` | `astro_moon_surf_bright_median` | `4.9795` | `5.015` | `5.0565` |
| `Bits 12-13` | `>> 12` | `astro_moon_dist_median` | `0.0025792` | `0.0025876` | `0.0026056` |
| `Bits 14-15` | `>> 14` | `astro_moon_dist_rate_median` | `-0.024216` | `-0.000249` | `0.0070807` |

### Container: `packed_astro_container_040` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_helio_dist_median` | `0.98663` | `0.99374` | `1.0024` |
| `Bits 2-3` | `>> 2` | `astro_moon_helio_dist_rate_median` | `0.089` | `0.3245` | `0.44759` |
| `Bits 4-5` | `>> 4` | `astro_moon_phase_angle_median` | `81.938` | `82.496` | `82.913` |
| `Bits 6-7` | `>> 6` | `astro_moon_elong_median` | `96.937` | `97.354` | `97.913` |
| `Bits 8-9` | `>> 8` | `astro_moon_illum_frac_median` | `56.16` | `56.497` | `57.011` |
| `Bits 10-11` | `>> 10` | `astro_saturn_ra_icrf_median` | `339.99` | `343.42` | `346.6` |
| `Bits 12-13` | `>> 12` | `astro_saturn_dec_icrf_median` | `-10.177` | `-8.8254` | `-7.5811` |
| `Bits 14-15` | `>> 14` | `astro_saturn_ra_app_median` | `340.3` | `343.73` | `346.91` |

### Container: `packed_astro_container_041` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_dec_app_median` | `-10.054` | `-8.6995` | `-7.4523` |
| `Bits 2-3` | `>> 2` | `astro_saturn_azim_median` | `65.604` | `76.793` | `312.15` |
| `Bits 4-5` | `>> 4` | `astro_saturn_elev_median` | `-50.381` | `-49.507` | `-34.122` |
| `Bits 6-7` | `>> 6` | `astro_saturn_app_mag_median` | `0.9865` | `1.021` | `1.0705` |
| `Bits 8-9` | `>> 8` | `astro_saturn_surf_bright_median` | `6.7165` | `6.7175` | `6.813` |
| `Bits 10-11` | `>> 10` | `astro_saturn_dist_median` | `10.455` | `10.469` | `10.68` |
| `Bits 12-13` | `>> 12` | `astro_saturn_dist_rate_median` | `-18.831` | `-7.0537` | `6.279` |
| `Bits 14-15` | `>> 14` | `astro_saturn_helio_dist_median` | `9.708` | `9.7166` | `9.7252` |

### Container: `packed_astro_container_042` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_helio_dist_rate_median` | `-0.5009` | `-0.49765` | `-0.49446` |
| `Bits 2-3` | `>> 2` | `astro_saturn_phase_angle_median` | `1.3969` | `3.715` | `3.8056` |
| `Bits 4-5` | `>> 4` | `astro_saturn_elong_median` | `13.815` | `39.846` | `39.998` |
| `Bits 6-7` | `>> 6` | `astro_saturn_illum_frac_median` | `56.16` | `56.497` | `57.011` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_ra_icrf_median` | `36.52` | `41.45` | `47.772` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_dec_icrf_median` | `13.437` | `15.103` | `16.977` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_ra_app_median` | `36.846` | `41.779` | `48.107` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_dec_app_median` | `13.545` | `15.204` | `17.067` |

### Container: `packed_astro_container_043` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_azim_median` | `281.63` | `301.12` | `322.85` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_elev_median` | `-29.21` | `-23.755` | `-11.68` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_app_mag_median` | `-2.261` | `-2.116` | `-2.031` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_surf_bright_median` | `5.3255` | `5.3475` | `5.368` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_dist_median` | `5.1814` | `5.6025` | `5.8958` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_dist_rate_median` | `12.437` | `21.308` | `27.096` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_helio_dist_median` | `4.9939` | `5.0004` | `5.0074` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_helio_dist_rate_median` | `0.36664` | `0.39043` | `0.41454` |

### Container: `packed_astro_container_044` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_phase_angle_median` | `4.9156` | `8.5793` | `10.936` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_elong_median` | `25.311` | `48.582` | `73.637` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_illum_frac_median` | `56.16` | `56.497` | `57.011` |
| `Bits 6-7` | `>> 6` | `astro_mars_ra_icrf_median` | `278.54` | `303.05` | `326.55` |
| `Bits 8-9` | `>> 8` | `astro_mars_dec_icrf_median` | `-20.941` | `-14.658` | `-6.2233` |
| `Bits 10-11` | `>> 10` | `astro_mars_ra_app_median` | `278.9` | `303.4` | `326.88` |
| `Bits 12-13` | `>> 12` | `astro_mars_dec_app_median` | `-20.871` | `-14.549` | `-6.0934` |
| `Bits 14-15` | `>> 14` | `astro_mars_azim_median` | `62.642` | `62.752` | `62.822` |

### Container: `packed_astro_container_045` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_elev_median` | `-54.25` | `-45.671` | `-34.493` |
| `Bits 2-3` | `>> 2` | `astro_mars_app_mag_median` | `1.1755` | `1.2415` | `1.2975` |
| `Bits 4-5` | `>> 4` | `astro_mars_surf_bright_median` | `4.091` | `4.0975` | `4.147` |
| `Bits 6-7` | `>> 6` | `astro_mars_dist_median` | `2.0389` | `2.1539` | `2.269` |
| `Bits 8-9` | `>> 8` | `astro_mars_dist_rate_median` | `-6.8323` | `-6.7815` | `-6.7234` |
| `Bits 10-11` | `>> 10` | `astro_mars_helio_dist_median` | `1.3856` | `1.4018` | `1.4285` |
| `Bits 12-13` | `>> 12` | `astro_mars_helio_dist_rate_median` | `-1.7829` | `-1.2608` | `-0.59158` |
| `Bits 14-15` | `>> 14` | `astro_mars_phase_angle_median` | `16.553` | `21.591` | `26.176` |

### Container: `packed_astro_container_046` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_elong_median` | `24.338` | `31.239` | `37.539` |
| `Bits 2-3` | `>> 2` | `astro_mars_illum_frac_median` | `56.16` | `56.497` | `57.011` |
| `Bits 4-5` | `>> 4` | `astro_ceres_ra_icrf_median` | `272.36` | `282.76` | `290.29` |
| `Bits 6-7` | `>> 6` | `astro_ceres_dec_icrf_median` | `-23.747` | `-23.229` | `-22.72` |
| `Bits 8-9` | `>> 8` | `astro_ceres_ra_app_median` | `272.72` | `283.13` | `290.66` |
| `Bits 10-11` | `>> 10` | `astro_ceres_dec_app_median` | `-23.702` | `-23.201` | `-22.717` |
| `Bits 12-13` | `>> 12` | `astro_ceres_azim_median` | `90.99` | `103.59` | `117.76` |
| `Bits 14-15` | `>> 14` | `astro_ceres_elev_median` | `-33.597` | `-19.963` | `-5.1901` |

### Container: `packed_astro_container_047` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_ceres_app_mag_median` | `8.702` | `8.963` | `9.024` |
| `Bits 2-3` | `>> 2` | `astro_ceres_surf_bright_median` | `6.8205` | `6.9455` | `6.9615` |
| `Bits 4-5` | `>> 4` | `astro_ceres_dist_median` | `2.5544` | `2.9392` | `3.281` |
| `Bits 6-7` | `>> 6` | `astro_ceres_dist_rate_median` | `-21.785` | `-21.355` | `-17.886` |
| `Bits 8-9` | `>> 8` | `astro_ceres_helio_dist_median` | `2.7963` | `2.8201` | `2.8429` |
| `Bits 10-11` | `>> 10` | `astro_ceres_helio_dist_rate_median` | `1.2918` | `1.3469` | `1.3873` |
| `Bits 12-13` | `>> 12` | `astro_ceres_phase_angle_median` | `16.33` | `19.408` | `19.751` |
| `Bits 14-15` | `>> 14` | `astro_ceres_elong_median` | `52.768` | `73.347` | `96.169` |

### Container: `packed_astro_container_048` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_ceres_illum_frac_median` | `56.16` | `56.497` | `57.011` |
| `Bits 2-3` | `>> 2` | `astro_venus_ra_icrf_median` | `29.235` | `259.24` | `299.04` |
| `Bits 4-5` | `>> 4` | `astro_venus_dec_icrf_median` | `-20.782` | `-11.1` | `3.069` |
| `Bits 6-7` | `>> 6` | `astro_venus_ra_app_median` | `29.552` | `259.59` | `299.38` |
| `Bits 8-9` | `>> 8` | `astro_venus_dec_app_median` | `-20.719` | `-10.98` | `3.1995` |
| `Bits 10-11` | `>> 10` | `astro_venus_azim_median` | `33.045` | `48.409` | `67.207` |
| `Bits 12-13` | `>> 12` | `astro_venus_elev_median` | `-48.856` | `-44.946` | `-38.71` |
| `Bits 14-15` | `>> 14` | `astro_venus_app_mag_median` | `-3.915` | `-3.885` | `-3.8805` |

### Container: `packed_astro_container_049` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_surf_bright_median` | `0.838` | `0.9265` | `1.023` |
| `Bits 2-3` | `>> 2` | `astro_venus_dist_median` | `1.4316` | `1.5638` | `1.6629` |
| `Bits 4-5` | `>> 4` | `astro_venus_dist_rate_median` | `4.4874` | `6.5478` | `8.2972` |
| `Bits 6-7` | `>> 6` | `astro_venus_helio_dist_median` | `0.72529` | `0.72614` | `0.72703` |
| `Bits 8-9` | `>> 8` | `astro_venus_helio_dist_rate_median` | `-0.15352` | `0.028748` | `0.19241` |
| `Bits 10-11` | `>> 10` | `astro_venus_phase_angle_median` | `18.904` | `29.283` | `39.62` |
| `Bits 12-13` | `>> 12` | `astro_venus_elong_median` | `13.58` | `20.982` | `27.962` |
| `Bits 14-15` | `>> 14` | `astro_venus_illum_frac_median` | `56.16` | `56.497` | `57.011` |

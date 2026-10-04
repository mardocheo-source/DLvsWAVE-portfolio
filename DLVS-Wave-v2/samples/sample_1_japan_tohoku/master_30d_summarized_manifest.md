# DLVS-Wave v2.0 Master Manifest & Decodification Report: Master 30D Summarized (sample_1_japan_tohoku)

> **Generated at**: `2026-08-27 14:11:38 UTC`  
> **Chronological Timeline**: `2024-01-01` to `2024-04-30` (`5` time steps)

## 1. Dataset Dimensions & Compression Summary

| Dimension | Raw Uncompressed | Quantized Bit-Packed (2-Bit / 16-Bit) | Reduction Ratio |
| :--- | :--- | :--- | :--- |
| **Feature Columns** | `405` columns | `55` columns | **8.0x fewer fields** |
| **Record Count** | `5` rows | `5` rows | 1:1 Synchronized |
| **Storage Size** | `34,622 bytes` | `3,062 bytes` | **91.16% space saved** |
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
| **`astro_jupiter`** | 60 | `min`, `min`, `min`, `min`, ... (+56 more) |
| **`astro_mars`** | 60 | `min`, `min`, `min`, `min`, ... (+56 more) |
| **`astro_mercury`** | 60 | `min`, `min`, `min`, `min`, ... (+56 more) |
| **`astro_moon`** | 60 | `min`, `min`, `min`, `min`, ... (+56 more) |
| **`astro_saturn`** | 60 | `min`, `min`, `min`, `min`, ... (+56 more) |
| **`astro_sun`** | 40 | `min`, `min`, `min`, `min`, ... (+36 more) |
| **`astro_venus`** | 60 | `min`, `min`, `min`, `min`, ... (+56 more) |

## 4. Container Decodification Matrix & Quantile Codebook

This matrix allows 100% exact decompression of packed integer fields into their discrete quantile bins `[0, 1, 2, 3]`.

### Container: `packed_astro_container_000` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_ra_icrf_min` | `9.591` | `37.406` | `280.57` |
| `Bits 2-3` | `>> 2` | `astro_sun_dec_icrf_min` | `-17.673` | `-7.6091` | `4.1286` |
| `Bits 4-5` | `>> 4` | `astro_sun_ra_app_min` | `9.8966` | `37.732` | `280.92` |
| `Bits 6-7` | `>> 6` | `astro_sun_dec_app_min` | `-17.585` | `-7.4844` | `4.2592` |
| `Bits 8-9` | `>> 8` | `astro_sun_azim_min` | `115.96` | `124.46` | `131.37` |
| `Bits 10-11` | `>> 10` | `astro_sun_elev_min` | `21.672` | `30.091` | `40.585` |
| `Bits 12-13` | `>> 12` | `astro_sun_app_mag_min` | `-26.775` | `-26.762` | `-26.744` |
| `Bits 14-15` | `>> 14` | `astro_sun_dist_min` | `0.98507` | `0.99081` | `0.99892` |

### Container: `packed_astro_container_001` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_dist_rate_min` | `0.0084881` | `0.1926` | `0.23974` |
| `Bits 2-3` | `>> 2` | `astro_sun_illum_frac_min` | `0.2074` | `0.3032` | `0.5771` |
| `Bits 4-5` | `>> 4` | `astro_moon_ra_icrf_min` | `6.8299` | `7.6241` | `11.134` |
| `Bits 6-7` | `>> 6` | `astro_moon_dec_icrf_min` | `-29.167` | `-29.12` | `-28.98` |
| `Bits 8-9` | `>> 8` | `astro_moon_ra_app_min` | `7.1343` | `7.9291` | `11.441` |
| `Bits 10-11` | `>> 10` | `astro_moon_dec_app_min` | `-29.151` | `-29.13` | `-28.985` |
| `Bits 12-13` | `>> 12` | `astro_moon_azim_min` | `3.0435` | `5.7209` | `8.8862` |
| `Bits 14-15` | `>> 14` | `astro_moon_elev_min` | `-39.028` | `-27.059` | `-24.882` |

### Container: `packed_astro_container_002` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_app_mag_min` | `-12.524` | `-12.495` | `-12.463` |
| `Bits 2-3` | `>> 2` | `astro_moon_surf_bright_min` | `3.457` | `3.46` | `3.491` |
| `Bits 4-5` | `>> 4` | `astro_moon_dist_min` | `0.002369` | `0.0023822` | `0.0024186` |
| `Bits 6-7` | `>> 6` | `astro_moon_dist_rate_min` | `-0.30988` | `-0.27994` | `-0.24584` |
| `Bits 8-9` | `>> 8` | `astro_moon_helio_dist_min` | `0.98416` | `0.99062` | `0.99882` |
| `Bits 10-11` | `>> 10` | `astro_moon_helio_dist_rate_min` | `-0.64447` | `-0.51557` | `-0.48595` |
| `Bits 12-13` | `>> 12` | `astro_moon_phase_angle_min` | `3.3732` | `4.6369` | `5.4035` |
| `Bits 14-15` | `>> 14` | `astro_moon_elong_min` | `5.2067` | `6.3027` | `8.6962` |

### Container: `packed_astro_container_003` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_illum_frac_min` | `0.2074` | `0.3032` | `0.5771` |
| `Bits 2-3` | `>> 2` | `astro_mars_ra_icrf_min` | `266.7` | `291.27` | `315.36` |
| `Bits 4-5` | `>> 4` | `astro_mars_dec_icrf_min` | `-22.836` | `-18.049` | `-10.481` |
| `Bits 6-7` | `>> 6` | `astro_mars_ra_app_min` | `267.05` | `291.62` | `315.7` |
| `Bits 8-9` | `>> 8` | `astro_mars_dec_app_min` | `-22.79` | `-17.956` | `-10.358` |
| `Bits 10-11` | `>> 10` | `astro_mars_azim_min` | `159.62` | `163.84` | `170.17` |
| `Bits 12-13` | `>> 12` | `astro_mars_elev_min` | `25.696` | `31.708` | `40.383` |
| `Bits 14-15` | `>> 14` | `astro_mars_app_mag_min` | `1.172` | `1.184` | `1.216` |

### Container: `packed_astro_container_004` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_surf_bright_min` | `4.013` | `4.027` | `4.044` |
| `Bits 2-3` | `>> 2` | `astro_mars_dist_min` | `1.9841` | `2.098` | `2.2136` |
| `Bits 4-5` | `>> 4` | `astro_mars_dist_rate_min` | `-6.7344` | `-6.6724` | `-6.511` |
| `Bits 6-7` | `>> 6` | `astro_mars_helio_dist_min` | `1.3822` | `1.3926` | `1.4145` |
| `Bits 8-9` | `>> 8` | `astro_mars_helio_dist_rate_min` | `-1.9691` | `-1.5349` | `-0.92946` |
| `Bits 10-11` | `>> 10` | `astro_mars_phase_angle_min` | `13.976` | `19.207` | `24.017` |
| `Bits 12-13` | `>> 12` | `astro_mars_elong_min` | `20.737` | `27.991` | `34.552` |
| `Bits 14-15` | `>> 14` | `astro_mars_illum_frac_min` | `0.2074` | `0.3032` | `0.5771` |

### Container: `packed_astro_container_005` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_ra_icrf_min` | `34.857` | `38.85` | `44.585` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_dec_icrf_min` | `12.817` | `14.25` | `16.066` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_ra_app_min` | `35.181` | `39.177` | `44.917` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_dec_app_min` | `12.928` | `14.354` | `16.162` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_azim_min` | `57.861` | `73.924` | `86.78` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_elev_min` | `-16.205` | `2.9528` | `22.332` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_app_mag_min` | `-2.355` | `-2.178` | `-2.065` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_surf_bright_min` | `5.319` | `5.336` | `5.357` |

### Container: `packed_astro_container_006` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_dist_min` | `4.9516` | `5.4114` | `5.773` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_dist_rate_min` | `7.3096` | `16.831` | `24.215` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_helio_dist_min` | `4.9908` | `4.9972` | `5.004` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_helio_dist_rate_min` | `0.35485` | `0.37899` | `0.4033` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_phase_angle_min` | `2.8877` | `6.9252` | `10.01` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_elong_min` | `14.504` | `37.157` | `61.263` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_illum_frac_min` | `0.2074` | `0.3032` | `0.5771` |
| `Bits 14-15` | `>> 14` | `astro_saturn_ra_icrf_min` | `338.38` | `341.76` | `345.12` |

### Container: `packed_astro_container_007` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_dec_icrf_min` | `-10.81` | `-9.4777` | `-8.1568` |
| `Bits 2-3` | `>> 2` | `astro_saturn_ra_app_min` | `338.69` | `342.07` | `345.43` |
| `Bits 4-5` | `>> 4` | `astro_saturn_dec_app_min` | `-10.688` | `-9.3533` | `-8.0294` |
| `Bits 6-7` | `>> 6` | `astro_saturn_azim_min` | `113.07` | `132.68` | `160.64` |
| `Bits 8-9` | `>> 8` | `astro_saturn_elev_min` | `10.585` | `28.747` | `41.298` |
| `Bits 10-11` | `>> 10` | `astro_saturn_app_mag_min` | `0.955` | `0.956` | `1.054` |
| `Bits 12-13` | `>> 12` | `astro_saturn_surf_bright_min` | `6.646` | `6.701` | `6.77` |
| `Bits 14-15` | `>> 14` | `astro_saturn_dist_min` | `10.28` | `10.295` | `10.596` |

### Container: `packed_astro_container_008` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_dist_rate_min` | `-22.885` | `-12.964` | `-0.36141` |
| `Bits 2-3` | `>> 2` | `astro_saturn_helio_dist_min` | `9.7037` | `9.7124` | `9.7211` |
| `Bits 4-5` | `>> 4` | `astro_saturn_helio_dist_rate_min` | `-0.50336` | `-0.5007` | `-0.49735` |
| `Bits 6-7` | `>> 6` | `astro_saturn_phase_angle_min` | `0.1906` | `2.6092` | `2.7031` |
| `Bits 8-9` | `>> 8` | `astro_saturn_elong_min` | `1.8913` | `26.689` | `27.326` |
| `Bits 10-11` | `>> 10` | `astro_saturn_illum_frac_min` | `0.2074` | `0.3032` | `0.5771` |
| `Bits 12-13` | `>> 12` | `astro_mercury_ra_icrf_min` | `14.878` | `16.004` | `261.33` |
| `Bits 14-15` | `>> 14` | `astro_mercury_dec_icrf_min` | `-22.595` | `-8.6362` | `4.4464` |

### Container: `packed_astro_container_009` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mercury_ra_app_min` | `15.186` | `16.312` | `261.68` |
| `Bits 2-3` | `>> 2` | `astro_mercury_dec_app_min` | `-22.544` | `-8.5102` | `4.5747` |
| `Bits 4-5` | `>> 4` | `astro_mercury_azim_min` | `103.46` | `131.25` | `153.11` |
| `Bits 6-7` | `>> 6` | `astro_mercury_elev_min` | `25.278` | `28.088` | `36.957` |
| `Bits 8-9` | `>> 8` | `astro_mercury_app_mag_min` | `-1.76` | `-0.316` | `0.998` |
| `Bits 10-11` | `>> 10` | `astro_mercury_surf_bright_min` | `1.445` | `2.883` | `3.791` |
| `Bits 12-13` | `>> 12` | `astro_mercury_dist_min` | `0.6852` | `0.76972` | `0.77753` |
| `Bits 14-15` | `>> 14` | `astro_mercury_dist_rate_min` | `-38.196` | `-10.522` | `18.129` |

### Container: `packed_astro_container_010` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mercury_helio_dist_min` | `0.34246` | `0.35363` | `0.37899` |
| `Bits 2-3` | `>> 2` | `astro_mercury_helio_dist_rate_min` | `-10.003` | `-0.15454` | `0.81244` |
| `Bits 4-5` | `>> 4` | `astro_mercury_phase_angle_min` | `5.9147` | `43.287` | `118.41` |
| `Bits 6-7` | `>> 6` | `astro_mercury_elong_min` | `2.2128` | `2.2252` | `18.011` |
| `Bits 8-9` | `>> 8` | `astro_mercury_illum_frac_min` | `0.2074` | `0.3032` | `0.5771` |
| `Bits 10-11` | `>> 10` | `astro_venus_ra_icrf_min` | `28.651` | `240.61` | `279.82` |
| `Bits 12-13` | `>> 12` | `astro_venus_dec_icrf_min` | `-22.442` | `-16.664` | `-4.0066` |
| `Bits 14-15` | `>> 14` | `astro_venus_ra_app_min` | `28.968` | `240.95` | `280.18` |

### Container: `packed_astro_container_011` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_dec_app_min` | `-22.421` | `-16.566` | `-3.8752` |
| `Bits 2-3` | `>> 2` | `astro_venus_azim_min` | `130.96` | `147.57` | `160.04` |
| `Bits 4-5` | `>> 4` | `astro_venus_elev_min` | `28.327` | `32.205` | `42.015` |
| `Bits 6-7` | `>> 6` | `astro_venus_app_mag_min` | `-3.946` | `-3.893` | `-3.885` |
| `Bits 8-9` | `>> 8` | `astro_venus_surf_bright_min` | `0.802` | `0.882` | `0.976` |
| `Bits 10-11` | `>> 10` | `astro_venus_dist_min` | `1.3569` | `1.5037` | `1.6195` |
| `Bits 12-13` | `>> 12` | `astro_venus_dist_rate_min` | `3.3157` | `5.6358` | `7.5761` |
| `Bits 14-15` | `>> 14` | `astro_venus_helio_dist_min` | `0.72434` | `0.72523` | `0.72548` |

### Container: `packed_astro_container_012` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_helio_dist_rate_min` | `-0.21161` | `-0.064952` | `0.12354` |
| `Bits 2-3` | `>> 2` | `astro_venus_phase_angle_min` | `13.73` | `24.303` | `34.59` |
| `Bits 4-5` | `>> 4` | `astro_venus_elong_min` | `9.8445` | `17.459` | `24.639` |
| `Bits 6-7` | `>> 6` | `astro_venus_illum_frac_min` | `0.2074` | `0.3032` | `0.5771` |
| `Bits 8-9` | `>> 8` | `astro_sun_ra_icrf_max` | `38.36` | `311.67` | `341.12` |
| `Bits 10-11` | `>> 10` | `astro_sun_dec_icrf_max` | `-7.9879` | `3.7408` | `14.442` |
| `Bits 12-13` | `>> 12` | `astro_sun_ra_app_max` | `38.687` | `312.01` | `341.43` |
| `Bits 14-15` | `>> 14` | `astro_sun_dec_app_max` | `-7.8639` | `3.8717` | `14.55` |

### Container: `packed_astro_container_013` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_azim_max` | `124.2` | `131.16` | `137.37` |
| `Bits 2-3` | `>> 2` | `astro_sun_elev_max` | `29.757` | `40.241` | `49.239` |
| `Bits 4-5` | `>> 4` | `astro_sun_app_mag_max` | `-26.763` | `-26.745` | `-26.727` |
| `Bits 6-7` | `>> 6` | `astro_sun_dist_max` | `0.99056` | `0.99863` | `1.007` |
| `Bits 8-9` | `>> 8` | `astro_sun_dist_rate_max` | `0.18655` | `0.24257` | `0.27679` |
| `Bits 10-11` | `>> 10` | `astro_sun_illum_frac_max` | `99.778` | `99.837` | `99.913` |
| `Bits 12-13` | `>> 12` | `astro_moon_ra_icrf_max` | `347.01` | `353.63` | `354.16` |
| `Bits 14-15` | `>> 14` | `astro_moon_dec_icrf_max` | `27.355` | `27.461` | `27.667` |

### Container: `packed_astro_container_014` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_ra_app_max` | `347.32` | `353.93` | `354.47` |
| `Bits 2-3` | `>> 2` | `astro_moon_dec_app_max` | `27.355` | `27.468` | `27.649` |
| `Bits 4-5` | `>> 4` | `astro_moon_azim_max` | `348.4` | `350.87` | `352.89` |
| `Bits 6-7` | `>> 6` | `astro_moon_elev_max` | `22.216` | `27.076` | `30.795` |
| `Bits 8-9` | `>> 8` | `astro_moon_app_mag_max` | `-4.978` | `-4.766` | `-4.641` |
| `Bits 10-11` | `>> 10` | `astro_moon_surf_bright_max` | `6.332` | `6.341` | `6.364` |
| `Bits 12-13` | `>> 12` | `astro_moon_dist_max` | `0.0027157` | `0.002733` | `0.0027412` |
| `Bits 14-15` | `>> 14` | `astro_moon_dist_rate_max` | `0.2625` | `0.29596` | `0.33569` |

### Container: `packed_astro_container_015` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_helio_dist_max` | `0.99252` | `1.0004` | `1.0081` |
| `Bits 2-3` | `>> 2` | `astro_moon_helio_dist_rate_max` | `1.0717` | `1.2794` | `1.3811` |
| `Bits 4-5` | `>> 4` | `astro_moon_phase_angle_max` | `171.28` | `173.68` | `174.78` |
| `Bits 6-7` | `>> 6` | `astro_moon_elong_max` | `174.58` | `175.35` | `176.62` |
| `Bits 8-9` | `>> 8` | `astro_moon_illum_frac_max` | `99.778` | `99.837` | `99.913` |
| `Bits 10-11` | `>> 10` | `astro_mars_ra_icrf_max` | `314.58` | `337.4` | `359.03` |
| `Bits 12-13` | `>> 12` | `astro_mars_dec_icrf_max` | `-18.26` | `-10.764` | `-1.8007` |
| `Bits 14-15` | `>> 14` | `astro_mars_ra_app_max` | `290.81` | `314.92` | `337.72` |

### Container: `packed_astro_container_016` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_dec_app_max` | `-18.169` | `-10.642` | `-1.6676` |
| `Bits 2-3` | `>> 2` | `astro_mars_azim_max` | `163.68` | `169.9` | `180.16` |
| `Bits 4-5` | `>> 4` | `astro_mars_elev_max` | `31.457` | `40.068` | `49.582` |
| `Bits 6-7` | `>> 6` | `astro_mars_app_mag_max` | `1.184` | `1.29` | `1.332` |
| `Bits 8-9` | `>> 8` | `astro_mars_surf_bright_max` | `4.125` | `4.187` | `4.222` |
| `Bits 10-11` | `>> 10` | `astro_mars_dist_max` | `2.0942` | `2.2098` | `2.3227` |
| `Bits 12-13` | `>> 12` | `astro_mars_dist_rate_max` | `-6.5135` | `-6.5092` | `-6.3843` |
| `Bits 14-15` | `>> 14` | `astro_mars_helio_dist_max` | `1.392` | `1.4136` | `1.4442` |

### Container: `packed_astro_container_017` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_helio_dist_rate_max` | `-1.5524` | `-0.95187` | `-0.23626` |
| `Bits 2-3` | `>> 2` | `astro_mars_phase_angle_max` | `19.039` | `23.865` | `28.216` |
| `Bits 4-5` | `>> 4` | `astro_mars_elong_max` | `27.762` | `34.343` | `40.459` |
| `Bits 6-7` | `>> 6` | `astro_mars_illum_frac_max` | `99.778` | `99.837` | `99.913` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_ra_icrf_max` | `38.684` | `44.374` | `51.134` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_dec_icrf_max` | `14.194` | `16.003` | `17.864` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_ra_app_max` | `39.011` | `44.705` | `51.472` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_dec_app_max` | `14.299` | `16.1` | `17.949` |

### Container: `packed_astro_container_018` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_azim_max` | `73.462` | `86.365` | `99.539` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_elev_max` | `2.3034` | `21.693` | `40.494` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_app_mag_max` | `-2.183` | `-2.068` | `-2.008` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_surf_bright_max` | `5.335` | `5.359` | `5.372` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_dist_max` | `5.3972` | `5.7632` | `5.9794` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_dist_rate_max` | `16.543` | `24.025` | `27.553` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_helio_dist_max` | `4.997` | `5.0037` | `5.0109` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_helio_dist_rate_max` | `0.37741` | `0.40126` | `0.42527` |

### Container: `packed_astro_container_019` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_phase_angle_max` | `6.8022` | `9.93` | `11.361` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_elong_max` | `36.382` | `60.428` | `86.596` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_illum_frac_max` | `99.778` | `99.837` | `99.913` |
| `Bits 6-7` | `>> 6` | `astro_saturn_ra_icrf_max` | `341.65` | `345.01` | `347.91` |
| `Bits 8-9` | `>> 8` | `astro_saturn_dec_icrf_max` | `-9.523` | `-8.1986` | `-7.0762` |
| `Bits 10-11` | `>> 10` | `astro_saturn_ra_app_max` | `341.96` | `345.32` | `348.22` |
| `Bits 12-13` | `>> 12` | `astro_saturn_dec_app_max` | `-9.3987` | `-8.0712` | `-6.946` |
| `Bits 14-15` | `>> 14` | `astro_saturn_azim_max` | `131.92` | `159.54` | `195.35` |

### Container: `packed_astro_container_020` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_elev_max` | `28.208` | `41.024` | `42.969` |
| `Bits 2-3` | `>> 2` | `astro_saturn_app_mag_max` | `0.991` | `1.053` | `1.072` |
| `Bits 4-5` | `>> 4` | `astro_saturn_surf_bright_max` | `6.727` | `6.766` | `6.851` |
| `Bits 6-7` | `>> 6` | `astro_saturn_dist_max` | `10.589` | `10.6` | `10.711` |
| `Bits 8-9` | `>> 8` | `astro_saturn_dist_rate_max` | `-13.35` | `-0.79846` | `12.098` |
| `Bits 10-11` | `>> 10` | `astro_saturn_helio_dist_max` | `9.7121` | `9.7208` | `9.7293` |
| `Bits 12-13` | `>> 12` | `astro_saturn_helio_dist_rate_max` | `-0.49896` | `-0.49544` | `-0.49184` |
| `Bits 14-15` | `>> 14` | `astro_saturn_phase_angle_max` | `2.6221` | `4.6406` | `4.7356` |

### Container: `packed_astro_container_021` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_elong_max` | `26.454` | `52.731` | `53.221` |
| `Bits 2-3` | `>> 2` | `astro_saturn_illum_frac_max` | `99.778` | `99.837` | `99.913` |
| `Bits 4-5` | `>> 4` | `astro_mercury_ra_icrf_max` | `23.735` | `292.18` | `342.32` |
| `Bits 6-7` | `>> 6` | `astro_mercury_dec_icrf_max` | `-9.4274` | `4.4509` | `13.065` |
| `Bits 8-9` | `>> 8` | `astro_mercury_ra_app_max` | `24.052` | `292.53` | `342.63` |
| `Bits 10-11` | `>> 10` | `astro_mercury_dec_app_max` | `-9.3026` | `4.579` | `13.188` |
| `Bits 12-13` | `>> 12` | `astro_mercury_azim_max` | `152.12` | `153.98` | `157.12` |
| `Bits 14-15` | `>> 14` | `astro_mercury_elev_max` | `28.79` | `36.286` | `52.715` |

### Container: `packed_astro_container_022` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mercury_app_mag_max` | `0.508` | `0.769` | `1.087` |
| `Bits 2-3` | `>> 2` | `astro_mercury_surf_bright_max` | `3.51` | `3.644` | `4.254` |
| `Bits 4-5` | `>> 4` | `astro_mercury_dist_max` | `0.74726` | `1.2703` | `1.3613` |
| `Bits 6-7` | `>> 6` | `astro_mercury_dist_rate_max` | `17.328` | `20.977` | `22.578` |
| `Bits 8-9` | `>> 8` | `astro_mercury_helio_dist_max` | `0.46478` | `0.46631` | `0.46669` |
| `Bits 10-11` | `>> 10` | `astro_mercury_helio_dist_rate_max` | `1.3112` | `9.5409` | `10.059` |
| `Bits 12-13` | `>> 12` | `astro_mercury_phase_angle_max` | `117.4` | `120.79` | `121.96` |
| `Bits 14-15` | `>> 14` | `astro_mercury_elong_max` | `18.702` | `22.786` | `23.499` |

### Container: `packed_astro_container_023` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mercury_illum_frac_max` | `99.778` | `99.837` | `99.913` |
| `Bits 2-3` | `>> 2` | `astro_venus_ra_icrf_max` | `278.49` | `317.59` | `353.27` |
| `Bits 4-5` | `>> 4` | `astro_venus_dec_icrf_max` | `-16.993` | `-4.4863` | `9.9547` |
| `Bits 6-7` | `>> 6` | `astro_venus_ra_app_max` | `278.84` | `317.92` | `353.57` |
| `Bits 8-9` | `>> 8` | `astro_venus_dec_app_max` | `-16.897` | `-4.3552` | `10.073` |
| `Bits 10-11` | `>> 10` | `astro_venus_azim_max` | `147.1` | `159.65` | `171.12` |
| `Bits 12-13` | `>> 12` | `astro_venus_elev_max` | `32.468` | `41.645` | `51.738` |
| `Bits 14-15` | `>> 14` | `astro_venus_app_mag_max` | `-3.894` | `-3.885` | `-3.876` |

### Container: `packed_astro_container_024` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_surf_bright_max` | `0.879` | `0.973` | `1.071` |
| `Bits 2-3` | `>> 2` | `astro_venus_dist_max` | `1.4993` | `1.6161` | `1.6969` |
| `Bits 4-5` | `>> 4` | `astro_venus_dist_rate_max` | `5.5662` | `7.5158` | `9.2684` |
| `Bits 6-7` | `>> 6` | `astro_venus_helio_dist_max` | `0.72535` | `0.72748` | `0.72798` |
| `Bits 8-9` | `>> 8` | `astro_venus_helio_dist_rate_max` | `-0.071205` | `0.11793` | `0.23077` |
| `Bits 10-11` | `>> 10` | `astro_venus_phase_angle_max` | `23.958` | `34.247` | `44.772` |
| `Bits 12-13` | `>> 12` | `astro_venus_elong_max` | `17.212` | `24.407` | `31.188` |
| `Bits 14-15` | `>> 14` | `astro_venus_illum_frac_max` | `99.778` | `99.837` | `99.913` |

### Container: `packed_astro_container_025` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_ra_icrf_mean` | `37.883` | `235.43` | `296.3` |
| `Bits 2-3` | `>> 2` | `astro_sun_dec_icrf_mean` | `-13.072` | `-1.9533` | `9.4645` |
| `Bits 4-5` | `>> 4` | `astro_sun_ra_app_mean` | `38.21` | `235.74` | `296.65` |
| `Bits 6-7` | `>> 6` | `astro_sun_dec_app_mean` | `-12.964` | `-1.8232` | `9.586` |
| `Bits 8-9` | `>> 8` | `astro_sun_azim_mean` | `120.21` | `127.89` | `134.41` |
| `Bits 10-11` | `>> 10` | `astro_sun_elev_mean` | `25.422` | `35.143` | `45.161` |
| `Bits 12-13` | `>> 12` | `astro_sun_app_mag_mean` | `-26.769` | `-26.754` | `-26.736` |
| `Bits 14-15` | `>> 14` | `astro_sun_dist_mean` | `0.98758` | `0.99463` | `1.003` |

### Container: `packed_astro_container_026` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_dist_rate_mean` | `0.094653` | `0.23402` | `0.24116` |
| `Bits 2-3` | `>> 2` | `astro_sun_illum_frac_mean` | `53.515` | `53.703` | `53.973` |
| `Bits 4-5` | `>> 4` | `astro_moon_ra_icrf_mean` | `177.88` | `179.31` | `188.15` |
| `Bits 6-7` | `>> 6` | `astro_moon_dec_icrf_mean` | `-3.0522` | `-2.1469` | `-0.63902` |
| `Bits 8-9` | `>> 8` | `astro_moon_ra_app_mean` | `178.22` | `179.64` | `188.5` |
| `Bits 10-11` | `>> 10` | `astro_moon_dec_app_mean` | `-3.0627` | `-2.1648` | `-0.65886` |
| `Bits 12-13` | `>> 12` | `astro_moon_azim_mean` | `177.35` | `188.65` | `188.82` |
| `Bits 14-15` | `>> 14` | `astro_moon_elev_mean` | `-4.7618` | `-2.7134` | `-0.20268` |

### Container: `packed_astro_container_027` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_app_mag_mean` | `-9.8159` | `-9.815` | `-9.7718` |
| `Bits 2-3` | `>> 2` | `astro_moon_surf_bright_mean` | `4.9978` | `5.0049` | `5.009` |
| `Bits 4-5` | `>> 4` | `astro_moon_dist_mean` | `0.0025746` | `0.0025816` | `0.0025847` |
| `Bits 6-7` | `>> 6` | `astro_moon_dist_rate_mean` | `0.014702` | `0.024045` | `0.026658` |
| `Bits 8-9` | `>> 8` | `astro_moon_helio_dist_mean` | `0.98786` | `0.99493` | `1.0033` |
| `Bits 10-11` | `>> 10` | `astro_moon_helio_dist_rate_mean` | `0.095482` | `0.32244` | `0.45621` |
| `Bits 12-13` | `>> 12` | `astro_moon_phase_angle_mean` | `84.237` | `84.59` | `85.016` |
| `Bits 14-15` | `>> 14` | `astro_moon_elong_mean` | `94.888` | `95.313` | `95.667` |

### Container: `packed_astro_container_028` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_illum_frac_mean` | `53.515` | `53.703` | `53.973` |
| `Bits 2-3` | `>> 2` | `astro_mars_ra_icrf_mean` | `278.55` | `303.01` | `326.49` |
| `Bits 4-5` | `>> 4` | `astro_mars_dec_icrf_mean` | `-20.802` | `-14.569` | `-6.1941` |
| `Bits 6-7` | `>> 6` | `astro_mars_ra_app_mean` | `278.91` | `303.35` | `326.82` |
| `Bits 8-9` | `>> 8` | `astro_mars_dec_app_mean` | `-20.732` | `-14.46` | `-6.0651` |
| `Bits 10-11` | `>> 10` | `astro_mars_azim_mean` | `161.57` | `166.64` | `174.79` |
| `Bits 12-13` | `>> 12` | `astro_mars_elev_mean` | `28.329` | `35.744` | `45.003` |
| `Bits 14-15` | `>> 14` | `astro_mars_app_mag_mean` | `1.1755` | `1.2377` | `1.2896` |

### Container: `packed_astro_container_029` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_surf_bright_mean` | `4.083` | `4.1041` | `4.1274` |
| `Bits 2-3` | `>> 2` | `astro_mars_dist_mean` | `2.039` | `2.1539` | `2.2687` |
| `Bits 4-5` | `>> 4` | `astro_mars_dist_rate_mean` | `-6.6116` | `-6.5985` | `-6.5101` |
| `Bits 6-7` | `>> 6` | `astro_mars_helio_dist_mean` | `1.3861` | `1.4023` | `1.4288` |
| `Bits 8-9` | `>> 8` | `astro_mars_helio_dist_rate_mean` | `-1.775` | `-1.2546` | `-0.58847` |
| `Bits 10-11` | `>> 10` | `astro_mars_phase_angle_mean` | `16.536` | `21.571` | `26.154` |
| `Bits 12-13` | `>> 12` | `astro_mars_elong_mean` | `24.307` | `31.214` | `37.528` |
| `Bits 14-15` | `>> 14` | `astro_mars_illum_frac_mean` | `53.515` | `53.703` | `53.973` |

### Container: `packed_astro_container_030` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_ra_icrf_mean` | `36.61` | `41.508` | `47.804` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_dec_icrf_mean` | `13.461` | `15.111` | `16.973` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_ra_app_mean` | `36.935` | `41.837` | `48.138` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_dec_app_mean` | `13.569` | `15.212` | `17.063` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_azim_mean` | `66.066` | `80.249` | `92.993` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_elev_mean` | `-7.0272` | `12.347` | `31.477` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_app_mag_mean` | `-2.2638` | `-2.1185` | `-2.0331` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_surf_bright_mean` | `5.3261` | `5.3475` | `5.3668` |

### Container: `packed_astro_container_031` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_dist_mean` | `5.1789` | `5.597` | `5.8888` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_dist_rate_mean` | `12.016` | `20.651` | `26.267` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_helio_dist_mean` | `4.9939` | `5.0004` | `5.0074` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_helio_dist_rate_mean` | `0.36691` | `0.39077` | `0.41365` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_phase_angle_mean` | `4.8903` | `8.525` | `10.846` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_elong_mean` | `25.358` | `48.657` | `73.741` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_illum_frac_mean` | `53.515` | `53.703` | `53.973` |
| `Bits 14-15` | `>> 14` | `astro_saturn_ra_icrf_mean` | `340` | `343.41` | `346.57` |

### Container: `packed_astro_container_032` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_dec_icrf_mean` | `-10.173` | `-8.83` | `-7.5938` |
| `Bits 2-3` | `>> 2` | `astro_saturn_ra_app_mean` | `340.31` | `343.72` | `346.88` |
| `Bits 4-5` | `>> 4` | `astro_saturn_dec_app_mean` | `-10.05` | `-8.7041` | `-7.4649` |
| `Bits 6-7` | `>> 6` | `astro_saturn_azim_mean` | `122.06` | `145.34` | `177.74` |
| `Bits 8-9` | `>> 8` | `astro_saturn_elev_mean` | `19.667` | `35.481` | `42.88` |
| `Bits 10-11` | `>> 10` | `astro_saturn_app_mag_mean` | `0.9807` | `1.0153` | `1.0681` |
| `Bits 12-13` | `>> 12` | `astro_saturn_surf_bright_mean` | `6.7137` | `6.7156` | `6.8121` |
| `Bits 14-15` | `>> 14` | `astro_saturn_dist_mean` | `10.448` | `10.461` | `10.67` |

### Container: `packed_astro_container_033` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_dist_rate_mean` | `-18.413` | `-7.01` | `5.9388` |
| `Bits 2-3` | `>> 2` | `astro_saturn_helio_dist_mean` | `9.7079` | `9.7166` | `9.7252` |
| `Bits 4-5` | `>> 4` | `astro_saturn_helio_dist_rate_mean` | `-0.50102` | `-0.49776` | `-0.49444` |
| `Bits 6-7` | `>> 6` | `astro_saturn_phase_angle_mean` | `1.3937` | `3.6828` | `3.7748` |
| `Bits 8-9` | `>> 8` | `astro_saturn_elong_mean` | `13.88` | `39.885` | `40.009` |
| `Bits 10-11` | `>> 10` | `astro_saturn_illum_frac_mean` | `53.515` | `53.703` | `53.973` |
| `Bits 12-13` | `>> 12` | `astro_mercury_ra_icrf_mean` | `18.815` | `126.9` | `273.14` |
| `Bits 14-15` | `>> 14` | `astro_mercury_dec_icrf_mean` | `-17.553` | `3.5415` | `4.4487` |

### Container: `packed_astro_container_034` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mercury_ra_app_mean` | `19.127` | `127.21` | `273.5` |
| `Bits 2-3` | `>> 2` | `astro_mercury_dec_app_mean` | `-17.46` | `3.6698` | `4.5768` |
| `Bits 4-5` | `>> 4` | `astro_mercury_azim_mean` | `126.36` | `145.5` | `153.54` |
| `Bits 6-7` | `>> 6` | `astro_mercury_elev_mean` | `27.221` | `31.253` | `46.801` |
| `Bits 8-9` | `>> 8` | `astro_mercury_app_mag_mean` | `-0.84843` | `-0.13163` | `1.0425` |
| `Bits 10-11` | `>> 10` | `astro_mercury_surf_bright_mean` | `2.3405` | `3.1433` | `4.2285` |
| `Bits 12-13` | `>> 12` | `astro_mercury_dist_mean` | `0.69164` | `1.05` | `1.1135` |
| `Bits 14-15` | `>> 14` | `astro_mercury_dist_rate_mean` | `-4.7752` | `4.9592` | `22.194` |

### Container: `packed_astro_container_035` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mercury_helio_dist_mean` | `0.41512` | `0.4233` | `0.43839` |
| `Bits 2-3` | `>> 2` | `astro_mercury_helio_dist_rate_mean` | `-1.4595` | `0.087298` | `6.6779` |
| `Bits 4-5` | `>> 4` | `astro_mercury_phase_angle_mean` | `57.522` | `71.763` | `119.6` |
| `Bits 6-7` | `>> 6` | `astro_mercury_elong_mean` | `12.017` | `12.789` | `21.703` |
| `Bits 8-9` | `>> 8` | `astro_mercury_illum_frac_mean` | `53.515` | `53.703` | `53.973` |
| `Bits 10-11` | `>> 10` | `astro_venus_ra_icrf_mean` | `70.899` | `259.35` | `298.92` |
| `Bits 12-13` | `>> 12` | `astro_venus_dec_icrf_mean` | `-20.402` | `-10.914` | `3.0353` |
| `Bits 14-15` | `>> 14` | `astro_venus_ra_app_mean` | `71.206` | `259.7` | `299.26` |

### Container: `packed_astro_container_036` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_dec_app_mean` | `-20.342` | `-10.795` | `3.1638` |
| `Bits 2-3` | `>> 2` | `astro_venus_azim_mean` | `139.51` | `153.76` | `165.63` |
| `Bits 4-5` | `>> 4` | `astro_venus_elev_mean` | `29.821` | `36.648` | `47.135` |
| `Bits 6-7` | `>> 6` | `astro_venus_app_mag_mean` | `-3.917` | `-3.885` | `-3.8819` |
| `Bits 8-9` | `>> 8` | `astro_venus_surf_bright_mean` | `0.83897` | `0.9271` | `1.0231` |
| `Bits 10-11` | `>> 10` | `astro_venus_dist_mean` | `1.4303` | `1.5624` | `1.6612` |
| `Bits 12-13` | `>> 12` | `astro_venus_dist_rate_mean` | `4.4653` | `6.5865` | `8.421` |
| `Bits 14-15` | `>> 14` | `astro_venus_helio_dist_mean` | `0.72529` | `0.72606` | `0.72692` |

### Container: `packed_astro_container_037` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_helio_dist_rate_mean` | `-0.14919` | `0.027941` | `0.18696` |
| `Bits 2-3` | `>> 2` | `astro_venus_phase_angle_mean` | `18.882` | `29.28` | `39.641` |
| `Bits 4-5` | `>> 4` | `astro_venus_elong_mean` | `13.562` | `20.965` | `27.945` |
| `Bits 6-7` | `>> 6` | `astro_venus_illum_frac_mean` | `53.515` | `53.703` | `53.973` |
| `Bits 8-9` | `>> 8` | `astro_sun_ra_icrf_median` | `37.883` | `296.4` | `327.23` |
| `Bits 10-11` | `>> 10` | `astro_sun_dec_icrf_median` | `-13.206` | `-1.9633` | `9.5638` |
| `Bits 12-13` | `>> 12` | `astro_sun_ra_app_median` | `38.21` | `296.75` | `327.55` |
| `Bits 14-15` | `>> 14` | `astro_sun_dec_app_median` | `-13.096` | `-1.832` | `9.6866` |

### Container: `packed_astro_container_038` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_sun_azim_median` | `120.28` | `127.94` | `134.42` |
| `Bits 2-3` | `>> 2` | `astro_sun_elev_median` | `25.26` | `35.13` | `45.298` |
| `Bits 4-5` | `>> 4` | `astro_sun_app_mag_median` | `-26.77` | `-26.754` | `-26.736` |
| `Bits 6-7` | `>> 6` | `astro_sun_dist_median` | `0.98746` | `0.99459` | `1.0031` |
| `Bits 8-9` | `>> 8` | `astro_sun_dist_rate_median` | `0.087573` | `0.2281` | `0.24116` |
| `Bits 10-11` | `>> 10` | `astro_sun_illum_frac_median` | `57.196` | `57.465` | `58.052` |
| `Bits 12-13` | `>> 12` | `astro_moon_ra_icrf_median` | `185.14` | `186.5` | `194.44` |
| `Bits 14-15` | `>> 14` | `astro_moon_dec_icrf_median` | `-4.7859` | `-3.8657` | `-2.0323` |

### Container: `packed_astro_container_039` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_ra_app_median` | `185.45` | `186.81` | `194.76` |
| `Bits 2-3` | `>> 2` | `astro_moon_dec_app_median` | `-4.7878` | `-3.8669` | `-2.1674` |
| `Bits 4-5` | `>> 4` | `astro_moon_azim_median` | `191.09` | `197.44` | `201.42` |
| `Bits 6-7` | `>> 6` | `astro_moon_elev_median` | `-4.3249` | `-3.5629` | `-1.1179` |
| `Bits 8-9` | `>> 8` | `astro_moon_app_mag_median` | `-10.424` | `-10.409` | `-10.374` |
| `Bits 10-11` | `>> 10` | `astro_moon_surf_bright_median` | `4.9585` | `4.991` | `5.0345` |
| `Bits 12-13` | `>> 12` | `astro_moon_dist_median` | `0.0025892` | `0.0026042` | `0.0026152` |
| `Bits 14-15` | `>> 14` | `astro_moon_dist_rate_median` | `0.021597` | `0.033309` | `0.037611` |

### Container: `packed_astro_container_040` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_moon_helio_dist_median` | `0.98663` | `0.99374` | `1.0024` |
| `Bits 2-3` | `>> 2` | `astro_moon_helio_dist_rate_median` | `0.089` | `0.3245` | `0.44759` |
| `Bits 4-5` | `>> 4` | `astro_moon_phase_angle_median` | `80.731` | `81.372` | `81.713` |
| `Bits 6-7` | `>> 6` | `astro_moon_elong_median` | `98.137` | `98.477` | `99.12` |
| `Bits 8-9` | `>> 8` | `astro_moon_illum_frac_median` | `57.196` | `57.465` | `58.052` |
| `Bits 10-11` | `>> 10` | `astro_mars_ra_icrf_median` | `278.54` | `303.05` | `326.55` |
| `Bits 12-13` | `>> 12` | `astro_mars_dec_icrf_median` | `-20.942` | `-14.658` | `-6.2234` |
| `Bits 14-15` | `>> 14` | `astro_mars_ra_app_median` | `278.9` | `303.4` | `326.87` |

### Container: `packed_astro_container_041` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_dec_app_median` | `-20.872` | `-14.549` | `-6.0935` |
| `Bits 2-3` | `>> 2` | `astro_mars_azim_median` | `161.53` | `166.51` | `174.58` |
| `Bits 4-5` | `>> 4` | `astro_mars_elev_median` | `28.191` | `35.663` | `45.014` |
| `Bits 6-7` | `>> 6` | `astro_mars_app_mag_median` | `1.1755` | `1.241` | `1.2975` |
| `Bits 8-9` | `>> 8` | `astro_mars_surf_bright_median` | `4.091` | `4.0975` | `4.147` |
| `Bits 10-11` | `>> 10` | `astro_mars_dist_median` | `2.0389` | `2.1538` | `2.269` |
| `Bits 12-13` | `>> 12` | `astro_mars_dist_rate_median` | `-6.6471` | `-6.6067` | `-6.5101` |
| `Bits 14-15` | `>> 14` | `astro_mars_helio_dist_median` | `1.3856` | `1.4018` | `1.4285` |

### Container: `packed_astro_container_042` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mars_helio_dist_rate_median` | `-1.7829` | `-1.2608` | `-0.59158` |
| `Bits 2-3` | `>> 2` | `astro_mars_phase_angle_median` | `16.553` | `21.591` | `26.175` |
| `Bits 4-5` | `>> 4` | `astro_mars_elong_median` | `24.339` | `31.24` | `37.54` |
| `Bits 6-7` | `>> 6` | `astro_mars_illum_frac_median` | `57.196` | `57.465` | `58.052` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_ra_icrf_median` | `36.521` | `41.45` | `47.773` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_dec_icrf_median` | `13.437` | `15.103` | `16.977` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_ra_app_median` | `36.846` | `41.779` | `48.107` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_dec_app_median` | `13.545` | `15.204` | `17.068` |

### Container: `packed_astro_container_043` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_azim_median` | `66.288` | `80.307` | `92.902` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_elev_median` | `-7.0681` | `12.361` | `31.512` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_app_mag_median` | `-2.261` | `-2.116` | `-2.031` |
| `Bits 6-7` | `>> 6` | `astro_jupiter_surf_bright_median` | `5.3255` | `5.3475` | `5.368` |
| `Bits 8-9` | `>> 8` | `astro_jupiter_dist_median` | `5.1814` | `5.6025` | `5.8958` |
| `Bits 10-11` | `>> 10` | `astro_jupiter_dist_rate_median` | `12.062` | `20.77` | `26.479` |
| `Bits 12-13` | `>> 12` | `astro_jupiter_helio_dist_median` | `4.9939` | `5.0004` | `5.0074` |
| `Bits 14-15` | `>> 14` | `astro_jupiter_helio_dist_rate_median` | `0.36664` | `0.39043` | `0.41454` |

### Container: `packed_astro_container_044` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_jupiter_phase_angle_median` | `4.9152` | `8.5786` | `10.935` |
| `Bits 2-3` | `>> 2` | `astro_jupiter_elong_median` | `25.31` | `48.582` | `73.636` |
| `Bits 4-5` | `>> 4` | `astro_jupiter_illum_frac_median` | `57.196` | `57.465` | `58.052` |
| `Bits 6-7` | `>> 6` | `astro_saturn_ra_icrf_median` | `339.99` | `343.42` | `346.6` |
| `Bits 8-9` | `>> 8` | `astro_saturn_dec_icrf_median` | `-10.177` | `-8.8254` | `-7.5812` |
| `Bits 10-11` | `>> 10` | `astro_saturn_ra_app_median` | `340.3` | `343.73` | `346.91` |
| `Bits 12-13` | `>> 12` | `astro_saturn_dec_app_median` | `-10.054` | `-8.6995` | `-7.4523` |
| `Bits 14-15` | `>> 14` | `astro_saturn_azim_median` | `121.81` | `144.9` | `177.59` |

### Container: `packed_astro_container_045` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_elev_median` | `19.814` | `35.808` | `42.88` |
| `Bits 2-3` | `>> 2` | `astro_saturn_app_mag_median` | `0.9865` | `1.0205` | `1.0705` |
| `Bits 4-5` | `>> 4` | `astro_saturn_surf_bright_median` | `6.7165` | `6.7175` | `6.813` |
| `Bits 6-7` | `>> 6` | `astro_saturn_dist_median` | `10.455` | `10.469` | `10.679` |
| `Bits 8-9` | `>> 8` | `astro_saturn_dist_rate_median` | `-18.584` | `-7.0904` | `5.9708` |
| `Bits 10-11` | `>> 10` | `astro_saturn_helio_dist_median` | `9.708` | `9.7166` | `9.7252` |
| `Bits 12-13` | `>> 12` | `astro_saturn_helio_dist_rate_median` | `-0.5009` | `-0.49765` | `-0.49446` |
| `Bits 14-15` | `>> 14` | `astro_saturn_phase_angle_median` | `1.397` | `3.7147` | `3.8056` |

### Container: `packed_astro_container_046` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_saturn_elong_median` | `13.816` | `39.845` | `39.999` |
| `Bits 2-3` | `>> 2` | `astro_saturn_illum_frac_median` | `57.196` | `57.465` | `58.052` |
| `Bits 4-5` | `>> 4` | `astro_mercury_ra_icrf_median` | `18.142` | `20.806` | `271.31` |
| `Bits 6-7` | `>> 6` | `astro_mercury_dec_icrf_median` | `-18.409` | `4.2544` | `4.4487` |
| `Bits 8-9` | `>> 8` | `astro_mercury_ra_app_median` | `18.453` | `21.119` | `271.66` |
| `Bits 10-11` | `>> 10` | `astro_mercury_dec_app_median` | `-18.313` | `4.3853` | `4.5768` |
| `Bits 12-13` | `>> 12` | `astro_mercury_azim_median` | `125.54` | `146.22` | `153.54` |
| `Bits 14-15` | `>> 14` | `astro_mercury_elev_median` | `27.323` | `30.807` | `48.285` |

### Container: `packed_astro_container_047` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mercury_app_mag_median` | `-0.7175` | `-0.211` | `1.0425` |
| `Bits 2-3` | `>> 2` | `astro_mercury_surf_bright_median` | `2.4145` | `3.129` | `4.2285` |
| `Bits 4-5` | `>> 4` | `astro_mercury_dist_median` | `0.69164` | `1.0664` | `1.1447` |
| `Bits 6-7` | `>> 6` | `astro_mercury_dist_rate_median` | `-2.1` | `5.7504` | `22.194` |
| `Bits 8-9` | `>> 8` | `astro_mercury_helio_dist_median` | `0.42203` | `0.43112` | `0.44754` |
| `Bits 10-11` | `>> 10` | `astro_mercury_helio_dist_rate_median` | `-2.4127` | `0.087298` | `7.3599` |
| `Bits 12-13` | `>> 12` | `astro_mercury_phase_angle_median` | `53.898` | `67.282` | `119.6` |
| `Bits 14-15` | `>> 14` | `astro_mercury_elong_median` | `12.194` | `14.533` | `22.108` |

### Container: `packed_astro_container_048` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_mercury_illum_frac_median` | `57.196` | `57.465` | `58.052` |
| `Bits 2-3` | `>> 2` | `astro_venus_ra_icrf_median` | `29.235` | `259.24` | `299.03` |
| `Bits 4-5` | `>> 4` | `astro_venus_dec_icrf_median` | `-20.782` | `-11.1` | `3.0692` |
| `Bits 6-7` | `>> 6` | `astro_venus_ra_app_median` | `29.552` | `259.59` | `299.38` |
| `Bits 8-9` | `>> 8` | `astro_venus_dec_app_median` | `-20.72` | `-10.98` | `3.1997` |
| `Bits 10-11` | `>> 10` | `astro_venus_azim_median` | `139.78` | `153.84` | `165.65` |
| `Bits 12-13` | `>> 12` | `astro_venus_elev_median` | `29.502` | `36.493` | `47.277` |
| `Bits 14-15` | `>> 14` | `astro_venus_app_mag_median` | `-3.9155` | `-3.885` | `-3.8805` |

### Container: `packed_astro_container_049` (`uint16`)
| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Bits 0-1` | `>> 0` | `astro_venus_surf_bright_median` | `0.838` | `0.9265` | `1.023` |
| `Bits 2-3` | `>> 2` | `astro_venus_dist_median` | `1.4315` | `1.5638` | `1.6628` |
| `Bits 4-5` | `>> 4` | `astro_venus_dist_rate_median` | `4.4739` | `6.587` | `8.4145` |
| `Bits 6-7` | `>> 6` | `astro_venus_helio_dist_median` | `0.72529` | `0.72614` | `0.72703` |
| `Bits 8-9` | `>> 8` | `astro_venus_helio_dist_rate_median` | `-0.15352` | `0.028748` | `0.19241` |
| `Bits 10-11` | `>> 10` | `astro_venus_phase_angle_median` | `18.904` | `29.283` | `39.619` |
| `Bits 12-13` | `>> 12` | `astro_venus_elong_median` | `13.58` | `20.983` | `27.963` |
| `Bits 14-15` | `>> 14` | `astro_venus_illum_frac_median` | `57.196` | `57.465` | `58.052` |

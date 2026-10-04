"""Independent magnitude thresholds shared by CLI, data builders and reports.

Legacy energy_magnitude/location_magnitude remain aliases. An explicit energy
training threshold stays fixed when validation is relaxed; without one, legacy
energy training follows the effective validation threshold. Refit uses the same
training label threshold. Download coverage must include every enabled floor.
"""
import math


OPTIONS={
    'download_floor':'Minimum magnitude downloaded from the earthquake catalog',
    'energy_training_magnitude':'Energy training and forecast-refit label threshold',
    'energy_validation_magnitude':'Requested energy validation event threshold',
    'energy_validation_min_magnitude':'Lowest permitted energy validation threshold; equal to requested disables relaxation',
    'location_training_magnitude':'Location training event threshold',
    'location_validation_magnitude':'Requested location validation event threshold',
    'location_validation_min_magnitude':'Lowest permitted location validation threshold; equal to requested disables relaxation',
}


def policy(config):
    download=float(config.get('download_floor',5.5))
    ev=float(config.get('energy_validation_magnitude',config.get('energy_magnitude',7.7)))
    lt=float(config.get('location_training_magnitude',config.get('location_magnitude',6.8)))
    lv=float(config.get('location_validation_magnitude',lt))
    return {'download_floor':download,'energy_training_magnitude':float(config.get('energy_training_magnitude',ev)),
            'energy_validation_magnitude':ev,
            'energy_validation_min_magnitude':float(config.get('energy_validation_min_magnitude',max(download,ev-float(config.get('maximum_energy_target_reduction',.5))))),
            'location_training_magnitude':lt,'location_validation_magnitude':lv,
            'location_validation_min_magnitude':float(config.get('location_validation_min_magnitude',download))}


def validate(config):
    p=policy(config)
    for name,value in p.items():
        if not math.isfinite(value):raise ValueError(f'{name} must be finite')
        if value<p['download_floor']:raise ValueError(f'{name} is below download_floor; download the required catalog first')
    for scope in ['energy','location']:
        if p[scope+'_validation_min_magnitude']>p[scope+'_validation_magnitude']:
            raise ValueError(f'{scope} validation minimum exceeds its requested threshold')
    step=float(config.get('magnitude_step',.1))
    if not math.isfinite(step) or step<=0:raise ValueError('magnitude_step must be positive and finite')
    reduction=float(config.get('maximum_energy_target_reduction',.5))
    if not math.isfinite(reduction) or reduction<0:raise ValueError('maximum_energy_target_reduction must be nonnegative and finite')
    return p


def energy_training(config,effective_validation):
    return float(config.get('energy_training_magnitude',effective_validation))

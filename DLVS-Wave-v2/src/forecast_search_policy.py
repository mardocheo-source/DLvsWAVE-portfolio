"""Validate optional compact-search and resource settings for Japan and World."""
import math


def validate(config):
    for family,counts in config.get('energy_feature_counts',{}).items():
        if family not in ['kan','deep_learning','lcs'] or not isinstance(counts,list) or not counts or any(type(x) is not int or x<1 for x in counts):
            raise ValueError('energy_feature_counts needs positive integer lists for kan/deep_learning/lcs')
    for key in ['max_parallel_workers','minimum_available_memory_mb','astronomy_shift_max_base_fields']:
        if key in config and (type(config[key]) is not int or config[key]<1):
            raise ValueError(key+' must be a positive integer')
    for key in ['energy_branch_max_seconds','maximum_seconds']:
        if key in config and (not isinstance(config[key],(int,float)) or not math.isfinite(config[key]) or config[key]<=0):
            raise ValueError(key+' must be finite and positive')

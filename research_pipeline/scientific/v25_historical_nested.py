#!/usr/bin/env python3
"""V25 deep-history wrapper with only body groups defensible from 1611 onward."""
from __future__ import annotations

import v23_hokkaido_extended_search as ext
import v24_hokkaido_nested_rolling as nested


DEEP_PRIMARY = {"sun", "mercury", "venus", "moon", "mars", "jupiter", "uranus", "io", "europa", "ganymede", "callisto"}
PLANETS_LUMINARIES = {"sun", "mercury", "venus", "moon", "mars", "jupiter", "uranus"}
LUMINARIES_INNER = {"sun", "moon", "mercury", "venus", "mars"}
JUPITER_SYSTEM = {"jupiter", "io", "europa", "ganymede", "callisto"}


def main() -> None:
    ext.REGION = (38.8, 46.0, 140.0, 150.5)
    ext.BODY_GROUPS = {
        "deep_primary_all": DEEP_PRIMARY,
        "planets_luminaries": PLANETS_LUMINARIES,
        "luminaries_inner": LUMINARIES_INNER,
        "jupiter_system": JUPITER_SYSTEM,
        "no_sun": "exclude:sun",
        "no_moon": "exclude:moon",
        "no_inner_planets": "exclude:mercury,venus,mars",
        "no_jupiter_system": "exclude:jupiter,io,europa,ganymede,callisto",
    }
    nested.main()


if __name__ == "__main__":
    main()

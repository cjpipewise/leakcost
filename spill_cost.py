"""Spill response and damage cost model.

Implements Etkin (2004) EPA BOSCEM as three separate cost streams - response,
socioeconomic damage, environmental damage - each with its own base table and
its own modifier chain, then adds a separate excavation-based model for
produced water, which Etkin does not cover.

All volumes SI. Etkin's tables are per US gallon and are converted internally.
"""

import math

import spill_config as cfg

GAL_PER_M3 = 264.1721
M3_PER_BBL = 0.1589873


def _loglog(x, xs, ys):
    lx = math.log10(max(x, 1e-12))
    lxs = [math.log10(v) for v in xs]
    lys = [math.log10(max(v, 1e-12)) for v in ys]
    if lx <= lxs[0]:
        return 10.0 ** lys[0]
    if lx >= lxs[-1]:
        return 10.0 ** lys[-1]
    i = max(j for j in range(len(lxs) - 1) if lxs[j] <= lx)
    t = (lx - lxs[i]) / (lxs[i + 1] - lxs[i])
    return 10.0 ** (lys[i] + t * (lys[i + 1] - lys[i]))


def inflation_factor(base_year, target_year, table=None, forward=None):
    table = table or cfg.CPI_US
    forward = cfg.CPI_FORWARD_RATE if forward is None else forward
    years = sorted(table)

    def index_at(y):
        if y in table:
            return table[y]
        if y < years[0]:
            return table[years[0]] / ((1.0 + forward) ** (years[0] - y))
        if y > years[-1]:
            return table[years[-1]] * ((1.0 + forward) ** (y - years[-1]))
        lo = max(v for v in years if v < y)
        hi = min(v for v in years if v > y)
        t = (y - lo) / (hi - lo)
        return table[lo] + t * (table[hi] - table[lo])

    return index_at(target_year) / index_at(base_year)


def spill_cost(volume_m3, substance, terrain, jurisdiction,
               remoteness_km=0.0, currency='CAD', config=None):
    c = config or cfg

    if volume_m3 <= 0:
        raise ValueError('volume_m3 must be positive')
    if substance not in c.SUBSTANCE_GRADE:
        raise KeyError('unknown substance %r' % substance)
    if terrain not in c.TERRAIN:
        raise KeyError('unknown terrain %r' % terrain)
    if jurisdiction not in c.JURISDICTION:
        raise KeyError('unknown jurisdiction %r' % jurisdiction)
    if currency not in ('CAD', 'USD'):
        raise ValueError("currency must be 'CAD' or 'USD'")

    t = c.TERRAIN[terrain]
    juris = c.JURISDICTION[jurisdiction]
    target = c.MODEL['target_year']
    eff = c.MODEL['recovery_effectiveness']

    remoteness = min(
        1.0 + c.REMOTENESS_A * math.log10(1.0 + remoteness_km / c.REMOTENESS_K0_KM),
        c.REMOTENESS_CAP)

    grade = c.SUBSTANCE_GRADE[substance]
    env_sensitivity = 0.5 * (t['freshwater'] + t['wildlife'])
    juris_ref = juris / c.JURISDICTION[c.JURISDICTION_REFERENCE]

    if grade is None:
        s = c.SALT
        infl = inflation_factor(s['unit_cost_year'], target)
        soil_m3 = volume_m3 * s['soil_per_brine']
        unit = (s['unit_cost_cad_per_m3_soil']
                * (max(soil_m3, 1.0) / s['reference_soil_m3']) ** s['scale_exponent'])
        response_cad = (soil_m3 * unit * s['consulting_uplift'] * t['medium']
                        * remoteness * infl)
        damage_cad = (response_cad * s['damage_ratio']
                      * env_sensitivity / s['damage_reference_sensitivity'])
        response = response_cad * juris_ref / c.USD_TO_CAD
        socio = 0.0
        environmental = damage_cad * juris_ref / c.USD_TO_CAD
        unit_note = 'excavation model'
    else:
        infl = inflation_factor(c.COST_BASE_YEAR, target)
        table = c.RESPONSE_USD_PER_GAL[grade]
        if eff in table:
            resp_gal = _loglog(volume_m3 * GAL_PER_M3, c.VOLUME_ANCHORS_GAL, table[eff])
        else:
            base = _loglog(volume_m3 * GAL_PER_M3, c.VOLUME_ANCHORS_GAL, table[10])
            resp_gal = base * c.EFFECTIVENESS_FACTOR[eff]
        socio_gal = _loglog(volume_m3 * GAL_PER_M3, c.VOLUME_ANCHORS_GAL,
                            c.SOCIOECONOMIC_USD_PER_GAL[grade])
        env_gal = _loglog(volume_m3 * GAL_PER_M3, c.VOLUME_ANCHORS_GAL,
                          c.ENVIRONMENTAL_USD_PER_GAL[grade])
        dmg_adj = c.EFFECTIVENESS_FACTOR[eff]
        gal = volume_m3 * GAL_PER_M3

        response = resp_gal * t['medium'] * remoteness * gal * infl * juris
        socio = socio_gal * t['socio'] * dmg_adj * gal * infl * juris
        environmental = env_gal * env_sensitivity * dmg_adj * gal * infl * juris
        unit_note = 'Etkin %s' % grade.replace('_', ' ')

    response *= c.CALIBRATION
    socio *= c.CALIBRATION
    environmental *= c.CALIBRATION

    total = response + socio + environmental
    floor = (c.MODEL['min_event_cost_cad'] / c.USD_TO_CAD
             * inflation_factor(2026, target) * juris_ref)
    if total < floor:
        scale = floor / total
        response *= scale
        socio *= scale
        environmental *= scale
        total = floor

    rate = c.USD_TO_CAD if currency == 'CAD' else 1.0
    return {
        'volume_m3': volume_m3,
        'currency': currency,
        'basis': unit_note,
        'response': response * rate,
        'socioeconomic': socio * rate,
        'environmental': environmental * rate,
        'total': total * rate,
        'unit_cost_per_m3': total * rate / volume_m3,
        'remoteness_factor': remoteness,
        'env_sensitivity': env_sensitivity,
        'jurisdiction_factor': juris,
        'inflation_factor': infl,
        'at_floor': total <= floor * 1.0000001,
    }

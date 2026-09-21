import math

import numpy as np
import streamlit as st
import streamlit.components.v1 as components

import spill_config as cfg
from spill_cost import spill_cost, M3_PER_BBL
from chart_svg import chart_svg, chart_html, money

st.set_page_config(page_title=cfg.APP_TITLE, layout='wide',
                   initial_sidebar_state='collapsed')

st.markdown(
    '<style>:root{--sx-ink:%s;--sx-muted:%s;--sx-rule:%s;--sx-deep:%s;'
    '--sx-signal:%s;--sx-field:%s;--sx-field-edge:%s;}</style>'
    % (cfg.INK, cfg.MUTED, cfg.RULE, cfg.DEEP, cfg.SIGNAL,
       cfg.FIELD, cfg.FIELD_EDGE),
    unsafe_allow_html=True)

st.markdown("""
<style>
  header[data-testid="stHeader"], footer { display: none !important; }
  .block-container { padding: 0.9rem 1.8rem 0.6rem; max-width: 100%; }
  * { touch-action: manipulation; }
  .sx-title { font-size: 1.35rem; font-weight: 620; letter-spacing: -0.015em;
              color: var(--sx-ink); margin: 0 0 0.1rem; }
  .sx-group { font-size: 0.78rem; font-weight: 680; color: var(--sx-muted);
              margin: 0.6rem 0 0.35rem; padding-bottom: 0.3rem;
              border-bottom: 1px solid var(--sx-rule); }
  .sx-readout { display: flex; gap: 2.6rem; margin: 0 0 0.4rem;
                flex-wrap: wrap; align-items: flex-end; }
  .sx-value { font-size: 2.15rem; font-weight: 300; letter-spacing: -0.03em;
              color: var(--sx-deep); line-height: 1.02;
              font-variant-numeric: tabular-nums; }
  .sx-sub { font-size: 0.94rem; color: var(--sx-signal); font-weight: 500;
            margin-top: 0.2rem; font-variant-numeric: tabular-nums; }
  .sx-where { font-size: 0.8rem; color: var(--sx-muted); margin-top: 0.05rem; }
  .sx-note { font-size: 0.76rem; color: var(--sx-muted); line-height: 1.5;
             max-width: 78ch; margin-top: 0.5rem; }
  div[data-baseweb="select"] > div { min-height: 48px; font-size: 1.02rem; }
  .stNumberInput input, .stTextInput input { min-height: 42px;
      font-size: 0.98rem; font-variant-numeric: tabular-nums; }
  .stNumberInput button { width: 30px; }
  .stNumberInput input, .stTextInput input,
  div[data-baseweb="select"] > div {
      background: var(--sx-field) !important;
      border-color: var(--sx-field-edge) !important; }
  .stNumberInput input:focus, .stTextInput input:focus {
      border-color: var(--sx-deep) !important; }
  .sx-tight .stNumberInput button { display: none; }
  .sx-tight .stNumberInput input { padding-right: 6px; }
  hr.sx-div { border: none; border-top: 1px solid var(--sx-rule);
              margin: 0.55rem 0 0.35rem; }
  label p { font-size: 0.85rem !important; font-weight: 600 !important;
            color: var(--sx-ink) !important; }
  .stButton button, .stDownloadButton button { min-height: 42px;
      font-weight: 600; }
  @media (prefers-reduced-motion: reduce) { * { transition: none !important; } }
</style>
""", unsafe_allow_html=True)

ss = st.session_state


def defaults():
    out = []
    for n, p, h in cfg.LEAK_SCENARIOS:
        unit = 'days' if h >= 48.0 else 'hours'
        out.append(dict(name=n, pct=p, unit=unit,
                        dur=h / 24.0 if unit == 'days' else h))
    return out


def to_hours(row):
    return row['dur'] * 24.0 if row['unit'] == 'days' else row['dur']


def bounds(lo, hi, factor, value):
    # Converted limits are rounded so the validation message reads cleanly in
    # imperial rather than quoting a full-precision conversion.
    lo, hi = math.ceil(lo / factor), math.floor(hi / factor)
    return float(lo), float(hi), float(min(max(value / factor, lo), hi))


def duration(hours):
    if hours >= 48.0:
        return '%g days' % round(hours / 24.0, 1)
    if hours >= 1.0:
        return '%g h' % round(hours, 2)
    return '%g min' % round(hours * 60.0)


ss.setdefault('rows', defaults())
ss.setdefault('seq', 0)

# Every widget key carries this. Bumping it mints new widget IDs, which is the
# only reliable way to make a field fall back to its value/index parameter -
# clearing session_state alone leaves the stored widget value in place.
ss.setdefault('nonce', 0)
nk = '_%d' % ss['nonce']

ss.setdefault('units', cfg.DEFAULT_UNITS)
ss.setdefault('currency', cfg.DEFAULT_CURRENCY)

head, unit_col, cur_col, reset_col = st.columns([5, 1.6, 1.6, 1.1],
                                                vertical_alignment='center')
with head:
    st.markdown('<p class="sx-title">%s</p>' % cfg.APP_TITLE,
                unsafe_allow_html=True)
with unit_col:
    units = (st.segmented_control('Units', ['SI', 'US'], default=ss['units'],
                                  key='units' + nk,
                                  label_visibility='collapsed')
             if cfg.SHOW_UNIT_TOGGLE else cfg.DEFAULT_UNITS) or ss['units']
# Changing units pulls the currency with it. Changing currency does not pull
# the units, so an odd pairing stays possible if someone wants it. The nonce
# bump is what lets the currency control pick up the pulled value.
if units != ss['units']:
    ss['units'] = units
    ss['currency'] = cfg.UNITS_CURRENCY[units]
    ss['nonce'] += 1
    st.rerun()
with cur_col:
    currency = st.segmented_control('Currency', ['CAD', 'USD'],
                                    default=ss['currency'],
                                    key='currency' + nk,
                                    label_visibility='collapsed') \
        or ss['currency']
ss['currency'] = currency
with reset_col:
    # Clearing state puts the model inputs back to config defaults; carrying a
    # bumped nonce across the wipe is what makes the fields on screen follow.
    if st.button('Reset', key='reset' + nk, width='stretch'):
        n = ss['nonce'] + 1
        for k in list(ss.keys()):
            del ss[k]
        ss['nonce'] = n
        st.rerun()

us = units == 'US'
symbol = 'C$' if currency == 'CAD' else 'US$'
panel, view = st.columns([1.25, 2.4], gap='large')

with panel:
    st.markdown('<p class="sx-group">Pipeline</p>', unsafe_allow_html=True)

    subs = list(cfg.SUBSTANCE_GRADE)
    ss.setdefault('substance', cfg.DEFAULT_SUBSTANCE)
    substance = st.selectbox('Product', subs,
                             index=subs.index(ss['substance']),
                             key='sel_substance' + nk)
    ss['substance'] = substance

    ss.setdefault('flow_m3d', cfg.DEFAULT_FLOW_M3D)
    lo, hi = cfg.FLOW_RANGE_M3D
    f = M3_PER_BBL if us else 1.0
    lo, hi, val = bounds(lo, hi, f, ss.flow_m3d)
    shown = st.number_input(
        'Flow rate (%s)' % ('BBL/day' if us else 'm\u00b3/day'),
        min_value=lo, max_value=hi, value=val,
        step=100.0, format='%.0f', key='flow_%s%s' % (units, nk))
    ss.flow_m3d = shown * f

    st.markdown('<p class="sx-group">Location</p>', unsafe_allow_html=True)

    terrains = list(cfg.TERRAIN)
    ss.setdefault('terrain', cfg.DEFAULT_TERRAIN)
    terrain = st.selectbox('Terrain', terrains,
                           index=terrains.index(ss['terrain']),
                           key='sel_terrain' + nk)
    ss['terrain'] = terrain

    ss.setdefault('remote_km', cfg.DEFAULT_REMOTENESS_KM)
    lo, hi = cfg.REMOTENESS_RANGE_KM
    f = 1.609344 if us else 1.0
    lo, hi, val = bounds(lo, hi, f, ss.remote_km)
    shown = st.number_input(
        'Distance from road access (%s)' % ('miles' if us else 'km'),
        min_value=lo, max_value=hi, value=val,
        step=1.0, format='%.1f', key='remote_%s%s' % (units, nk))
    ss.remote_km = shown * f

    juris = list(cfg.JURISDICTION)
    ss.setdefault('jurisdiction', cfg.DEFAULT_JURISDICTION)
    jurisdiction = st.selectbox('Jurisdiction', juris,
                                index=juris.index(ss['jurisdiction']),
                                key='sel_jurisdiction' + nk)
    ss['jurisdiction'] = jurisdiction

    st.markdown('<p class="sx-group">Scenarios</p>', unsafe_allow_html=True)

    b1, b2 = st.columns(2)
    if b1.button('Load defaults', width='stretch'):
        ss['rows'] = defaults()
        ss['seq'] += 1
        st.rerun()
    if b2.button('Clear all', width='stretch'):
        ss['rows'] = []
        ss['seq'] += 1
        st.rerun()

    drop = None
    for i, row in enumerate(ss['rows']):
        k = 'r%s_%d_%d' % (nk, ss['seq'], i)
        nm, rm = st.columns([5, 1], vertical_alignment='bottom')
        row['name'] = nm.text_input('Name', value=row['name'],
                                    key=k + 'n', label_visibility='collapsed')
        if rm.button('\u2715', key=k + 'x', width='stretch'):
            drop = i
        st.markdown('<div class="sx-tight">', unsafe_allow_html=True)
        c1, c2, c3 = st.columns([1.0, 1.0, 1.15])
        lo, hi = cfg.SCENARIO_PCT_RANGE
        row['pct'] = c1.number_input('% flow', min_value=lo, max_value=hi,
                                     value=float(row['pct']), step=0.1,
                                     format='%.3f', key=k + 'p')
        row['dur'] = c2.number_input('Duration', min_value=0.01,
                                     max_value=1200.0, value=float(row['dur']),
                                     step=1.0, format='%.2f', key=k + 'd')
        row['unit'] = c3.selectbox('Unit', ['hours', 'days'],
                                   index=0 if row['unit'] == 'hours' else 1,
                                   key=k + 'u')
        st.markdown('</div><hr class="sx-div">', unsafe_allow_html=True)

    if drop is not None:
        ss['rows'].pop(drop)
        ss['seq'] += 1
        st.rerun()

    if len(ss['rows']) < cfg.MAX_SCENARIOS:
        if st.button('Add scenario', width='stretch'):
            ss['rows'].append(dict(name='New scenario', pct=1.0, dur=24.0,
                                   unit='hours'))
            ss['seq'] += 1
            st.rerun()

    st.markdown('<p class="sx-group">Chart</p>', unsafe_allow_html=True)
    show_refs = st.toggle('Volume benchmarks', value=cfg.SHOW_BENCHMARKS,
                          key='show_refs' + nk)


def cost_at(v):
    return spill_cost(v, substance, terrain, jurisdiction,
                      remoteness_km=ss.remote_km, currency=currency)


scenarios = []
for row in ss['rows']:
    hours = to_hours(row)
    vol = max(ss.flow_m3d * row['pct'] / 100.0 * hours / 24.0, 1e-9)
    detail = '%g%% of flow \u00b7 %s' % (row['pct'], duration(hours))
    scenarios.append((row['name'], detail, vol, cost_at(vol)['total']))

if scenarios:
    vols = np.asarray([s[2] for s in scenarios])
    pad = cfg.CURVE_SPAN_DECADES
    lo_v, hi_v = np.log10(vols.min()) - pad, np.log10(vols.max()) + pad
else:
    a, b = cfg.NO_SCENARIO_SPAN
    lo_v, hi_v = np.log10(ss.flow_m3d * a), np.log10(ss.flow_m3d * b)

grid = np.logspace(lo_v, hi_v, 180)
totals = [cost_at(v)['total'] for v in grid]

subtitle = '%s \u00b7 %s \u00b7 %g %s/day \u00b7 %g %s from access \u00b7 %s' % (
    substance, terrain.lower(),
    round(ss.flow_m3d / M3_PER_BBL if us else ss.flow_m3d),
    'BBL' if us else 'm\u00b3',
    round(ss.remote_km / 1.609 if us else ss.remote_km, 1),
    'miles' if us else 'km', jurisdiction)

with view:
    readout, save_col = st.columns([4, 1], vertical_alignment='center')
    with readout:
        if scenarios:
            worst = max(scenarios, key=lambda s: s[3])
            wv = worst[2] / M3_PER_BBL if us else worst[2]
            ref = cost_at(worst[2])
            blocks = ['<div><div class="sx-value">%s</div>'
                      '<div class="sx-sub">%.2f %s</div>'
                      '<div class="sx-where">%s</div></div>'
                      % (money(worst[3], symbol), wv,
                         'BBL' if us else 'm\u00b3', worst[0])]
            blocks.append('<div><div class="sx-where">Response %s &nbsp; '
                          'Socioeconomic %s &nbsp; Environmental %s</div>'
                          '<div class="sx-where">%s</div></div>'
                          % (money(ref['response'], symbol),
                             money(ref['socioeconomic'], symbol),
                             money(ref['environmental'], symbol),
                             ref['basis']))
        else:
            blocks = ['<div><div class="sx-value">&mdash;</div>'
                      '<div class="sx-where">No scenarios loaded &mdash; '
                      'the curve shows cost against release volume.</div>'
                      '</div>']
        st.markdown('<div class="sx-readout">%s</div>' % ''.join(blocks),
                    unsafe_allow_html=True)
    save_slot = save_col.empty()

    refs = cfg.REFERENCE_VOLUMES if show_refs else []
    components.html(chart_html(grid, totals, scenarios, refs,
                               units=units, currency=currency,
                               title=cfg.CHART_TITLE, subtitle=subtitle),
                    height=cfg.CHART_HEIGHT_PX, scrolling=False)

    static, _ = chart_svg(grid, totals, scenarios, refs,
                          units=units, currency=currency,
                          title=cfg.CHART_TITLE, subtitle=subtitle)
    save_slot.download_button(
        'Save chart', static,
        file_name='leak_cost_%s.svg' % substance.split()[0].lower(),
        mime='image/svg+xml', width='stretch')

    st.markdown('<p class="sx-note">%s</p>'
                % (cfg.DISCLAIMER % cfg.MODEL['target_year']),
                unsafe_allow_html=True)

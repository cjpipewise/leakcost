import numpy as np
import streamlit as st
import streamlit.components.v1 as components

import spill_config as cfg
from spill_cost import spill_cost, M3_PER_BBL
from chart_svg import chart_svg, chart_html, money

st.set_page_config(page_title=cfg.APP_TITLE, layout='wide',
                   initial_sidebar_state='collapsed')

st.markdown(
    '<style>:root{--sx-ink:%s;--sx-muted:%s;--sx-rule:%s;'
    '--sx-deep:%s;--sx-signal:%s;}</style>'
    % (cfg.INK, cfg.MUTED, cfg.RULE, cfg.DEEP, cfg.SIGNAL),
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
  .stNumberInput button { width: 34px; }
  label p { font-size: 0.85rem !important; font-weight: 600 !important;
            color: var(--sx-ink) !important; }
  .stButton button, .stDownloadButton button { min-height: 42px;
      font-weight: 600; }
  @media (prefers-reduced-motion: reduce) { * { transition: none !important; } }
</style>
""", unsafe_allow_html=True)

ss = st.session_state

if not ss.get('unlocked'):
    _, mid, _ = st.columns([1, 1.1, 1])
    with mid:
        st.markdown('<p class="sx-title">%s</p><p class="sx-where">%s</p>'
                    % (cfg.APP_TITLE, cfg.LOCK_PROMPT), unsafe_allow_html=True)
        with st.form('unlock', border=False):
            who = st.text_input('User')
            pw = st.text_input('Password', type='password')
            if st.form_submit_button('Sign in', width='stretch'):
                if who.strip() == cfg.AUTH_USER and pw == cfg.AUTH_PASS:
                    ss['unlocked'] = True
                    st.rerun()
                else:
                    st.error('That user and password do not match.')
    st.stop()


def defaults():
    return [dict(name=n, pct=p, hours=h, override=0.0)
            for n, p, h in cfg.LEAK_SCENARIOS]


def duration(hours):
    if hours >= 48.0:
        return '%g days' % round(hours / 24.0, 1)
    if hours >= 1.0:
        return '%g h' % round(hours, 2)
    return '%g min' % round(hours * 60.0)


ss.setdefault('rows', defaults())
ss.setdefault('seq', 0)

head, unit_col, cur_col, lock_col = st.columns([5, 1.6, 1.6, 1.1],
                                               vertical_alignment='center')
with head:
    st.markdown('<p class="sx-title">%s</p>' % cfg.APP_TITLE,
                unsafe_allow_html=True)
with unit_col:
    units = (st.segmented_control('Units', ['SI', 'US'],
                                  default=cfg.DEFAULT_UNITS,
                                  label_visibility='collapsed')
             if cfg.SHOW_UNIT_TOGGLE else cfg.DEFAULT_UNITS) or cfg.DEFAULT_UNITS
with cur_col:
    currency = st.segmented_control('Currency', ['CAD', 'USD'],
                                    default=cfg.DEFAULT_CURRENCY,
                                    label_visibility='collapsed') \
        or cfg.DEFAULT_CURRENCY
with lock_col:
    if st.button('Lock', width='stretch'):
        ss['unlocked'] = False
        st.rerun()

us = units == 'US'
symbol = 'C$' if currency == 'CAD' else 'US$'
panel, view = st.columns([1.25, 2.4], gap='large')

with panel:
    st.markdown('<p class="sx-group">Pipeline</p>', unsafe_allow_html=True)

    subs = list(cfg.SUBSTANCE_GRADE)
    substance = st.selectbox('Product', subs,
                             index=subs.index(cfg.DEFAULT_SUBSTANCE))

    ss.setdefault('flow_m3d', cfg.DEFAULT_FLOW_M3D)
    lo, hi = cfg.FLOW_RANGE_M3D
    shown = st.number_input(
        'Flow rate (%s)' % ('BBL/day' if us else 'm\u00b3/day'),
        min_value=lo / M3_PER_BBL if us else lo,
        max_value=hi / M3_PER_BBL if us else hi,
        value=float(ss.flow_m3d / M3_PER_BBL if us else ss.flow_m3d),
        step=100.0, format='%.0f', key='flow_%s' % units)
    ss.flow_m3d = shown * M3_PER_BBL if us else shown

    st.markdown('<p class="sx-group">Location</p>', unsafe_allow_html=True)

    terrains = list(cfg.TERRAIN)
    terrain = st.selectbox('Terrain', terrains,
                           index=terrains.index(cfg.DEFAULT_TERRAIN))

    ss.setdefault('remote_km', cfg.DEFAULT_REMOTENESS_KM)
    lo, hi = cfg.REMOTENESS_RANGE_KM
    shown = st.number_input(
        'Distance from road access (%s)' % ('miles' if us else 'km'),
        min_value=lo, max_value=hi / 1.609 if us else hi,
        value=float(ss.remote_km / 1.609 if us else ss.remote_km),
        step=1.0, format='%.1f', key='remote_%s' % units)
    ss.remote_km = shown * 1.609 if us else shown

    juris = list(cfg.JURISDICTION)
    jurisdiction = st.selectbox('Jurisdiction', juris,
                                index=juris.index(cfg.DEFAULT_JURISDICTION))

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
        k = 'r%d_%d_%s' % (ss['seq'], i, units)
        nm, rm = st.columns([5, 1], vertical_alignment='bottom')
        row['name'] = nm.text_input('Name', value=row['name'],
                                    key=k + 'n', label_visibility='collapsed')
        if rm.button('\u2715', key=k + 'x', width='stretch'):
            drop = i
        c1, c2, c3 = st.columns(3)
        lo, hi = cfg.SCENARIO_PCT_RANGE
        row['pct'] = c1.number_input('% flow', min_value=lo, max_value=hi,
                                     value=float(row['pct']), step=0.1,
                                     format='%.3f', key=k + 'p')
        lo, hi = cfg.SCENARIO_HOURS_RANGE
        row['hours'] = c2.number_input('Hours', min_value=lo, max_value=hi,
                                       value=float(row['hours']), step=1.0,
                                       format='%.2f', key=k + 'h')
        row['override'] = c3.number_input('Cost (0=auto)', min_value=0.0,
                                          value=float(row['override']),
                                          step=1000.0, format='%.0f',
                                          key=k + 'c')

    if drop is not None:
        ss['rows'].pop(drop)
        ss['seq'] += 1
        st.rerun()

    if len(ss['rows']) < cfg.MAX_SCENARIOS:
        if st.button('Add scenario', width='stretch'):
            ss['rows'].append(dict(name='New scenario', pct=1.0, hours=24.0,
                                   override=0.0))
            ss['seq'] += 1
            st.rerun()


def cost_at(v):
    return spill_cost(v, substance, terrain, jurisdiction,
                      remoteness_km=ss.remote_km, currency=currency)


scenarios = []
for row in ss['rows']:
    vol = max(ss.flow_m3d * row['pct'] / 100.0 * row['hours'] / 24.0, 1e-9)
    total = row['override'] if row['override'] > 0 else cost_at(vol)['total']
    detail = '%g%% of flow \u00b7 %s' % (row['pct'], duration(row['hours']))
    scenarios.append((row['name'], detail, vol, total, row['override'] > 0))

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
                      '<div class="sx-where">%s &mdash; largest loaded</div>'
                      '</div>'
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

    components.html(chart_html(grid, totals, scenarios, cfg.REFERENCE_VOLUMES,
                               units=units, currency=currency,
                               title=cfg.CHART_TITLE, subtitle=subtitle),
                    height=cfg.CHART_HEIGHT_PX, scrolling=False)

    static, _ = chart_svg(grid, totals, scenarios, cfg.REFERENCE_VOLUMES,
                          units=units, currency=currency,
                          title=cfg.CHART_TITLE, subtitle=subtitle)
    save_slot.download_button(
        'Save chart', static,
        file_name='leak_cost_%s.svg' % substance.split()[0].lower(),
        mime='image/svg+xml', width='stretch')

    st.markdown('<p class="sx-note">%s</p>' % cfg.DISCLAIMER,
                unsafe_allow_html=True)

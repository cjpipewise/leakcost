"""Builds the cost curve as inline SVG plus a small amount of JavaScript.

chart_svg returns a standalone, static SVG suitable for download. chart_html
wraps the same markup with hover behaviour for the browser. There is no
matplotlib dependency, which keeps the stlite bundle small.
"""

import json
import math

import spill_config as cfg

W, H = 1060.0, 620.0
ML, MR, MT, MB = 92.0, 34.0, 96.0, 66.0
M3_PER_BBL = 0.1589873


def money(v, symbol):
    a = abs(v)
    for div, suf in ((1e9, 'B'), (1e6, 'M'), (1e3, 'k')):
        if a >= div:
            q = v / div
            return '%s%.*f%s' % (symbol, 0 if abs(q) >= 10 else 1, q, suf)
    return '%s%.0f' % (symbol, v)


def _decades(lo, hi):
    out = []
    e = math.floor(math.log10(lo))
    while 10.0 ** e <= hi * 1.0000001:
        if 10.0 ** e >= lo * 0.9999999:
            out.append(10.0 ** e)
        e += 1
    return out


def _fmt_vol(v):
    if v >= 1000:
        return '%,.0f'.replace('%,', '{:,}').format(int(round(v)))
    if v >= 10:
        return '%.0f' % v
    if v >= 1:
        return '%.1f' % v
    return '%.2f' % v


def chart_svg(volumes, totals, scenarios, refs, units='SI', currency='CAD',
              title='Leak Cost Estimate', subtitle='', interactive=False):
    us = units == 'US'
    symbol = 'C$' if currency == 'CAD' else 'US$'
    vunit = 'BBL' if us else 'm\u00b3'
    conv = (1.0 / M3_PER_BBL) if us else 1.0

    xs = [v * conv for v in volumes]
    ys = list(totals)
    x_lo, x_hi = min(xs), max(xs)
    y_lo, y_hi = min(ys), max(ys)
    x_lo = 10.0 ** math.floor(math.log10(x_lo))
    x_hi = 10.0 ** math.ceil(math.log10(x_hi))
    y_lo = 10.0 ** math.floor(math.log10(y_lo))
    y_hi = 10.0 ** math.ceil(math.log10(y_hi))

    def px(v):
        return ML + (math.log10(v) - math.log10(x_lo)) / \
            (math.log10(x_hi) - math.log10(x_lo)) * (W - ML - MR)

    def py(v):
        return H - MB - (math.log10(v) - math.log10(y_lo)) / \
            (math.log10(y_hi) - math.log10(y_lo)) * (H - MT - MB)

    p = []
    p.append('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %g %g" '
             'width="100%%" font-family="-apple-system, BlinkMacSystemFont, '
             '\'Segoe UI\', Roboto, sans-serif">' % (W, H))
    p.append('<rect width="%g" height="%g" fill="white"/>' % (W, H))

    p.append('<text x="%g" y="34" font-size="23" font-weight="640" fill="%s" '
             'letter-spacing="-0.3">%s</text>' % (ML - 44, cfg.INK, title))
    if subtitle:
        p.append('<text x="%g" y="56" font-size="13" fill="%s">%s</text>'
                 % (ML - 44, cfg.MUTED, subtitle))

    for gx in _decades(x_lo, x_hi):
        p.append('<line x1="%g" y1="%g" x2="%g" y2="%g" stroke="%s" '
                 'stroke-width="1"/>' % (px(gx), MT, px(gx), H - MB, cfg.GRID))
        p.append('<text x="%g" y="%g" font-size="13" fill="%s" '
                 'text-anchor="middle">%s</text>'
                 % (px(gx), H - MB + 24, cfg.MUTED, _fmt_vol(gx)))
    for gy in _decades(y_lo, y_hi):
        p.append('<line x1="%g" y1="%g" x2="%g" y2="%g" stroke="%s" '
                 'stroke-width="1"/>' % (ML, py(gy), W - MR, py(gy), cfg.GRID))
        p.append('<text x="%g" y="%g" font-size="13" fill="%s" '
                 'text-anchor="end">%s</text>'
                 % (ML - 12, py(gy) + 4, cfg.MUTED, money(gy, symbol)))

    p.append('<text x="%g" y="%g" font-size="14" fill="%s" '
             'text-anchor="middle">Release volume (%s)</text>'
             % (ML + (W - ML - MR) / 2.0, H - 16, cfg.INK, vunit))
    p.append('<text transform="translate(22,%g) rotate(-90)" font-size="14" '
             'fill="%s" text-anchor="middle">Total cost (%s)</text>'
             % (MT + (H - MT - MB) / 2.0, cfg.INK, currency))

    for name, vol_m3 in refs:
        rv = vol_m3 * conv
        if not (x_lo <= rv <= x_hi):
            continue
        p.append('<line x1="%g" y1="%g" x2="%g" y2="%g" stroke="%s" '
                 'stroke-width="1.3" stroke-dasharray="4 4"/>'
                 % (px(rv), MT + 6, px(rv), H - MB, cfg.REF))
        p.append('<text x="%g" y="%g" font-size="11.5" fill="%s" '
                 'text-anchor="middle">%s</text>'
                 % (px(rv), MT - 6, cfg.REF, name))

    pts = ' '.join('%.2f,%.2f' % (px(a), py(b)) for a, b in zip(xs, ys))
    p.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="3.4" '
             'stroke-linecap="round" stroke-linejoin="round"/>' % (pts, cfg.DEEP))

    rows, placed = [], []
    order = ([i for i, s in enumerate(scenarios) if not s[4]]
             + [i for i, s in enumerate(scenarios) if s[4]])
    marks = []
    for i in order:
        label, detail, vol_m3, total, custom = scenarios[i]
        vx = vol_m3 * conv
        if not (x_lo <= vx <= x_hi):
            continue
        ax, ay = px(vx), py(total)
        mx, my = ax, ay
        for step in range(1, 7):
            if all((mx - qx) ** 2 + (my - qy) ** 2 >= 30.0 ** 2
                   for qx, qy in placed):
                break
            mx, my = ax + 26.0 * step * 0.86, ay - 26.0 * step * 0.5
        placed.append((mx, my))
        marks.append((i, ax, ay, mx, my, cfg.SIGNAL if custom else cfg.INK))
        rows.append((i, label, detail, vol_m3 * conv, total, custom))

    for i, ax, ay, mx, my, col in marks:
        p.append('<g class="mk" data-i="%d">' % i)
        if (mx - ax) ** 2 + (my - ay) ** 2 > 1.0:
            p.append('<line x1="%g" y1="%g" x2="%g" y2="%g" stroke="%s" '
                     'stroke-width="1.4"/>' % (ax, ay, mx, my, col))
            p.append('<circle cx="%g" cy="%g" r="3" fill="%s"/>' % (ax, ay, col))
        p.append('<circle cx="%g" cy="%g" r="13" fill="%s" stroke="white" '
                 'stroke-width="2.4"/>' % (mx, my, col))
        p.append('<text x="%g" y="%g" font-size="12" font-weight="700" '
                 'fill="white" text-anchor="middle">%d</text>'
                 % (mx, my + 4, i + 1))
        p.append('</g>')

    rows.sort(key=lambda r: r[0])

    ly = MT + 16
    for i, label, detail, vx, total, custom in rows:
        col = cfg.SIGNAL if custom else cfg.MUTED
        p.append('<g class="lg" data-i="%d">' % i)
        p.append('<rect x="%g" y="%g" width="562" height="21" fill="%s" '
                 'opacity="0" class="lgbg"/>' % (ML + 8, ly - 15, cfg.PANEL))
        p.append('<circle cx="%g" cy="%g" r="7.5" fill="%s"/>'
                 % (ML + 22, ly - 5, col))
        p.append('<text x="%g" y="%g" font-size="11" font-weight="700" '
                 'fill="white" text-anchor="middle">%d</text>'
                 % (ML + 22, ly - 1, i + 1))
        p.append('<text x="%g" y="%g" font-size="13.5" font-weight="600" '
                 'fill="%s">%s</text>' % (ML + 38, ly, col, label))
        p.append('<text x="%g" y="%g" font-size="13" fill="%s">%s</text>'
                 % (ML + 190, ly, col, detail))
        p.append('<text x="%g" y="%g" font-size="13" fill="%s" '
                 'text-anchor="end">%s %s</text>'
                 % (ML + 452, ly, col, _fmt_vol(vx), vunit))
        p.append('<text x="%g" y="%g" font-size="13.5" font-weight="600" '
                 'fill="%s" text-anchor="end">%s</text>'
                 % (ML + 560, ly, col, money(total, symbol)))
        p.append('</g>')
        ly += 23

    if interactive:
        p.append('<g id="hov" style="display:none">')
        p.append('<line id="hovline" y1="%g" y2="%g" stroke="%s" '
                 'stroke-width="1.2" stroke-dasharray="4 4"/>' % (MT, H - MB, cfg.SIGNAL))
        p.append('<circle id="hovdot" r="6" fill="%s" stroke="white" '
                 'stroke-width="2"/>' % cfg.SIGNAL)
        p.append('</g>')
        p.append('<rect id="hit" x="%g" y="%g" width="%g" height="%g" '
                 'fill="transparent"/>' % (ML, MT, W - ML - MR, H - MT - MB))

    p.append('</svg>')
    svg = ''.join(p)

    meta = dict(ml=ML, mr=MR, mt=MT, mb=MB, w=W, h=H,
                xlo=x_lo, xhi=x_hi, ylo=y_lo, yhi=y_hi,
                xs=xs, ys=ys, symbol=symbol, vunit=vunit)
    return svg, meta


def chart_html(volumes, totals, scenarios, refs, units='SI', currency='CAD',
               title='Leak Cost Estimate', subtitle=''):
    svg, meta = chart_svg(volumes, totals, scenarios, refs, units, currency,
                          title, subtitle, interactive=True)
    return """<div id="wrap" style="position:relative;width:100%%">%s
<div id="tip" style="position:absolute;display:none;pointer-events:none;
 background:%s;color:#fff;padding:6px 10px;border-radius:6px;font-size:12.5px;
 font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
 white-space:nowrap;transform:translate(-50%%,-140%%);box-shadow:0 2px 8px rgba(0,0,0,.18)">
</div></div>
<style>
 .mk circle {transition:r .12s ease}
 .mk.on circle {r:17}
 .lg {cursor:default}
 .lg.on .lgbg {opacity:1}
 svg text {user-select:none}
</style>
<script>
(function(){
 var M=%s, wrap=document.getElementById('wrap'), svg=wrap.querySelector('svg'),
     tip=document.getElementById('tip'), hit=document.getElementById('hit'),
     hov=document.getElementById('hov'), hl=document.getElementById('hovline'),
     hd=document.getElementById('hovdot'),
     mks=[].slice.call(wrap.querySelectorAll('.mk')),
     lgs=[].slice.call(wrap.querySelectorAll('.lg'));

 function pair(i,on){
  mks.forEach(function(e){if(+e.dataset.i===i)e.classList.toggle('on',on);});
  lgs.forEach(function(e){if(+e.dataset.i===i)e.classList.toggle('on',on);});
 }
 mks.concat(lgs).forEach(function(e){
  e.addEventListener('mouseenter',function(){pair(+e.dataset.i,true);});
  e.addEventListener('mouseleave',function(){pair(+e.dataset.i,false);});
 });

 function pxToVol(x){
  var f=(x-M.ml)/(M.w-M.ml-M.mr);
  return Math.pow(10, Math.log10(M.xlo)+f*(Math.log10(M.xhi)-Math.log10(M.xlo)));
 }
 function volToPx(v){
  return M.ml+(Math.log10(v)-Math.log10(M.xlo))/(Math.log10(M.xhi)-Math.log10(M.xlo))*(M.w-M.ml-M.mr);
 }
 function costToPy(v){
  return M.h-M.mb-(Math.log10(v)-Math.log10(M.ylo))/(Math.log10(M.yhi)-Math.log10(M.ylo))*(M.h-M.mt-M.mb);
 }
 function fmtMoney(v){
  var a=Math.abs(v), u=[[1e9,'B'],[1e6,'M'],[1e3,'k']];
  for(var i=0;i<u.length;i++){ if(a>=u[i][0]){ var q=v/u[i][0];
    return M.symbol+(Math.abs(q)>=10?q.toFixed(0):q.toFixed(1))+u[i][1]; } }
  return M.symbol+v.toFixed(0);
 }
 function fmtVol(v){ return v>=1000?Math.round(v).toLocaleString():
   (v>=10?v.toFixed(0):(v>=1?v.toFixed(1):v.toFixed(2))); }

 if(!hit) return;
 hit.addEventListener('mousemove',function(ev){
  var r=svg.getBoundingClientRect(), s=M.w/r.width;
  var sx=(ev.clientX-r.left)*s;
  var v=pxToVol(sx), lo=0, hi=M.xs.length-1, k=0;
  for(var i=0;i<M.xs.length;i++){ if(M.xs[i]<=v) k=i; }
  var j=Math.min(k+1,M.xs.length-1), y;
  if(j===k){ y=M.ys[k]; } else {
   var t=(Math.log10(v)-Math.log10(M.xs[k]))/(Math.log10(M.xs[j])-Math.log10(M.xs[k]));
   y=Math.pow(10,Math.log10(M.ys[k])+t*(Math.log10(M.ys[j])-Math.log10(M.ys[k])));
  }
  var cx=volToPx(v), cy=costToPy(y);
  hov.style.display='block';
  hl.setAttribute('x1',cx); hl.setAttribute('x2',cx);
  hd.setAttribute('cx',cx); hd.setAttribute('cy',cy);
  tip.style.display='block';
  tip.style.left=(cx/s)+'px'; tip.style.top=(cy/s)+'px';
  tip.textContent=fmtVol(v)+' '+M.vunit+'  \\u00b7  '+fmtMoney(y);
 });
 hit.addEventListener('mouseleave',function(){
  hov.style.display='none'; tip.style.display='none';
 });
})();
</script>""" % (svg, cfg.INK, json.dumps(meta))

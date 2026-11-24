"""Generates the UML, DFD and ER diagrams used in the hackViz report as SVG files.

Usage:  python make_diagrams.py <output-dir>
Render to PNG with:  node render_diagrams.mjs <svg-dir> <png-dir>
"""
import html
import math
import os
import sys

OUT = sys.argv[1] if len(sys.argv) > 1 else "svg"
INK = "#000000"
FILL = "#ffffff"
FILL2 = "#eeeeee"
NOTE = "#ffffff"
LOOP = "#010101"
FONT = "Arial, Helvetica, sans-serif"

DEFS = """<defs>
<marker id="arrow" viewBox="0 0 12 12" refX="11.5" refY="6" markerWidth="12" markerHeight="12" markerUnits="userSpaceOnUse" orient="auto-start-reverse"><path d="M0,1 L12,6 L0,11 z" fill="#000000"/></marker>
<marker id="arrowred" viewBox="0 0 12 12" refX="11.5" refY="6" markerWidth="12" markerHeight="12" markerUnits="userSpaceOnUse" orient="auto-start-reverse"><path d="M0,1 L12,6 L0,11 z" fill="#000000"/></marker>
<marker id="open" viewBox="0 0 14 14" refX="13" refY="7" markerWidth="14" markerHeight="14" markerUnits="userSpaceOnUse" orient="auto-start-reverse"><path d="M1,1 L13,7 L1,13" fill="none" stroke="#000000" stroke-width="1.6"/></marker>
<marker id="diamond" viewBox="0 0 24 14" refX="23" refY="7" markerWidth="24" markerHeight="14" markerUnits="userSpaceOnUse" orient="auto-start-reverse"><path d="M1,7 L12,1 L23,7 L12,13 z" fill="#000000" stroke="#000000" stroke-width="1.2"/></marker>
<marker id="tri"viewBox="0 0 20 20" refX="19" refY="10" markerWidth="20" markerHeight="20" markerUnits="userSpaceOnUse" orient="auto"><path d="M1,1 L19,10 L1,19 z" fill="#ffffff" stroke="#000000" stroke-width="1.6"/></marker>
</defs>"""


def esc(s):
    return html.escape(s, quote=False)


def f(v):
    return f"{v:.1f}"


class Diagram:
    def __init__(self, w, h):
        self.w, self.h, self.p = w, h, []

    def add(self, *items):
        for it in items:
            if isinstance(it, (list, tuple)):
                self.add(*it)
            elif it:
                self.p.append(it)

    def save(self, name):
        os.makedirs(OUT, exist_ok=True)
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
               f'viewBox="0 0 {self.w} {self.h}" font-family="{FONT}">' + DEFS +
               f'<rect width="{self.w}" height="{self.h}" fill="#ffffff"/>' + "\n".join(self.p) + "</svg>")
        with open(os.path.join(OUT, name + ".svg"), "w", encoding="utf-8") as fh:
            fh.write(svg)


# ------------------------------------------------------------------ primitives
def text(x, y, s, size=17, anchor="middle", weight="normal", italic=False, fill=INK, lh=1.2, valign="middle"):
    lines = s.split("\n")
    step = size * lh
    if valign == "middle":
        y0 = y - (len(lines) - 1) * step / 2 + size * 0.36
    elif valign == "top":
        y0 = y + size * 0.9
    else:
        y0 = y
    st = ' font-style="italic"' if italic else ""
    spans = "".join(f'<tspan x="{f(x)}" y="{f(y0 + i * step)}">{esc(l)}</tspan>' for i, l in enumerate(lines))
    return f'<text font-size="{size}" text-anchor="{anchor}" font-weight="{weight}" fill="{fill}"{st}>{spans}</text>'


def tw(s, size):
    return max(len(l) for l in s.split("\n")) * size * 0.55


def label(x, y, s, size=15, bg="#ffffff", fill=INK, weight="normal", italic=False):
    n = len(s.split("\n"))
    w = tw(s, size) + 10
    h = n * size * 1.2 + 6
    return (f'<rect x="{f(x - w / 2)}" y="{f(y - h / 2)}" width="{f(w)}" height="{f(h)}" fill="{bg}"/>' +
            text(x, y, s, size, fill=fill, weight=weight, italic=italic))


def rect(x, y, w, h, rx=0, fill=FILL, stroke=INK, sw=1.6, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<rect x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" rx="{rx}" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="{sw}"{d}/>')


def line(x1, y1, x2, y2, sw=1.6, stroke=INK, dash=None, end=None, start=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    me = f' marker-end="url(#{end})"' if end else ""
    ms = f' marker-start="url(#{start})"' if start else ""
    return f'<line x1="{f(x1)}" y1="{f(y1)}" x2="{f(x2)}" y2="{f(y2)}" stroke="{stroke}" stroke-width="{sw}"{d}{me}{ms}/>'


def path(d, sw=1.6, stroke=INK, dash=None, end=None, start=None, fill="none"):
    ds = f' stroke-dasharray="{dash}"' if dash else ""
    me = f' marker-end="url(#{end})"' if end else ""
    ms = f' marker-start="url(#{start})"' if start else ""
    return f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{ds}{me}{ms}/>'


def poly(pts, **kw):
    d = "M" + " L".join(f"{f(x)},{f(y)}" for x, y in pts)
    return path(d, **kw)


def circle(cx, cy, r, fill="#ffffff", stroke=INK, sw=1.6):
    return f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(r)}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'


class S:
    """Shape geometry used to clip connectors at shape borders."""

    def __init__(self, kind, x, y, a, b=None):
        self.k, self.x, self.y, self.a = kind, x, y, a
        self.b = a if b is None else b

    def edge(self, tx, ty):
        dx, dy = tx - self.x, ty - self.y
        if dx == 0 and dy == 0:
            return self.x, self.y
        if self.k in ("ellipse", "circle"):
            s = 1 / math.sqrt((dx / self.a) ** 2 + (dy / self.b) ** 2)
        elif self.k == "diamond":
            s = 1 / (abs(dx) / self.a + abs(dy) / self.b)
        else:
            s = min(self.a / abs(dx) if dx else 1e9, self.b / abs(dy) if dy else 1e9)
        return self.x + dx * s, self.y + dy * s

    @property
    def top(self):
        return self.x, self.y - self.b

    @property
    def bottom(self):
        return self.x, self.y + self.b

    @property
    def left(self):
        return self.x - self.a, self.y

    @property
    def right(self):
        return self.x + self.a, self.y


def connect(a, b, off=0, **kw):
    """Straight connector between two shapes; `off` shifts it sideways (for paired flows)."""
    dx, dy = b.x - a.x, b.y - a.y
    ln = math.hypot(dx, dy) or 1
    nx, ny = -dy / ln * off, dx / ln * off
    p1 = a.edge(b.x + nx, b.y + ny)
    p2 = b.edge(a.x + nx, a.y + ny)
    p1 = (p1[0] + nx, p1[1] + ny)
    p2 = (p2[0] + nx, p2[1] + ny)
    return line(p1[0], p1[1], p2[0], p2[1], **kw), ((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2)


# ------------------------------------------------------------------ UML pieces
def actor(cx, top, name, size=16):
    r = 13
    hy = top + r
    neck = hy + r
    hip = neck + 34
    parts = [circle(cx, hy, r), line(cx, neck, cx, hip), line(cx - 24, neck + 12, cx + 24, neck + 12),
             line(cx, hip, cx - 19, hip + 30), line(cx, hip, cx + 19, hip + 30),
             text(cx, hip + 30 + 8, name, size, weight="bold", valign="top")]
    return parts, S("rect", cx, neck + 15, 26, 48)


def usecase(cx, cy, s, rx=112, ry=33, size=15, fill=FILL):
    return ([f'<ellipse cx="{f(cx)}" cy="{f(cy)}" rx="{rx}" ry="{ry}" fill="{fill}" stroke="{INK}" stroke-width="1.6"/>',
             text(cx, cy, s, size)], S("ellipse", cx, cy, rx, ry))


def action(cx, cy, s, w=260, h=56, size=15, fill=FILL, rx=16):
    return [rect(cx - w / 2, cy - h / 2, w, h, rx=rx, fill=fill), text(cx, cy, s, size)], S("rect", cx, cy, w / 2, h / 2)


def objnode(cx, cy, s, w=200, h=50, size=15):
    return [rect(cx - w / 2, cy - h / 2, w, h, rx=0, fill="#ffffff"), text(cx, cy, s, size)], S("rect", cx, cy, w / 2, h / 2)


def diamond(cx, cy, w, h, s="", size=14, fill="#ffffff"):
    pts = [(cx, cy - h / 2), (cx + w / 2, cy), (cx, cy + h / 2), (cx - w / 2, cy)]
    d = "M" + " L".join(f"{f(x)},{f(y)}" for x, y in pts) + " Z"
    out = [path(d, fill=fill)]
    if s:
        out.append(text(cx, cy, s, size))
    return out, S("diamond", cx, cy, w / 2, h / 2)


def initial(cx, cy):
    return [circle(cx, cy, 11, fill=INK)], S("circle", cx, cy, 11)


def final(cx, cy):
    return [circle(cx, cy, 14), circle(cx, cy, 8, fill=INK, sw=0)], S("circle", cx, cy, 14)


def flowfinal(cx, cy):
    r = 13
    k = r * 0.7
    return [circle(cx, cy, r), line(cx - k, cy - k, cx + k, cy + k), line(cx - k, cy + k, cx + k, cy - k)], S("circle", cx, cy, r)


def bar(cx, cy, w, h=8, vertical=False):
    if vertical:
        return [rect(cx - h / 2, cy - w / 2, h, w, fill=INK, sw=0)], S("rect", cx, cy, h / 2, w / 2)
    return [rect(cx - w / 2, cy - h / 2, w, h, fill=INK, sw=0)], S("rect", cx, cy, w / 2, h / 2)


def hourglass(cx, cy, s="", size=14, side="right"):
    pts = f"M{f(cx - 13)},{f(cy - 16)} L{f(cx + 13)},{f(cy - 16)} L{f(cx - 13)},{f(cy + 16)} L{f(cx + 13)},{f(cy + 16)} Z"
    out = [path(pts, fill="#ffffff")]
    if s:
        if side == "right":
            out.append(text(cx + 22, cy, s, size, anchor="start"))
        elif side == "left":
            out.append(text(cx - 22, cy, s, size, anchor="end"))
        else:
            out.append(text(cx, cy + 34, s, size))
    return out, S("rect", cx, cy, 13, 16)


def send_signal(cx, cy, s, w=200, h=54, size=15):
    x, y = cx - w / 2, cy - h / 2
    d = f"M{f(x)},{f(y)} L{f(x + w - 18)},{f(y)} L{f(x + w)},{f(cy)} L{f(x + w - 18)},{f(y + h)} L{f(x)},{f(y + h)} Z"
    return [path(d, fill=FILL), text(cx - 6, cy, s, size)], S("rect", cx, cy, w / 2, h / 2)


def accept_event(cx, cy, s, w=200, h=54, size=15):
    x, y = cx - w / 2, cy - h / 2
    d = f"M{f(x)},{f(y)} L{f(x + w)},{f(y)} L{f(x + w)},{f(y + h)} L{f(x)},{f(y + h)} L{f(x + 18)},{f(cy)} Z"
    return [path(d, fill=FILL), text(cx + 6, cy, s, size)], S("rect", cx, cy, w / 2, h / 2)


def connector(cx, cy, s):
    return [circle(cx, cy, 15), text(cx, cy, s, 15, weight="bold")], S("circle", cx, cy, 15)


def note(x, y, w, h, s, size=14, anchor_to=None):
    fold = 14
    d = (f"M{f(x)},{f(y)} L{f(x + w - fold)},{f(y)} L{f(x + w)},{f(y + fold)} L{f(x + w)},{f(y + h)} "
         f"L{f(x)},{f(y + h)} Z")
    out = [path(d, fill=NOTE), path(f"M{f(x + w - fold)},{f(y)} L{f(x + w - fold)},{f(y + fold)} L{f(x + w)},{f(y + fold)}"),
           text(x + 10, y + 8, s, size, anchor="start", valign="top")]
    if anchor_to:
        out.append(line(anchor_to[0][0], anchor_to[0][1], anchor_to[1][0], anchor_to[1][1], dash="5,4"))
    return out


def stereo_arrow(p1, p2, kind, lx=None, ly=None, size=14):
    """Dashed «include»/«extend» dependency from p1 to p2."""
    out = [line(p1[0], p1[1], p2[0], p2[1], dash="7,5", end="open")]
    mx, my = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2
    out.append(label(lx if lx is not None else mx, ly if ly is not None else my, f"«{kind}»", size, italic=False))
    return out


def flow(pts, lab=None, lpos=None, size=14, color=INK, dash=None, end="arrow"):
    mk = end
    if color == LOOP and dash is None:
        dash = "8,5"
    out = [poly(pts, end=mk, stroke=color, dash=dash)]
    if lab:
        if lpos is None:
            i = len(pts) // 2
            lpos = ((pts[i - 1][0] + pts[i][0]) / 2, (pts[i - 1][1] + pts[i][1]) / 2)
        out.append(label(lpos[0], lpos[1], lab, size, fill=color))
    return out


def legend(x, y, w, items, title="Legend", size=13):
    rowh = 26
    h = 34 + rowh * len(items)
    out = [rect(x, y, w, h, rx=6, fill="#ffffff", dash="4,3"), text(x + 10, y + 8, title, 14, anchor="start", weight="bold", valign="top")]
    for i, (sym, desc) in enumerate(items):
        yy = y + 42 + i * rowh
        out.append(sym(x + 14, yy))
        out.append(text(x + 82, yy, desc, size, anchor="start"))
    return out


# ------------------------------------------------------------------ DFD pieces
def process(cx, cy, r, num, name, size=15):
    return ([circle(cx, cy, r, fill=FILL2), text(cx, cy - r + 22, num, size, weight="bold"),
             line(cx - r * 0.72, cy - r + 33, cx + r * 0.72, cy - r + 33, sw=1),
             text(cx, cy + 12, name, size - 1)], S("circle", cx, cy, r))


def store(cx, cy, did, name, w=230, h=40, size=15, dup=False):
    """Gane-Sarson data store; dup=True adds the duplicate-store stripe."""
    x, y = cx - w / 2, cy - h / 2
    out = [rect(x, y, w, h, fill="#ffffff", stroke="#ffffff", sw=0),
           line(x, y, x + w, y), line(x, y + h, x + w, y + h), line(x, y, x, y + h), line(x + 46, y, x + 46, y + h),
           text(x + 23, cy, did, size, weight="bold"), text(x + 54, cy, name, size, anchor="start")]
    if dup:
        out.append(line(x + 7, y, x + 7, y + h))
    return out, S("rect", cx, cy, w / 2, h / 2)


def entity(cx, cy, s, w=210, h=66, size=15):
    x, y = cx - w / 2, cy - h / 2
    return ([rect(x + 5, y + 5, w, h, fill="#cccccc", sw=0), rect(x, y, w, h, fill="#ffffff"), text(cx, cy, s, size, weight="bold")],
            S("rect", cx, cy, w / 2, h / 2))


# ================================================================== diagrams
def use_case_diagram():
    d = Diagram(1000, 1250)
    d.add(rect(232, 40, 548, 1185, rx=4, fill="#ffffff"),
          text(506, 64, "hackViz Insider-Risk Monitoring System", 17, weight="bold"),
          text(110, 22, "Primary actors", 15, italic=True), text(900, 22, "Secondary actors", 15, italic=True))
    A, B = 382, 640
    uc = {}
    for key, col, y, s in [
        ("dash", A, 125, "View Security\nDashboard"), ("prof", A, 220, "View Employee\nProfile"),
        ("now", A, 318, "Analyze Now"), ("csv", A, 418, "Export Activity\n(CSV)"),
        ("mon", A, 515, "View Monitoring\nStatus"), ("alerts", A, 612, "View Anomaly\nAlerts"),
        ("evid", A, 708, "Inspect Evidence\nRecord"), ("add", A, 810, "Add Employee"),
        ("reset", A, 902, "Reset / Seed\nDataset"), ("pair", A, 1010, "Pair Chrome\nExtension"),
        ("coll", A, 1135, "Collect Browser\nActivity"),
        ("filter", B, 165, "Filter / Search\nActivity"), ("ctx", B, 300, "Build Behavioural\nContext"),
        ("assess", B, 405, "Assess Activity\nBatch"), ("valid", B, 515, "Validate Response &\nVerify Evidence"),
        ("retry", B, 625, "Retry Analysis"), ("verify", B, 1010, "Verify\nEmployee ID"),
        ("nav", B, 1095, "Collect\nNavigation"), ("dl", B, 1180, "Collect\nDownload"),
    ]:
        rx = 112 if col == A else 118
        parts, shape = usecase(col, y, s, rx=rx)
        d.add(parts)
        uc[key] = shape

    an, an_s = actor(110, 380, "Security\nAnalyst")
    ad, ad_s = actor(110, 790, "System\nAdministrator")
    em, em_s = actor(110, 1015, "Monitored\nEmployee")
    ol, ol_s = actor(900, 200, "Ollama LLM\nService\n«system»")
    db, db_s = actor(900, 362, "PostgreSQL\nDatabase\n«system»")
    tm, tm_s = actor(900, 524, "Scheduler\n«timer»")
    d.add(an, ad, em, ol, db, tm)

    for a_s, keys in [(an_s, ["dash", "prof", "now", "alerts", "csv", "mon"]), (ad_s, ["add", "reset"]),
                      (em_s, ["pair", "coll"])]:
        for k in keys:
            tx, ty = uc[k].left
            sx, sy = a_s.edge(tx, ty)
            d.add(line(sx, sy, tx, ty))
    asr = uc["assess"]
    for a_s, ang in ((ol_s, -35), (db_s, 0), (tm_s, 35)):
        tx = asr.x + asr.a * math.cos(math.radians(ang))
        ty = asr.y + asr.b * math.sin(math.radians(ang))
        sx, sy = a_s.edge(tx, ty)
        d.add(line(sx, sy, tx, ty))
    # actor generalization: administrator is a specialised analyst
    d.add(line(110, 790, 110, 532, end="tri"))
    # include / extend relationships
    d.add(stereo_arrow(uc["filter"].edge(*uc["prof"].right), uc["prof"].edge(*uc["filter"].left), "extend", lx=515, ly=184))
    d.add(stereo_arrow(uc["now"].edge(uc["assess"].x, uc["assess"].y), uc["assess"].edge(uc["now"].x, uc["now"].y), "include", lx=505, ly=372))
    d.add(stereo_arrow(uc["assess"].top, uc["ctx"].bottom, "include", lx=B + 58, ly=352))
    d.add(stereo_arrow(uc["assess"].bottom, uc["valid"].top, "include", lx=B + 58, ly=460))
    d.add(stereo_arrow(uc["retry"].top, uc["valid"].bottom, "extend", lx=B + 58, ly=570))
    d.add(stereo_arrow(uc["evid"].top, uc["alerts"].bottom, "extend", lx=A + 52, ly=660))
    d.add(stereo_arrow(uc["pair"].right, uc["verify"].left, "include", lx=(A + B) / 2 + 6, ly=995))
    # use-case generalization
    d.add(line(*uc["nav"].edge(*uc["coll"].right), *uc["coll"].edge(*uc["nav"].left), end="tri"))
    d.add(line(*uc["dl"].edge(*uc["coll"].right), *uc["coll"].edge(*uc["dl"].left), end="tri"))
    # notes
    d.add(note(792, 700, 200, 120, "condition:\n{response invalid,\ntimeout or LLM\nunavailable}\nextension point:\nvalidation", 13,
               anchor_to=((792, 720), uc["retry"].right)))
    d.add(note(14, 1180 - 6, 205, 62, "Pairing requires the\nmonitoring-notice\nconsent checkbox", 13))
    d.add(legend(792, 990, 200, [
        (lambda x, y: line(x, y, x + 56, y), "association"),
        (lambda x, y: line(x, y, x + 56, y, dash="7,5", end="open"), "«include»/«extend»"),
        (lambda x, y: line(x, y, x + 56, y, end="tri"), "generalization"),
        (lambda x, y: note(x, y - 10, 56, 20, "", 10), "note"),
    ]))
    d.save("uc_diagram")


def activity_diagram():
    d = Diagram(1000, 1330)
    d.add(text(250, 14, "Collection (browser extension and backend)", 15, italic=True),
          text(640, 14, "Analysis (background worker)", 15, italic=True),
          line(421, 4, 421, 1320, dash="3,6", stroke="#888888"))
    L, R = 250, 735
    n = {}

    def put(key, parts_shape):
        parts, shape = parts_shape
        d.add(parts)
        n[key] = shape
        return shape

    put("i", initial(L, 58))
    put("a1", action(L, 128, "Browser event committed\n(top-level navigation\nor completed download)", w=290, h=70))
    put("d1", diamond(L, 232, 190, 70, "Employee\npaired?"))
    put("ff", flowfinal(62, 232))
    put("a2", action(L, 330, "Strip query string & fragment,\nbuild metadata event", w=300))
    put("a3", action(L, 425, "Append to local queue\n(chrome.storage)", w=260))
    put("m1", diamond(L, 505, 40, 40))
    put("d2", diamond(L, 590, 190, 70, "Backend\nreachable?"))
    put("t1", hourglass(66, 505))
    d.add(text(14, 462, "wait for 30-s\nalarm", 13, anchor="start"))
    put("a4", action(L, 690, "POST /api/activity/batch", w=260, h=48))
    put("a5", action(L, 782, "Validate event and store\nin PostgreSQL", w=270))
    put("s1", send_signal(L, 875, "New live event\nstored", w=220))
    put("cA", connector(L, 950, "A"))

    d.add(flow([n["i"].bottom, n["a1"].top]), flow([n["a1"].bottom, n["d1"].top]))
    d.add(flow([n["d1"].left, n["ff"].right], "[no]", (122, 218)))
    d.add(flow([n["d1"].bottom, n["a2"].top], "[yes]", (L + 30, 280)))
    d.add(flow([n["a2"].bottom, n["a3"].top]), flow([n["a3"].bottom, n["m1"].top]), flow([n["m1"].bottom, n["d2"].top]))
    d.add(flow([n["d2"].left, (66, 590), (66, 523)], "[no]", (110, 575), color=LOOP))
    d.add(flow([(79, 505), n["m1"].left], "retry loop", (150, 490), color=LOOP))
    d.add(flow([n["d2"].bottom, n["a4"].top], "[yes]", (L + 30, 641)))
    d.add(flow([n["a4"].bottom, n["a5"].top]), flow([n["a5"].bottom, n["s1"].top]), flow([n["s1"].bottom, n["cA"].top]))
    d.add(note(40, 186, 120, 0, "", 1) if False else [])
    d.add(note(330, 160, 130, 56, "nothing is\ncollected", 13, anchor_to=((330, 188), (n["ff"].x + 12, 222))) if False else [])

    # analysis column
    put("cA2", connector(R - 180, 66, "A"))
    put("m2", diamond(R, 66, 40, 40))
    put("t2", hourglass(R, 132, "every 3 s", 14))
    put("d3", diamond(R, 225, 230, 78, "≥ 5 new events or\n≥ 90 s idle?", 13))
    put("fork", bar(R, 300, 330))
    put("p1", action(R - 92, 365, "Summarise\nhistorical baseline", w=170, h=56))
    put("p2", action(R + 92, 365, "Compute rule-\nbased indicators", w=170, h=56))
    put("join", bar(R, 430, 330))
    put("a6", action(R, 492, "Build role-aware prompt\n(≤ 15 context + ≤ 35 new)", w=290))
    put("m3", diamond(R, 565, 40, 40))
    put("a7", action(R, 638, "Query Ollama qwen2.5:3b\n(JSON schema)", w=270))
    put("d4", diamond(R, 735, 170, 74, "Response\nvalid?"))
    put("a8", action(912, 735, "Send corrective\nmessage", w=140, h=56, size=14))
    put("a9", action(R - 233, 735, "Record failure,\nschedule back-off", w=150, h=60, size=14))
    put("a10", action(R, 835, "Verify evidence IDs\nagainst supplied records", w=280))
    put("d5", diamond(R, 930, 220, 80, "Anomaly without\nvalid evidence?", 13))
    put("a11", action(R, 1030, "Save assessment and\nadvance cursor (one transaction)", w=300, h=60))
    put("o1", objnode(R, 1112, "Assessment\n[saved]", w=170, h=52))
    put("a12", action(R, 1192, "Display alert and\nevidence in dashboard", w=260))
    put("fin", final(R, 1272))

    d.add(flow([n["cA2"].right, n["m2"].left]))
    d.add(flow([n["m2"].bottom, n["t2"].top]), flow([n["t2"].bottom, n["d3"].top]))
    d.add(flow([n["d3"].right, (975, 225), (975, 66), n["m2"].right], "[no]", (935, 210), color=LOOP))
    d.add(label(985 - 40, 100, "poll loop", 13, fill=LOOP))
    d.add(flow([n["d3"].bottom, n["fork"].top], "[yes]", (R + 28, 280)))
    d.add(flow([(R - 92, 304), n["p1"].top]), flow([(R + 92, 304), n["p2"].top]))
    d.add(flow([n["p1"].bottom, (R - 92, 426)]), flow([n["p2"].bottom, (R + 92, 426)]))
    d.add(flow([n["join"].bottom, n["a6"].top]), flow([n["a6"].bottom, n["m3"].top]), flow([n["m3"].bottom, n["a7"].top]))
    d.add(flow([n["a7"].bottom, n["d4"].top]))
    d.add(flow([n["d4"].right, n["a8"].left], None, color=LOOP))
    d.add(label(912, 785, "[no, 1st attempt]", 13, fill=LOOP))
    d.add(flow([n["a8"].top, (912, 565), n["m3"].right], "corrective retry", (855, 548), color=LOOP))
    d.add(flow([n["d4"].left, n["a9"].right]))
    d.add(label(614, 712, "[no, 2nd\nattempt]", 12))
    d.add(flow([n["a9"].top, (R - 233, 30), (R, 30), n["m2"].top], None, color=LOOP))
    d.add(label(R - 233, 260, "retry\nlater", 13, fill=LOOP))
    d.add(flow([n["d4"].bottom, n["a10"].top], "[yes]", (R + 28, 786)))
    d.add(flow([n["a10"].bottom, n["d5"].top]))
    d.add(flow([n["d5"].left, (R - 233, 930), n["a9"].bottom], "[yes]", (585, 915)))
    d.add(flow([n["d5"].bottom, n["a11"].top], "[no]", (R + 24, 982)))
    d.add(flow([n["a11"].bottom, n["o1"].top]), flow([n["o1"].bottom, n["a12"].top]), flow([n["a12"].bottom, n["fin"].top]))
    d.add(note(852, 872, 140, 66, "IDs not in the\nprompt are\nremoved & logged", 13, anchor_to=((900, 872), (860, 864))))
    d.add(note(560, 1215, 125, 50, "cursor moves only\nafter success", 12, anchor_to=((622, 1215), (650, 1058))) if False else [])
    d.add(note(870, 1070, 125, 48, "cursor moves\nonly on success", 13, anchor_to=((870, 1090), n["a11"].right)))

    d.add(legend(30, 1000, 400, [
        (lambda x, y: initial(x + 12, y)[0] + final(x + 44, y)[0], "initial node / activity final node"),
        (lambda x, y: flowfinal(x + 12, y)[0] + connector(x + 46, y, "A")[0], "flow final / connector"),
        (lambda x, y: diamond(x + 28, y, 36, 22)[0], "decision / merge with [guards]"),
        (lambda x, y: bar(x + 28, y, 50, 7)[0], "fork / join (parallel flows)"),
        (lambda x, y: hourglass(x + 28, y)[0], "time event"),
        (lambda x, y: objnode(x + 28, y, "", w=50, h=20)[0], "object node"),
        (lambda x, y: [line(x, y, x + 56, y, stroke=LOOP, dash="8,5", end="arrow")], "loop / retry flow (dashed)"),
    ], title="Notation", size=13))
    d.save("activity_diagram")


def swimlane_diagram():
    lanes = ["Employee", "Chrome\nExtension", "FastAPI\nBackend", "PostgreSQL", "Analysis\nWorker", "Ollama\nLLM", "Security\nAnalyst"]
    lw = 146
    W = lw * len(lanes)
    H = 1350
    d = Diagram(W, H)
    for i, name in enumerate(lanes):
        d.add(rect(i * lw, 0, lw, H, fill="#ffffff" if i % 2 else "#ffffff", sw=1.2),
              rect(i * lw, 0, lw, 54, fill=FILL2, sw=1.2), text(i * lw + lw / 2, 27, name, 15, weight="bold"))
    cx = [i * lw + lw / 2 for i in range(len(lanes))]
    n = {}

    def put(key, parts_shape):
        d.add(parts_shape[0])
        n[key] = parts_shape[1]

    aw, ah = 128, 54
    put("i", initial(cx[0], 90))
    put("e1", action(cx[0], 160, "Confirm notice,\nenter employee ID", w=aw, h=ah, size=13))
    put("x1", send_signal(cx[1], 235, "Send pairing\nrequest", w=aw, h=ah, size=13))
    put("b1", accept_event(cx[2], 235, "Receive\nrequest", w=aw, h=ah, size=13))
    put("p1", action(cx[3], 310, "Look up\nemployee", w=aw, h=ah, size=13))
    put("bd", diamond(cx[2], 310, 110, 60, "exists?", 13))
    put("x2", action(cx[1], 310, "Show\nerror", w=aw - 30, h=48, size=13))
    put("p2", action(cx[3], 395, "INSERT\nsession", w=aw, h=ah, size=13))
    put("x3", action(cx[1], 395, "Store pairing,\nstart monitoring", w=aw, h=ah, size=13))
    put("e2", action(cx[0], 480, "Browse sites,\ndownload files", w=aw, h=ah, size=13))
    put("x4", action(cx[1], 560, "Capture metadata,\nstrip query", w=aw + 6, h=ah, size=13))
    put("xm", diamond(cx[1], 627, 30, 30))
    put("xd", diamond(cx[1], 695, 96, 58, "backend\nup?", 12))
    put("xt", hourglass(cx[1], 775))
    d.add(text(cx[1] + 20, 775, "wait\n30 s", 12, anchor="start"))
    put("b2", action(cx[2], 695, "Validate &\ningest batch", w=aw, h=ah, size=13))
    put("p3", action(cx[3], 780, "INSERT\nactivity_logs", w=aw, h=ah, size=13))
    put("t1", hourglass(cx[4], 780))
    d.add(text(cx[4], 752, "every 3 s", 12))
    put("w1", action(cx[4], 870, "Select new live\nevents (cursor)", w=aw + 6, h=ah, size=13))
    put("wd", diamond(cx[4], 955, 120, 62, "threshold\nreached?", 12))
    put("w2", action(cx[4], 1045, "Build context\n& prompt", w=118, h=ah, size=13))
    put("o1", action(cx[5], 1045, "Generate JSON\nassessment", w=118, h=ah, size=13))
    put("w3", action(cx[4], 1125, "Validate &\nverify evidence", w=aw, h=ah, size=13))
    put("wv", diamond(cx[4], 1205, 104, 58, "valid?", 13))
    put("p4", action(cx[3], 1205, "Save assessment,\nadvance cursor", w=aw + 8, h=ah, size=13))
    put("a1", action(cx[6], 1205, "Review alert\n& evidence", w=aw, h=ah, size=13))
    put("fin", final(cx[6], 1300))

    d.add(flow([n["i"].bottom, n["e1"].top]))
    d.add(flow([n["e1"].bottom, (cx[0], 235), n["x1"].left]))
    d.add(flow([n["x1"].right, n["b1"].left]))
    d.add(flow([n["b1"].bottom, n["bd"].top]))
    d.add(flow([n["b1"].right, (cx[3], 235), n["p1"].top], None))
    d.add(flow([n["p1"].left, n["bd"].right], "row", (cx[3] - 70, 298), size=12))
    d.add(flow([n["bd"].left, n["x2"].right], "[no]", (cx[1] + 70, 298), size=12))
    d.add(flow([n["x2"].left, (cx[0] + 20, 310), (cx[0] + 20, n["e1"].y + 27)], "loop", (cx[0] + 44, 260), size=12, color=LOOP))
    d.add(flow([n["bd"].bottom, (cx[2], 395), n["p2"].left], "[yes]", (cx[2] + 24, 352), size=12))
    d.add(flow([n["p2"].bottom, (cx[3], 432), (cx[1] + 30, 432), (cx[1] + 30, n["x3"].y + 27)]))
    d.add(flow([n["x3"].bottom, (cx[1], 480), n["e2"].right]))
    d.add(flow([n["e2"].bottom, (cx[0], 560), n["x4"].left]))
    d.add(flow([n["x4"].bottom, n["xm"].top]))
    d.add(flow([n["xm"].bottom, n["xd"].top]))
    d.add(flow([n["xd"].bottom, n["xt"].top], "[no]", (cx[1] + 22, 740), size=12, color=LOOP))
    d.add(flow([(cx[1] - 13, 775), (cx[1] - 58, 775), (cx[1] - 58, 627), n["xm"].left], "retry", (cx[1] - 58, 700), size=11, color=LOOP))
    d.add(flow([n["xd"].right, n["b2"].left], "[yes]", (cx[1] + 70, 680), size=12))
    d.add(flow([n["b2"].bottom, (cx[2], 780), n["p3"].left]))
    d.add(flow([n["p3"].right, n["t1"].left], None, dash="6,4"))
    d.add(label(cx[3] + 70, 760, "new rows", 11))
    d.add(flow([n["t1"].bottom, n["w1"].top]))
    d.add(flow([n["w1"].bottom, n["wd"].top]))
    d.add(flow([n["wd"].right, (cx[4] + 66, 955), (cx[4] + 66, 780), n["t1"].right], None, color=LOOP))
    d.add(label(cx[4] + 66, 915, "[no]", 12, fill=LOOP))
    d.add(flow([n["wd"].bottom, n["w2"].top], "[yes]", (cx[4] + 24, 998), size=12))
    d.add(flow([n["w2"].right, n["o1"].left]))
    d.add(label(cx[5] - 73, 1018, "prompt", 11))
    d.add(flow([n["o1"].bottom, (cx[5], 1125), n["w3"].right], "JSON", (cx[5] - 40, 1112), size=12))
    d.add(flow([n["w3"].bottom, n["wv"].top]))
    d.add(flow([n["wv"].right, (cx[5] + 40, 1205), (cx[5] + 40, n["o1"].y + 27)], "[no] retry", (cx[5] + 10, 1222), size=12, color=LOOP))
    d.add(flow([n["wv"].left, n["p4"].right], "[yes]", (cx[4] - 70, 1190), size=12))
    d.add(flow([n["p4"].bottom, (cx[3], 1262), (cx[6] - 30, 1262), (cx[6] - 30, n["a1"].y + 27)], "poll every 3-5 s", (cx[5], 1249), size=12))
    d.add(flow([n["a1"].bottom, n["fin"].top]))
    d.save("swimlane_diagram")


def dfd_level0():
    d = Diagram(1000, 480)
    pr, ps = process(500, 315, 105, "0", "hackViz\nInsider-Risk\nMonitoring\nSystem", 16)
    d.add(pr)
    for x, y, s, w in [(115, 250, "Monitored Employee\n(Chrome + extension)", 210), (115, 395, "System\nAdministrator", 210),
                       (885, 250, "Security Analyst", 210), (885, 395, "Ollama LLM Service\n(local, qwen2.5:3b)", 210),
                       (500, 55, "Synthetic CERT-style\nDataset Generator", 280)]:
        d.add(entity(x, y, s, w=w, h=70 if y != 55 else 60)[0])

    def cx_at(y, side):
        dx = math.sqrt(max(0.0, 105 ** 2 - (y - 315) ** 2))
        return 500 - dx if side == "L" else 500 + dx

    def hflow(x1, x2, y, lab, ly):
        d.add(line(x1, y, x2, y, end="arrow"), label((x1 + x2) / 2, ly, lab, 13))

    hflow(220, cx_at(235, "L"), 235, "navigation &\ndownload metadata,\npairing request", 205)
    hflow(cx_at(265, "L"), 220, 265, "pairing status, name &\nrole, ingest results", 292)
    hflow(220, cx_at(380, "L"), 380, "new employees,\nconfiguration, reset", 352)
    hflow(cx_at(410, "L"), 220, 410, "monitoring and\nsystem status", 438)
    hflow(780, cx_at(235, "R"), 235, "queries, filters,\nAnalyze Now,\nexport request", 205)
    hflow(cx_at(265, "R"), 780, 265, "dashboard data, alerts,\nevidence records, CSV", 292)
    hflow(cx_at(380, "R"), 780, 380, "role-aware prompt\n(JSON schema)", 352)
    hflow(780, cx_at(410, "R"), 410, "JSON assessment", 432)
    d.add(line(500, 85, 500, 210, end="arrow"), label(578, 150, "historical activity\nrecords (CSV)", 13))
    d.save("dfd_level0")


def dfd_level1():
    d = Diagram(1040, 1160)
    n = {}

    def put(k, ps):
        d.add(ps[0])
        n[k] = ps[1]

    put("emp", entity(100, 230, "Monitored\nEmployee", w=170, h=70))
    put("ana", entity(900, 120, "Security\nAnalyst", w=170, h=66))
    put("oll", entity(900, 870, "Ollama LLM\nService", w=170, h=66))
    put("adm", entity(100, 1110, "System\nAdministrator", w=170, h=60))
    put("p1", process(330, 110, 70, "1.0", "Manage\nExtension\nPairing"))
    put("p2", process(330, 400, 70, "2.0", "Ingest &\nValidate\nActivity"))
    put("p3", process(650, 600, 70, "3.0", "Build\nBehavioural\nContext"))
    put("p4", process(650, 830, 70, "4.0", "Assess with\nLLM"))
    put("p5", process(900, 400, 70, "5.0", "Present &\nExport\nResults"))
    put("p6", process(330, 990, 70, "6.0", "Manage\nEmployees &\nDataset"))
    put("d5", store(620, 50, "D5", "Extension Sessions", w=210))
    put("d1", store(620, 170, "D1", "Employees", w=210))
    put("d2", store(650, 400, "D2", "Activity Logs", w=210))
    put("d1b", store(330, 600, "D1", "Employees", w=200, dup=True))
    put("d4", store(900, 690, "D4", "Analysis State", w=170))
    put("d3", store(650, 1020, "D3", "Assessments", w=210))
    put("d6", store(120, 880, "D6", "Dataset Files", w=200))
    put("d2b", store(330, 1120, "D2", "Activity Logs", w=220, dup=True))

    def circ(k, y, side):
        c = n[k]
        dx = math.sqrt(max(0.0, c.a ** 2 - (y - c.y) ** 2))
        return (c.x - dx, y) if side == "L" else (c.x + dx, y)

    def at(k, deg):
        c = n[k]
        return (c.x + c.a * math.cos(math.radians(deg)), c.y + c.a * math.sin(math.radians(deg)))

    def F(pts, lab=None, lp=None, color=INK):
        d.add(flow(pts, lab, lp, size=13, color=color))

    F([(80, 195), (80, 95), circ("p1", 95, "L")], "employee ID,\nconsent", (170, 72))
    F([circ("p1", 130, "L"), (120, 130), (120, 195)], "name, role,\ntoken", (192, 158))
    F([at("p1", -35), (515, 50)], "new session", (450, 36))
    F([(515, 170), at("p1", 25)], "employee\nrecord", (452, 190))
    F([(80, 265), (80, 385), circ("p2", 385, "L")], "activity events\n(batch)", (190, 360))
    F([circ("p2", 425, "L"), (120, 425), (120, 265)], "ingest results", (190, 446), color=LOOP)
    F([(580, 190), (580, 260), (330, 260), (330, 330)], "employee check", (455, 246))
    F([(400, 400), (545, 400)], "validated\nevents", (472, 375))
    F([(650, 420), (650, 530)], "history +\nnew events", (712, 475))
    F([(755, 400), (830, 400)], "activity,\nevidence", (792, 375))
    F([(880, 153), (880, 333)], "queries,\nfilters", (835, 245))
    F([(920, 333), (920, 153)], "dashboard,\nalerts, CSV", (982, 245))
    F([(900, 470), (900, 570), circ("p3", 570, "R")], "analysis\nrequest", (805, 548), color=LOOP)
    F([(815, 690), (745, 690), (745, 630), circ("p3", 630, "R")], "cursor,\nretry time", (787, 662), color=LOOP)
    F([(650, 670), (650, 760)], "context, indicators,\nallowed IDs", (560, 715))
    F([at("p4", -45), (900, at("p4", -45)[1]), (900, 710)], "cursor / failure\nstate", (807, 757), color=LOOP)
    F([circ("p4", 855, "R"), (815, 855)], "prompt", (765, 841))
    F([(815, 885), circ("p4", 885, "R")], "JSON\nassessment", (760, 912))
    F([(650, 900), (650, 1000)], "validated\nassessment", (716, 950))
    F([(755, 1020), (1012, 1020), (1012, 400), (970, 400)], "alerts", (1012, 960))
    F([(430, 600), (580, 600)], "role,\ndepartment", (505, 577))
    F([(330, 920), (330, 620)], "employee\nrecords", (272, 770))
    F([(185, 1095), at("p6", 150)], "new employee,\nreset", (160, 1040))
    F([(200, 900), at("p6", 220)], "fictional\ndataset", (178, 942))
    F([(330, 1060), (330, 1100)], "historical\nrecords", (402, 1080))
    d.add(note(782, 1062, 250, 86, "Loops (dashed):\nL1  ingest results / resend\nL2  cursor & retry via D4\nL3  analyst request → 3.0 → 5.0", 12))
    d.save("dfd_level1")


def dfd_level2():
    d = Diagram(1000, 1020)
    n = {}

    def put(k, ps):
        d.add(ps[0])
        n[k] = ps[1]

    put("p3", entity(130, 115, "3.0 Build Behavioural\nContext (Level 1)", w=200, h=66))
    put("oll", entity(890, 260, "Ollama LLM\nService", w=170, h=66))
    put("q1", process(440, 150, 62, "4.1", "Compose\nprompt"))
    put("q2", process(680, 260, 62, "4.2", "Query\nLLM"))
    put("q3", process(680, 480, 62, "4.3", "Parse\nJSON"))
    put("q4", process(440, 560, 62, "4.4", "Validate\nschema &\nconsistency"))
    put("q5", process(440, 790, 62, "4.5", "Verify\nevidence IDs"))
    put("q6", process(700, 860, 62, "4.6", "Save &\nadvance\ncursor"))
    put("q7", process(150, 680, 62, "4.7", "Record\nfailure &\nback-off"))
    put("d1", store(140, 300, "D1", "Employees", w=220))
    put("d3", store(870, 690, "D3", "Assessments", w=220))
    put("d4", store(720, 985, "D4", "Analysis State", w=220))

    def at(k, deg):
        c = n[k]
        return (c.x + c.a * math.cos(math.radians(deg)), c.y + c.a * math.sin(math.radians(deg)))

    def F(pts, lab=None, lp=None, color=INK):
        d.add(flow(pts, lab, lp, size=13, color=color))

    F([(230, 120), (440 - math.sqrt(62 ** 2 - 30 ** 2), 120)], "context, indicators,\nallowed IDs", (300, 170))
    F([(250, 285), at("q1", 135)], "role, expected\ncategories", (330, 292))
    F([at("q1", 30), at("q2", 200)], "messages", (560, 190))
    F([(680 + math.sqrt(62 ** 2 - 15 ** 2), 245), (805, 245)], "prompt +\nschema", (772, 220))
    F([(805, 275), (680 + math.sqrt(62 ** 2 - 15 ** 2), 275)], "raw\nresponse", (772, 300))
    F([(680, 322), (680, 418)], "response\ntext", (735, 370))
    F([at("q3", 200), at("q4", 20)], "parsed\nobject", (560, 488))
    F([(440, 498), (440, 212)], "[invalid, 1st attempt]\ncorrective message", (440, 355), color=LOOP)
    F([(440, 622), (440, 728)], "valid\nassessment", (500, 675))
    F([at("q4", 200), at("q7", -30)], "[invalid twice]", (290, 590), color=LOOP)
    F([at("q5", 200), at("q7", 30)], "[anomaly without\nvalid evidence]", (300, 800), color=LOOP)
    F([at("q5", 20), at("q6", 200)], "verified\nassessment", (565, 862))
    F([at("q6", -50), (840, 710)], "assessment +\nindicators", (835, 792))
    F([(700, 922), (700, 965)], "cursor =\nmax ID", (760, 940))
    F([(150, 742), (150, 985), (610, 985)], "error, next retry time", (380, 968), color=LOOP)
    d.add(note(765, 400, 225, 126, "L2a  invalid response: one\ncorrective retry (4.4 → 4.1)\nL2b  invalid twice, no valid\nevidence, timeout or LLM down:\nnothing saved; batch retried\nlater from D4", 12))
    d.save("dfd_level2")


def er_diagram():
    d = Diagram(1000, 1000)

    def ent(x, y, w, name, attrs):
        rowh = 23
        h = 40 + rowh * len(attrs) + 8
        out = [rect(x, y, w, h, rx=4, fill="#ffffff"), rect(x, y, w, 40, rx=4, fill=FILL2),
               text(x + w / 2, y + 20, name, 16, weight="bold")]
        for i, (key, a) in enumerate(attrs):
            yy = y + 40 + 6 + rowh * i + rowh / 2
            if key:
                out.append(text(x + 10, yy, key, 11.5, anchor="start", weight="bold", fill="#000000"))
            out.append(text(x + 56, yy, a, 14, anchor="start"))
        return out, (x, y, w, h)

    emp, eb = ent(360, 30, 280, "EMPLOYEE", [
        ("PK", "id : integer"), ("UQ", "employee_id : varchar(32)"), ("", "name : varchar(120)"),
        ("", "role : varchar(120)"), ("", "department : varchar(120)"), ("", "email : varchar(254)"),
        ("", "profile : jsonb"), ("", "is_synthetic : boolean"), ("", "created_at : timestamptz")])
    act, ab = ent(20, 360, 300, "ACTIVITY_LOG", [
        ("PK", "id : bigint"), ("FK", "employee_id : varchar(32)"), ("", "event_type : varchar(32)"),
        ("", "domain : varchar(255)"), ("", "url : varchar(2048)"), ("", "filename : varchar(512)"),
        ("", "timestamp : timestamptz"), ("", "source : varchar(32)"), ("", "safe_metadata : jsonb"),
        ("UQ", "client_event_id : varchar(64)"), ("UQ", "dataset_record_id"), ("", "received_at : timestamptz")])
    ano, nb = ent(680, 360, 300, "ANOMALY (assessment)", [
        ("PK", "id : integer"), ("FK", "employee_id : varchar(32)"), ("", "is_anomaly : boolean"),
        ("", "risk_level : varchar(8)"), ("", "confidence : float"), ("", "reason : text"),
        ("", "evidence_event_ids : jsonb"), ("", "recommended_action : text"), ("", "analysis_source"),
        ("UQ", "batch_id : varchar(36)"), ("", "batch_start/end_event_id"), ("", "analyzed_event_ids : jsonb"),
        ("", "indicators : jsonb"), ("", "model_name : varchar(64)"), ("", "raw_response : text"),
        ("", "validation_notes : jsonb"), ("", "duration_ms : integer"), ("", "created_at : timestamptz")])
    st, sb = ent(355, 360, 290, "ANALYSIS_STATE", [
        ("PK,FK", "employee_id"), ("", "last_analyzed_event_id"), ("", "last_success_at"), ("", "last_attempt_at"),
        ("", "last_error : text"), ("", "consecutive_failures"), ("", "next_retry_at")])
    ses, xb = ent(355, 640, 290, "EXTENSION_SESSION", [
        ("PK", "id : integer"), ("UQ", "session_token : varchar(64)"), ("FK", "employee_id"),
        ("", "paired_at"), ("", "last_heartbeat_at"), ("", "last_event_at"), ("", "events_received"),
        ("", "disconnected_at")])
    d.add(emp, act, ano, st, ses)

    def cf(x, y, dx, dy, kind):
        """Crow's-foot end. (x,y) is on the entity border; (dx,dy) points away from the entity."""
        px, py = -dy, dx
        out = []
        if kind == "one_one":
            for dist in (10, 18):
                out.append(line(x + dx * dist + px * 9, y + dy * dist + py * 9, x + dx * dist - px * 9, y + dy * dist - py * 9))
        if kind in ("zero_many", "one_many"):
            for s in (-11, 0, 11):
                out.append(line(x + dx * 18, y + dy * 18, x + px * s, y + py * s))
        if kind == "zero_one":
            out.append(line(x + dx * 12 + px * 9, y + dy * 12 + py * 9, x + dx * 12 - px * 9, y + dy * 12 - py * 9))
        if kind in ("zero_many", "zero_one"):
            out.append(circle(x + dx * 30, y + dy * 30, 7))
        return out

    def rel(pts, k1, k2, lab, lp, dash=None):
        (x1, y1), (x1b, y1b) = pts[0], pts[1]
        (x2, y2), (x2b, y2b) = pts[-1], pts[-2]
        n1 = math.hypot(x1b - x1, y1b - y1)
        n2 = math.hypot(x2b - x2, y2b - y2)
        d.add(poly(pts, dash=dash), cf(x1, y1, (x1b - x1) / n1, (y1b - y1) / n1, k1),
              cf(x2, y2, (x2b - x2) / n2, (y2b - y2) / n2, k2), label(lp[0], lp[1], lab, 14, italic=True))

    rel([(360, 150), (170, 150), (170, 360)], "one_one", "zero_many", "performs", (170, 255))
    rel([(640, 150), (830, 150), (830, 360)], "one_one", "zero_many", "is assessed in", (830, 255))
    rel([(500, 285), (500, 360)], "one_one", "zero_one", "has cursor", (565, 322))
    rel([(380, 285), (380, 318), (337, 318), (337, 780), (355, 780)], "one_one", "zero_many", "pairs via", (282, 735))
    rel([(680, 790), (662, 790), (662, 950), (170, 950), (170, 684)], "zero_many", "zero_many",
        "cites as evidence (evidence_event_ids)", (420, 950), dash="7,5")
    d.add(rect(690, 838, 295, 105, rx=6, fill="#ffffff", dash="4,3"),
          text(700, 846, "Crow's-foot notation", 13, anchor="start", weight="bold", valign="top"))
    for i, (kind, desc) in enumerate([("one_one", "exactly one"), ("zero_many", "zero or many"), ("zero_one", "zero or one")]):
        yy = 880 + i * 22
        d.add(line(705, yy, 765, yy), cf(765, yy, -1, 0, kind), text(785, yy, desc, 13, anchor="start"))
    d.add(line(870, 880, 930, 880, dash="6,4"), text(870, 902, "logical link", 12, anchor="start"),
          text(870, 920, "(JSON array)", 12, anchor="start"))
    d.save("er_diagram")


def sequence_diagram():
    names = ["«actor»\nEmployee", ":Chrome\nExtension", ":FastAPI\nBackend", ":PostgreSQL",
             ":Analysis\nWorker", ":Ollama\nLLM", ":Analyst\nDashboard"]
    W, H = 1070, 1340
    gap = 150
    xs = [80 + i * gap for i in range(len(names))]
    d = Diagram(W, H)
    for x, nm in zip(xs, names):
        d.add(rect(x - 66, 18, 132, 52, rx=4, fill=FILL2), text(x, 44, nm, 14, weight="bold"),
              line(x, 70, x, H - 14, dash="6,5", stroke="#777777", sw=1.2))
    E, X, B, P, Wk, O, A = range(7)
    acts = []

    def act(i, y1, y2):
        acts.append(rect(xs[i] - 6, y1, 12, y2 - y1, fill="#ffffff", sw=1.3))

    msgs = []

    def msg(i, j, y, s, ret=False):
        x1, x2 = xs[i], xs[j]
        x1 += 6 if x2 > x1 else -6
        x2 += -6 if x2 > x1 else 6
        msgs.append(line(x1, y, x2, y, dash="6,4" if ret else None, end="open" if ret else "arrow"))
        msgs.append(text((x1 + x2) / 2, y - 9, s, 12.5))

    def selfmsg(i, y, s):
        x = xs[i] + 6
        msgs.append(path(f"M{x},{y} L{x + 34},{y} L{x + 34},{y + 24} L{x + 2},{y + 24}", end="arrow"))
        msgs.append(text(x + 44, y + 12, s, 12.5, anchor="start"))

    frags = []   # fragment outlines (drawn under activations)
    tabs = []    # operator tabs and guards (drawn over activations)

    def frag(x1, y1, x2, y2, op, guard, gx=None, gy=None):
        w = len(op) * 9 + 22
        frags.append(rect(x1, y1, x2 - x1, y2 - y1, fill="none", sw=1.3))
        tabs.append(path(f"M{x1},{y1} L{x1 + w},{y1} L{x1 + w},{y1 + 14} L{x1 + w - 8},{y1 + 22} L{x1},{y1 + 22} Z", fill=FILL2, sw=1.3))
        tabs.append(text(x1 + 6, y1 + 11, op, 13, anchor="start", weight="bold"))
        if gx is None:
            gx, gy = x1 + w + 10, y1 + 11
        tabs.append(label(gx + tw(guard, 12.5) / 2, gy, guard, 12.5, italic=True))

    # pairing
    act(X, 98, 375); act(B, 133, 372); act(P, 170, 222); act(P, 260, 280)
    msg(E, X, 108, "1: enter ID + consent")
    msg(X, B, 143, "2: POST /api/extension/pair")
    msg(B, P, 180, "3: SELECT employee")
    msg(P, B, 214, "4: row", ret=True)
    frag(xs[X] - 45, 232, xs[P] + 75, 380, "alt", "[employee exists]", gx=xs[X] + 12, gy=258)
    msg(B, P, 272, "5: INSERT session")
    msg(B, X, 304, "6: 201 name, role, token", ret=True)
    frags.append(line(xs[X] - 45, 320, xs[P] + 75, 320, dash="6,4", sw=1.2))
    tabs.append(label(xs[X] + 12 + tw("[else]", 12.5) / 2, 336, "[else]", 12.5, italic=True))
    msg(B, X, 364, "7: 404 not found", ret=True)
    # live collection
    frag(xs[E] - 55, 400, xs[P] + 75, 635, "loop", "[each navigation / completed download]")
    act(X, 436, 625); act(B, 540, 615)
    msg(E, X, 446, "8: browse / download")
    selfmsg(X, 464, "9: strip query, enqueue")
    frag(xs[X] - 30, 505, xs[P] + 60, 625, "opt", "[backend reachable]")
    msg(X, B, 550, "10: POST /activity/batch")
    msg(B, P, 580, "11: INSERT activity")
    msg(B, X, 610, "12: 201 results", ret=True)
    # worker
    frag(xs[P] - 65, 655, xs[O] + 75, 1050, "loop", "[every 3 s]")
    act(Wk, 690, 1040); act(P, 694, 726); act(P, 784, 820)
    msg(Wk, P, 702, "13: pending events")
    msg(P, Wk, 730, "14: counts", ret=True)
    frag(xs[P] - 50, 752, xs[O] + 62, 1038, "opt", "[≥ 5 events or 90 s idle]")
    msg(Wk, P, 792, "15: read window")
    msg(P, Wk, 822, "16: rows", ret=True)
    selfmsg(Wk, 838, "17: baseline,\nindicators, prompt")
    act(O, 888, 936)
    msg(Wk, O, 898, "18: POST /api/chat")
    msg(O, Wk, 930, "19: JSON", ret=True)
    rx1, rx2 = xs[Wk] - 70, xs[O] + 52
    refs = [rect(rx1, 950, rx2 - rx1, 44, fill="#ffffff", sw=1.3),
            path(f"M{rx1},950 L{rx1 + 38},950 L{rx1 + 38},962 L{rx1 + 31},968 L{rx1},968", fill=FILL2, sw=1.3),
            text(rx1 + 5, 959, "ref", 12, anchor="start", weight="bold"),
            text((rx1 + rx2) / 2 + 12, 980, "Validate response & verify evidence", 12.5)]
    msg(Wk, P, 1022, "20: INSERT anomaly + cursor")
    # dashboard
    frag(xs[B] - 62, 1068, xs[A] + 70, 1318, "loop", "[every 3-5 s while the dashboard is open]")
    act(A, 1100, 1305); act(B, 1105, 1300); act(P, 1136, 1172)
    msg(A, B, 1114, "21: GET /api/anomalies")
    msg(B, P, 1144, "22: SELECT")
    msg(P, B, 1172, "23: rows", ret=True)
    msg(B, A, 1200, "24: alerts JSON", ret=True)
    frag(xs[B] - 48, 1220, xs[A] + 56, 1308, "opt", "[analyst clicks an evidence ID]")
    msg(A, B, 1260, "25: GET /api/activity/{id}")
    msg(B, A, 1292, "26: original record", ret=True)
    d.add(frags, acts, tabs, refs, msgs)
    d.save("sequence_diagram")


def state(cx, cy, w, h, name, body="", size=15):
    x, y = cx - w / 2, cy - h / 2
    out = [rect(x, y, w, h, rx=14, fill=FILL), text(cx, y + 18, name, size, weight="bold")]
    if body:
        out += [line(x, y + 34, x + w, y + 34, sw=1.1), text(x + 10, y + 40, body, 12.5, anchor="start", valign="top")]
    return out, S("rect", cx, cy, w / 2, h / 2)


def state_analysis():
    d = Diagram(1000, 820)
    n = {}

    def put(k, ps):
        d.add(ps[0])
        n[k] = ps[1]

    def T(pts, lab=None, lp=None, color=INK):
        d.add(flow(pts, lab, lp, size=13, color=color))

    put("i", initial(50, 120))
    put("idle", state(200, 120, 210, 84, "Idle", "entry / cursor up to date"))
    put("pend", state(520, 120, 230, 84, "Pending", "do / count new live\nevents"))
    put("queue", state(850, 120, 200, 84, "Queued", "entry / add job to\nworker queue"))
    # composite state with nested states, an initial pseudostate and an exit point
    d.add(rect(380, 290, 540, 270, rx=18, fill="#ffffff"), text(650, 310, "Analysing", 16, weight="bold"),
          line(380, 326, 920, 326, sw=1.1))
    put("ii", initial(410, 400))
    put("ctx", state(520, 400, 150, 56, "Building\ncontext", size=13))
    put("qry", state(720, 400, 150, 56, "Querying\nLLM", size=13))
    put("val", state(720, 500, 150, 56, "Validating", size=13))
    xp = (720, 560)
    d.add(circle(xp[0], xp[1], 8), line(xp[0] - 5, xp[1] - 5, xp[0] + 5, xp[1] + 5), line(xp[0] - 5, xp[1] + 5, xp[0] + 5, xp[1] - 5),
          text(xp[0] + 14, xp[1] + 14, "exit point", 11, anchor="start", italic=True))
    put("fail", state(200, 420, 220, 84, "Failed", "entry / record error,\nconsecutive_failures++"))
    put("wait", state(200, 660, 230, 84, "Waiting for retry", "do / back-off 60 s x\nfailures (max 600 s)"))
    put("fin", final(40, 800))

    T([n["i"].right, n["idle"].left])
    T([(305, 110), (405, 110)], "new live event", (355, 92))
    T([(560, 78), (560, 46), (620, 46), (620, 78)], "new live event [count < 5]", (590, 30))
    T([(635, 120), (750, 120)], "[count ≥ 5 or\nidle ≥ 90 s]", (692, 90))
    T([(260, 162), (260, 215), (850, 215), (850, 162)], "Analyze Now (manual)", (560, 215))
    T([(900, 162), (900, 290)], "worker free", (845, 245))
    T([n["ii"].right, n["ctx"].left])
    T([n["ctx"].right, n["qry"].left])
    T([(760, 428), (760, 472)], "response", (818, 450))
    T([(645, 500), (612, 500), (612, 450), (680, 450), (680, 428)], None, None, color=LOOP)
    d.add(label(520, 522, "[invalid, 1st attempt]\n/ corrective retry", 13, fill=LOOP))
    T([(720, 528), (720, 552)])
    T([(720, 568), (720, 760), (62, 760), (62, 200), (130, 200), (130, 162)],
      "[valid] / save assessment, advance cursor", (500, 760))
    T([(380, 420), (310, 420)], None, None, color=LOOP)
    d.add(label(345, 470, "[invalid\ntwice] or\ntimeout /\nLLM down", 12, fill=LOOP))
    T([(200, 462), (200, 618)], "after error\nrecorded", (255, 540))
    T([(315, 660), (965, 660), (965, 140), (950, 140)], "after(retry delay)", (650, 660), color=LOOP)
    T([(95, 150), (12, 150), (12, 800), (26, 800)])
    d.add(text(64, 800, "backend stopped", 12, anchor="start", italic=True))
    d.save("state_analysis")


def state_extension():
    d = Diagram(1000, 640)
    n = {}

    def put(k, ps):
        d.add(ps[0])
        n[k] = ps[1]

    put("i", initial(60, 90))
    put("un", state(200, 90, 200, 80, "Unpaired", "do / collect nothing"))
    put("ch", diamond(470, 90, 60, 60))
    put("pi", state(470, 270, 230, 80, "Paired - Idle", "entry / store token\ndo / heartbeat 30 s"))
    put("tx", state(820, 270, 230, 80, "Transmitting", "do / POST batch\nfrom queue"))
    put("off", state(820, 480, 230, 80, "Offline - Queueing", "do / keep events in\nchrome.storage"))
    put("inv", state(470, 480, 230, 80, "Pairing invalid", "entry / clear queue,\nshow error"))
    put("fin", final(60, 560))

    def tr(pts, lab, lp, color=INK):
        d.add(flow(pts, lab, lp, size=13, color=color))

    tr([n["i"].right, n["un"].left], None, None)
    tr([n["un"].right, n["ch"].left], "Pair [notice\nconfirmed]", (360, 60))
    tr([n["ch"].bottom, n["pi"].top], "[employee exists]", (555, 175))
    tr([n["ch"].right, (720, 90), (720, 40), (200, 40), n["un"].top], "[not found] / show error", (460, 26), color=LOOP)
    tr([(n["pi"].x + 115, 255), (n["tx"].x - 115, 255)], "event captured", (645, 240))
    tr([(n["tx"].x - 115, 290), (n["pi"].x + 115, 290)], "batch accepted", (645, 305))
    tr([(n["tx"].x - 40, 310), (n["off"].x - 40, 440)], "backend\nunreachable", (720, 375), color=LOOP)
    tr([(n["off"].x + 40, 440), (n["tx"].x + 40, 310)], "alarm (30 s)\n[backend up]", (925, 375), color=LOOP)
    tr([(n["pi"].x, 310), (n["inv"].x, 440)], "401 / 403 / 404\n(token revoked)", (548, 375))
    tr([n["inv"].left, (200, 480), n["un"].bottom], "user re-pairs", (240, 300) if False else (200, 300))
    tr([(n["pi"].x - 115, 270), (300, 270), (300, 130)] if False else [(n["pi"].x - 115, 270), (260, 270), (260, 130)],
       "Disconnect", (300, 210) if False else (255, 205))
    tr([(n["un"].x - 60, 130), (n["un"].x - 60, 560) if False else (140, 545), n["fin"].right] if False else [(130, 130), (130, 560), n["fin"].right],
       "extension\nremoved", (130, 470))
    d.add(note(560, 560, 330, 60, "Disconnect and token revocation can occur in\nany paired state (shown from Paired - Idle)", 12))
    d.save("state_extension")


def deployment_diagram():
    d = Diagram(1000, 790)

    def node3d(x, y, w, h, title, fill="#ffffff", depth=14):
        return [path(f"M{x},{y} L{x + depth},{y - depth} L{x + w + depth},{y - depth} L{x + w + depth},{y + h - depth} L{x + w},{y + h} Z", fill="#e6e6e6"),
                rect(x, y, w, h, fill=fill), line(x + w, y, x + w + depth, y - depth),
                text(x + 12, y + 10, title, 14, anchor="start", weight="bold", valign="top")]

    def comp(x, y, w, h, name, stereo="«component»"):
        return [rect(x, y, w, h, rx=3, fill=FILL), text(x + w / 2 - 6, y + 20, stereo, 12, italic=True),
                text(x + w / 2 - 6, y + 44, name, 14, weight="bold"),
                rect(x + w - 24, y + 8, 16, 18, fill="#ffffff", sw=1.2), rect(x + w - 28, y + 11, 8, 4, fill="#ffffff", sw=1.2),
                rect(x + w - 28, y + 19, 8, 4, fill="#ffffff", sw=1.2)]

    def artifact(x, y, w, h, name):
        return [rect(x, y, w, h, fill="#ffffff"), text(x + w / 2, y + 18, "«artifact»", 12, italic=True),
                text(x + w / 2, y + 40, name, 14, weight="bold"),
                path(f"M{x + w - 22},{y + 6} L{x + w - 10},{y + 6} L{x + w - 6},{y + 10} L{x + w - 6},{y + 24} L{x + w - 22},{y + 24} Z", fill="#ffffff", sw=1.1)]

    d.add(node3d(20, 40, 930, 735, "«device»  Windows 11 laptop (16 GB RAM, CPU only)"))
    d.add(node3d(50, 100, 410, 250, "«execution environment»  Google Chrome"))
    d.add(comp(70, 160, 175, 80, "React dashboard"))
    d.add(comp(265, 160, 175, 80, "MV3 extension"))
    d.add(text(255, 280, "popup + service worker:\nwebNavigation, downloads,\nstorage, alarms", 12.5))
    d.add(node3d(520, 100, 410, 250, "«execution environment»  Python 3.12 / Uvicorn :8000"))
    d.add(comp(540, 150, 175, 80, "FastAPI routes"))
    d.add(comp(735, 150, 175, 80, "Analysis worker"))
    d.add(comp(540, 250, 175, 80, "Validators / schemas"))
    d.add(comp(735, 250, 175, 80, "Seed & export"))
    d.add(node3d(50, 470, 270, 230, "«execution environment»\nNode.js / Vite :5173"))
    d.add(artifact(80, 570, 210, 62, "dashboard bundle"))
    d.add(node3d(360, 470, 270, 230, "«database»\nPostgreSQL 16 :5432"))
    d.add(artifact(390, 570, 210, 62, "hackviz database"))
    d.add(node3d(670, 470, 270, 230, "«execution environment»\nOllama :11434"))
    d.add(artifact(700, 570, 210, 62, "qwen2.5:3b model"))
    # assembly connector (ball-and-socket): extension requires, FastAPI routes provides the REST interface
    d.add(line(540, 195, 505, 195), circle(497, 195, 8), path("M487,181 A14,14 0 0,0 487,209"), line(487, 195, 440, 195),
          text(492, 168, "REST /api", 12.5, weight="bold"))
    # communication paths between nodes
    for pts, lab, lp in [
        ([(157, 470), (157, 240)], "HTTP :5173\n(page, /api proxy)", (157, 410)),
        ([(352, 240), (352, 395), (505, 395), (505, 300), (540, 300)], "HTTP JSON :8000\n(events, pairing)", (430, 395)),
        ([(627, 330), (627, 420), (495, 420), (495, 470)], "psycopg :5432", (560, 432)),
        ([(910, 190), (950, 190), (950, 430), (805, 430), (805, 470)], "HTTP :11434\n/api/chat", (880, 430)),
    ]:
        d.add(poly(pts, start="arrow", end="arrow"), label(lp[0], lp[1], lab, 12.5))
    d.add(note(60, 718, 870, 40, "All nodes run on one laptop; the extension talks to the backend directly, the dashboard through the Vite proxy.", 12.5))
    d.save("deployment_diagram")


def package_diagram():
    d = Diagram(1000, 500)
    W, H = 250, 120
    pos = {"routes": (40, 90), "services": (375, 90), "schemas": (710, 90),
           "db": (40, 350), "models": (375, 350), "seed": (710, 350)}
    info = {"routes": ("app.routes", "system, employees, activity,\nanomalies, export, extension"),
            "services": ("app.services", "analyzer, indicators, worker,\ndomain_catalog, ollama_client"),
            "schemas": ("app.schemas", "EmployeeCreate, ActivityIn,\nAnomalyOut, LLMAssessment"),
            "db": ("app.database / config", "engine, SessionLocal,\nsettings (PostgreSQL only)"),
            "models": ("app.models", "Employee, ActivityLog, Anomaly,\nAnalysisState, ExtensionSession"),
            "seed": ("app.seed / app.main", "dataset import, FastAPI app,\nworker start-up")}
    sh = {}
    for k, (x, y) in pos.items():
        name, items = info[k]
        tabw = max(110, len(name) * 9 + 20)
        d.add(rect(x, y - 24, tabw, 24, fill=FILL2), text(x + 8, y - 12, name, 14, anchor="start", weight="bold"),
              rect(x, y, W, H, fill="#ffffff"), text(x + W / 2, y + H / 2, items, 13))
        sh[k] = S("rect", x + W / 2, y + H / 2, W / 2, H / 2)

    def dep(a, b, lab="«import»"):
        ln, mid = connect(sh[a], sh[b], dash="7,5", end="open")
        d.add(ln, label(mid[0], mid[1], lab, 12.5))

    dep("routes", "services")
    dep("services", "schemas")
    dep("models", "db")
    dep("seed", "models")
    for pts, lab, lp in [([(250, 210), (520, 350)], "«import»", (385, 280)),
                         ([(560, 210), (560, 350)], "«import»", (560, 280)),
                         ([(930, 350), (600, 210)], "«use»", (765, 280))]:
        d.add(poly(pts, dash="7,5", end="open"), label(lp[0], lp[1], lab, 12.5))
    d.add(poly([(165, 66), (165, 28), (835, 28), (835, 66)], dash="7,5", end="open"),
          label(500, 28, "«import»", 12.5))
    d.save("package_diagram")


def architecture_diagram():
    d = Diagram(1000, 760)
    L = 40
    layers = [("Presentation", "React dashboard (Vite)  |  extension popup", 40, 80),
              ("Collection", "Chrome MV3 service worker: webNavigation, downloads, queue", 145, 80),
              ("Application", "FastAPI: REST routes, validation, CSV export, pairing, seeding", 250, 80),
              ("Intelligence", None, 355, 250),
              ("Data", "PostgreSQL: employees, activity_logs, anomalies, analysis_state, sessions  |  dataset files", 630, 80)]
    for name, desc, y, h in layers:
        d.add(rect(L, y, 920, h, rx=8, fill=FILL), rect(L, y, 170, h, rx=8, fill=FILL2),
              text(L + 85, y + h / 2, name, 16, weight="bold"))
        if desc:
            d.add(text(585, y + h / 2, desc, 15))
    # intelligence layer detail
    d.add(rect(230, 370, 710, 52, rx=6, fill="#ffffff"),
          text(585, 396, "Analysis worker: temporal engine, baseline, rule indicators, prompt, validation", 14.5))
    d.add(rect(230, 440, 450, 150, rx=6, fill="#ffffff", sw=2.2),
          text(455, 460, "Transformer LLM  (implemented)", 15, weight="bold"),
          text(455, 515, "Qwen2.5-3B-Instruct via Ollama\ndecoder-only Transformer, 36 blocks\ngrouped-query self-attention + SwiGLU FFN\nJSON-constrained risk assessment", 13.5))
    d.add(rect(700, 440, 240, 150, rx=6, fill="#ffffff", dash="8,5"),
          text(820, 460, "LSTM autoencoder", 15, weight="bold"),
          text(820, 482, "«planned, future work»", 13, italic=True),
          text(820, 535, "sequence reconstruction\nerror as anomaly score;\nTransformer LLM would\nexplain flagged windows", 13))
    d.add(line(455, 422, 455, 440, end="arrow"), line(820, 422, 820, 440, end="arrow", dash="6,4"),
          line(700, 515, 680, 515, end="arrow", dash="6,4"))
    for y in (120, 225, 330, 605):
        d.add(line(470, y, 470, y + 25, end="arrow", start="arrow"))
    d.add(text(500, 735, "All layers run on one CPU-only laptop; no data leaves the machine.  "
                         "Dashed = planned, not implemented.", 14, italic=True))
    d.save("architecture_layers")


def _box(cx, y, w, h, s, size=15, fill=FILL, dash=None, weight="normal", sw=1.6):
    return [rect(cx - w / 2, y, w, h, rx=6, fill=fill, dash=dash, sw=sw), text(cx, y + h / 2, s, size, weight=weight)]


def _down(cx, y1, y2, dash=None):
    return line(cx, y1, cx, y2, end="arrow", dash=dash)


def transformer_diagram():
    """Qwen2.5-3B decoder-only Transformer as used by hackViz (values from `ollama show --verbose`)."""
    d = Diagram(1040, 1230)
    cx, W = 420, 400
    d.add(_box(cx, 30, W, 74, "Prompt built by the analysis worker\nrisk rubric · role · baseline · rule indicators\n· up to 50 chronological event lines", 14, fill=FILL2))
    d.add(_down(cx, 104, 140))
    d.add(_box(cx, 140, W, 52, "Byte-level BPE tokenizer\n(context window used: 4,096 tokens)", 14))
    d.add(_down(cx, 192, 228))
    d.add(_box(cx, 228, W, 46, "Token embedding  (d_model = 2048)", 15))
    # stacked decoder block
    d.add(rect(186, 312, 500, 520, rx=10, fill="#ffffff", sw=1.2), rect(178, 320, 500, 520, rx=10, fill="#ffffff", sw=1.2),
          rect(170, 328, 500, 520, rx=10, fill=FILL2, sw=2))
    d.add(_down(cx, 274, 328))
    d.add(text(184, 346, "Decoder block  × 36", 15, anchor="start", weight="bold"))
    bx = cx
    d.add(_down(bx, 328, 372))
    d.add(_box(bx, 372, 300, 42, "RMSNorm", 14))
    d.add(_down(bx, 414, 440))
    d.add(_box(bx, 440, 340, 84, "Causal grouped-query self-attention\n16 query heads · 2 key/value heads\nrotary position encoding (RoPE)", 13.5))
    d.add(_down(bx, 524, 562))
    d.add(circle(bx, 576, 14), text(bx, 576, "+", 20, weight="bold"))
    d.add(_down(bx, 590, 622))
    d.add(_box(bx, 622, 300, 42, "RMSNorm", 14))
    d.add(_down(bx, 664, 690))
    d.add(_box(bx, 690, 340, 66, "SwiGLU feed-forward network\n2048 → 11008 → 2048", 13.5))
    d.add(_down(bx, 756, 792))
    d.add(circle(bx, 806, 14), text(bx, 806, "+", 20, weight="bold"))
    # residual connections
    rx_ = 628
    d.add(poly([(bx, 356), (rx_, 356), (rx_, 576), (bx + 14, 576)], end="arrow"),
          poly([(bx, 604), (rx_, 604), (rx_, 806), (bx + 14, 806)], end="arrow"),
          label(rx_, 543, "residual", 12.5), label(rx_, 774, "residual", 12.5))
    d.add(_down(bx, 820, 872))
    d.add(_box(cx, 872, W, 44, "Final RMSNorm", 14))
    d.add(_down(cx, 916, 946))
    d.add(_box(cx, 946, W, 52, "LM head: linear projection + softmax\nover the vocabulary", 14))
    d.add(_down(cx, 998, 1028))
    d.add(_box(cx, 1028, W, 60, "JSON-schema-constrained decoding\ntemperature 0.1 · seed 7 · at most 600 tokens", 14))
    d.add(_down(cx, 1088, 1124))
    d.add(_box(cx, 1124, W, 70, "Assessment JSON: is_anomaly, risk_level,\nconfidence, reason, evidence_event_ids\n→ validator and evidence check", 13.5, fill=FILL2))
    # autoregressive loop
    lx = 745
    d.add(flow([(cx + W / 2, 1058), (lx, 1058), (lx, 251), (cx + W / 2, 251)], color=LOOP),
          label(lx, 640, "next token\nappended\n(autoregressive\nloop)", 13))
    # side notes
    d.add(note(780, 30, 240, 128, "Model facts\nQwen2.5-3B-Instruct\n3.1 B parameters\n4-bit (Q4_K_M) weights\nserved by Ollama on CPU\nused as-is, no fine-tuning", 13.5))
    d.add(legend(780, 900, 240, [
        (lambda x, y: line(x, y, x + 56, y, end="arrow"), "data flow"),
        (lambda x, y: line(x, y, x + 56, y, end="arrow", dash="8,5"), "autoregressive loop"),
        (lambda x, y: [circle(x + 28, y, 11), text(x + 28, y, "+", 16, weight="bold")], "residual addition"),
        (lambda x, y: [rect(x + 10, y - 13, 40, 22, sw=1), rect(x + 4, y - 9, 40, 22, fill=FILL2, sw=1.4)], "repeated block"),
    ]))
    d.save("transformer_architecture")


def lstm_autoencoder_diagram():
    """Planned (NOT implemented) LSTM sequence autoencoder from the original proposal."""
    d = Diagram(1080, 790)
    d.add(rect(14, 14, 1052, 762, rx=10, fill="#ffffff", dash="10,6", sw=1.8))
    d.add(text(34, 44, "«planned, not implemented»  LSTM sequence autoencoder (future work)", 17,
               anchor="start", weight="bold"))
    d.add(_box(145, 80, 210, 70, "Activity window\nn ≤ 50 events of one\nemployee, in order", 14, fill=FILL2))
    d.add(line(250, 115, 300, 115, end="arrow"))
    d.add(_box(430, 80, 260, 70, "Event encoding\ntype · hour · domain category\n· file size · role → vector", 13.5))
    cells = [250, 400, 610]
    names = ["1", "2", "n"]
    # input bus
    d.add(line(430, 150, 430, 190), line(cells[0], 190, cells[-1], 190))
    for c, nm in zip(cells, names):
        d.add(line(c, 190, c, 240, end="arrow"), label(c + 22, 214, f"x{nm}", 13, italic=True))
    d.add(text(40, 270, "Encoder\n(2 LSTM\nlayers)", 14, anchor="start", weight="bold"))
    for i, c in enumerate(cells):
        d.add(_box(c, 240, 100, 60, "LSTM\ncell", 14))
    d.add(text(505, 270, "…", 24, weight="bold"))
    for a, b in ((cells[0], cells[1]), (cells[1], 470), (540, cells[2])):
        d.add(line(a + 50 if a in cells else a, 262, b - 50 if b in cells else b, 262, end="arrow"))
    d.add(label(325, 250, "h, c", 12.5, italic=True))
    # latent vector
    d.add(line(660, 270, 760, 270, end="arrow"))
    d.add(_box(840, 240, 160, 60, "latent vector z\n(sequence summary)", 13.5, fill=FILL2, weight="bold"))
    # decoder input bus
    d.add(poly([(840, 300), (840, 380), (cells[0], 380)]))
    for c in cells:
        d.add(line(c, 380, c, 420, end="arrow"))
    d.add(label(720, 380, "z repeated n times", 12.5, italic=True))
    d.add(text(40, 450, "Decoder\n(2 LSTM\nlayers)", 14, anchor="start", weight="bold"))
    for c in cells:
        d.add(_box(c, 420, 100, 60, "LSTM\ncell", 14))
    d.add(text(505, 450, "…", 24, weight="bold"))
    for a, b in ((cells[0], cells[1]), (cells[1], 470), (540, cells[2])):
        d.add(line(a + 50 if a in cells else a, 442, b - 50 if b in cells else b, 442, end="arrow"))
    d.add(label(325, 430, "h, c", 12.5, italic=True))
    # reconstruction bus
    for c, nm in zip(cells, names):
        d.add(line(c, 480, c, 540), label(c + 24, 512, f"x̂{nm}", 13, italic=True))
    d.add(line(cells[0], 540, 700, 540, end="arrow"))
    d.add(_box(855, 505, 310, 70, "Reconstruction error\ne = (1/n) Σ ‖xₜ − x̂ₜ‖²", 14))
    d.add(_down(855, 575, 620))
    d.add(_box(855, 620, 310, 70, "Score above the employee's\nown 95th-percentile baseline?", 14))
    d.add(line(700, 655, 610, 655, end="arrow"), label(655, 640, "yes", 13, weight="bold"))
    d.add(_box(400, 620, 420, 70, "Window + score sent to the Transformer LLM\n(current pipeline) for an evidence-based\nexplanation", 13.5, fill=FILL2))
    d.add(_down(855, 690, 726), text(855, 742, "no: window treated as normal", 13, italic=True))
    # LSTM cell detail note
    d.add(note(720, 72, 330, 120, "LSTM cell (one time step t)\nforget fₜ, input iₜ, output oₜ gates\ncₜ = fₜ ⊙ cₜ₋₁ + iₜ ⊙ gₜ\nhₜ = oₜ ⊙ tanh(cₜ)\ntrained on normal behaviour only", 13.5))
    d.save("lstm_autoencoder")


def timeline_diagram():
    weeks = 11
    rows = [("Project setup, dataset selection", 1, 1), ("Novelty and DeepLog literature review", 2, 2),
            ("CERT exploratory data analysis", 3, 3), ("Preprocessing / event unification design", 4, 4),
            ("Temporal engine design", 5, 5), ("E-mail and file analysis approach", 6, 6),
            ("Architecture choice (local LLM)", 7, 7), ("Mock demo data and users", 8, 8),
            ("Implementation: backend, LLM, extension", 9, 9), ("Evaluation and testing", 10, 10),
            ("Integration, fixes, documentation", 11, 11)]
    x0, cw, rh = 380, 52, 38
    d = Diagram(x0 + cw * weeks + 30, 70 + rh * len(rows) + 20)
    for w in range(weeks):
        d.add(rect(x0 + w * cw, 30, cw, 30, fill=FILL2, sw=1), text(x0 + w * cw + cw / 2, 45, f"W{w + 1}", 14, weight="bold"))
    for i, (name, s, e) in enumerate(rows):
        y = 70 + i * rh
        d.add(rect(20, y, x0 - 20 + cw * weeks, rh, fill="#ffffff" if i % 2 else "#ffffff", sw=0.6),
              text(30, y + rh / 2, name, 14, anchor="start"),
              rect(x0 + (s - 1) * cw + 4, y + 8, (e - s + 1) * cw - 8, rh - 16, rx=5, fill="#555555", sw=0))
    d.save("timeline")


# ------------------------------------------------------------------ simple UML diagrams (template set)
ROW = 21


def uml_class(x, y, w, name, attrs=(), methods=(), stereo=None, size=14):
    """Three-compartment UML class box. Returns (svg parts, bottom y)."""
    top = 34 + (18 if stereo else 0)
    ha = max(len(attrs), 1) * ROW + 10
    hm = max(len(methods), 1) * ROW + 10
    h = top + ha + hm
    out = [rect(x, y, w, h, fill="#ffffff"), rect(x, y, w, top, fill=FILL2)]
    if stereo:
        out.append(text(x + w / 2, y + 16, f"«{stereo}»", 12.5, italic=True))
    out.append(text(x + w / 2, y + top - 15, name, 15, weight="bold"))
    out.append(line(x, y + top + ha, x + w, y + top + ha))
    for i, a in enumerate(attrs):
        out.append(text(x + 10, y + top + 6 + i * ROW, a, size, anchor="start", valign="top"))
    for i, m in enumerate(methods):
        out.append(text(x + 10, y + top + ha + 6 + i * ROW, m, size, anchor="start", valign="top"))
    return out, y + h


def mult(x, y, s, anchor="middle"):
    return text(x, y, s, 13, anchor=anchor, weight="bold")


def _legend_uml(x, y, w, kinds):
    items = {
        "comp": (lambda a, b: line(a + 2, b, a + 58, b, start="diamond"), "composition (whole-part)"),
        "assoc": (lambda a, b: line(a, b, a + 56, b, end="open"), "association (navigable)"),
        "dep": (lambda a, b: line(a, b, a + 56, b, end="open", dash="7,5"), "dependency «uses»"),
        "gen": (lambda a, b: line(a, b, a + 56, b, end="tri"), "generalisation (is-a)"),
    }
    return legend(x, y, w, [items[k] for k in kinds])


def class_domain_diagram():
    d = Diagram(1120, 800)
    emp, eb = uml_class(40, 250, 300, "Employee", [
        "+ id: int", "+ employee_id: str {unique}", "+ name: str", "+ role: str", "+ department: str",
        "+ email: str [0..1]", "+ is_synthetic: bool"], ["+ (ORM entity, no methods)"], "entity")
    act, ab = uml_class(420, 30, 300, "ActivityLog", [
        "+ id: bigint", "+ event_type: str", "+ domain: str", "+ url: str", "+ filename: str",
        "+ timestamp: datetime", "+ source: str", "+ client_event_id: str"], ["+ (ORM entity)"], "entity")
    ano, nb = uml_class(420, 380, 300, "Anomaly", [
        "+ id: int", "+ is_anomaly: bool", "+ risk_level: str", "+ confidence: float", "+ reason: text",
        "+ evidence_event_ids: int[*]", "+ duration_ms: int"], ["+ (ORM entity)"], "entity")
    ses, sb = uml_class(800, 30, 290, "ExtensionSession", [
        "+ session_token: str", "+ paired_at: datetime", "+ last_heartbeat_at: datetime",
        "+ events_received: int", "+ disconnected_at: datetime"], ["+ (ORM entity)"], "entity")
    st, tb = uml_class(800, 380, 290, "AnalysisState", [
        "+ last_analyzed_event_id: bigint", "+ consecutive_failures: int", "+ next_retry_at: datetime",
        "+ last_error: text"], ["+ (ORM entity)"], "entity")
    d.add(emp, act, ano, ses, st)
    # compositions from Employee (cascade delete)
    d.add(poly([(340, 290), (380, 290), (380, 150), (420, 150)], start="diamond"),
          mult(358, 280, "1"), mult(400, 140, "0..*"), label(380, 220, "performs", 13, italic=True))
    d.add(poly([(340, 470), (420, 470)], start="diamond"), mult(358, 460, "1"), mult(400, 460, "0..*"),
          text(380, 505, "is assessed\nin", 13, italic=True))
    d.add(poly([(190, 250), (190, 14), (945, 14), (945, 30)], start="diamond"), mult(202, 238, "1", "start"),
          mult(960, 21, "0..*", "start"), label(600, 14, "pairs through", 13, italic=True))
    d.add(poly([(190, eb), (190, 775), (945, 775), (945, tb)], start="diamond"), mult(202, eb + 14, "1", "start"),
          mult(960, tb + 14, "0..1", "start"), label(600, 775, "has analysis cursor", 13, italic=True))
    # Anomaly cites ActivityLog
    d.add(line(570, 380, 570, ab, end="open"), mult(582, 368, "0..*", "start"), mult(582, ab + 14, "1..*", "start"),
          label(570, (380 + ab) / 2, "cites as evidence", 13, italic=True))
    d.add(_legend_uml(420, 650, 290, ["comp", "assoc"]))
    d.save("class_domain")


def class_analysis_diagram():
    d = Diagram(1120, 860)
    wk, wb = uml_class(40, 30, 300, "AnalysisWorker", [
        "- _q: Queue[Job]", "- _active: dict[str, Job]", "- _thread: Thread"], [
        "+ start(): void", "+ stop(): void", "+ request(employee_id, mode): Job",
        "+ status(): dict", "- _scan(): void", "- _run(job: Job): void"], "control")
    an, nb = uml_class(420, 30, 300, "analyzer", [], [
        "+ select_batch(db, emp, mode)", "+ build_baseline(db, emp): dict", "+ build_prompt(...): str",
        "+ validate_response(raw, ids)", "+ analyze_employee(db, emp): dict"], "service module")
    ol, ob = uml_class(800, 30, 290, "ollama_client", ["- ollama_url: str (localhost)"], [
        "+ check(): dict", "+ chat(messages, schema): (str, dict)", "+ parse_json_object(text): dict"],
        "service module")
    jb, jbb = uml_class(40, 340, 300, "Job", [
        "+ employee_id: str", "+ mode: str  (manual | auto)", "+ state: str", "+ result: dict [0..1]",
        "+ error: str [0..1]"], ["+ public(): dict"], "data class")
    la, lab = uml_class(420, 340, 300, "LLMAssessment", [
        "+ is_anomaly: bool", "+ risk_level: low | medium | high", "+ confidence: float [0, 1]",
        "+ reason: str", "+ evidence_event_ids: int[*]", "+ recommended_action: str"],
        ["- _consistent(): self"], "Pydantic schema")
    oe, oeb = uml_class(780, 340, 260, "OllamaError", [], [], "exception")
    d.add(wk, an, ol, jb, la, oe)
    subs = ["OllamaUnavailable", "ModelMissing", "OllamaTimeout", "OllamaBadResponse"]
    cxs = [620, 760, 900, 1040]
    for cx, s in zip(cxs, subs):
        d.add(rect(cx - 66, 620, 132, 48, fill="#ffffff"), text(cx, 644, s, 12.5, weight="bold"),
              line(cx, 620, cx, 595))
    d.add(line(cxs[0], 595, cxs[-1], 595), line(910, 595, 910, oeb, end="tri"))
    ae, aeb = uml_class(40, 620, 250, "AnalysisError", [], [], "exception")
    d.add(ae, rect(340, 640, 200, 48, fill="#ffffff"), text(440, 664, "NothingToAnalyze", 12.5, weight="bold"),
          line(340, 664, 290, 664, end="tri"))
    # relationships
    d.add(line(190, wb, 190, 340, start="diamond"), mult(202, wb + 16, "1", "start"), mult(202, 330, "0..*", "start"))
    d.add(line(340, 110, 420, 110, end="open"), label(380, 96, "runs", 13, italic=True))
    d.add(line(720, 110, 800, 110, end="open"), label(760, 96, "calls", 13, italic=True))
    d.add(line(570, nb, 570, 340, end="open", dash="7,5"), label(570, (nb + 340) / 2, "«validates with»", 13))
    d.add(line(945, ob, 945, 340, end="open", dash="7,5"), label(945, (ob + 340) / 2, "«raises»", 13))
    d.add(poly([(450, nb), (450, 290), (380, 290), (380, 595), (165, 595), (165, 620)], end="open", dash="7,5"),
          label(380, 560, "«raises»", 13))
    d.add(_legend_uml(600, 700, 300, ["comp", "assoc", "dep", "gen"]))
    d.save("class_analysis")


def _lifeline(d, x, name, top=30, bottom=810, actor_=False):
    if actor_:
        d.add(actor(x, top - 8, name, 14)[0])
        d.add(line(x, top + 122, x, bottom, dash="6,5", sw=1.2))
    else:
        w = max(150, tw(name, 14) + 24)
        d.add(rect(x - w / 2, top, w, 46, fill=FILL2), text(x, top + 23, name, 14, weight="bold"),
              line(x, top + 46, x, bottom, dash="6,5", sw=1.2))


def _msg(d, x1, x2, y, s, ret=False, n=None):
    lab = f"{n}: {s}" if n else s
    if x1 == x2:
        d.add(poly([(x1, y - 8), (x1 + 50, y - 8), (x1 + 50, y + 12), (x1 + 4, y + 12)], end="arrow"),
              text(x1 + 58, y + 2, lab, 13, anchor="start"))
        return
    d.add(line(x1, y, x2 - (6 if x2 > x1 else -6), y, end="open" if ret else "arrow", dash="7,5" if ret else None))
    d.add(label((x1 + x2) / 2, y - 11, lab, 13))


def sequence_pairing_diagram():
    """Second sequence case: on-demand analysis (Analyze Now)."""
    d = Diagram(1120, 900)
    X = {"an": 80, "ds": 260, "api": 450, "wk": 650, "ol": 840, "db": 1020}
    _lifeline(d, X["an"], "Security\nAnalyst", actor_=True, bottom=870)
    _lifeline(d, X["ds"], "Dashboard", bottom=870)
    _lifeline(d, X["api"], "FastAPI", bottom=870)
    _lifeline(d, X["wk"], "Analysis worker", bottom=870)
    _lifeline(d, X["ol"], "Ollama LLM", bottom=870)
    _lifeline(d, X["db"], "PostgreSQL", bottom=870)
    msgs = [("an", "ds", "click Analyze Now", False), ("ds", "api", "POST /api/analyze/{id}", False),
            ("api", "wk", "request(id, \"manual\")", False), ("api", "ds", "202 job queued", True),
            ("wk", "db", "read window + history", False), ("db", "wk", "events, baseline data", True),
            ("wk", "wk", "indicators, build prompt", False), ("wk", "ol", "POST /api/chat (schema)", False),
            ("ol", "wk", "JSON assessment", True), ("wk", "wk", "validate, verify evidence", False),
            ("wk", "db", "INSERT anomaly + cursor", False), ("ds", "api", "GET /api/analysis/status", False),
            ("api", "ds", "job done, anomaly id", True), ("ds", "an", "show alert + evidence", True)]
    y = 200
    for i, (a, b, s, r) in enumerate(msgs, 1):
        _msg(d, X[a], X[b], y, s, r, i)
        y += 46 if a != b else 56
    d.save("sequence_analyze")


def _obj(x, y, name, w=None):
    w = w or max(170, tw(name, 14) + 26)
    t = text(x, y, name, 14, weight="bold")
    uw = tw(name, 14) * 0.98
    return [rect(x - w / 2, y - 24, w, 48, fill=FILL2), t, line(x - uw / 2, y + 9, x + uw / 2, y + 9, sw=1.1)]


def _cmsg(p1, p2, msgs, side=1, off=16):
    """Numbered messages along a link from p1 to p2 (arrow shows direction)."""
    (x1, y1), (x2, y2) = p1, p2
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    L = math.hypot(x2 - x1, y2 - y1)
    ux, uy = (x2 - x1) / L, (y2 - y1) / L
    nx, ny = -uy * side, ux * side
    ax, ay = mx + nx * off, my + ny * off
    out = [line(ax - ux * 28, ay - uy * 28, ax + ux * 28, ay + uy * 28, end="arrow", sw=1.4)]
    body = "\n".join(msgs)
    h = len(msgs) * 16
    if abs(nx) > 0.5:          # link is mostly vertical: put the text beside it
        anchor = "start" if nx > 0 else "end"
        out.append(text(ax + nx * 12, ay, body, 13, anchor=anchor))
    else:                      # mostly horizontal: above or below
        out.append(text(ax, ay + ny * (10 + h / 2), body, 13))
    return out


def collab_analyze_diagram():
    d = Diagram(1120, 640)
    P = {"an": (150, 90), "ds": (520, 90), "api": (900, 90), "wk": (900, 320), "az": (900, 550),
         "ol": (480, 550), "db": (480, 320)}
    names = {"an": "analyst : SecurityAnalyst", "ds": ": Dashboard", "api": ": FastAPI", "wk": ": AnalysisWorker",
             "az": ": analyzer", "ol": ": ollama_client", "db": ": PostgreSQL"}
    links = [("an", "ds"), ("ds", "api"), ("api", "wk"), ("wk", "az"), ("az", "ol"), ("az", "db"), ("api", "db")]
    for a, b in links:
        d.add(line(*P[a], *P[b], sw=1.4))
    for k, p in P.items():
        d.add(_obj(*p, names[k]))
    d.add(_cmsg(P["an"], P["ds"], ["1: clickAnalyzeNow()"], side=-1))
    d.add(_cmsg(P["ds"], P["api"], ["2: POST /api/analyze/{id}", "9: GET /employees/{id}/anomalies"], side=-1))
    d.add(_cmsg(P["api"], P["wk"], ["3: request(id, \"manual\")"], side=-1, off=20))
    d.add(_cmsg(P["wk"], P["az"], ["4: analyze_employee(id)"], side=-1, off=20))
    d.add(_cmsg(P["az"], P["db"], ["5: select_batch(), build_baseline()", "8: INSERT anomaly, move cursor"], side=-1, off=18))
    d.add(_cmsg(P["az"], P["ol"], ["6: chat(prompt, schema)"], side=-1))
    d.add(poly([(970, 526), (970, 490), (1040, 490), (1040, 540), (987, 540)], end="arrow"),
          text(1100, 598, "7: validate_response()", 13, anchor="end"))
    d.add(_cmsg(P["api"], P["db"], ["10: SELECT anomalies"], side=1, off=18))
    d.add(_cmsg(P["ds"], P["an"], ["11: show alert"], side=-1))
    d.save("collab_analyze")


def collab_ingest_diagram():
    d = Diagram(1120, 600)
    P = {"em": (150, 90), "sw": (520, 90), "api": (900, 90), "sc": (900, 320), "db": (520, 320), "wk": (520, 530)}
    names = {"em": "employee : MonitoredEmployee", "sw": ": ServiceWorker", "api": "activity : FastAPI route",
             "sc": ": ActivityIn (schema)", "db": ": PostgreSQL", "wk": ": AnalysisWorker"}
    for a, b in [("em", "sw"), ("sw", "api"), ("api", "sc"), ("api", "db"), ("db", "wk")]:
        d.add(line(*P[a], *P[b], sw=1.4))
    for k, p in P.items():
        d.add(_obj(*p, names[k]))
    d.add(_cmsg(P["em"], P["sw"], ["1: visit page / download"], side=-1))
    d.add(poly([(560, 114), (560, 170), (480, 170), (480, 114)], end="arrow"),
          text(520, 190, "2: stripQuery(), enqueue()", 13))
    d.add(_cmsg(P["sw"], P["api"], ["3: POST /api/activity/batch", "6: per-event results  (reply)"], side=-1))
    d.add(_cmsg(P["api"], P["sc"], ["4: validate(event)"], side=1, off=20))
    d.add(_cmsg(P["api"], P["db"], ["5: INSERT activity_logs"], side=1, off=18))
    d.add(_cmsg(P["wk"], P["db"], ["7: _scan(): count new live events"], side=1, off=20))
    d.add(poly([(605, 520), (665, 520), (665, 544), (607, 544)], end="arrow"),
          text(675, 532, "8: request(id, \"auto\")  [≥ 5 events or 90 s idle]", 13, anchor="start"))
    d.save("collab_ingest")


def component_diagram():
    d = Diagram(1120, 600)

    def comp(x, y, w, h, name, sub=None, fill="#ffffff"):
        out = [rect(x, y, w, h, rx=3, fill=fill), text(x + w / 2 - 8, y + 20, "«component»", 12, italic=True),
               text(x + w / 2 - 8, y + 42, name, 14.5, weight="bold"),
               rect(x + w - 26, y + 8, 16, 18, fill="#ffffff", sw=1.2), rect(x + w - 30, y + 11, 8, 4, fill="#ffffff", sw=1.2),
               rect(x + w - 30, y + 19, 8, 4, fill="#ffffff", sw=1.2)]
        if sub:
            out.append(text(x + w / 2, y + h - 24, sub, 12.5, italic=True))
        return out

    def assembly(x1, x2, y, lab):
        """Required interface on the x1 side meets the provided interface of the x2 side."""
        bx = (x1 + x2) / 2
        return [line(x1, y, bx - 16, y), path(f"M{bx - 4},{y - 13} A13,13 0 0,0 {bx - 4},{y + 13}"),
                circle(bx + 6, y, 8), line(bx + 14, y, x2, y), label(bx, y - 26, lab, 12.5)]

    d.add(comp(40, 60, 260, 110, "Chrome Extension", "popup + service worker"))
    d.add(comp(40, 250, 260, 110, "React Dashboard", "Vite, Recharts"))
    d.add(rect(420, 30, 330, 520, rx=4, fill="#ffffff", sw=2),
          text(585, 52, "«component»  FastAPI Backend", 15, weight="bold"))
    d.add(comp(450, 80, 270, 100, "Routes", "employees, activity, extension,\nanomalies, export, system"))
    d.add(comp(450, 240, 270, 100, "Analysis Worker", "queue, scheduler, retries"))
    d.add(comp(450, 400, 270, 110, "Analyzer", "baseline, indicators, prompt,\nvalidation"))
    d.add(line(585, 180, 585, 240, end="open", dash="7,5"), line(585, 340, 585, 400, end="open", dash="7,5"))
    d.add(comp(870, 400, 210, 110, "Ollama Server", "qwen2.5:3b"))
    d.add(comp(870, 80, 210, 110, "PostgreSQL 16", "used by routes, worker\nand analyzer"))
    d.add(assembly(300, 450, 115, "REST /api (JSON)"))
    d.add(line(300, 305, 370, 305), line(370, 305, 370, 165), assembly(370, 450, 165, "REST /api"))
    d.add(assembly(720, 870, 135, "SQL (psycopg)"), assembly(720, 870, 455, "HTTP /api/chat"))
    d.add(legend(40, 470, 330, [
        (lambda a, b: [line(a, b, a + 20, b), circle(a + 28, b, 8)], "provided interface"),
        (lambda a, b: [line(a, b, a + 26, b), path(f"M{a + 38},{b - 12} A12,12 0 0,0 {a + 38},{b + 12}")], "required interface"),
    ]))
    d.save("component_diagram")


if __name__ == "__main__":
    for fn in (use_case_diagram, activity_diagram, swimlane_diagram, dfd_level0, dfd_level1, dfd_level2,
               er_diagram, sequence_diagram, state_analysis, state_extension, deployment_diagram,
               package_diagram, architecture_diagram, timeline_diagram, transformer_diagram,
               lstm_autoencoder_diagram, class_domain_diagram, class_analysis_diagram,
               sequence_pairing_diagram, collab_analyze_diagram, collab_ingest_diagram, component_diagram):
        fn()
    print("diagrams written to", OUT)

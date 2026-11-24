"""Simple report diagrams drawn in the notation of the UCS503 lecture slides (CSED, TIET).

DFD      : process = circle (number + name), source/sink = rectangle, data store = two parallel
           lines "Dn: name", one-way labelled arrows; context, level-1 and level-2 are balanced.
Use case : stick-man actors, ellipses, system boundary, <<includes>> / <<extends>>.
Activity : rounded actions, initial/final nodes, decision + merge diamonds with [guards], fork/join.
Class    : three compartments, "- name : type", association / composition / generalisation /
           dependency with multiplicities.

Usage:  python simple_diagrams.py svg      (then render_diagrams.mjs + to_jpeg.mjs as usual)
"""
from make_diagrams import (Diagram, rect, text, line, poly, label, circle, actor, diamond, initial, final,
                           usecase, connect, S, FILL, FILL2, OUT, INK, _lifeline, _msg, _obj, _cmsg)

FS = 15


# ------------------------------------------------------------------ helpers
def box(cx, cy, w, h, s, rx=8, fill=FILL, bold=False, size=FS, dash=None):
    return ([rect(cx - w / 2, cy - h / 2, w, h, rx=rx, fill=fill, dash=dash),
             text(cx, cy, s, size, weight="bold" if bold else "normal")], S("rect", cx, cy, w / 2, h / 2))


def proc(cx, cy, r, num, name):
    """DFD process: circle with number above a line and the name below."""
    return ([circle(cx, cy, r, fill=FILL2), text(cx, cy - r * 0.5, num, FS, weight="bold"),
             line(cx - r * 0.72, cy - r * 0.28, cx + r * 0.72, cy - r * 0.28), text(cx, cy + r * 0.22, name, 14)],
            S("circle", cx, cy, r))


def entity(cx, cy, name, w=190, h=56):
    """DFD source/sink: rectangle."""
    return box(cx, cy, w, h, name, rx=0, bold=True)


def dstore(cx, cy, label_, w=210, h=40):
    """DFD data store: two horizontal parallel lines with 'Dn: name' between them."""
    x0, y0 = cx - w / 2, cy - h / 2
    return ([line(x0, y0, x0 + w, y0, sw=2), line(x0, y0 + h, x0 + w, y0 + h, sw=2), text(cx, cy, label_, 14)],
            S("rect", cx, cy, w / 2, h / 2))


def arrow(a, b, lab=None, lpos=None, dash=None, size=13, off=0):
    ln, mid = connect(a, b, off=off, end="arrow", dash=dash)
    out = [ln]
    if lab:
        p = lpos or mid
        out.append(label(p[0], p[1], lab, size))
    return out


def path_arrow(pts, lab=None, lpos=None, size=13, dash=None, end="arrow"):
    out = [poly(pts, end=end, dash=dash)]
    if lab:
        out.append(label(lpos[0], lpos[1], lab, size))
    return out


def guard(x, y, s, anchor="middle"):
    return text(x, y, f"[{s}]", 13, anchor=anchor)


def act(cx, cy, s, w=300, h=50):
    return box(cx, cy, w, h, s, rx=24)


def merge(cx, cy):
    return diamond(cx, cy, 30, 30)


def bar(cx, cy, w):
    return [rect(cx - w / 2, cy - 4, w, 8, fill=INK, sw=0)], S("rect", cx, cy, w / 2, 4)


def sclass(x, y, w, name, attrs=(), methods=()):
    """UML class with the three compartments shown in the lecture (name / attributes / operations)."""
    top, row = 36, 22
    ha = max(len(attrs), 1) * row + 8
    hm = max(len(methods), 1) * row + 8
    h = top + ha + hm
    out = [rect(x, y, w, h, fill="#ffffff"), rect(x, y, w, top, fill=FILL2),
           text(x + w / 2, y + top / 2, name, 15, weight="bold"),
           line(x, y + top + ha, x + w, y + top + ha)]
    for i, a in enumerate(attrs):
        out.append(text(x + 10, y + top + 5 + i * row, a, 14, anchor="start", valign="top"))
    for i, m in enumerate(methods):
        out.append(text(x + 10, y + top + ha + 5 + i * row, m, 14, anchor="start", valign="top"))
    return out, S("rect", x + w / 2, y + h / 2, w / 2, h / 2), y + h


def state(cx, cy, s, w=200, h=56):
    return box(cx, cy, w, h, s, rx=22, fill=FILL2)


def mult(x, y, s):
    return text(x, y, s, 14, weight="bold")


# ================================================================== ARCHITECTURE (lecture: layered / 3-tier, pipe and filter)
def architecture_diagram():
    d = Diagram(1000, 540)
    tiers = [("Presentation tier", 30, [("React Dashboard", None), ("Chrome Extension popup", None)]),
             ("Logic tier", 205, [("FastAPI Backend", None), ("Analysis Worker", None),
                                  ("Transformer LLM\n(Qwen2.5 via Ollama)", None), ("LSTM autoencoder\n(planned)", "8,5")]),
             ("Data tier", 380, [("PostgreSQL Database", None)])]
    for name, y, comps in tiers:
        d.add(rect(30, y, 940, 130, rx=6, fill="#f4f4f4"), text(50, y + 20, name, 16, anchor="start", weight="bold"))
        n = len(comps)
        w = (880 - (n - 1) * 20) / n
        for i, (c, dash) in enumerate(comps):
            x = 60 + i * (w + 20)
            d.add(rect(x, y + 45, w, 66, rx=4, fill="#ffffff", dash=dash), text(x + w / 2, y + 78, c, 14))
    d.add(line(500, 160, 500, 205, end="arrow", start="arrow"), line(500, 335, 500, 380, end="arrow", start="arrow"))
    d.add(text(500, 528, "Client/server, layered (3-tier) style. Dashed = planned, not implemented.", 13, italic=True))
    d.save("architecture_layers")


def pipeline_diagram():
    steps = ["Validate\nevent", "Store\nevent", "Build\ncontext", "Assess\nwith LLM", "Verify\nevidence", "Show\nalert"]
    d = Diagram(1180, 150)
    xs = [130 + i * 185 for i in range(len(steps))]
    B = []
    for x, s in zip(xs, steps):
        parts, sh = box(x, 75, 140, 64, s, rx=0, fill="#f4f4f4")
        d.add(parts)
        B.append(sh)
    d.add(line(10, 75, 60, 75, end="arrow"), text(20, 50, "event", 13, anchor="start"))
    for i in range(len(B) - 1):
        d.add(arrow(B[i], B[i + 1]))
    d.add(line(200 + 185 * 5, 75, 1170, 75, end="arrow"))
    d.save("architecture_pipeline")


def dashed_usecase(cx, cy, s, rx=150, ry=32):
    return ([f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="#ffffff" stroke="#000000" stroke-width="1.6" stroke-dasharray="8,5"/>',
             text(cx, cy, s, 15)], S("ellipse", cx, cy, rx, ry))


def dashed_proc(cx, cy, r, num, name):
    return ([f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="#ffffff" stroke="#000000" stroke-width="1.6" stroke-dasharray="8,5"/>',
             text(cx, cy - r * 0.5, num, FS, weight="bold"),
             line(cx - r * 0.72, cy - r * 0.28, cx + r * 0.72, cy - r * 0.28, dash="6,4"), text(cx, cy + r * 0.22, name, 13)],
            S("circle", cx, cy, r))


# ================================================================== USE CASE
def use_case_diagram():
    d = Diagram(1080, 940)
    d.add(rect(300, 30, 420, 880, rx=0, fill="#ffffff"), text(510, 55, "hackViz System", 17, weight="bold"))
    ys = {"Add Employee": 105, "Pair Extension": 190, "Send Browser Activity": 275, "View Dashboard": 370,
          "Export CSV": 465, "View Alerts & Evidence": 555, "Analyze Now": 645, "Assess Activity": 745}
    uc = {}
    for n, y in ys.items():
        parts, sh = usecase(510, y, n, rx=150, ry=32)
        d.add(parts)
        uc[n] = sh
    parts, uc["lstm"] = dashed_usecase(510, 850, "Score with Transformer decoder", rx=165)
    d.add(parts)
    A = {}
    for key, cx, top, name in [("emp", 120, 170, "Employee"), ("an", 120, 470, "Security\nAnalyst"),
                               ("ad", 955, 60, "Administrator"), ("tr", 955, 640, "LLM\n(Qwen2.5)"),
                               ("ls", 955, 790, "Transformer\ndecoder")]:
        parts, A[key] = actor(cx, top, name)
        d.add(parts)
    for a, u, dash in [("emp", "Pair Extension", None), ("emp", "Send Browser Activity", None),
                       ("an", "View Dashboard", None), ("an", "Export CSV", None), ("an", "View Alerts & Evidence", None),
                       ("an", "Analyze Now", None), ("ad", "Add Employee", None), ("tr", "Assess Activity", None),
                       ("ls", "lstm", "7,5")]:
        ln, _ = connect(A[a], uc[u], dash=dash)
        d.add(ln)
    d.add(line(510, 677, 510, 711, dash="7,5", end="open"), text(522, 694, "<<includes>>", 13, anchor="start"))
    d.add(line(510, 433, 510, 404, dash="7,5", end="open"), text(522, 418, "<<extends>>", 13, anchor="start"))
    d.add(line(510, 818, 510, 779, dash="7,5", end="open"), text(522, 799, "<<extends>>", 13, anchor="start"))
    d.save("uc_diagram")


# ================================================================== ACTIVITY
def activity_diagram():
    d = Diagram(860, 1240)
    cx = 400
    N = {}

    def add(key, parts_sh):
        parts, sh = parts_sh
        d.add(parts)
        N[key] = sh
    add("i", initial(cx, 40))
    add("m1", merge(cx, 100))
    add("a1", act(cx, 170, "Capture browser event"))
    add("a2", act(cx, 250, "Send event to backend"))
    add("d1", diamond(cx, 335, 40, 40))
    add("rej", act(690, 335, "Reject event", w=200))
    add("fr", final(690, 420))
    add("a3", act(cx, 425, "Store event in database"))
    add("d2", diamond(cx, 515, 40, 40))
    add("ls", box(cx, 595, 360, 50, "Score window with Transformer decoder", rx=24, dash="8,5"))
    add("m2", merge(cx, 670))
    add("a4", act(cx, 740, "Ask LLM for assessment", w=340))
    add("d3", diamond(cx, 830, 40, 40))
    add("fork", bar(cx, 905, 360))
    add("a5", act(250, 975, "Save alert", w=220))
    add("a6", act(550, 975, "Update analysis cursor", w=240))
    add("join", bar(cx, 1045, 360))
    add("a7", act(cx, 1115, "Show alert on dashboard"))
    add("f", final(cx, 1185))
    for a, b in [("i", "m1"), ("m1", "a1"), ("a1", "a2"), ("a2", "d1"), ("d1", "a3"), ("a3", "d2"),
                 ("m2", "a4"), ("a4", "d3"), ("d3", "fork"), ("join", "a7"), ("a7", "f"), ("rej", "fr")]:
        d.add(arrow(N[a], N[b]))
    d.add(arrow(N["d2"], N["ls"], dash="7,5"), arrow(N["ls"], N["m2"], dash="7,5"))
    d.add(arrow(N["d1"], N["rej"]), guard(505, 322, "invalid"), guard(cx + 12, 375, "valid", "start"))
    d.add(line(250, 909, 250, 950, end="arrow"), line(550, 909, 550, 950, end="arrow"),
          line(250, 1000, 250, 1041, end="arrow"), line(550, 1000, 550, 1041, end="arrow"))
    d.add(guard(cx + 12, 552, "5 new events or 90 s idle", "start"),
          path_arrow([(cx - 20, 515), (130, 515), (130, 100), (cx - 15, 100)]), guard(140, 300, "else: wait", "start"))
    d.add(guard(cx + 12, 868, "valid response", "start"),
          path_arrow([(cx + 20, 830), (720, 830), (720, 670), (cx + 15, 670)]), guard(730, 750, "invalid: retry", "start"))
    d.save("activity_diagram")


# ================================================================== SWIMLANE
def swimlane_diagram():
    lanes = ["Employee", "Chrome Extension", "Backend", "Security Analyst"]
    W, H, lw = 1100, 840, 275
    d = Diagram(W, H)
    for i, n in enumerate(lanes):
        d.add(rect(i * lw, 0, lw, H, fill="#ffffff"), text(i * lw + lw / 2, 25, n, 16, weight="bold"))
    d.add(line(0, 50, W, 50))
    c = [lw / 2 + i * lw for i in range(4)]
    N = {}

    def add(key, ps):
        parts, sh = ps
        d.add(parts)
        N[key] = sh
    add("i", initial(c[0], 85))
    add("m", merge(c[0], 135))
    add("browse", act(c[0], 200, "Browse / download", w=220))
    add("cap", act(c[1], 200, "Capture metadata", w=220))
    add("send", act(c[1], 285, "Send event", w=220))
    add("store", act(c[2], 285, "Validate and store", w=220))
    add("dec", diamond(c[2], 375, 40, 40))
    add("ls", box(c[2], 465, 240, 50, "Transformer decoder score", rx=24, dash="8,5"))
    add("ask", act(c[2], 550, "Ask LLM,\nverify evidence", w=240, h=58))
    add("save", act(c[2], 640, "Save alert", w=220))
    add("see", act(c[3], 640, "See alert on dashboard", w=230))
    add("open", act(c[3], 725, "Open evidence record", w=230))
    add("f", final(c[3], 800))
    for a, b in [("i", "m"), ("m", "browse"), ("browse", "cap"), ("cap", "send"), ("send", "store"), ("store", "dec"),
                 ("ask", "save"), ("save", "see"), ("see", "open"), ("open", "f")]:
        d.add(arrow(N[a], N[b]))
    d.add(arrow(N["dec"], N["ls"], dash="7,5"), arrow(N["ls"], N["ask"], dash="7,5"))
    d.add(guard(c[2] + 12, 415, "enough new events", "start"))
    d.add(path_arrow([(c[2] - 20, 375), (40, 375), (40, 135), (c[0] - 15, 135)]), guard(50, 360, "else: wait", "start"))
    d.save("swimlane_diagram")


# ================================================================== DFDs (balanced)
def dfd_level0():
    d = Diagram(1000, 520)
    pp, P = proc(500, 260, 100, "0", "hackViz\nInsider-Risk\nSystem")
    d.add(pp)
    E = {}
    for k, x, y, n in [("emp", 140, 90, "EMPLOYEE"), ("ad", 140, 430, "ADMINISTRATOR"),
                       ("an", 860, 90, "SECURITY ANALYST"), ("ol", 860, 430, "LLM\n(Qwen2.5)")]:
        parts, E[k] = entity(x, y, n, w=210, h=60)
        d.add(parts)
    d.add(arrow(E["emp"], P, "browser activity", (285, 150)))
    d.add(arrow(E["ad"], P, "employee details", (285, 370)))
    d.add(arrow(E["an"], P, "Analyze Now request", (770, 200), off=-14))
    d.add(arrow(P, E["an"], "alerts and evidence", (630, 128), off=-14))
    d.add(arrow(P, E["ol"], "prompt", (640, 330), off=14))
    d.add(arrow(E["ol"], P, "assessment JSON", (790, 360), off=14))
    d.save("dfd_level0")


def dfd_level1():
    d = Diagram(1320, 580)
    xs = [140, 400, 660, 920, 1180]
    names = [("1.0", "Manage\nEmployees"), ("2.0", "Collect\nActivity"), ("3.0", "Build\nContext"),
             ("4.0", "Assess\nwith LLM"), ("5.0", "Present\nAlerts")]
    P = []
    for x, (n, nm) in zip(xs, names):
        parts, sh = proc(x, 275, 72, n, nm)
        d.add(parts)
        P.append(sh)
    E = {}
    for k, x, n in [("ad", 140, "ADMINISTRATOR"), ("emp", 400, "EMPLOYEE"), ("an1", 660, "SECURITY ANALYST"),
                    ("ol", 920, "LLM\n(Qwen2.5)"), ("an2", 1180, "SECURITY ANALYST")]:
        parts, E[k] = entity(x, 75, n, w=200, h=60)
        d.add(parts)
    d.add(arrow(E["ad"], P[0]), label(140, 150, "employee details", 13))
    d.add(arrow(E["emp"], P[1]), label(400, 150, "browser activity", 13))
    d.add(arrow(E["an1"], P[2]), label(660, 150, "Analyze Now request", 13))
    d.add(arrow(P[3], E["ol"], off=-14), label(870, 150, "prompt", 13))
    d.add(arrow(E["ol"], P[3], off=-14), label(985, 165, "assessment\nJSON", 13))
    d.add(arrow(P[4], E["an2"]), label(1180, 150, "alerts and evidence", 13))
    d.add(arrow(P[2], P[3]), label(790, 255, "behaviour\ncontext", 13))
    S1 = dstore(270, 470, "D1: Employees"); d.add(S1[0])
    S2 = dstore(530, 470, "D2: Activity Logs"); d.add(S2[0])
    S3 = dstore(1080, 470, "D3: Assessments"); d.add(S3[0])
    d.add(arrow(P[0], S1[1], "employee\nrecord", (180, 380)))
    d.add(arrow(S1[1], P[1], "employee\ncheck", (318, 365)))
    d.add(arrow(P[1], S2[1], "valid\nevents", (480, 365)))
    d.add(arrow(S2[1], P[2], "event history", (640, 400)))
    d.add(arrow(P[3], S3[1], "verified\nassessment", (1035, 380)))
    d.add(arrow(S3[1], P[4], "stored\nalerts", (1170, 400)))
    # planned LSTM process (dashed): reads the event sequence, gives an anomaly score to 4.0
    pp, P6 = dashed_proc(800, 490, 66, "6.0", "Score with\nTransformer\ndecoder")
    d.add(pp)
    d.add(arrow(S2[1], P6, dash="7,5"), label(680, 520, "event\nsequence", 13))
    d.add(arrow(P6, P[3], dash="7,5"), label(895, 405, "anomaly\nscore", 13))
    d.save("dfd_level1")


def dfd_level2():
    d = Diagram(1100, 560)
    xs = [230, 470, 710, 950]
    names = [("4.1", "Compose\nPrompt"), ("4.2", "Parse\nResponse"), ("4.3", "Verify\nEvidence"), ("4.4", "Save\nAssessment")]
    P = []
    for x, (n, nm) in zip(xs, names):
        parts, sh = proc(x, 290, 72, n, nm)
        d.add(parts)
        P.append(sh)
    parts, ol = entity(350, 80, "LLM\n(Qwen2.5)", w=220, h=60)
    d.add(parts)
    d.add(line(20, 290, 158, 290, end="arrow"), label(75, 250, "behaviour context\n(from 3.0)", 13))
    d.add(poly([(60, 470), (175, 470), (180, 357)], end="arrow", dash="7,5"),
          label(95, 500, "anomaly score\n(from 6.0)", 13))
    d.add(arrow(P[0], ol), label(250, 175, "prompt", 13))
    d.add(arrow(ol, P[1]), label(470, 175, "assessment JSON", 13))
    d.add(arrow(P[1], P[2]), label(590, 262, "parsed\nresult", 13))
    d.add(arrow(P[2], P[3]), label(830, 262, "verified\nresult", 13))
    S3 = dstore(950, 480, "D3: Assessments")
    d.add(S3[0], arrow(P[3], S3[1]), label(950, 410, "verified assessment", 13))
    d.save("dfd_level2")


# ================================================================== SEQUENCE
def sequence_diagram():
    d = Diagram(1000, 700)
    X = {"emp": 100, "ext": 360, "be": 620, "db": 880}
    _lifeline(d, X["emp"], "Employee", actor_=True, bottom=670)
    _lifeline(d, X["ext"], ": Chrome Extension", bottom=670)
    _lifeline(d, X["be"], ": Backend", bottom=670)
    _lifeline(d, X["db"], ": Database", bottom=670)
    msgs = [("emp", "ext", "enter ID + consent", False), ("ext", "be", "pair request", False),
            ("be", "db", "find employee", False), ("db", "be", "employee found", True),
            ("be", "ext", "paired: name, role", True), ("emp", "ext", "visit page / download", False),
            ("ext", "be", "send event", False), ("be", "db", "save event", False), ("be", "ext", "OK", True)]
    y = 200
    for i, (a, b, s, r) in enumerate(msgs, 1):
        _msg(d, X[a], X[b], y, s, r, i)
        y += 52
    d.save("sequence_diagram")


def sequence_analyze():
    d = Diagram(1160, 780)
    X = {"an": 80, "ds": 260, "be": 450, "ls": 650, "tr": 850, "db": 1060}
    _lifeline(d, X["an"], "Analyst", actor_=True, bottom=750)
    _lifeline(d, X["ds"], ": Dashboard", bottom=750)
    _lifeline(d, X["be"], ": Backend", bottom=750)
    d.add(rect(X["ls"] - 95, 30, 190, 46, fill="#ffffff", dash="8,5"), text(X["ls"], 53, ": Transformer decoder", 14, weight="bold"),
          line(X["ls"], 76, X["ls"], 750, dash="6,5", sw=1.2))
    _lifeline(d, X["tr"], ": LLM", bottom=750)
    _lifeline(d, X["db"], ": Database", bottom=750)
    msgs = [("an", "ds", "click Analyze Now", False), ("ds", "be", "analyze request", False),
            ("be", "db", "read events", False), ("db", "be", "events", True),
            ("be", "ls", "score window", False), ("ls", "be", "anomaly score", True),
            ("be", "tr", "prompt", False), ("tr", "be", "assessment JSON", True),
            ("be", "db", "save alert", False), ("be", "ds", "alert", True), ("ds", "an", "show alert", True)]
    y = 200
    for i, (a, b, s, r) in enumerate(msgs, 1):
        _msg(d, X[a], X[b], y, s, r, i)
        y += 50
    d.save("sequence_analyze")


# ================================================================== COLLABORATION
def collab_analyze():
    d = Diagram(1000, 520)
    P = {"an": (150, 90), "ds": (500, 90), "be": (850, 90), "ol": (850, 420), "db": (500, 420)}
    names = {"an": ": Analyst", "ds": ": Dashboard", "be": ": Backend", "ol": ": Ollama LLM", "db": ": Database"}
    for a, b in [("an", "ds"), ("ds", "be"), ("be", "ol"), ("be", "db")]:
        d.add(line(*P[a], *P[b], sw=1.4))
    for k, p in P.items():
        d.add(_obj(*p, names[k]))
    d.add(_cmsg(P["an"], P["ds"], ["1: click Analyze Now"], side=-1))
    d.add(_cmsg(P["ds"], P["be"], ["2: analyze request"], side=-1))
    d.add(_cmsg(P["be"], P["db"], ["3: read events", "5: save alert"], side=-1, off=18))
    d.add(_cmsg(P["be"], P["ol"], ["4: prompt"], side=-1, off=20))
    d.add(_cmsg(P["ds"], P["an"], ["6: show alert"], side=-1))
    d.save("collab_analyze")


def collab_ingest():
    d = Diagram(1000, 520)
    P = {"em": (150, 90), "ex": (500, 90), "be": (850, 90), "db": (850, 420), "wk": (500, 420)}
    names = {"em": ": Employee", "ex": ": Chrome Extension", "be": ": Backend", "db": ": Database",
             "wk": ": Analysis Worker"}
    for a, b in [("em", "ex"), ("ex", "be"), ("be", "db"), ("db", "wk")]:
        d.add(line(*P[a], *P[b], sw=1.4))
    for k, p in P.items():
        d.add(_obj(*p, names[k]))
    d.add(_cmsg(P["em"], P["ex"], ["1: visit page"], side=-1))
    d.add(_cmsg(P["ex"], P["be"], ["2: send event"], side=-1))
    d.add(_cmsg(P["be"], P["db"], ["3: save event"], side=-1, off=20))
    d.add(_cmsg(P["wk"], P["db"], ["4: check new events"], side=1))
    d.save("collab_ingest")


# ================================================================== CLASS
def class_domain():
    d = Diagram(1060, 600)
    emp, E, eb = sclass(410, 220, 240, "Employee", ["- employee_id : str", "- name : str", "- role : str",
                                                     "- department : str"])
    act_, A, ab = sclass(40, 30, 260, "ActivityLog", ["- id : int", "- event_type : str", "- url : str",
                                                      "- timestamp : datetime"])
    ano, N, nb = sclass(40, 340, 260, "Anomaly", ["- risk_level : str", "- confidence : float", "- reason : str",
                                                  "- evidence_ids : int[*]"])
    ses, X, xb = sclass(760, 30, 260, "ExtensionSession", ["- session_token : str", "- paired_at : datetime",
                                                           "- events_received : int"])
    sta, T, tb = sclass(760, 340, 260, "AnalysisState", ["- last_event_id : int", "- failures : int",
                                                         "- next_retry_at : datetime"])
    d.add(emp, act_, ano, ses, sta)
    # composition: Employee (whole, multiplicity 1) owns its records
    for other in (A, N, X, T):
        ln, _ = connect(E, other, start="diamond")
        d.add(ln)
    d.add(mult(432, 207, "1"), mult(318, 175, "0..*"), mult(432, 402, "1"), mult(318, 380, "0..*"),
          mult(628, 207, "1"), mult(742, 175, "0..*"), mult(628, 402, "1"), mult(742, 380, "0..1"))
    ln, _ = connect(N, A)
    d.add(ln, label(170, 300, "cites ▸", 13, italic=True), mult(190, 270, "1..*"), mult(190, 328, "*"))
    d.save("class_domain")


def class_analysis():
    d = Diagram(1120, 640)
    wk, W, wb = sclass(40, 40, 300, "AnalysisWorker", ["- queue : Queue"],
                       ["+ start() : void", "+ request(id : str) : Job"])
    az, Z, zb = sclass(410, 40, 300, "Analyzer", ["- window_size : int"],
                       ["+ build_prompt() : str", "+ analyze_employee(id : str) : dict"])
    am, AM, amb = sclass(790, 40, 290, "<<abstract>> AnomalyModel", ["- name : str"],
                         ["+ assess(window) : result"])
    jb, J, jbb = sclass(40, 340, 300, "Job", ["- employee_id : str", "- mode : str", "- state : str"])
    la, L, lb = sclass(410, 340, 300, "LLMAssessment", ["- risk_level : str", "- confidence : float",
                                                        "- reason : str"])
    d.add(wk, az, am, jb, la)
    tr, T, tb = sclass(740, 380, 180, "LLM", ["- model : qwen2.5:3b", "- layers : int = 36"],
                       ["+ generate(prompt) : str"])
    d.add(tr)
    # planned LSTM class drawn dashed
    x, y, w = 935, 380, 170
    top, row = 36, 22
    h = top + 2 * row + 8 + 2 * row + 8
    d.add(rect(x, y, w, h, fill="#ffffff", dash="8,5"), rect(x, y, w, top, fill=FILL2, dash="8,5"),
          text(x + w / 2, y + 18, "TransformerDecoder", 14, weight="bold"),
          line(x, y + top + 2 * row + 8, x + w, y + top + 2 * row + 8, dash="6,4"),
          text(x + 8, y + top + 5, "- hidden_size : int", 13, anchor="start", valign="top"),
          text(x + 8, y + top + 5 + row, "- threshold : float", 13, anchor="start", valign="top"),
          text(x + 8, y + top + 2 * row + 13, "+ train(events)", 13, anchor="start", valign="top"),
          text(x + 8, y + top + 3 * row + 13, "+ score(window) : float", 13, anchor="start", valign="top"))
    # generalisation: both models are AnomalyModels
    d.add(line(830, 380, 830, 345), line(1020, 380, 1020, 345, dash="6,4"), line(830, 345, 1020, 345),
          line(935, 345, 935, amb, end="tri"))
    ln, _ = connect(W, J, start="diamond"); d.add(ln, mult(205, wb + 14, "1"), mult(210, 328, "*"))
    ln, _ = connect(W, Z, end="open"); d.add(ln, label(375, 100, "runs", 13, italic=True))
    ln, _ = connect(Z, AM, end="open"); d.add(ln, label(750, 62, "uses", 13, italic=True))
    ln, _ = connect(Z, L, dash="7,5", end="open"); d.add(ln, label(560, (zb + 340) / 2, "<<creates>>", 13))
    d.save("class_analysis")


# ================================================================== STATE
def state_analysis():
    d = Diagram(1000, 430)
    p, I = initial(50, 110); d.add(p)
    parts, idle = state(210, 110, "Idle"); d.add(parts)
    parts, pend = state(500, 110, "Pending"); d.add(parts)
    parts, ana = state(810, 110, "Analysing"); d.add(parts)
    parts, fail = state(810, 340, "Failed"); d.add(parts)
    d.add(arrow(I, idle))
    d.add(arrow(idle, pend), label(355, 90, "new event", 13))
    d.add(arrow(pend, ana), label(655, 90, "5 events / 90 s", 13))
    d.add(path_arrow([(810, 138), (810, 220), (210, 220), (210, 138)], "alert saved", (500, 220)))
    d.add(arrow(ana, fail, off=-30), label(700, 260, "error / timeout", 13))
    d.add(arrow(fail, ana, off=-30), label(920, 260, "retry later", 13))
    d.save("state_analysis")


def state_extension():
    d = Diagram(1050, 430)
    p, I = initial(50, 110); d.add(p)
    parts, np_ = state(220, 110, "Not Paired"); d.add(parts)
    parts, pa = state(540, 110, "Paired"); d.add(parts)
    parts, se = state(860, 110, "Sending"); d.add(parts)
    parts, off = state(860, 340, "Offline"); d.add(parts)
    d.add(arrow(I, np_))
    d.add(arrow(np_, pa, off=-12), label(380, 80, "pair + consent", 13))
    d.add(arrow(pa, np_, off=-12), label(380, 140, "disconnect", 13))
    d.add(arrow(pa, se, off=-12), label(700, 80, "event captured", 13))
    d.add(arrow(se, pa, off=-12), label(700, 140, "sent OK", 13))
    d.add(arrow(se, off, off=-30), label(745, 225, "backend down", 13))
    d.add(arrow(off, se, off=-30), label(975, 225, "retry 30 s", 13))
    d.save("state_extension")


# ================================================================== COMPONENT / DEPLOYMENT
def comp(cx, cy, w, h, name, sub=None):
    x, y = cx - w / 2, cy - h / 2
    out = [rect(x, y, w, h, rx=4, fill="#ffffff"), text(cx, cy - (10 if sub else 0), name, 16, weight="bold"),
           rect(x + w - 30, y + 8, 18, 20, fill="#ffffff", sw=1.2), rect(x + w - 35, y + 12, 10, 4, fill="#ffffff", sw=1.2),
           rect(x + w - 35, y + 20, 10, 4, fill="#ffffff", sw=1.2)]
    if sub:
        out.append(text(cx, cy + 16, sub, 13, italic=True))
    return out, S("rect", cx, cy, w / 2, h / 2)


def component_diagram():
    d = Diagram(1040, 440)
    parts, ext = comp(160, 100, 240, 90, "Chrome Extension"); d.add(parts)
    parts, dash = comp(160, 340, 240, 90, "React Dashboard"); d.add(parts)
    parts, be = comp(520, 220, 260, 110, "FastAPI Backend", "routes + analysis worker"); d.add(parts)
    parts, db = comp(880, 100, 240, 90, "PostgreSQL"); d.add(parts)
    parts, ol = comp(880, 340, 240, 90, "Ollama LLM", "qwen2.5:3b"); d.add(parts)
    d.add(arrow(ext, be, "REST API", (330, 140), dash="7,5"), arrow(dash, be, "REST API", (330, 300), dash="7,5"),
          arrow(be, db, "SQL", (710, 140), dash="7,5"), arrow(be, ol, "HTTP /api/chat", (710, 300), dash="7,5"))
    d.save("component_diagram")


def deployment_diagram():
    d = Diagram(1000, 500)
    d.add(rect(20, 20, 960, 460, rx=0, fill="#ffffff", sw=2),
          text(40, 46, "<<device>>  Windows laptop (16 GB RAM, CPU only)", 16, anchor="start", weight="bold"))
    nodes = {}
    for k, cx, cy, name, sub in [("ch", 210, 170, "Google Chrome", "dashboard + extension"),
                                 ("be", 640, 170, "Python Backend", "FastAPI  :8000"),
                                 ("db", 430, 380, "PostgreSQL", "database  :5432"),
                                 ("ol", 820, 380, "Ollama", "qwen2.5:3b  :11434")]:
        d.add(rect(cx - 125 + 10, cy - 45 - 10, 250, 90, fill="#e6e6e6", sw=1.2))
        parts, nodes[k] = box(cx, cy, 250, 90, "", rx=0, fill="#ffffff")
        d.add(parts, text(cx, cy - 12, name, 16, weight="bold"), text(cx, cy + 16, sub, 14))
    for a, b, lab, lp in [("ch", "be", "HTTP", (425, 152)), ("be", "db", "SQL", (520, 290)),
                          ("be", "ol", "HTTP", (745, 290))]:
        ln, _ = connect(nodes[a], nodes[b])
        d.add(ln, label(lp[0], lp[1], lab, 13))
    d.save("deployment_diagram")


# ================================================================== MODEL DIAGRAMS
def transformer_diagram():
    d = Diagram(620, 880)
    cx = 310
    ys = {}
    for k, y, s, fl in [("p", 60, "Prompt: role, baseline, recent events", FILL2), ("t", 160, "Tokenizer", FILL),
                        ("e", 250, "Token embedding", FILL)]:
        parts, ys[k] = box(cx, y, 380, 54, s, fill=fl); d.add(parts)
    d.add(rect(cx - 220, 320, 440, 270, rx=10, fill="#f4f4f4", sw=2),
          text(cx - 205, 342, "Decoder block  x 36", 15, anchor="start", weight="bold"))
    parts, ys["a"] = box(cx, 410, 320, 56, "Self-attention"); d.add(parts)
    parts, ys["f"] = box(cx, 520, 320, 56, "Feed-forward network"); d.add(parts)
    for k, y, s, fl in [("o", 660, "Output layer (softmax)", FILL), ("j", 760, "JSON: risk, reason, evidence IDs", FILL2)]:
        parts, ys[k] = box(cx, y, 380, 54, s, fill=fl); d.add(parts)
    for a, b in [("p", "t"), ("t", "e"), ("a", "f"), ("o", "j")]:
        d.add(arrow(ys[a], ys[b]))
    d.add(line(cx, 277, cx, 382, end="arrow"), line(cx, 548, cx, 633, end="arrow"))
    d.add(text(cx, 835, "Qwen2.5-3B-Instruct, run locally by Ollama", 14, italic=True))
    d.save("transformer_architecture")


def lstm_autoencoder_diagram():
    d = Diagram(1120, 400)
    d.add(rect(14, 14, 1092, 372, rx=10, fill="#ffffff", dash="10,6"),
          text(36, 44, "Planned (not implemented): LSTM autoencoder", 17, anchor="start", weight="bold"))
    xs = [120, 335, 550, 765, 980]
    names = ["Event\nsequence", "LSTM\nencoder", "Latent\nvector", "LSTM\ndecoder", "Rebuilt\nsequence"]
    B = []
    for x, n in zip(xs, names):
        parts, sh = box(x, 150, 170, 74, n, fill=FILL2 if "LSTM" in n else FILL); d.add(parts); B.append(sh)
    for i in range(4):
        d.add(arrow(B[i], B[i + 1]))
    parts, err = box(765, 300, 260, 64, "Reconstruction error\n(high = unusual)"); d.add(parts)
    parts, llm = box(330, 300, 330, 64, "Transformer LLM explains\nthe unusual window", fill=FILL2); d.add(parts)
    d.add(line(980, 187, 980, 300), line(980, 300, 895, 300, end="arrow"))
    d.add(arrow(err, llm))
    d.save("lstm_autoencoder")


if __name__ == "__main__":
    for fn in (architecture_diagram, pipeline_diagram, use_case_diagram, activity_diagram, swimlane_diagram,
               dfd_level0, dfd_level1, dfd_level2, sequence_diagram, sequence_analyze, collab_analyze, collab_ingest,
               class_domain, class_analysis, state_analysis, state_extension, component_diagram, deployment_diagram,
               transformer_diagram, lstm_autoencoder_diagram):
        fn()
    print("simple diagrams written to", OUT)

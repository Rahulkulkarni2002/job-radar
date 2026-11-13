#!/usr/bin/env python3
"""One-off company probe: list EVERY data/analytics role at the given companies (last 30 days) and say whether
the candidate's rules keep it, and if not, the first rule that removes it.
Usage (GitHub Actions 'Probe companies'): python scraper/probe.py "airbnb,workday,linkedin,broadcom"
Writes docs/data/probe.json."""
import json, os, re, sys, pathlib
os.environ.setdefault("MAX_AGE_DAYS", "30")
HERE = pathlib.Path(__file__).resolve().parent
ns = {"__name__": "probe", "__file__": str(HERE / "scrape.py")}
exec((HERE / "scrape.py").read_text(), ns)
g = ns
WANT = [w.strip().lower() for w in (sys.argv[1] if len(sys.argv) > 1 else "airbnb,workday,linkedin,broadcom").split(",") if w.strip()]
DATAISH = r"analyst|analytics|data|scientist|insight|intelligence|strategy|forecast|pricing|finance|financial|quant|research|machine learning|ai\b"
_rel = g["relevant"]; g["relevant"] = lambda t: bool(re.search(DATAISH, (t or "").lower()))   # see everything data-ish, judge later
boards = json.load(open(HERE / "boards.json"))
fetch = {"greenhouse": g["greenhouse"], "lever": g["lever"], "ashby": g["ashby"], "smartrecruiters": g["smartrecruiters"],
         "workday": g["workday"]}
jobs = []
for kind, entries in boards.items():
    if kind not in fetch: continue
    items = entries.items() if isinstance(entries, dict) else [(e, e) for e in entries]
    for slug, name in items:
        if any(w in (str(slug) + " " + str(name)).lower() for w in WANT):
            try: jobs += fetch[kind](slug, name)
            except Exception as e: print("ERR", kind, slug, e)
table = g["h1b_table"]()
def verdict(j):
    if not _rel(j["title"]): return "title not an analyst/data role for you (or senior/engineer title)"
    if g["age"](j["posted"]) > 15: return f"posted {g['age'](j['posted'])} days ago (> 15)"
    checks = [
        (lambda: re.search(g["TITLE_INFLATED"], j["title"].lower().strip()) and (j["years"] is None or j["years"] > 2), "senior title"),
        (lambda: g["senior_in_jd"](j["title"], j["jd"]), "senior role (stated in JD)"),
        (lambda: g["role_experience_problem"](j["jd"]), "requires data-scientist-title / publication experience"),
        (lambda: j["years"] is not None and j["years"] > 4, f"needs {j['years']}+ years"),
        (lambda: j["sponsor_jd"] == "no", "won't sponsor / citizens only"),
        (lambda: g["timing_problem"](j["jd"]), "start date / grad window"),
        (lambda: g["degree_problem"](j["jd"]), "PhD / licence required"),
        (lambda: g["domain_problem"](j["jd"]), "needs IB / consulting / PE / Big4 experience"),
        (lambda: g["engineering_problem"](j["jd"]), "engineering / hardware role"),
        (lambda: g["opt_related"](j["title"], j["jd"]) == "weak", "not Business-Analytics related (OPT)"),
        (lambda: g["part_time"](j["title"], j["jd"]), "part-time / temp")]
    for f, why in checks:
        if f(): return why
    m, hit, miss = g["skill_match"](j["title"], j["jd"])
    if m is None or m < 55: return f"skill match {m}% (< 55%)"
    rg = g["required_gaps"](j["jd"], miss, [list(x) for x in hit[2]], g["TERM_RX"], g["_section_is_preferred"])
    if rg: return "requires a skill outside your set: " + ", ".join(rg[:3])
    f, hits, _ = g["fit"](j["title"], j["jd"])
    return f"KEPT: fit {round(.5 * f + .5 * m)}, asks {j['years']} yrs, gaps {miss[:4]}"
out = [{"company": j["company"], "title": j["title"], "location": j["location"], "posted": j["posted"], "years": j["years"],
        "url": j["url"], "verdict": verdict(j)} for j in jobs if g["us"](j["location"])]
out.sort(key=lambda x: (not x["verdict"].startswith("KEPT"), x["company"], x["posted"]), reverse=False)
pathlib.Path(HERE.parent / "docs/data/probe.json").write_text(json.dumps({"companies": WANT, "n": len(out), "jobs": out}, indent=1))
for x in out: print(f'{x["company"]} | {x["title"]} | {x["posted"]} | {x["verdict"]}')

#!/usr/bin/env python3
"""Find the careers pages (Ashby / Greenhouse / Lever / Workable) of Y Combinator companies that are hiring.
Source: open-source YC directory (github.com/yc-oss/api). Runs weekly in GitHub Actions.
Writes scraper/yc_boards.json  {"ashby": {slug: name}, "greenhouse": {...}, "lever": {...}, "workable": {...}, "companies": [names]}"""
import json, re, urllib.request, urllib.error, concurrent.futures as cf, pathlib, time
ROOT = pathlib.Path(__file__).resolve().parent
UA = {"User-Agent": "Mozilla/5.0 (JobRadar personal job search)", "Accept": "application/json"}
SRC = "https://raw.githubusercontent.com/yc-oss/api/main/companies/hiring.json"
def ok(url, data=None):
    try:
        req = urllib.request.Request(url, data=data, headers={**UA, **({"Content-Type": "application/json"} if data else {})})
        with urllib.request.urlopen(req, timeout=15) as r: return r.status == 200 and len(r.read(2000)) > 20
    except Exception: return False
def candidates(c):
    out = [c.get("slug") or ""]
    dom = re.sub(r"^https?://(www\.)?", "", (c.get("website") or "")).split("/")[0]
    if dom: out.append(dom.split(".")[0])
    n = re.sub(r"[^a-z0-9 ]", "", (c.get("name") or "").lower())
    out += [n.replace(" ", ""), n.replace(" ", "-")]
    return [x for i, x in enumerate(out) if x and x not in out[:i]]
def probe(c):
    found = {}
    for s in candidates(c):
        if "ashby" not in found and ok(f"https://api.ashbyhq.com/posting-api/job-board/{s}"): found["ashby"] = s
        if "greenhouse" not in found and ok(f"https://boards-api.greenhouse.io/v1/boards/{s}"): found["greenhouse"] = s
        if "lever" not in found and ok(f"https://api.lever.co/v0/postings/{s}?mode=json&limit=1"): found["lever"] = s
        if found: break
    if not found:
        for s in candidates(c)[:2]:
            if ok(f"https://apply.workable.com/api/v3/accounts/{s}/jobs", json.dumps({"query": ""}).encode()): found["workable"] = s; break
    return c, found
def main():
    cos = json.loads(urllib.request.urlopen(urllib.request.Request(SRC, headers=UA), timeout=120).read())
    cos = [c for c in cos if c.get("status") in ("Active", "Public") and any(re.search(r"United States|America|Remote", r) for r in (c.get("regions") or []))]
    out = {"ashby": {}, "greenhouse": {}, "lever": {}, "workable": {}, "companies": sorted({c["name"] for c in cos})}
    t0 = time.time()
    with cf.ThreadPoolExecutor(24) as ex:
        for c, found in ex.map(probe, cos):
            for k, s in found.items(): out[k][s] = c["name"]
    json.dump(out, open(ROOT / "yc_boards.json", "w"), indent=0)
    print(f"YC: {len(cos)} hiring US/remote companies -> careers pages found:", {k: len(v) for k, v in out.items() if k != "companies"}, f"in {time.time()-t0:.0f}s")
if __name__ == "__main__":
    main()

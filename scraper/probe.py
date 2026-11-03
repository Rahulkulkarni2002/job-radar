import urllib.request, json, re
UA = {"User-Agent": "Mozilla/5.0 (JobRadar personal job search)"}
g = urllib.request.urlopen(urllib.request.Request("https://www.google.com/about/careers/applications/jobs/results/?q=data%20analyst&location=United%20States&sort_by=date", headers=UA), timeout=30).read().decode("utf-8", "ignore")
raw = next(mm.group(2) for mm in re.finditer(r"AF_initDataCallback\(\{key: '(ds:\d+)'.*?data:(.*?), sideChannel", g, re.S) if mm.group(1) == "ds:1")
d = json.loads(raw); jobs = d[0]; print("GOOGLE n jobs", len(jobs), "| tail of d", json.dumps(d[1:])[:200])
j = jobs[0]
for i, v in enumerate(j):
    s = json.dumps(v)
    print(f"GOOGLE [{i}] {type(v).__name__}: {s[:160]}")
def ts(o, path):
    if isinstance(o, int) and 1_600_000_000 < o < 2_000_000_000: print("GOOGLE TIMESTAMP at", path, o)
    if isinstance(o, list):
        for k, x in enumerate(o): ts(x, path + f"[{k}]")
ts(j, "job")

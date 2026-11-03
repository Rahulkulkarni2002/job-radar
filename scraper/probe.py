import urllib.request, json, re
UA = {"User-Agent": "Mozilla/5.0 (JobRadar personal job search)", "Accept": "application/json, text/html"}
def get(url, data=None, headers=None):
    h = dict(UA); h.update(headers or {})
    with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=h), timeout=30) as r: return r.read().decode("utf-8", "ignore")
# TikTok job keys
body = json.dumps({"recruitment_id_list": [], "job_category_id_list": [], "subject_id_list": [], "location_code_list": [], "keyword": "data analyst", "limit": 3, "offset": 0, "portal_entrance": 1}).encode()
d = json.loads(get("https://api.lifeattiktok.com/api/v1/public/supplier/search/job/posts", body, {"Content-Type": "application/json", "website-path": "tiktok"}))
j = d["data"]["job_post_list"][0]
print("TIKTOK KEYS", sorted(j.keys())); print("TIKTOK city_info", json.dumps(j.get("city_info"))[:400]); print("TIKTOK times", {k: v for k, v in j.items() if "time" in k.lower() or "date" in k.lower()})
print("TIKTOK total", d["data"].get("count"))
# Apple hydration
h = get("https://jobs.apple.com/en-us/search?search=data%20analyst&sort=newest&location=united-states-USA")
m = re.search(r"window\.__staticRouterHydrationData\s*=\s*JSON\.parse\((\".*?\")\);", h, re.S)
print("APPLE hydration found", bool(m))
if m:
    data = json.loads(json.loads(m.group(1)))
    def find(o, path=""):
        if isinstance(o, dict):
            if "searchResults" in o: print("APPLE searchResults at", path); return o["searchResults"]
            for k, v in o.items():
                r = find(v, path + "/" + k)
                if r is not None: return r
        elif isinstance(o, list):
            for i, v in enumerate(o[:5]):
                r = find(v, path + f"[{i}]")
                if r is not None: return r
    sr = find(data)
    if sr: print("APPLE first", json.dumps(sr[0])[:900])
# Google AF_initDataCallback
g = get("https://www.google.com/about/careers/applications/jobs/results/?q=%22data%20analyst%22&location=United%20States&sort_by=date")
for mm in re.finditer(r"AF_initDataCallback\(\{key: '(ds:\d+)'.*?data:(.*?), sideChannel", g, re.S):
    key, raw = mm.group(1), mm.group(2)
    print("GOOGLE", key, "len", len(raw), raw[:700].replace("\n", " "))

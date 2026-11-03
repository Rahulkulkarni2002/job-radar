import urllib.request, json, re
UA = {"User-Agent": "Mozilla/5.0 (JobRadar personal job search)", "Accept": "application/json, text/html"}
def get(url, data=None, headers=None):
    h = dict(UA); h.update(headers or {})
    with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=h), timeout=30) as r: return r.read().decode("utf-8", "ignore")
body = json.dumps({"recruitment_id_list": [], "job_category_id_list": [], "subject_id_list": [], "location_code_list": [], "keyword": "data analyst", "limit": 3, "offset": 0, "portal_entrance": 1}).encode()
d = json.loads(get("https://api.lifeattiktok.com/api/v1/public/supplier/search/job/posts", body, {"Content-Type": "application/json", "website-path": "tiktok"}))
j = d["data"]["job_post_list"][0]; print("TIKTOK job_post_info", json.dumps(j.get("job_post_info"))[:500]); print("TIKTOK id", j["id"])
for u in [f"https://api.lifeattiktok.com/api/v1/public/supplier/job/posts/{j['id']}", f"https://api.lifeattiktok.com/api/v1/public/supplier/job/post/{j['id']}"]:
    try: t = get(u, headers={"website-path": "tiktok"}); print("TIKTOK detail", u[-40:], re.findall(r'"(\w*(?:time|date)\w*)":\s*"?(\d+|[\d-]+)', t)[:8], t[:200])
    except Exception as e: print("TIKTOK detail err", u[-40:], e)
try:
    h = get(f"https://lifeattiktok.com/search/{j['id']}"); print("TIKTOK html dates", re.findall(r'(datePosted|publish_time|publishTime)\W+([\w:\- .]+)', h)[:5])
except Exception as e: print("TIKTOK html err", e)
g = get("https://www.google.com/about/careers/applications/jobs/results/?q=data%20analyst&location=United%20States&sort_by=date")
for mm in re.finditer(r"AF_initDataCallback\(\{key: '(ds:\d+)'.*?data:(.*?), sideChannel", g, re.S):
    if mm.group(1) == "ds:1": raw = mm.group(2); print("GOOGLE ds:1 len", len(raw)); print("GOOGLE sample", raw[:1500].replace("\n", " "))
gd = get("https://www.google.com/about/careers/applications/jobs/results/?q=data%20analyst&location=United%20States&sort_by=date")
ids = re.findall(r"jobs/results/(\d+)-([\w-]+)", gd); print("GOOGLE link ids", ids[:3])
if ids:
    dd = get(f"https://www.google.com/about/careers/applications/jobs/results/{ids[0][0]}-{ids[0][1]}")
    print("GOOGLE detail dates", re.findall(r'(datePosted|"\d{4}-\d{2}-\d{2}T)', dd)[:5], "| title", re.findall(r"<title>(.*?)</title>", dd)[:1])
a = get("https://jobs.apple.com/en-us/details/200690189")
print("APPLE detail hydration", bool(re.search(r"__staticRouterHydrationData", a)), re.findall(r'(minimumQualifications|preferredQualifications|description)', a)[:6])

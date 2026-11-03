"""Temporary probe: find current public endpoints for Apple / Google / TikTok careers (prints status + snippet)."""
import urllib.request, json, re
UA = {"User-Agent": "Mozilla/5.0 (JobRadar personal job search)", "Accept": "application/json, text/html"}
def hit(label, url, data=None, headers=None):
    h = dict(UA); h.update(headers or {})
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=h), timeout=30) as r:
            b = r.read().decode("utf-8", "ignore"); hd = dict(r.headers)
            print(f"\n### {label} -> {r.status} len={len(b)} ctype={hd.get('Content-Type')}")
            for pat in [r'positionId["\\\\:]+\s*"?\w+', r'jobs/results/\d+-[\w-]+', r'"job_post_list"', r'datePosted', r'"publish_time"', r'postingDate', r'AF_initDataCallback', r'__staticRouterHydrationData', r'"totalRecords"']:
                m = re.findall(pat, b)
                if m: print(f"   {pat!r}: {len(m)} e.g. {m[:2]}")
            print("   head:", re.sub(r"\s+", " ", b[:300]))
    except Exception as e:
        print(f"\n### {label} -> ERROR {e}")
hit("apple html search", "https://jobs.apple.com/en-us/search?search=data%20analyst&sort=newest&location=united-states-USA")
hit("apple api v1 search GET", "https://jobs.apple.com/api/v1/search?searchString=data%20analyst&locale=en-us&sort=newest")
hit("apple csrf", "https://jobs.apple.com/api/v1/CSRFToken")
hit("apple role detail sample", "https://jobs.apple.com/api/v1/jobDetails/200589123")
hit("google html results", "https://www.google.com/about/careers/applications/jobs/results/?q=%22data%20analyst%22&location=United%20States&sort_by=date")
hit("google api v3", "https://careers.google.com/api/v3/search/?q=analyst")
body = json.dumps({"recruitment_id_list": [], "job_category_id_list": [], "subject_id_list": [], "location_code_list": [], "keyword": "data analyst", "limit": 10, "offset": 0, "portal_entrance": 1}).encode()
for hdrs in ({"Content-Type": "application/json", "website-path": "tiktok"},
             {"Content-Type": "application/json", "website-path": "tiktok", "Accept-Language": "en-US", "portal-channel": "tiktok", "portal-platform": "pc"},
             {"Content-Type": "application/json", "Portal-Channel": "tiktok", "Portal-Platform": "pc", "Website-Path": "tiktok", "env": "prod"}):
    hit(f"tiktok posts {list(hdrs)[1:]}", "https://api.lifeattiktok.com/api/v1/public/supplier/search/job/posts", body, hdrs)
hit("tiktok html", "https://lifeattiktok.com/search?keyword=data%20analyst")

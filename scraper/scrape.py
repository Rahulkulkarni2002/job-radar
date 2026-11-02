#!/usr/bin/env python3
"""Job Radar scraper - runs in GitHub Actions every few hours.
Sources: company career boards (Greenhouse, Lever, Ashby, Workday, SmartRecruiters public job APIs)
         + SimplifyJobs New-Grad feed (scraped from company career pages).
Output:  docs/data/jobs.json  (jobs posted <= MAX_AGE days, relevant to analytics / data / AI / finance roles)
No personal data is stored here - personalization (ATS, chance %) happens in the browser.
"""
import json, re, time, datetime, pathlib, urllib.request, concurrent.futures as cf, html, hashlib, csv, io, os

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "data" / "jobs.json"
BOARDS = json.load(open(ROOT / "scraper" / "boards.json"))
MAX_AGE = int(os.environ.get("MAX_AGE_DAYS", 15))
TODAY = datetime.date.today()
UA = {"User-Agent": "Mozilla/5.0 (JobRadar personal job search)", "Accept": "application/json"}
SIMPLIFY = ["https://raw.githubusercontent.com/SimplifyJobs/New-Grad-Positions/dev/.github/scripts/listings.json"]

TITLE_INCLUDE = r"analyst|analytics|data scien|insight|business intelligence|\bbi\b|fp&a|financ|forecast|pricing|revenue|strategy|operations|decision|reporting|product analyst|\bai\b|machine learning analyst|data associate|quantitative|consult|marketing scien|growth|economist|planning|research"
TITLE_EXCLUDE = r"senior|\bsr\b|staff|principal|director|\bvp\b|head of|\blead\b|manager|intern\b|internship|co-op|software engineer|hardware|firmware|mechanical|electrical|civil|nurse|clinical|sales rep|account executive|technician|recruit|attorney|counsel|phd|\biii\b|\biv\b|post-?doc|professor|driver|warehouse"
CLEARANCE_COS = r"booz allen|northrop|lockheed|raytheon|\brtx\b|saic|leidos|general dynamics|bae systems|amentum|vantor|l3harris|mitre|caci|peraton|parsons|anduril|aerospace corp|guidehouse"
US = r"\b(usa|united states|u\.s\.|remote|[A-Z][a-z]+,\s?(A[LKZR]|C[AOT]|D[EC]|FL|GA|HI|I[ADLN]|K[SY]|LA|M[ADEINOST]|N[CDEHJMVY]|O[HKR]|PA|RI|S[CD]|T[NX]|UT|V[AT]|W[AIVY])\b|NYC|SF|new york|san francisco|seattle|boston|austin|chicago|los angeles|san diego|atlanta|denver|dallas)"
NON_US = r"\b(uk|united kingdom|canada|india|germany|ireland|singapore|london|toronto|bangalore|bengaluru|mexico|poland|australia|brazil|japan|france|netherlands|spain|philippines)\b"
NO_SPONSOR = r"((not|unable to|cannot|can't|won't|will not|does not|do not|are not able to)\s+(currently\s+)?(provide|offer|support|sponsor)\w*\s+(\w+\s+){0,4}(visa|sponsorship|h-?1b)|without (the need for )?(current or future )?(employer |visa )?sponsorship|must be a u\.?s\.? citizen|u\.?s\.? citizenship (is )?required|active (security )?clearance|green card holders? only|not eligible for (visa|h-?1b|opt)|no (visa )?sponsorship)"
SPONSOR_OK = r"((will|can|able to|we)\s+(consider\s+)?(provide|offer|support)\w*\s+(\w+\s+){0,3}(visa|h-?1b|immigration) sponsorship|sponsorship (is )?available|open to sponsor|visa sponsorship (is )?(available|provided|offered)|h-?1b sponsorship available)"
SAL = re.compile(r"\$\s?(\d{2,3}(?:,\d{3})+|\d{2,3}(?:\.\d)?\s?[kK])\s*(?:-|–|to)\s*\$?\s?(\d{2,3}(?:,\d{3})+|\d{2,3}(?:\.\d)?\s?[kK])")

def get(url, timeout=25, data=None):
    h = dict(UA)
    if data: h["Content-Type"] = "application/json"
    with urllib.request.urlopen(urllib.request.Request(url, headers=h, data=data), timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "ignore"))
def strip(h): return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", html.unescape(h or "")))).strip()
ALWAYS = r"data analyst|business analyst|analytics engineer|ai analyst|data scientist|bi analyst|bi developer|insights analyst|product analyst|financial analyst|fp&a|decision scien"
NOT_FIT = r"engineer|engineering|research scientist|scientist, ml systems|materials|chemist|biolog|physic|lab |laboratory|clinical|geospatial|gis\b|programmer|developer(?! - bi)|full stack|technologist|mechanic"
def relevant(t):
    t = t.lower()
    if re.search(TITLE_EXCLUDE, t): return False
    if re.search(ALWAYS, t): return True
    return bool(re.search(TITLE_INCLUDE, t)) and not re.search(NOT_FIT, t)
def us(loc): return bool(re.search(US, loc or "", re.I)) and not re.search(NON_US, loc or "", re.I)
def age(d): return (TODAY - datetime.date.fromisoformat(d)).days
def money(x):
    x = x.replace(",", "").replace(" ", "").lower()
    return float(x[:-1]) * 1000 if x.endswith("k") else float(x)
def salary(txt, comp=None):
    if comp: return comp
    m = SAL.search(txt or "")
    if not m: return ""
    lo, hi = money(m.group(1)), money(m.group(2))
    if lo < 20000 or hi > 600000: return ""
    return f"${lo/1000:.0f}K – ${hi/1000:.0f}K"
def years_required(txt):
    t = (txt or "").lower()
    m = re.findall(r"(\d{1,2})\s*\+?\s*(?:-|–|to)?\s*\d{0,2}\s*\+?\s*years?(?:'|’)?\s*(?:of\s+)?(?:relevant\s+|professional\s+|work\s+|related\s+|industry\s+|full-time\s+)*(?:experience|exp)", t)
    n = [int(x) for x in m if int(x) < 15]
    if n: return min(n)
    if re.search(r"new grad|recent graduate|entry[- ]level|university graduate|early career|campus|0-?\s?[12] years", t): return 0
    return None

def job(company, title, url, posted, loc, txt, source, comp=None):
    txt = txt or ""
    sp = "no" if re.search(NO_SPONSOR, txt, re.I) else "yes" if re.search(SPONSOR_OK, txt, re.I) else "unknown"
    return {"id": hashlib.sha1(url.encode()).hexdigest()[:12], "company": company.strip(), "title": title.strip(), "url": url,
            "posted": posted, "location": (loc or "").strip()[:80], "salary": salary(txt, comp), "years": years_required(txt),
            "sponsor_jd": sp, "source": source, "jd": txt[:8000]}

# ---------------- sources ----------------
def simplify():
    out, now = [], time.time()
    for u in SIMPLIFY:
        for x in get(u, 90):
            if not x.get("active") or now - x.get("date_posted", 0) > MAX_AGE * 86400: continue
            loc = "; ".join(x.get("locations", []))
            if not us(loc) or not relevant(x["title"]): continue
            out.append(job(x["company_name"], x["title"], x["url"], datetime.date.fromtimestamp(x["date_posted"]).isoformat(), loc, "", "Simplify new-grad"))
    return out
def greenhouse(slug, name):
    out = []
    for j in get(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true").get("jobs", []):
        posted = (j.get("first_published") or j.get("updated_at") or "")[:10]
        loc = (j.get("location") or {}).get("name", "")
        if posted and age(posted) <= MAX_AGE and relevant(j["title"]) and us(loc):
            out.append(job(name, j["title"], j["absolute_url"], posted, loc, strip(j.get("content")), "Greenhouse"))
    return out
def lever(slug, name):
    out = []
    for j in get(f"https://api.lever.co/v0/postings/{slug}?mode=json"):
        posted = datetime.date.fromtimestamp(j["createdAt"] / 1000).isoformat()
        loc = (j.get("categories") or {}).get("location", "") or ""
        if age(posted) <= MAX_AGE and relevant(j["text"]) and us(loc):
            txt = (j.get("descriptionPlain") or "") + " " + " ".join(strip(l.get("content")) for l in j.get("lists", [])) + " " + (j.get("additionalPlain") or "")
            sr = j.get("salaryRange") or {}
            comp = f"${sr['min']/1000:.0f}K – ${sr['max']/1000:.0f}K" if sr.get("min") and sr.get("max") and sr.get("interval", "per-year-salary") == "per-year-salary" else None
            out.append(job(name, j["text"], j["hostedUrl"], posted, loc, txt, "Lever", comp))
    return out
def ashby(slug, name):
    out = []
    for j in get(f"https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true").get("jobs", []):
        posted = (j.get("publishedAt") or "")[:10]
        loc = (j.get("location") or "") + (" Remote" if j.get("isRemote") else "")
        if posted and age(posted) <= MAX_AGE and relevant(j["title"]) and us(loc):
            comp = (j.get("compensation") or {}).get("compensationTierSummary") or None
            out.append(job(name, j["title"], j["jobUrl"], posted, loc, j.get("descriptionPlain", ""), "Ashby", comp))
    return out
def workday(board, name):
    tenant, wd, site = board.split("|"); base = f"https://{tenant}.{wd}.myworkdayjobs.com"; out = []
    for q in ("analyst", "data", "analytics"):
        d = get(f"{base}/wday/cxs/{tenant}/{site}/jobs", data=json.dumps({"limit": 20, "offset": 0, "searchText": q, "appliedFacets": {}}).encode())
        for j in d.get("jobPostings", []):
            p = (j.get("postedOn") or "").lower()
            n = 0 if "today" in p else 1 if "yesterday" in p else (99 if "30+" in p else int((re.findall(r"\d+", p) or [99])[0]))
            loc = j.get("locationsText", "")
            if n > MAX_AGE or not relevant(j["title"]) or (not us(loc) and "locations" not in loc.lower()): continue
            try: info = get(f"{base}/wday/cxs/{tenant}/{site}{j['externalPath']}").get("jobPostingInfo", {})
            except Exception: info = {}
            loc2 = info.get("location") or loc
            if not us(loc2) and "locations" not in loc.lower(): continue
            out.append(job(name, j["title"], f"{base}/en-US/{site}{j['externalPath']}", (TODAY - datetime.timedelta(days=n)).isoformat(), loc2, strip(info.get("jobDescription")), "Workday"))
    return out
def smartrecruiters(slug, name):
    out = []
    for j in get(f"https://api.smartrecruiters.com/v1/companies/{slug}/postings?limit=100").get("content", []):
        posted = (j.get("releasedDate") or "")[:10]
        l = j.get("location") or {}
        loc = ", ".join(filter(None, [l.get("city"), l.get("region"), "USA" if l.get("country") == "us" else l.get("country")]))
        if posted and age(posted) <= MAX_AGE and relevant(j["name"]) and l.get("country") == "us":
            try: txt = " ".join(strip(s.get("text")) for s in get(f"https://api.smartrecruiters.com/v1/companies/{slug}/postings/{j['id']}").get("jobAd", {}).get("sections", {}).values())
            except Exception: txt = ""
            out.append(job(name, j["name"], f"https://jobs.smartrecruiters.com/{slug}/{j['id']}", posted, loc, txt, "SmartRecruiters"))
    return out
FETCH = {"greenhouse": greenhouse, "lever": lever, "ashby": ashby, "workday": workday, "smartrecruiters": smartrecruiters}

# ---------------- H-1B history (USCIS H-1B Employer Data Hub, public) ----------------
def norm_co(c):
    c = re.sub(r"\(.*?\)", " ", (c or "").lower())
    c = re.sub(r"\b(inc|llc|ltd|corp|corporation|co|company|group|holdings|technologies|technology|the|usa|us|na|n a|l l c|plc|lp|llp)\b", " ", c)
    return re.sub(r"[^a-z0-9]+", " ", c).strip()
def h1b_table():
    """Return {normalized employer: approvals in latest fiscal years}. Best effort; empty dict if unavailable."""
    cache = ROOT / "scraper" / "h1b_counts.json"
    counts = {}
    for fy in (2025, 2024, 2023):
        url = f"https://www.uscis.gov/sites/default/files/document/data/h1b_datahubexport-{fy}.csv"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA["User-Agent"]})
            raw = urllib.request.urlopen(req, timeout=120).read().decode("utf-8", "ignore")
            for row in csv.DictReader(io.StringIO(raw)):
                name = row.get("Employer (Petitioner) Name") or row.get("Employer") or ""
                tot = 0
                for k, v in row.items():
                    if k and "approval" in k.lower():
                        try: tot += int(str(v).replace(",", "") or 0)
                        except ValueError: pass
                if name: counts[norm_co(name)] = counts.get(norm_co(name), 0) + tot
            print(f"H-1B data hub FY{fy}: {len(counts)} employers")
            break
        except Exception as e:
            print(f"H-1B data hub FY{fy} unavailable: {str(e)[:80]}")
    if counts: json.dump(counts, open(cache, "w"))
    elif cache.exists(): counts = json.load(open(cache))
    return counts
def h1b_lookup(table, company):
    n = norm_co(company)
    if not n or not table: return None
    if n in table: return table[n]
    first = n.split()[0] if n.split() else n
    cands = [v for k, v in table.items() if k == n or k.startswith(n + " ") or (len(first) > 4 and k.split()[:1] == [first])]
    return max(cands) if cands else 0

def enrich(j):
    """Fetch JD text for a feed job straight from the company's career page API (Workday / Greenhouse / Lever)."""
    u = j["url"]
    try:
        m = re.match(r"https://([\w-]+)\.(wd\d+)\.myworkdayjobs\.com/(?:[a-z]{2}-[A-Z]{2}/)?([\w-]+)(/job/.+?)(?:\?|$)", u)
        if m:
            t, wd, site, path = m.groups()
            info = get(f"https://{t}.{wd}.myworkdayjobs.com/wday/cxs/{t}/{site}{path}").get("jobPostingInfo", {})
            txt = strip(info.get("jobDescription"))
        elif "greenhouse" in u or "gh_jid=" in u:
            jid = (re.search(r"gh_jid=(\d+)", u) or re.search(r"/jobs/(\d+)", u)).group(1)
            slug = (re.search(r"greenhouse\.io/([\w-]+)/jobs", u) or [None, None])[1]
            if not slug: return j
            txt = strip(get(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs/{jid}").get("content"))
        elif "jobs.lever.co" in u:
            slug, jid = re.search(r"jobs\.lever\.co/([\w.-]+)/([\w-]+)", u).groups()
            d = get(f"https://api.lever.co/v0/postings/{slug}/{jid}")
            txt = (d.get("descriptionPlain") or "") + " " + " ".join(strip(l.get("content")) for l in d.get("lists", []))
        else: return j
        if txt:
            k = job(j["company"], j["title"], j["url"], j["posted"], j["location"], txt, j["source"])
            j.update({x: k[x] for x in ("jd", "salary", "years", "sponsor_jd")})
    except Exception: pass
    return j

def main():
    t0 = time.time(); res, errs = [], {}
    try: res += simplify()
    except Exception as e: errs["simplify"] = str(e)[:80]
    tasks = [(k, b, name) for k, v in BOARDS.items() for b, name in v.items()]
    with cf.ThreadPoolExecutor(48) as ex:
        futs = {ex.submit(FETCH[k], b, name): k for k, b, name in tasks}
        for f in cf.as_completed(futs):
            try: res += f.result()
            except Exception: errs[futs[f]] = errs.get(futs[f], 0) + 1
    feed = [j for j in res if not j["jd"]]
    with cf.ThreadPoolExecutor(32) as ex: list(ex.map(enrich, feed))
    table = h1b_table()
    prev = {}
    if OUT.exists():
        try: prev = {j["id"]: j for j in json.load(open(OUT)).get("jobs", [])}
        except Exception: pass
    seen, jobs = set(), []
    for j in sorted(res, key=lambda j: (j["source"] == "Simplify new-grad",)):   # prefer direct ATS copy (has JD)
        key = (norm_co(j["company"]), re.sub(r"[^a-z0-9]+", " ", j["title"].lower()).strip())
        if key in seen or j["url"] in seen or re.search(CLEARANCE_COS, j["company"], re.I): continue
        seen.add(key); seen.add(j["url"])
        if j["years"] is not None and j["years"] > 3: continue
        j["h1b_approvals"] = h1b_lookup(table, j["company"])
        j["first_seen"] = prev.get(j["id"], {}).get("first_seen") or datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
        jobs.append(j)
    jobs.sort(key=lambda j: j["posted"], reverse=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    json.dump({"updated": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), "count": len(jobs),
               "boards": len(tasks), "errors": errs, "h1b_source": "USCIS H-1B Employer Data Hub" if table else "",
               "jobs": jobs}, open(OUT, "w"), separators=(",", ":"))
    print(f"{len(jobs)} jobs from {len(tasks)} boards in {time.time()-t0:.0f}s; board errors {errs}")

if __name__ == "__main__":
    main()

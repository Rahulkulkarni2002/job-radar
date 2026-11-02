#!/usr/bin/env python3
"""Job Radar scraper - runs in GitHub Actions every few hours.
Sources: company career boards (Greenhouse, Lever, Ashby, Workday, SmartRecruiters public job APIs)
         + SimplifyJobs New-Grad feed (scraped from company career pages).
Output:  docs/data/jobs.json  (jobs posted <= MAX_AGE days, relevant to analytics / data / AI / finance roles)
No personal data is stored here - personalization (ATS, chance %) happens in the browser.
"""
import json, re, time, urllib.error, datetime, pathlib, urllib.request, concurrent.futures as cf, html, hashlib, csv, io, os

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "data" / "jobs.json"
BOARDS = json.load(open(ROOT / "scraper" / "boards.json"))
MAX_AGE = int(os.environ.get("MAX_AGE_DAYS", 15))
TODAY = datetime.date.today()
UA = {"User-Agent": "Mozilla/5.0 (JobRadar personal job search)", "Accept": "application/json"}
SIMPLIFY = ["https://raw.githubusercontent.com/SimplifyJobs/New-Grad-Positions/dev/.github/scripts/listings.json"]

TITLE_INCLUDE = r"analyst|analytics|data scien|insight|business intelligence|\bbi\b|fp&a|financ|forecast|pricing|revenue|strategy|operations|decision|reporting|product analyst|\bai\b|machine learning analyst|data associate|quantitative|consult|marketing scien|growth|economist|planning|research"
TITLE_EXCLUDE = r"senior|\bsr\b|staff|principal|director|\bvp\b|head of|\blead\b|manager|intern\b|internship|co-op|software engineer|hardware|firmware|mechanical|electrical|civil|nurse|clinical|sales rep|account executive|technician|recruit|attorney|counsel|phd|\biii\b|\biv\b|post-?doc|professor|driver|warehouse|vice president|consultant - |change management|summer|2028|cyber|devops|payroll|robotics|bioinformatics|help ?desk|application development|soc analyst|threat|fraud investigator|coach|cleared|clearance|ts/sci|supervisor|crashworthiness|falcon"
CLEARANCE_COS = r"booz allen|northrop|lockheed|raytheon|\brtx\b|saic|leidos|general dynamics|bae systems|amentum|vantor|l3harris|mitre|caci|peraton|parsons|anduril|aerospace corp|guidehouse"
US = r"\b(usa|united states|u\.s\.|remote|[A-Z][a-z]+,\s?(A[LKZR]|C[AOT]|D[EC]|FL|GA|HI|I[ADLN]|K[SY]|LA|M[ADEINOST]|N[CDEHJMVY]|O[HKR]|PA|RI|S[CD]|T[NX]|UT|V[AT]|W[AIVY])\b|NYC|SF|new york|san francisco|seattle|boston|austin|chicago|los angeles|san diego|atlanta|denver|dallas)"
NON_US = r"\b(uk|united kingdom|canada|india|germany|ireland|singapore|london|toronto|bangalore|bengaluru|mexico|poland|australia|brazil|japan|france|netherlands|spain|philippines)\b"
NO_SPONSOR = r"((not|unable to|cannot|can't|won't|will not|does not|do not|are not able to)\s+(currently\s+)?(provide|offer|support|sponsor)\w*\s+(\w+\s+){0,4}(visa|sponsorship|h-?1b)|without (the need for )?(current or future )?(employer |visa )?sponsorship|must be a u\.?s\.? citizen|u\.?s\.? citizenship (is )?required|active (security )?clearance|green card holders? only|not eligible for (visa|h-?1b|opt)|no (visa )?sponsorship)"
SPONSOR_OK = r"((will|can|able to|we)\s+(consider\s+)?(provide|offer|support)\w*\s+(\w+\s+){0,3}(visa|h-?1b|immigration) sponsorship|sponsorship (is )?available|open to sponsor|visa sponsorship (is )?(available|provided|offered)|h-?1b sponsorship available)"
SAL = re.compile(r"\$\s?(\d{2,3}(?:,\d{3})+|\d{2,3}(?:\.\d)?\s?[kK])\s*(?:-|–|to)\s*\$?\s?(\d{2,3}(?:,\d{3})+|\d{2,3}(?:\.\d)?\s?[kK])")

def get(url, timeout=25, data=None, tries=3):
    """Honest client (identifies itself as a personal job-search bot). Retries only when the server asks us
    to slow down (429 / Retry-After) or has a temporary error; 401/403 refusals are respected, not retried."""
    h = dict(UA)
    if data: h["Content-Type"] = "application/json"
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=h, data=data), timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8", "ignore"))
        except urllib.error.HTTPError as e:
            if e.code in (429, 502, 503, 504) and i < tries - 1:
                time.sleep(min(int(e.headers.get("Retry-After") or 0) or 4 * (i + 1), 30)); continue
            raise
        except (urllib.error.URLError, TimeoutError):
            if i < tries - 1: time.sleep(2 * (i + 1)); continue
            raise

def strip(h): return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", html.unescape(h or "")))).strip()
AI_TITLE = r"\b(ai|a\.i\.|genai|gen ai|generative ai|artificial intelligence|llm|machine learning|ml)\b.{0,40}\b(analyst|associate|strategist|strategy|consultant|operations|ops|enablement|adoption|governance|solutions|product|research|insights?|implementation|evaluation|quality|program|transformation|innovation|deployment|specialist|lead analyst)\b|\b(analyst|associate|strategist|consultant|operations|researcher)\b.{0,30}\b(ai|genai|generative ai|artificial intelligence|llm)\b"
ALWAYS = r"data analyst|business analyst|analytics engineer|ai analyst|data scientist|bi analyst|bi developer|insights? analyst|product analyst|financial analyst|fp&a|decision scien|reporting analyst|pricing analyst|revenue analyst|strategy (and|&) operations|business intelligence|marketing analyst|operations analyst|research analyst|credit analyst|risk analyst|data associate|analytics associate|people analytics|forecasting analyst|planning analyst|quantitative analyst|economist|machine learning analyst"
CORE = r"\b(analyst|analytics|data|insights?|intelligence|forecast\w*|pricing|fp&a|financ\w+ anal\w+|statistic\w*|quantitative|decision|ai|machine learning)\b"
NOT_FIT = r"architect|engineer|engineering|research scientist|materials|chemist|biolog|physic|\blab\b|laboratory|clinical|geospatial|\bgis\b|programmer|developer|full stack|technologist|mechanic|specialist|generalist|coordinator|support|care\b|security|\bit\b|cloud|temporary|temp\b|inventory|workplace|vice president|assistant|administrator|representative|sales|recruit|nurse|teacher|tutor|driver|annotator|rater|trainer|writer|editor"
def relevant(t):
    t = t.lower()
    if re.search(TITLE_EXCLUDE, t): return False
    if re.search(ALWAYS, t) or (re.search(AI_TITLE, t) and not re.search(r"engineer|architect|scientist, ml|researcher, ml|annotator|rater|trainer|tutor|writer", t)): return True
    return bool(re.search(CORE, t)) and not re.search(NOT_FIT, t)
SKILLS = r"\b(sql|python|tableau|power bi|excel|statistic\w*|analytics|forecast\w*|machine learning|data analysis|dashboards?|modeling|pandas|snowflake|databricks|looker|a/b test\w*|regression)\b"
LEX = """sql|python|r|sas|stata|spss|excel|advanced excel|vba|pivot tables|vlookup|power bi|tableau|looker|qlik|domo|alteryx|dbt|airflow|snowflake|databricks|bigquery|redshift|aws|azure|gcp|
spark|pyspark|hadoop|hive|delta lake|duckdb|postgresql|mysql|etl|elt|etl/elt|data pipelines|data warehousing|data modeling|data mart|git|github|jupyter|docker|api|rest api|fastapi|streamlit|mlflow|
pandas|numpy|scikit-learn|xgboost|lightgbm|catboost|random forest|prophet|tensorflow|pytorch|nlp|llm|llms|generative ai|genai|ai|artificial intelligence|machine learning|deep learning|
statistics|statistical analysis|statistical inference|statistical modeling|regression|classification|clustering|segmentation|forecasting|time series|predictive modeling|predictive analytics|
causal inference|uplift modeling|a/b testing|experimentation|hypothesis testing|bayesian|optimization|cross-validation|feature engineering|model deployment|model validation|
dashboards|dashboard|data visualization|visualization|reporting|data storytelling|data cleaning|data quality|data validation|data analysis|data analytics|analytics|business intelligence|bi|
kpis|kpi|metrics|insights|stakeholders|stakeholder management|cross-functional|communication|presentation|powerpoint|
financial analysis|financial modeling|financial forecasting|fp&a|budgeting|budget|forecast|variance analysis|p&l|cash flow|accounts receivable|invoicing|month-end close|ratio analysis|
pricing|revenue|cost analysis|cost forecasting|customer analytics|churn|retention|rfm|crm|marketing analytics|campaign|attribution|product analytics|operations|supply chain|demand planning|
sap|oracle|netsuite|erp|salesforce|zoho|risk|credit risk|compliance|research|benchmarking|competitive analysis|business analytics|data science|data scientist|data analyst|analyst""".replace("\n", "")
SOFT = {"communication", "presentation", "stakeholders", "stakeholder management", "cross-functional", "analyst", "research", "operations", "risk", "metrics", "insights", "revenue", "campaign", "pricing"}
TERMS = sorted(set(LEX.split("|")) - SOFT, key=len, reverse=True)
TERM_RX = {t: re.compile(r"(?<![a-z0-9])" + re.escape(t) + r"(?![a-z0-9])") for t in TERMS}
SYN = {"ai": {"generative ai", "machine learning"}, "artificial intelligence": {"ai", "machine learning"}, "genai": {"generative ai"}, "bi": {"business intelligence", "tableau"},
       "business intelligence": {"bi", "tableau"}, "visualization": {"data visualization", "tableau"}, "dashboard": {"dashboards"}, "data analysis": {"data analytics", "analytics"},
       "statistics": {"statistical analysis"}, "experimentation": {"a/b testing"}, "forecast": {"forecasting"}, "budgeting": {"budget"}, "llm": {"generative ai"}, "llms": {"generative ai"}}
PROFILE = set(l.strip() for l in open(pathlib.Path(__file__).resolve().parent / "profile_skills.txt") if l.strip() and not l.startswith("#"))
MIN_MATCH = int(os.environ.get("MIN_MATCH", 80))
def skill_terms(text):
    t = " " + re.sub(r"\s+", " ", (text or "").lower()) + " "
    h = {x for x in TERMS if TERM_RX[x].search(t)}
    for a, b in [("dashboard", "dashboards"), ("kpi", "kpis"), ("llm", "llms"), ("forecast", "forecasting"), ("budget", "budgeting"), ("etl", "etl/elt"), ("elt", "etl/elt")]:
        if a in h and b in h: h.discard(a)
    return h
def skill_match(title, jd):
    want = skill_terms(title + " " + jd)
    if len(want) < 4: return None, [], []      # too few skills in the JD to judge
    hit = sorted(k for k in want if k in PROFILE or SYN.get(k, set()) & PROFILE)
    return round(100 * len(hit) / len(want)), hit, sorted(want - set(hit))
def skill_fit(jd):
    """None if no JD text; else number of distinct core skills mentioned."""
    if not jd: return None
    return len(set(m.lower() for m in re.findall(SKILLS, jd, re.I)))

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
WORDNUM = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}
def years_required(txt):
    """Strictest REQUIRED years of experience found in any sentence about experience (preferred/nice-to-have ignored).
    Handles '6+ years', '(6 + years)', '6-8 years', 'minimum of 5 years', 'at least five years', 'experience: 4 yrs'."""
    t = (txt or "").lower()
    for w, n in WORDNUM.items(): t = re.sub(r"\b" + w + r"\b(?=\s*(\(\d+\)\s*)?\+?\s*(or more )?(years?|yrs?))", str(n), t)
    best = None
    for s in re.split(r"(?<=[.!?;])\s+|\n+|\s\*\s|•|·", t):
        if not re.search(r"experience|exp\b|background|track record|working in|work in|history of", s): continue
        if re.search(r"prefer|nice to have|a plus|bonus|ideally|desired|years old|years of age|over \d+ years|for \d+ years,? (we|our|the company)", s): continue
        for m in re.finditer(r"(\d{1,2})\s*(?:\+|\s*plus)?\s*(?:-|–|to|or)?\s*(?:\d{1,2})?\s*\+?\s*\)?\s*(?:years?|yrs?)\b", s):
            n = int(m.group(1))
            if n < 15: best = n if best is None else max(best, n)
    if best is not None: return best
    if re.search(r"new grad|recent graduate|entry[- ]level|university graduate|early career|campus|0-?\s?[12] years", t): return 0
    return None

# ---------- strict eligibility checks (candidate: F-1 -> OPT starts 2027-01-28, graduates Dec 2026) ----------
OPT_START, LATEST_START = datetime.date(2027, 1, 28), datetime.date(2027, 3, 31)
GRAD = datetime.date(2026, 12, 15)
NEG = r"\b(not|no|unable|cannot|can't|won't|will not|without|n't|ineligible|not eligible|unavailable|not available|does not|do not|are not|is not|must be (a )?(u\.?s\.? )?citizen|only u\.?s\.? citizens|citizenship (is )?required|permanent residen\w*|green card)\b"
VISA = r"\b(sponsor\w*|visas?|h-?1b|h1-?b|f-?1|immigration|work authori[sz]ation|employment authori[sz]ation|authori[sz]ed to work)\b"
EEO = r"without regard|regardless of|discriminat|equal (employment )?opportunity|protected (veteran|characteristic|status)|e-verify|affirmative action|fair chance"
def sentences(t): return re.split(r"(?<=[.!?;])\s+|\n+|\s\*\s|•", t or "")
def no_sponsorship(t):
    for s in sentences(t):
        l = s.lower()
        if re.search(EEO, l): continue                     # equal-opportunity boilerplate, not a sponsorship statement
        l = re.sub(r"(employer|company)[- ]sponsored|sponsored (medical|health|dental|vision|benefit\w*|plans?|insurance|events?|teams?|programs?|retirement|401)", " ", l)
        visa = re.search(VISA, l) or re.search(r"\b(OPT|CPT)\b", s)   # OPT/CPT only in capitals (not "opt out")
        if visa and re.search(NEG, l): return s.strip()[:160]
        if re.search(r"security clearance|active clearance|ts/sci|secret clearance|u\.?s\.? citizenship", l): return s.strip()[:160]
    return None
MON = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
SEASON = {"spring": 5, "summer": 7, "fall": 12, "autumn": 12, "winter": 12}
def dates_in(s):
    out = []
    for m, y in re.findall(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+(?:\d{1,2}(?:st|nd|rd|th)?,?\s+)?(20\d\d)\b", s): out.append(datetime.date(int(y), MON[m], 15))
    for se, y in re.findall(r"\b(spring|summer|fall|autumn|winter)\s+(?:of\s+)?(20\d\d)\b", s): out.append(datetime.date(int(y), SEASON[se], 15))
    for m, y in re.findall(r"\b(\d{1,2})/(?:\d{1,2}/)?(20\d\d)\b", s):
        if 1 <= int(m) <= 12: out.append(datetime.date(int(y), int(m), 15))
    return out
def timing_problem(t):
    """Return a reason string if the JD's start date or graduation window doesn't fit the candidate, else None."""
    for s in sentences(t):
        l = s.lower(); ds = dates_in(l)
        if not ds: continue
        if re.search(r"graduat|class of|degree (completion|conferred)|completing (a|your) degree|students", l):
            lo, hi = min(ds), max(ds)
            if len(ds) == 1 and abs((ds[0] - GRAD).days) > 75: return "graduation window: " + s.strip()[:120]
            if len(ds) > 1 and not (lo - datetime.timedelta(days=45) <= GRAD <= hi + datetime.timedelta(days=45)): return "graduation window: " + s.strip()[:120]
        elif re.search(r"\bstart|availab|begin|commence|join(ing)? (us|the team|in)|employment on|program (starts|begins)|cohort", l):
            d = min(ds)
            if d.year >= 2027 and (d > LATEST_START): return "start date: " + s.strip()[:120]
            if d < OPT_START and d >= TODAY: return "start date before OPT: " + s.strip()[:120]
    return None

# ---------- OPT: job must be directly related to M.S. Business Analytics ----------
ANALYTIC_DUTIES = r"\b(data analysis|analy[sz]e (data|trends|results|performance|large)|analytics|statistic\w*|forecast\w*|predictive|modell?ing|machine learning|sql|python|\br\b|excel|tableau|power bi|looker|dashboards?|reporting|insights?|kpis?|metrics|business intelligence|data[- ]driven|quantitative|visuali[sz]\w*|optimi[sz]ation|experiment\w*|a/b test\w*|segmentation|data mining|data model\w*|trend analysis|root[- ]cause analysis)\b"
ANALYTIC_TITLE = r"analy|data|scien|insight|intelligence|forecast|quant|statistic|fp&a|financ|pricing|strategy|decision|research|economist|planning|reporting|ai\b|machine learning|product"
def opt_related(title, jd):
    """'strong' / 'ok' / 'weak' - how clearly the duties match a Business Analytics degree (for the OPT relatedness requirement)."""
    duties = {m.group(0).lower()[:12] for m in re.finditer(ANALYTIC_DUTIES, jd or "", re.I)}
    t = bool(re.search(ANALYTIC_TITLE, title.lower()))
    if len(duties) >= 8 and t: return "strong"
    if len(duties) >= 5 and t: return "ok"
    if len(duties) >= 3 and re.search(r"data analyst|data scien|analytics|business intelligence|quantitative|statistic|insights analyst|\bbi\b|machine learning|applied scientist|decision scien", title.lower()): return "ok"
    return "weak"
DOCTORATE = r"\b(ph\.?\s?d\.?|doctorate|doctoral|m\.?d\.?(/ph\.?d)?|pharm\.?d|psy\.?d|d\.?sc)\b"
LOWER_DEG = r"\b(master'?s?|m\.?s\.?c?\b|m\.?a\.?\b|mba|bachelor'?s?|b\.?s\.?c?\b|b\.?a\.?\b|undergraduate|equivalent (practical |work |professional )?experience|or equivalent|years of (relevant )?experience)\b"
LICENSE = r"\b(cpa|certified public accountant|cfa charter(holder)?|chartered financial analyst|registered nurse|\brn\b|licensed (physician|pharmacist|engineer|clinical)|board[- ]certified|\bpe license|professional engineer)\b"
PREF_HDR = r"preferred (qualifications|skills|experience|requirements)|nice[- ]to[- ]haves?|bonus points|pluses|what (would|could|will) set you apart|it would be great if|ideally you"
REQ_HDR = r"(required|minimum|basic|must[- ]have) (qualifications|skills|experience|requirements)|requirements|what you('ll)? (need|bring)|qualifications|who you are|you have"
def _section_is_preferred(t, pos):
    """Is position `pos` inside a 'preferred' section? (looks at the closest section header before it)"""
    before = t[max(0, pos - 2500):pos]
    p = [m.end() for m in re.finditer(PREF_HDR, before)]; r = [m.end() for m in re.finditer(REQ_HDR, before)]
    return bool(p) and (not r or max(p) > max(r))
def degree_problem(jd):
    """Reason string if a REQUIRED qualification needs a doctorate (no master's/experience alternative) or a licence he doesn't hold.
    Works on whitespace-collapsed JD text: decides required vs preferred from the nearest section header + local wording."""
    t = (jd or "").lower()
    for m in re.finditer(DOCTORATE, t):
        if _section_is_preferred(t, m.start()): continue
        win = t[max(0, m.start() - 90):m.end() + 140]
        if re.search(r"prefer|nice to have|a plus|bonus|ideally|desired|or pursuing", win): continue
        if re.search(LOWER_DEG, win): continue
        if not re.search(r"degree|required|qualification|must|field|holder|in (bio|computer|stat|math|phys|eng|econ|chem|neuro|epidem|psych)|\bwith\b|or an", win): continue
        return "requires doctorate: …" + (jd or "")[max(0, m.start() - 30):m.end() + 90].strip() + "…"
    for m in re.finditer(LICENSE, t):
        if _section_is_preferred(t, m.start()): continue
        win = t[max(0, m.start() - 80):m.end() + 80]
        if re.search(r"required|must|need|active|current|valid", win) and not re.search(r"prefer|pursu|work(ing)? toward|obtain within|progress|eligible to sit|a plus", win):
            return "requires licence: …" + (jd or "")[max(0, m.start() - 30):m.end() + 60].strip() + "…"
    return None

# ---------- profile FIT: does the JD ask for the candidate's actual core stack? ----------
PROFILE_CORE = {
 "SQL":(3,r"\bsql\b"),"Python":(3,r"\bpython\b"),"Tableau":(2,r"\btableau\b"),
 "ML":(3,r"machine learning|\bml\b|predictive model|classification|xgboost|scikit|random forest"),
 "Forecasting":(3,r"forecast"),"Stats":(2,r"statistic|regression|hypothesis test"),
 "A/B · causal":(2,r"a/b test|experiment|causal|uplift|incrementality"),
 "Segmentation/churn":(2,r"segmentation|churn|retention|customer analytics|rfm|lifetime value|\bltv\b|clv"),
 "Dashboards/BI":(2,r"dashboard|business intelligence|data visuali[sz]"),
 "Snowflake/Databricks":(2,r"snowflake|databricks|pyspark|\bspark\b|delta lake"),
 "ETL":(1,r"\betl\b|\belt\b|data pipeline"),
 "FP&A":(2,r"fp&a|financial (analysis|model|planning)|budget|variance analysis|cost analysis|p&l"),
 "Excel":(1,r"\bexcel\b"),"GenAI":(2,r"generative ai|genai|\bllms?\b|large language"),
 "Pandas":(1,r"pandas|numpy"),"Deployment":(1,r"mlflow|fastapi|model deploy|streamlit|\bapi\b"),
}
MAXW=sum(w for w,_ in PROFILE_CORE.values())
def fit(title,jd):
    t=(title+" "+jd).lower()
    hits=[k for k,(w,rx) in PROFILE_CORE.items() if re.search(rx,t)]
    w=sum(PROFILE_CORE[k][0] for k in hits)
    hard=any(k in hits for k in ("SQL","Python"))
    score=min(100,round(100*w/22))      # 22 weight pts ≈ a near-perfect match for him
    return score,hits,hard

MIN_FIT = int(os.environ.get("MIN_FIT", 45))

def part_time(title, jd):
    return bool(re.search(r"part[- ]time|adjunct|lecturer|\bper diem\b|\bprn\b|seasonal|temporary|\btemp\b|internship|\b(10|15|19) hours", (title + " " + (jd or "")[:1500]).lower())) and not re.search(r"\bfull[- ]time\b", title.lower())

def job(company, title, url, posted, loc, txt, source, comp=None):
    txt = txt or ""
    sp = "no" if (re.search(NO_SPONSOR, txt, re.I) or no_sponsorship(txt)) else "yes" if re.search(SPONSOR_OK, txt, re.I) else "unknown"
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
        try:
            d = get(f"{base}/wday/cxs/{tenant}/{site}/jobs", data=json.dumps({"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": q}).encode())
        except urllib.error.HTTPError as e:
            if e.code != 422: raise
            # our request format was rejected (not a block): retry once with the minimal payload this tenant accepts
            d = get(f"{base}/wday/cxs/{tenant}/{site}/jobs", data=json.dumps({"appliedFacets": {}, "limit": 20, "offset": 0}).encode())
        time.sleep(1.0)                                   # be polite: pause between searches on the same site
        for j in d.get("jobPostings", []):
            p = (j.get("postedOn") or "").lower()
            n = 0 if "today" in p else 1 if "yesterday" in p else (99 if "30+" in p else int((re.findall(r"\d+", p) or [99])[0]))
            loc = j.get("locationsText", "")
            if n > MAX_AGE or not relevant(j["title"]) or (not us(loc) and "locations" not in loc.lower()): continue
            try: info = get(f"{base}/wday/cxs/{tenant}/{site}{j['externalPath']}").get("jobPostingInfo", {})
            except Exception: info = {}
            loc2 = info.get("location") or loc
            if info.get("location") and not us(loc2): continue
            if not info.get("location") and not us(loc): continue
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
            j["source"] = "Workday" if "myworkdayjobs" in u else "Greenhouse" if ("greenhouse" in u or "gh_jid=" in u) else "Lever"
    except Exception: pass
    return j

def main():
    t0 = time.time(); res, errs, samples = [], {}, {}
    try: res += simplify()
    except Exception as e: errs["simplify"] = str(e)[:80]
    tasks = [(k, b, name) for k, v in BOARDS.items() for b, name in v.items()]
    def run(batch, workers):
        with cf.ThreadPoolExecutor(workers) as ex:
            futs = {ex.submit(FETCH[k], b, name): k for k, b, name in batch}
            for f in cf.as_completed(futs):
                try: res.extend(f.result())
                except Exception as e:
                    errs[futs[f]] = errs.get(futs[f], 0) + 1
                    samples.setdefault(futs[f], []).append(str(e)[:70])
    run([t for t in tasks if t[0] != "workday"], 48)
    run([t for t in tasks if t[0] == "workday"], 10)       # Workday: fewer parallel requests
    n_wd = sum(1 for t in tasks if t[0] == "workday")
    print(f"Workday companies reached: {n_wd - errs.get('workday', 0)}/{n_wd}")
    feed = [j for j in res if not j["jd"]]
    with cf.ThreadPoolExecutor(16) as ex: list(ex.map(enrich, feed))
    # PRIORITY RULE: only jobs confirmed on the company's own careers page. Feed jobs that could not be opened
    # on the company site (no JD fetched from it) are dropped.
    res[:] = [j for j in res if j["jd"]]
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
        if j["sponsor_jd"] == "no": continue              # strict: never list jobs that won't sponsor (incl. OPT/CPT exclusions)
        if timing_problem(j["jd"]): continue             # strict: start date Jan 28-Mar 31 2027 and Dec 2026 grad window
        if degree_problem(j["jd"]): continue             # strict: PhD/MD-only roles and required licenses (CPA/CFA/RN...) dropped
        j["opt"] = opt_related(j["title"], j["jd"])
        if j["opt"] == "weak": continue                  # OPT: duties must be directly related to Business Analytics
        if part_time(j["title"], j["jd"]): continue      # OPT: needs >= 20 h/week; part-time/temp/adjunct dropped
        j["contract"] = bool(re.search(r"(contract(or)?|1099|c2c|corp[- ]to[- ]corp|freelance|apprentice)", (j["title"] + " " + j["jd"][:1500]).lower()))
        m, hit, miss = skill_match(j["title"], j["jd"])
        if m is None or m < MIN_MATCH: continue          # candidate rule: keep only jobs with >= 80% skill match
        j["match"], j["missing"] = m, miss
        f, hits, hard = fit(j["title"], j["jd"])
        if f < MIN_FIT or not (hard or len(hits) >= 5): continue   # must ask for HIS core stack (SQL/Python + 4 core skills)
        j["fit"], j["why"] = f, hits
        j["ai"] = bool(re.search(AI_TITLE, j["title"].lower())) or len(re.findall(r"\b(ai|genai|generative ai|llms?|artificial intelligence|machine learning)\b", j["jd"].lower())) >= 6
        j["h1b_approvals"] = h1b_lookup(table, j["company"])
        j["first_seen"] = prev.get(j["id"], {}).get("first_seen") or datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
        jobs.append(j)
    jobs.sort(key=lambda j: j["posted"], reverse=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    # SAFETY GUARD: a sudden collapse means the scrape broke - keep the last good list instead of publishing it
    prev_n = len(prev)
    if prev_n >= 20 and len(jobs) < 0.4 * prev_n:
        print(f"GUARD: only {len(jobs)} jobs vs {prev_n} last time - NOT publishing; keeping previous list. Errors: {errs}")
        raise SystemExit(1)
    json.dump({"updated": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), "count": len(jobs),
               "boards": len(tasks), "errors": errs, "h1b_source": "USCIS H-1B Employer Data Hub" if table else "",
               "jobs": jobs}, open(OUT, "w"), separators=(",", ":"))
    for k, v in samples.items(): print("sample errors", k, sorted(set(v))[:4])
    print(f"{len(jobs)} jobs from {len(tasks)} boards in {time.time()-t0:.0f}s; board errors {errs}")

if __name__ == "__main__":
    main()

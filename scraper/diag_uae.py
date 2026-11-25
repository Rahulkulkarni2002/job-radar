"""Diagnostic: for each UAE careers page, how many UAE postings exist and where the filters drop them."""
import json, datetime, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import scrape as S
ub = json.load(open(S.ROOT / "scraper" / "uae_boards.json"))
rows, titles = [], []
def rec(kind, slug, name, items):
    """items: list of (title, loc, posted, is_ae)"""
    ae = [i for i in items if i[3]]
    rel = [i for i in ae if S.relevant(i[0])]
    r15 = [i for i in rel if i[2] and S.age(i[2]) <= 15]
    r45 = [i for i in rel if i[2] and S.age(i[2]) <= 45]
    rows.append({"ats": kind, "board": slug, "company": name, "all": len(items), "uae": len(ae), "uae_relevant": len(rel), "le15d": len(r15), "le45d": len(r45)})
    for t, l, p, _ in ae: titles.append({"company": name, "title": t, "loc": l, "posted": p, "relevant": S.relevant(t)})
for kind, v in ub.items():
    for slug, name in v.items():
        try:
            if kind == "greenhouse":
                it = [(j["title"], (j.get("location") or {}).get("name", ""), (j.get("first_published") or j.get("updated_at") or "")[:10]) for j in S.get(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs").get("jobs", [])]
            elif kind == "lever":
                it = [(j["text"], (j.get("categories") or {}).get("location", "") or "", datetime.date.fromtimestamp(j["createdAt"] / 1000).isoformat()) for j in S.get(f"https://api.lever.co/v0/postings/{slug}?mode=json")]
            elif kind == "ashby":
                it = [(j["title"], j.get("location", "") + " " + " ".join(s.get("location", "") for s in j.get("secondaryLocations", [])), (j.get("publishedAt") or "")[:10]) for j in S.get(f"https://api.ashbyhq.com/posting-api/job-board/{slug}").get("jobs", [])]
            elif kind == "smartrecruiters":
                it, off = [], 0
                while off < 1000:
                    c = S.get(f"https://api.smartrecruiters.com/v1/companies/{slug}/postings?limit=100&offset={off}").get("content", [])
                    it += [(j["name"], ((j.get("location") or {}).get("city") or "") + " " + ("UAE" if (j.get("location") or {}).get("country") == "ae" else ""), (j.get("releasedDate") or "")[:10]) for j in c]
                    if len(c) < 100: break
                    off += 100
            else: continue
            rec(kind, slug, name, [(t, l, p, S.uae(l)) for t, l, p in it])
        except Exception as e:
            rows.append({"ats": kind, "board": slug, "company": name, "error": str(e)[:100]})
for r in rows: print(json.dumps(r))
json.dump({"rows": rows, "titles": titles}, open(S.ROOT / "docs" / "data" / "uae_diag.json", "w"), indent=0)

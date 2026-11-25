#!/usr/bin/env python3
"""Find the careers pages (Greenhouse / Lever / Ashby / SmartRecruiters / Workable) of employers that hire in the UAE,
so the Dubai section is not limited to US companies with a Dubai office. Run from GitHub Actions ("Discover UAE careers pages").
Writes scraper/uae_boards.json  {"greenhouse": {slug: name}, "lever": {...}, "ashby": {...}, "smartrecruiters": {...}, "workable": {...}}"""
import json, re, urllib.request, concurrent.futures as cf, pathlib
ROOT = pathlib.Path(__file__).resolve().parent
UA = {"User-Agent": "Mozilla/5.0 (JobRadar personal job search)", "Accept": "application/json"}
# name -> extra slugs to try (besides the name without spaces / with hyphens)
COMPANIES = {
 "Careem": [], "Tabby": ["tabbyai", "tabby-ai"], "Tamara": ["tamaraco"], "Talabat": [], "noon": ["nooncom", "noon-com"], "Kitopi": [],
 "Property Finder": ["propertyfinder"], "Dubizzle": ["dubizzlegroup", "bayut", "dubizzle-group"], "Huspy": [], "Ziina": [], "Sarwa": [], "YAP": ["yappay"],
 "Mamo": ["mamopay"], "Stake": ["getstake"], "Pemo": [], "Qashio": [], "Alaan": [], "Fuze": ["fuzefinance"], "Baraka": ["getbaraka"], "G42": ["g42ai"],
 "Presight": ["presightai"], "Core42": [], "e&": ["eand", "etisalat"], "du": ["dutelecom", "eitc"], "Emirates NBD": ["emiratesnbd"], "Mashreq": ["mashreqbank"],
 "ADCB": [], "First Abu Dhabi Bank": ["fab", "bankfab"], "Wio Bank": ["wio", "wiobank"], "Majid Al Futtaim": ["majidalfuttaim", "maf"], "Chalhoub Group": ["chalhoub", "chalhoubgroup"],
 "Al-Futtaim": ["alfuttaim"], "Landmark Group": ["landmarkgroup"], "Aramex": [], "DP World": ["dpworld"], "Emaar": [], "Emirates": ["emiratesgroup"],
 "flydubai": [], "Etihad": ["etihadairways"], "ADNOC": [], "Mubadala": [], "Checkout.com": ["checkout", "checkoutcom"], "Deel": [], "Delivery Hero": ["deliveryhero"],
 "Deliveroo": [], "Swvl": [], "Anghami": [], "Namshi": [], "Ounass": [], "Mumzworld": [], "InstaShop": ["instashop"], "Calo": ["caloapp"], "Lean Technologies": ["leantech", "leantechnologies"],
 "Tarabut": ["tarabutgateway"], "NymCard": ["nymcard"], "Network International": ["networkinternational", "network"], "Astra Tech": ["astratech", "botim"], "Bayzat": [],
 "Zbooni": [], "Yalla Group": ["yalla"], "Fenix": ["fenixgames"], "Dubai Holding": ["dubaiholding"], "Kearney": [], "Oliver Wyman": ["oliverwyman"], "Careem Pay": ["careempay"],
 "Hala": [], "Washmen": [], "Justlife": [], "Eyewa": [], "Sary": [], "Trukker": [], "Fresha": [], "Revolut": [], "Wise": ["transferwise"], "Binance": [], "OKX": [], "Bybit": [], "Crypto.com": ["cryptocom", "crypto"],
 "Rain": ["rainfinancial"], "CoinMENA": ["coinmena"], "Sav": [], "Zeta": [], "Bolt": [], "inDrive": ["indrive"], "Kaizen Gaming": ["kaizengaming"], "Agoda": [], "Almosafer": [], "Wego": [],
 "dnata": [], "Jumeirah": ["jumeirahgroup"], "Americana": ["americanarestaurants"], "IFFCO": [], "Unilever": [], "Nestle": [], "PepsiCo": [], "Mondelez": [], "Henkel": [],
}
def slugs(name, extra):
    n = re.sub(r"[^a-z0-9 ]", "", name.lower().replace("&", "and"))
    out = [n.replace(" ", ""), n.replace(" ", "-")] + extra
    return [x for i, x in enumerate(out) if x and x not in out[:i]]
def fetch(url, data=None):
    try:
        req = urllib.request.Request(url, data=data, headers={**UA, **({"Content-Type": "application/json"} if data else {})})
        with urllib.request.urlopen(req, timeout=15) as r: return json.loads(r.read().decode("utf-8", "ignore"))
    except Exception: return None
def probe(item):
    name, extra = item; found = {}
    for s in slugs(name, extra):
        d = fetch(f"https://boards-api.greenhouse.io/v1/boards/{s}/jobs")
        if "greenhouse" not in found and d and d.get("jobs"): found["greenhouse"] = s
        d = fetch(f"https://api.lever.co/v0/postings/{s}?mode=json&limit=1")
        if "lever" not in found and isinstance(d, list) and d: found["lever"] = s
        d = fetch(f"https://api.ashbyhq.com/posting-api/job-board/{s}")
        if "ashby" not in found and d and d.get("jobs"): found["ashby"] = s
        d = fetch(f"https://api.smartrecruiters.com/v1/companies/{s}/postings?limit=1")
        if "smartrecruiters" not in found and d and d.get("totalFound", 0) > 0: found["smartrecruiters"] = s
        if found: break
    if not found:
        for s in slugs(name, extra)[:2]:
            d = fetch(f"https://apply.workable.com/api/v3/accounts/{s}/jobs", json.dumps({"query": ""}).encode())
            if d and d.get("results"): found["workable"] = s; break
    return name, found
def main():
    out = {"greenhouse": {}, "lever": {}, "ashby": {}, "smartrecruiters": {}, "workable": {}}
    with cf.ThreadPoolExecutor(16) as ex:
        for name, found in ex.map(probe, COMPANIES.items()):
            print(name, "->", found or "not found")
            for k, s in found.items(): out[k][s] = name
    json.dump(out, open(ROOT / "uae_boards.json", "w"), indent=0)
    print({k: len(v) for k, v in out.items()})
if __name__ == "__main__":
    main()

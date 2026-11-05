"""Regression tests: every job the candidate reported as wrongly shown/hidden. Runs before each scrape;
if any fails, the workflow stops and the site keeps the last good list."""
import pathlib, sys
src = (pathlib.Path(__file__).parent / "scrape.py").read_text()
ns = {"__name__": "rules_test", "__file__": str(pathlib.Path(__file__).parent / "scrape.py")}; exec(src, ns)
Y, D, NS, TP, DOM, ENG, REL = ns["years_required"], ns["degree_problem"], ns["no_sponsorship"], ns["timing_problem"], ns["domain_problem"], ns["engineering_problem"], ns["relevant"]
CASES = [
 ("years", "State Street: Strong experience (6 + years) in Product Analysis.", 6),
 ("years", "NVIDIA: for more than 25 years. What we need to see: * 8+ years in management consulting at a strategy firm.", 8),
 ("years", "Vercel: About you: 8+ years in Sales Strategy & Operations, Revenue Operations, or GTM Strategy at a high-growth company, with SQL preferred; able to", 8),
 ("years", "Centene: 2+ years of experience working with large databases, data verification.", 2),
 ("years", "2+ years required. 5+ years in consulting preferred.", 2),
 ("years", "Requirements: 2+ years of SQL. Preferred Qualifications: 5+ years in finance.", 2),
 ("years", "Unum: Master's is preferred 4 years of professional experience or equivalent relevant work experience preferred", None),
 ("years", "For over 100 years we have served clients. 1+ years in analytics.", 1),
 ("years", "Minimum of 5 years experience in FP&A.", 5),
 ("years", "At least five years of relevant experience.", 5),
 ("years", "Turn/River: Qualifications * 2-4 years of experience in SaaS FP&A or strategic finance.", 4),
 ("years", "1-3 years of experience in analytics.", 1),
 ("years", "2-3 years of SQL experience.", 2),
 ("years", "0-2 years of experience; new grads welcome.", 0),
 ("domain", "2-4 years of experience in technology investment banking or strategy consulting with software clients", True),
 ("domain", "Jerry: 1+ year of experience at a consulting firm, bank or tech company.", False),
 ("domain", "3+ years in management consulting or investment banking required.", True),
 ("domain", "2+ years of experience in analytics, consulting or a related analytical role.", False),
 ("domain", "Preferred qualifications: 2+ years in investment banking.", False),
 ("title_ok", "AI Research Resident (Algorithms Codesign)", False),
 ("title_ok", "AI/ML Researcher", False),
 ("title_ok", "Research Analyst - Oil & Chemicals", True),
 ("title_ok", "AI Analyst", True),
 ("title_ok", "Military SkillBridge – Social Impact Data & Insights Analyst", False),
 ("eng", "Normal Computing: Strong Python skills, plus some experience with a systems language (C++, Rust, or similar); validate ideas against our simulators and FPGA prototypes and against silicon", True),
 ("eng", "Data Analyst: SQL, Python, Tableau; build dashboards for leadership.", False),
 ("degree", "Flagship: REQUIRED QUALIFICATIONS PhD in biomedical engineering, physiology, or a related field, or an MD/PhD PREFERRED QUALIFICATIONS Published work", True),
 ("degree", "Requirements: Master's or PhD in Statistics, Computer Science or related field.", False),
 ("degree", "Requirements: Bachelor's degree. Preferred Qualifications: PhD in Economics.", False),
 ("degree", "Qualifications: PhD in a quantitative field or equivalent experience.", False),
 ("degree", "Requirements: Active CPA license required.", True),
 ("degree", "Preferred qualifications: active CPA license.", False),
 ("sponsor", "Centene: Must be authorized to work in the U.S. without the need for employment-based visa sponsorship now or in the future. Sponsorship and future sponsorship are not available for this opportunity, including H-1B, F-1, OPT, or CPT.", True),
 ("sponsor", "iHeartMedia: Benefits: Employer sponsored medical, dental and vision with a variety of coverage options. No relocation.", False),
 ("sponsor", "We consider all qualified applicants without regard to race, citizenship, immigration status or national origin.", False),
 ("sponsor", "You may opt out of marketing emails at any time; we do not share data.", False),
 ("timing", "Equifax: * Availability for full-time employment on June 7, 2027 (Spring 2027 graduation dates)", True),
 ("timing", "Candidates graduating in December 2026 are encouraged to apply.", False),
 ("timing", "We sponsor visas. Start date: February 2027. Open to students graduating between December 2026 and May 2027.", False),
]
fails = 0
for kind, text, want in CASES:
    got = {"years": lambda t: Y(t), "degree": lambda t: bool(D(t)), "sponsor": lambda t: bool(NS(t)), "timing": lambda t: bool(TP(t)), "domain": lambda t: bool(DOM(t)), "eng": lambda t: bool(ENG(t)), "title_ok": lambda t: bool(REL(t))}[kind](text)
    ok = got == want; fails += not ok
    print(("PASS " if ok else "FAIL ") + f"{kind:7} expected {want!s:5} got {got!s:5} | {text[:80]}")
print(f"{len(CASES) - fails}/{len(CASES)} rule tests passed")
sys.exit(1 if fails else 0)

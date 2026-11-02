# Job Radar

### 👉 [Open the live job board](https://rahulkulkarni2002.github.io/job-radar/)

[![Open Job Radar](https://img.shields.io/badge/Open-Job%20Radar-2457d6?style=for-the-badge)](https://rahulkulkarni2002.github.io/job-radar/)
[![Scrape jobs](https://github.com/Rahulkulkarni2002/job-radar/actions/workflows/scrape.yml/badge.svg)](https://github.com/Rahulkulkarni2002/job-radar/actions/workflows/scrape.yml)

**Quick links:** [Jobs](https://rahulkulkarni2002.github.io/job-radar/) · [Refresh now (Run workflow)](https://github.com/Rahulkulkarni2002/job-radar/actions/workflows/scrape.yml) · [Raw job data](docs/data/jobs.json)

A personal job board that refreshes itself every 3 hours, around the clock, for analytics, data, AI and finance roles.

**How it works**
- **Scraping:** a GitHub Action (`.github/workflows/scrape.yml`) checks about 2,700 company career boards on Greenhouse, Lever, Ashby, Workday and SmartRecruiters, plus company names discovered from the SimplifyJobs new-grad feed. **Only jobs confirmed on the company's own careers page are listed** (no job-board aggregators). It keeps only US roles posted in the last 15 days that ask for 3 years of experience or less.
- **Sponsorship:** the scraper reads each job description for wording such as "will not sponsor" or "visa sponsorship available". It also looks up the company's H-1B approval count in the USCIS H-1B Employer Data Hub.
- **Salary:** taken from the posting's pay range when the posting lists one.
- **Strict eligibility (F-1 → OPT from Jan 28 2027, graduating Dec 2026):**
- Dropped if **any** sentence says no visa sponsorship / no H-1B / no OPT-CPT / citizens only / clearance (equal-opportunity boilerplate ignored).
- Dropped if the JD gives a **start date outside Jan 28 – Mar 31 2027**, or a **graduation window that excludes Dec 2026** (e.g. "Spring 2027 grads").
- **Degree/licence:** dropped if a *required* qualification is a PhD/MD/doctorate with no Master's or equivalent-experience alternative, or a licence (CPA, CFA charter, RN, PE…).
- **OPT relatedness:** the job's duties must clearly be Business Analytics work (data analysis, statistics, forecasting, BI, ML, reporting/insights). Purely operational roles are dropped. Part-time/temp/adjunct roles are dropped (OPT needs ≥ 20 h/week). Contract roles are flagged (STEM OPT needs a W-2 employer enrolled in E-Verify).
- Kept only if your skills cover **≥ 80%** of the JD's hard skills, and ≤ 3 years required.
- **Website:** `docs/` is served by GitHub Pages and includes a **Jobs** tab and an **ATS** tab.
- **Privacy:** your resume is read only inside your browser and is never uploaded or saved to this repo. Your chance % and ATS score are calculated on your own device.

**Setup**
1. Settings → Pages → Source: *Deploy from a branch* → `main` / `docs`.
2. Actions → *Scrape jobs* → **Run workflow**, for the first run.
3. Open `https://<username>.github.io/<repo>/`.

**Note:** the chance % is a rough estimate. It starts from typical callback rates for cold applications and adjusts for ATS match, how fresh the posting is, sponsorship, and the experience required.

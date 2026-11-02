# Job Radar

A personal job board that refreshes itself every 3 hours, around the clock, for analytics, data, AI and finance roles.

**How it works**
- **Scraping:** a GitHub Action (`.github/workflows/scrape.yml`) checks about 2,700 company career boards on Greenhouse, Lever, Ashby, Workday and SmartRecruiters, plus the SimplifyJobs new-grad feed. It keeps only US roles posted in the last 15 days that ask for 3 years of experience or less.
- **Sponsorship:** the scraper reads each job description for wording such as "will not sponsor" or "visa sponsorship available". It also looks up the company's H-1B approval count in the USCIS H-1B Employer Data Hub.
- **Salary:** taken from the posting's pay range when the posting lists one.
- **Website:** `docs/` is served by GitHub Pages and includes a **Jobs** tab and an **ATS** tab.
- **Privacy:** your resume is read only inside your browser and is never uploaded or saved to this repo. Your chance % and ATS score are calculated on your own device.

**Setup**
1. Settings → Pages → Source: *Deploy from a branch* → `main` / `docs`.
2. Actions → *Scrape jobs* → **Run workflow**, for the first run.
3. Open `https://<username>.github.io/<repo>/`.

**Note:** the chance % is a rough estimate. It starts from typical callback rates for cold applications and adjusts for ATS match, how fresh the posting is, sponsorship, and the experience required.

"""Which of a job's gap skills are REQUIRED (not 'preferred / nice to have / a plus')?
A job is removed from the list when it requires a skill outside the candidate's confirmed set (see SKILLS.md)."""
import re

# workplace tools/terms that are mentioned as 'required' everywhere but learned in days - listed, never a reason to drop
SOFT_GAPS = {"powerpoint", "agile", "jira", "confluence", "smartsheet", "sharepoint", "uat", "compliance",
             "requirements gathering", "user stories", "six sigma"}
# close equivalents that are concepts he has practised (not a specific product) - fine even when required
CONCEPT_OK = {"optimization", "linear programming", "simulation", "variance analysis", "financial modeling", "fp&a", "p&l",
              "product analytics", "funnel analysis", "attribution", "inventory", "supply chain", "data governance"}
PREF_WORDS = r"prefer|nice[- ]to[- ]have|a plus|\bplus\b|bonus|ideally|desired|familiarity|exposure to|is helpful|helpful|good to have|not required"

DUTY_HDR = r"responsibilities|what you('ll| will) do|in this role|the role|about the (role|job|team)|day[- ]to[- ]day|your impact|you will:|key duties|job description|position summary|overview"
REQ_HDR2 = r"(basic|minimum|required) qualifications|qualifications|requirements|what you('ll)? (need|bring)|who you are|you have|about you|skills (and|&) experience|education and experience|knowledge,? skills"
PREF_HDR2 = r"preferred (qualifications|skills|experience)|nice[- ]to[- ]haves?|bonus|pluses|what (would|could|will) set you apart"
MINE = r"\b(python|sql|tableau|snowflake|databricks|excel|spark|pyspark|hadoop|hive|etl|elt|llms?|large language models?|chatgpt|claude|ai tools|optimization|forecasting|machine learning|recommendation|statistics)\b"

def _where(t, pos):
    """Which section is pos in: 'req' | 'pref' | 'duty' | None (closest heading before it)."""
    before = t[max(0, pos - 3000):pos]; best, kind = -1, None
    for k, rx in (("duty", DUTY_HDR), ("req", REQ_HDR2), ("pref", PREF_HDR2)):
        for m in re.finditer(rx, before):
            if re.search(r"\b(the|all|of|any|these|our|meet|if)\s+$", before[max(0, m.start() - 20):m.start()]): continue   # "bonus points IF you have" is not a requirements heading
            if m.start() >= best: best, kind = m.start(), k
    return kind

def required_gaps(jd, gaps, close, term_rx, section_is_preferred):
    """gaps: skills he lacks; close: [(skill, equivalent)]. Returns sorted list of skills the JD REQUIRES that he lacks."""
    t = re.sub(r"\s+", " ", (jd or "").lower())
    need = set(gaps) - SOFT_GAPS
    need |= {k for k, _ in close} - CONCEPT_OK          # a required Power BI / BigQuery / R is still a gap even if he has the cousin tool
    out = []
    for k in sorted(need):
        rx = term_rx.get(k)
        if rx is None: continue
        hits = list(rx.finditer(t))
        if not hits: continue
        required = False
        for m in hits:
            where = _where(t, m.start())
            if where in ("pref", "duty"): continue                       # duties ("you'll connect Salesforce") and nice-to-haves don't count
            if section_is_preferred(t, m.start()): continue
            seg = re.split(r"[.;•·]|\s\*\s|\s-\s", t[max(0, m.start() - 120):m.start()])[-1] + " " + re.split(r"[.;•·]|\s\*\s", t[m.end():m.end() + 100])[0]
            if re.search(PREF_WORDS, seg): continue
            # listed as one option among tools he has ("Tableau, Power BI or similar", "Python or R")
            if re.search(r"\b(or|and/or|e\.g\.|such as|like|similar|equivalent|any of|one or more|etc)\b", seg) and re.search(MINE, seg): continue   # one option among things he has
            if re.search(r"\b(utilize|use|using|leverage|leveraging|tools? (like|such as))\b", seg) and re.search(MINE, seg) and "," in seg: continue   # tool list in a duty sentence that includes his tools
            if where is None and not re.search(r"experience (with|in|using)|proficien|knowledge of|required|must|expertise", seg): continue
            required = True; break
        if required: out.append(k)
    return out

import random
import pandas as pd


# =========================================================
# RANDOMIZER TOGGLE
# Set to False to always use the first (original) wording.
# Set to True to pick varied phrasing on each prediction.
# Removing this flag entirely: set _RANDOMIZE = False below.
# =========================================================

_RANDOMIZE = True


def _pick(options):
    """Return a random element from options if randomizer is on, else the first."""
    if _RANDOMIZE and len(options) > 1:
        return random.choice(options)
    return options[0]


# =========================================================
# DOMAIN DETECTION
# =========================================================

DOMAIN_KEYWORDS = {
    "ml_ai": [
        "machine learning", "ml ", "mlops", "deep learning",
        "nlp", "computer vision", "vision", "ai ",
        "ai-", "ai_", "research scientist", "applied scientist",
        "machine learning scientist", "machine learning engineer",
        "ml engineer", "ml developer", "ml researcher"
    ],
    "data_eng": [
        "data engineer", "etl", "pipeline", "big data",
        "data infrastructure", "data architect", "cloud data",
        "database engineer", "data devops", "etl developer", "etl engineer"
    ],
    "analytics": [
        "analyst", "analytics", "bi", "business intelligence",
        "dashboard", "reporting", "insight"
    ],
    "scientist": [
        "data scientist", "data science"
    ],
}


def detect_domain_from_title(job_title):
    if not isinstance(job_title, str):
        return "other"

    title = f" {job_title.lower()} "

    if any(kw in title for kw in DOMAIN_KEYWORDS["ml_ai"]):
        return "ml_ai"
    if any(kw in title for kw in DOMAIN_KEYWORDS["analytics"]):
        return "analytics"
    if any(kw in title for kw in DOMAIN_KEYWORDS["data_eng"]):
        return "data_eng"
    if any(kw in title for kw in DOMAIN_KEYWORDS["scientist"]):
        return "scientist"

    return "other"


# =========================================================
# ROLE CLASSIFICATION
# =========================================================

DOMAIN_TO_ROLE = {
    "ml_ai": "Machine Learning / AI",
    "data_eng": "Data Engineering",
    "analytics": "Analytics",
    "scientist": "Data Science",
}


def classify_role_app2(domain, is_mgmt, is_exec):
    if is_mgmt:
        return "Management"
    return DOMAIN_TO_ROLE.get(domain, "Other")


# =========================================================
# MARKET TYPE
# =========================================================

MIN_SAMPLE = 15


def compute_market_type(job_title, company_location, experience_label, domain, prediction, df_app2):

    if "(" in company_location:
        company_location = company_location.split("(")[-1].replace(")", "").strip()

    EXP_MAP = {
        "Entry Level": "EN",
        "Mid Level": "MI",
        "Senior Level": "SE",
        "Executive Level": "EX"
    }

    exp_code = EXP_MAP.get(experience_label)

    title_mask = df_app2["job_title"] == job_title
    loc_mask = df_app2["company_location"] == company_location
    exp_mask = df_app2["experience_level"] == exp_code

    domain_mask = (
        df_app2["job_title"].str.lower().str.contains(domain.replace("_", " "), na=False)
        if domain != "other" else pd.Series(False, index=df_app2.index)
    )

    fallbacks = [
        df_app2[title_mask & loc_mask & exp_mask],
        df_app2[title_mask & exp_mask],
        df_app2[loc_mask & domain_mask & exp_mask],
        df_app2[domain_mask & exp_mask],
    ]

    for subset in fallbacks:
        if len(subset) >= MIN_SAMPLE:
            avg = subset["salary_in_usd"].mean()
            return "success" if prediction >= avg else "warning"

    return "info"


# =========================================================
# RECOMMENDATION ENGINE
# Each slot is a list of phrasings. _pick() selects one.
# The list structure is what enables variety — never remove
# the first element of any list (it is the original wording).
# =========================================================

# --- Base recommendations per experience level ---
# Each level: list of 3 slots, each slot is a list of phrasings.

BASE_RECS_POOLS = {
    "Entry Level": [
        [
            "Build strong fundamentals in your domain",
            "Strengthen your core technical foundations before branching out",
            "Invest time in mastering the basics of your field thoroughly",
            "Prioritise depth in foundational skills before chasing specialisation",
        ],
        [
            "Work on hands-on projects",
            "Build practical experience through real-world or personal projects",
            "Apply what you learn immediately through side projects or open-source work",
            "Supplement theoretical knowledge with tangible, hands-on deliverables",
        ],
        [
            "Create a strong portfolio (GitHub / real work)",
            "Document your work publicly — a visible portfolio accelerates early career growth",
            "Build a GitHub profile or portfolio site that demonstrates your capabilities",
            "Make your work discoverable: strong portfolios often speak louder than credentials at this stage",
        ],
    ],
    "Mid Level": [
        [
            "Improve real-world problem solving",
            "Seek out ambiguous, complex problems where there is no obvious playbook",
            "Push beyond routine tasks and take on challenges that stretch your capabilities",
            "Focus on solving problems that have measurable business impact, not just technical elegance",
        ],
        [
            "Start specialization in your domain",
            "Begin carving out a niche — generalists plateau; specialists grow faster at mid-level",
            "Identify the intersection of high demand and your strengths, and go deep there",
            "Develop a distinct area of expertise that makes you the go-to person for specific problems",
        ],
        [
            "Take ownership of projects",
            "Volunteer to lead end-to-end on a project, not just contribute to parts of it",
            "Treat at least one initiative as fully yours — own the outcomes, not just the tasks",
            "Move from execution to ownership: propose, plan, deliver, and debrief with minimal supervision",
        ],
    ],
    "Senior Level": [
        [
            "Focus on system design and scalability",
            "Think beyond features — invest in architecture, reliability, and long-term maintainability",
            "Develop a systems-thinking mindset: consider scale, failure modes, and cross-team dependencies",
            "Shift your lens from solving today's problem to designing solutions that survive growth",
        ],
        [
            "Lead major projects",
            "Take point on initiatives with cross-functional visibility and real organisational risk",
            "Seek projects where your decisions shape the direction of the team or product",
            "Drive a project from ambiguous brief to delivered outcome, coordinating across teams",
        ],
        [
            "Mentor juniors",
            "Dedicate consistent time to helping junior colleagues grow — it sharpens your own thinking",
            "Structured mentorship is a senior multiplier: your output scales through the people you develop",
            "Invest in the growth of those around you — mentoring is both a leadership signal and a force multiplier",
        ],
    ],
    "Executive Level": [
        [
            "Focus on business strategy and decisions",
            "Align every technical decision to measurable business outcomes and company direction",
            "Develop a strong grasp of business model dynamics — how your domain creates and protects value",
            "Shift from managing execution to shaping strategy: the questions you ask matter as much as the answers",
        ],
        [
            "Align tech with business goals",
            "Build a shared language between your technical teams and business stakeholders",
            "Drive decisions that bridge engineering feasibility with commercial and strategic priorities",
            "Ensure your team's roadmap is always traceable to tangible business outcomes",
        ],
        [
            "Drive organizational impact",
            "Measure your contribution at the organisational level — headcount, cost, revenue, or risk",
            "Think in systems: your leverage at this level comes from how you design teams, processes, and incentives",
            "Pursue initiatives whose impact is felt company-wide, not just within your immediate function",
        ],
    ],
}

# --- Role-specific tips ---
# Same structure: first item in each list is the original wording.

ROLE_RECS_POOLS = {
    "Entry Level": {
        "Machine Learning / AI": [
            "Focus on ML basics and statistics",
            "Build fluency in linear algebra, probability, and the mechanics of gradient-based learning",
            "Understand why models work before focusing on which models to use",
            "Master the fundamentals: loss functions, overfitting, and evaluation metrics before advanced architectures",
        ],
        "Data Science": [
            "Focus on EDA and statistical thinking",
            "Develop strong habits around exploratory analysis — understanding your data before modelling it",
            "Learn to ask sharp questions of data before reaching for a model",
            "Statistical intuition is a differentiator at this stage: invest in it early",
        ],
        "Data Engineering": [
            "Learn SQL and data pipelines",
            "Build solid SQL skills and understand how data moves from source to destination reliably",
            "Learn the fundamentals of ETL design and data quality management",
            "Focus on writing clean, testable pipeline code and understanding storage trade-offs",
        ],
        "Analytics": [
            "Learn SQL, Excel, and visualization tools",
            "Master SQL and at least one visualisation tool — these are the foundation of analytical work",
            "Build strong data storytelling skills alongside technical querying ability",
            "Learn to present findings clearly: analytics impact comes from communication, not just analysis",
        ],
    },
    "Mid Level": {
        "Machine Learning / AI": [
            "Learn model optimization and deployment",
            "Bridge the gap between notebook experiments and production-grade ML systems",
            "Develop skills in model monitoring, retraining pipelines, and serving infrastructure",
            "Move beyond training accuracy — focus on latency, drift detection, and reproducibility",
        ],
        "Data Engineering": [
            "Work with Spark, Kafka, distributed systems",
            "Get hands-on with distributed compute and streaming data at scale",
            "Understand the trade-offs in distributed storage and compute: when to use which tool",
            "Build production experience with orchestration tools like Airflow and real-time systems like Kafka",
        ],
        "Analytics": [
            "Improve dashboards and business insights",
            "Go beyond building dashboards — help stakeholders understand what the numbers mean",
            "Focus on decision-quality insights, not just report delivery",
            "Develop the ability to turn analytical findings into concrete recommendations for decision-makers",
        ],
    },
    "Senior Level": {
        "Machine Learning / AI": [
            "Work on production ML and MLOps",
            "Own the full ML lifecycle: from feature engineering through deployment and ongoing monitoring",
            "Invest in MLOps maturity — reproducibility, automated retraining, and robust observability",
            "Champion best practices that make your team's models reliable and maintainable in production",
        ],
        "Data Engineering": [
            "Design large-scale data architecture",
            "Think at the platform level — design data infrastructure that scales with the business",
            "Champion data quality and governance across the pipelines you own",
            "Move from building pipelines to designing the standards and patterns your team builds on",
        ],
        "Management": [
            "Improve leadership and team management",
            "Invest in developing people, not just delivering projects — your leverage is through your team",
            "Build psychological safety and a culture of constructive feedback within your team",
            "Learn to delegate effectively and measure success by what your team delivers without you",
        ],
        "Analytics": [
            "Drive business decisions using data insights",
            "Position yourself as a strategic partner to business stakeholders, not just an analyst",
            "Focus on influencing decisions, not just answering questions with data",
            "Build the credibility to push back on bad questions and reframe problems with evidence",
        ],
    },
    "Executive Level": {
        "Management": [
            "Strengthen leadership and vision",
            "Develop a clear, communicable vision that your organisation can execute against",
            "Leadership at this level is about clarity of direction and consistency of values",
            "Invest in your ability to attract, retain, and develop exceptional people",
        ],
        "Machine Learning / AI": [
            "Define AI strategy",
            "Build an AI strategy that is grounded in real business problems, not technology for its own sake",
            "Identify where AI creates durable competitive advantage versus where it is table stakes",
            "Lead the organisation's thinking on responsible AI — risk, fairness, and long-term trust",
        ],
        "Data Engineering": [
            "Oversee data infrastructure decisions",
            "Champion a data platform strategy that balances innovation speed with reliability and governance",
            "Ensure your organisation's data infrastructure is treated as a strategic asset, not a utility",
            "Drive decisions on build vs. buy, open-source vs. managed, and centralised vs. federated architecture",
        ],
        "Analytics": [
            "Drive business strategy",
            "Use data and analytical capability as a source of competitive advantage, not just reporting",
            "Build an analytics culture where evidence-based decision-making is the default, not the exception",
            "Position analytics as a strategic function: connect insights directly to revenue, cost, and risk outcomes",
        ],
        "Data Science": [
            "Lead advanced analytics initiatives",
            "Champion initiatives that use modelling and experimentation to drive measurable business outcomes",
            "Set the standard for analytical rigour and responsible use of models across the organisation",
            "Bridge data science capability and executive decision-making — translate model outputs into strategy",
        ],
    },
}

# --- Market-position tips ---

MARKET_RECS_POOLS = {
    "warning": [
        "Upskilling or role change may improve salary",
        "Your predicted salary is below the market average — targeted upskilling or a role change could close the gap",
        "Consider identifying the specific skills or credentials driving higher pay in your field and addressing those gaps",
        "A structured move — whether a new employer, a specialisation, or a promotion — is likely the fastest path to market parity",
    ],
    "success": [
        "You are well positioned — focus on growth",
        "Your salary is competitive relative to the market — now is the time to invest in your next level of impact",
        "You are tracking ahead of average for your profile — maintain momentum through continuous development",
        "Strong market positioning — use this stability as a platform to pursue higher-leverage opportunities and skills",
    ],
}


def generate_recommendations(role, experience_label, market_type):
    """
    Returns a list of recommendation strings.
    Output count: 3 (base) + 0 or 1 (role tip) + 0 or 1 (market tip) = 3 to 5 items.
    Signature unchanged.
    """
    pools = BASE_RECS_POOLS.get(experience_label)
    if pools:
        recs = [_pick(pool) for pool in pools]
    else:
        recs = [
            _pick([
                "Improve technical skills",
                "Continuously develop your technical skill set to stay competitive",
            ]),
            _pick([
                "Work on real-world projects",
                "Seek out practical experience that translates directly to professional value",
            ]),
        ]

    role_pool = ROLE_RECS_POOLS.get(experience_label, {}).get(role)
    if role_pool:
        recs.append(_pick(role_pool))

    market_pool = MARKET_RECS_POOLS.get(market_type)
    if market_pool:
        recs.append(_pick(market_pool))

    return recs


# =========================================================
# APP 2 — FINAL FUNCTION
# Signature unchanged.
# =========================================================

def generate_recommendations_app2(input_dict, prediction, df_app2, title_features_func):

    job_title = input_dict["Job Title"]
    experience_label = input_dict["Experience Level"]
    company_location = input_dict["Company Location"]

    _, _, exec_, is_mgmt, _ = title_features_func(job_title)

    domain = detect_domain_from_title(job_title)
    role = classify_role_app2(domain, is_mgmt, exec_)

    market_type = compute_market_type(
        job_title,
        company_location,
        experience_label,
        domain,
        prediction,
        df_app2
    )

    return generate_recommendations(role, experience_label, market_type)


# =========================================================
# APP 1 — JOB GROUP CLASSIFICATION
# =========================================================

def classify_job_group_app1(job_title):
    if not isinstance(job_title, str):
        return "Operations"

    t = job_title.lower()

    if any(x in t for x in ["engineer", "developer", "data", "scientist", "analyst", "architect", "it", "network"]):
        return "Tech"
    elif any(x in t for x in ["manager", "director", "vp", "chief", "ceo"]):
        return "Management"
    elif any(x in t for x in ["marketing", "sales", "brand", "advertising"]):
        return "Marketing_Sales"
    elif any(x in t for x in ["hr", "human resources", "recruit"]):
        return "HR"
    elif any(x in t for x in ["finance", "financial", "account"]):
        return "Finance"
    elif any(x in t for x in ["designer", "ux", "graphic", "creative"]):
        return "Design"
    else:
        return "Operations"


def get_experience_category_app1(experience):
    if experience <= 2:
        return "Entry"
    elif experience <= 5:
        return "Mid"
    else:
        return "Senior"


# Base recs pools — App 1 (3 slots, each a list of phrasings)

APP1_BASE_RECS_POOLS = {
    "Entry": [
        [
            "Focus on building strong foundational skills",
            "Invest in mastering core concepts before pursuing advanced specialisations",
            "Prioritise depth in fundamentals — they compound in value over a career",
            "Strong foundations accelerate everything that comes after: treat them as a long-term investment",
        ],
        [
            "Work on real-world projects",
            "Practical experience closes the gap between theoretical knowledge and professional readiness faster than any course",
            "Seek opportunities to apply your learning in real contexts, even outside formal employment",
            "Projects with real constraints and stakeholders teach things that textbooks and tutorials cannot",
        ],
        [
            "Explore different roles",
            "Experiment broadly early on — the career directions that suit you best often reveal themselves through exposure",
            "Use this stage to sample different functions and industries before committing to a specialisation",
            "Early breadth makes later depth more informed — explore before you optimise",
        ],
    ],
    "Mid": [
        [
            "Strengthen problem-solving",
            "Develop the ability to decompose complex, ambiguous problems into tractable steps",
            "Challenge yourself with problems that do not have obvious solutions or established playbooks",
            "Problem-solving at mid-level means navigating trade-offs, not just applying known techniques",
        ],
        [
            "Take ownership",
            "Move from completing tasks to owning outcomes — the difference defines who advances",
            "Treat at least one initiative as fully yours from brief to delivery to retrospective",
            "Ownership means caring about the result, not just the process: follow through even when it is uncomfortable",
        ],
        [
            "Build profile",
            "Make your work visible: internal recognition and external reputation both compound over time",
            "Write, speak, or publish in your domain — it establishes credibility and opens unexpected doors",
            "A strong professional profile is not vanity; it is leverage in negotiation and opportunity access",
        ],
    ],
    "Senior": [
        [
            "Focus on leadership",
            "Your impact at this stage is multiplied through others — invest in your ability to lead and influence",
            "Develop the skills to align, motivate, and develop a team, not just deliver individual work",
            "Leadership is a discipline: study it deliberately rather than assuming it comes naturally with seniority",
        ],
        [
            "Mentor juniors",
            "Teaching what you know accelerates both your team's growth and your own clarity of thinking",
            "Mentoring is a high-leverage senior activity: your output scales through the people you develop",
            "Invest time in structured mentorship — it builds loyalty, knowledge transfer, and your reputation as a leader",
        ],
        [
            "Drive impact",
            "At senior level, ambiguity is the job — seek out the problems with the highest organisational stakes",
            "Look for opportunities where your decisions shape the direction of a product, team, or business unit",
            "Senior contribution means identifying what matters most, not just executing what is asked of you",
        ],
    ],
}

# Role-specific tips — App 1

APP1_ROLE_RECS_POOLS = {
    "Tech": [
        "Improve technical depth and stay updated with new technologies",
        "Pursue depth in your core stack while maintaining awareness of adjacent technologies shaping your field",
        "Balance mastery of existing tools with deliberate exploration of emerging ones",
        "Technical credibility at senior levels requires both depth and the ability to evaluate new approaches critically",
    ],
    "Management": [
        "Strengthen leadership and team management skills",
        "Great managers create clarity, remove obstacles, and develop people — invest in all three deliberately",
        "Learn to deliver honest, constructive feedback and to have difficult conversations without damaging relationships",
        "Your team's performance is your output: invest as seriously in their growth as in your own",
    ],
    "Marketing_Sales": [
        "Improve communication and market understanding",
        "Deepen your understanding of customer psychology and buying behaviour — it sharpens every other skill in this domain",
        "Strong communicators in sales and marketing understand their audience's goals as well as their own",
        "Build fluency in data-driven decision-making: the best commercial professionals combine instinct with evidence",
    ],
    "HR": [
        "Focus on people management and organizational development",
        "Invest in understanding organisational behaviour and the systems that shape how people perform and stay",
        "HR professionals who understand business strategy — not just people processes — drive the most value",
        "Build skills in change management and organisational design: they are the highest-leverage HR capabilities",
    ],
    "Finance": [
        "Enhance financial analysis and strategic planning skills",
        "Move beyond reporting: develop the ability to model scenarios and communicate the implications to non-finance audiences",
        "Strategic finance is about informing decisions, not just tracking outcomes — develop that forward-looking lens",
        "Build proficiency in financial modelling and the ability to translate numbers into clear business narratives",
    ],
    "Design": [
        "Build strong design thinking and creativity",
        "Great design solves real problems for real people — keep user empathy at the centre of your practice",
        "Develop fluency in both the craft of design and the ability to articulate design decisions in business terms",
        "Creativity is trainable: build systematic habits of observation, ideation, and critique to sustain it",
    ],
    "Operations": [
        "Improve process efficiency and execution skills",
        "Operations excellence comes from relentless attention to where time, money, and effort are wasted — and fixing it",
        "Build skills in process mapping, data-driven root cause analysis, and change implementation",
        "The best operators combine executional discipline with the curiosity to question whether the process itself is right",
    ],
}

# Senior tip pool — App 1

APP1_SENIOR_TIP_POOL = [
    "Negotiate for leadership responsibilities and higher compensation",
    "Senior roles carry leverage in compensation discussions — research market rates and negotiate with data",
    "Use your seniority as a platform: pursue responsibilities that reflect your level and ensure your pay does too",
    "Do not leave compensation to chance — senior professionals who negotiate consistently earn more than those who do not",
]


def generate_recommendations_app1(input_dict):
    """
    Signature unchanged.
    Returns a list of recommendation strings.
    Output count: 3 (base) + 1 (role tip) + 0 or 1 (senior tip) = 4 to 5 items.
    """
    job_title = input_dict["Job Title"]
    experience = input_dict["Years of Experience"]
    senior = 1 if input_dict["Senior Position"] == "Yes" else 0

    job_group = classify_job_group_app1(job_title)
    exp_category = get_experience_category_app1(experience)

    pools = APP1_BASE_RECS_POOLS.get(exp_category, [
        ["Improve technical skills", "Continuously develop your skills to stay competitive in your field"],
        ["Work on real-world projects", "Seek practical experience that directly translates to professional value"],
    ])
    recs = [_pick(pool) for pool in pools]

    role_pool = APP1_ROLE_RECS_POOLS.get(job_group)
    if role_pool:
        recs.append(_pick(role_pool))

    if senior == 1:
        recs.append(_pick(APP1_SENIOR_TIP_POOL))

    return recs


# =========================================================
# RENDER
# =========================================================

def render_recommendations(recommendations):
    import streamlit as st

    if not recommendations:
        st.info("No recommendations available.")
        return

    for r in recommendations:
        st.markdown(f"- {r}")
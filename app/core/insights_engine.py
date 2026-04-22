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
# DOMAIN DETECTION (DATASET-ALIGNED)
# =========================================================

DOMAIN_KEYWORDS = {
    "ml_ai": [
        "machine learning",
        "ml ",
        "mlops",
        "deep learning",
        "nlp",
        "computer vision",
        "vision",
        "ai ",
        "ai-",
        "ai_",
        "research scientist",
        "applied scientist",
        "machine learning scientist",
        "machine learning engineer",
        "ml engineer",
        "ml developer",
        "ml researcher"
    ],

    "data_eng": [
        "data engineer",
        "etl",
        "pipeline",
        "big data",
        "data infrastructure",
        "data architect",
        "cloud data",
        "database engineer",
        "data devops",
        "etl developer",
        "etl engineer"
    ],

    "analytics": [
        "analyst",
        "analytics",
        "bi",
        "business intelligence",
        "dashboard",
        "reporting",
        "insight"
    ],

    "scientist": [
        "data scientist",
        "data science"
    ],
}


def detect_domain_from_title(job_title):
    if not isinstance(job_title, str):
        return "other"

    title = f" {job_title.lower()} "

    # PRIORITY ORDER

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
    "ml_ai":     "Machine Learning / AI",
    "data_eng":  "Data Engineering",
    "analytics": "Analytics",
    "scientist": "Data Science",
}


def classify_role_app2(domain, is_mgmt, is_exec):
    # Only override if actually management
    if is_mgmt:
        return "Management"

    return DOMAIN_TO_ROLE.get(domain, "Other")


# =========================================================
# MARKET COMPARISON
# =========================================================

MIN_SAMPLE = 15


def compute_market_insight(job_title, company_location, experience_label, domain, prediction, df_app2):

    # Normalize location
    if "(" in company_location:
        company_location = company_location.split("(")[-1].replace(")", "").strip()

    # Map UI labels to dataset
    EXP_MAP = {
        "Entry Level": "EN",
        "Mid Level": "MI",
        "Senior Level": "SE",
        "Executive Level": "EX"
    }

    exp_code = EXP_MAP.get(experience_label)

    title_mask = df_app2["job_title"] == job_title
    loc_mask   = df_app2["company_location"] == company_location
    exp_mask   = df_app2["experience_level"] == exp_code

    domain_mask = (
        df_app2["job_title"].str.lower().str.contains(domain.replace("_", " "), na=False)
        if domain != "other" else pd.Series(False, index=df_app2.index)
    )

    # Hierarchical fallback (experience ALWAYS included)
    fallbacks = [
        df_app2[title_mask & loc_mask & exp_mask],
        df_app2[title_mask & exp_mask],
        df_app2[loc_mask & domain_mask & exp_mask],
        df_app2[domain_mask & exp_mask],
    ]

    for subset in fallbacks:
        if len(subset) >= MIN_SAMPLE:
            avg = subset["salary_in_usd"].mean()

            if prediction >= avg:
                return (
                    "You are above the market average for this role and experience level.",
                    "success"
                )
            else:
                return (
                    "You are below the market average for this role and experience level.",
                    "warning"
                )

    return (
        "Not enough data available for reliable market comparison.",
        "info"
    )


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
            "Invest in mastering the core concepts of your field before branching into specialisations",
            "Strong foundational knowledge compounds over a career — prioritise depth over breadth early on",
            "Fundamentals outlast frameworks: build them thoroughly and they will pay dividends at every stage",
        ],
        [
            "Work on hands-on projects",
            "Apply what you learn through practical projects — real constraints teach what tutorials cannot",
            "Build tangible deliverables: projects with real objectives close the gap between knowledge and readiness",
            "Hands-on experience accelerates early career growth faster than any additional credential",
        ],
        [
            "Create a strong portfolio (GitHub / real work)",
            "Document your work publicly — a visible portfolio creates opportunities that applications alone cannot",
            "A strong GitHub profile or portfolio site makes your capabilities tangible and searchable",
            "At this stage, showing work is often more persuasive than describing it: invest in a visible body of work",
        ],
    ],
    "Mid Level": [
        [
            "Improve real-world problem solving",
            "Seek out complex, ambiguous problems where no obvious solution exists — that is where mid-level growth happens",
            "Move beyond solved problems: the most valuable skills at this stage come from navigating genuine uncertainty",
            "Challenge yourself with problems that have real stakes and no established playbook",
        ],
        [
            "Start specialization in your domain",
            "Identify the area where high demand intersects with your strengths, and go deep there",
            "Generalists plateau at mid-level; a well-chosen specialisation accelerates both growth and compensation",
            "Carve out a niche that makes you the go-to person for a specific, high-value class of problems",
        ],
        [
            "Take ownership of projects",
            "Own at least one initiative end-to-end — from proposal through delivery and retrospective",
            "Treat ownership as a mindset, not a title: take responsibility for outcomes, not just tasks",
            "The professionals who advance fastest at this level are those who treat their work as their own, not assigned",
        ],
    ],
    "Senior Level": [
        [
            "Focus on system design and scalability",
            "Shift your thinking from solving individual problems to designing systems that scale and survive growth",
            "Invest in architecture, reliability, and long-term maintainability — not just feature delivery",
            "Senior engineers and leaders are defined by the systems they leave behind, not just the problems they solved",
        ],
        [
            "Lead major projects",
            "Take point on high-visibility initiatives where your decisions have real organisational consequences",
            "Seek projects that require coordinating across teams, managing ambiguity, and delivering under scrutiny",
            "Drive initiatives from ambiguous brief to delivered outcome with minimal supervision and maximum accountability",
        ],
        [
            "Mentor juniors",
            "Teaching what you know is one of the highest-leverage activities at senior level — it scales your impact",
            "Structured mentorship builds your team's capability, your own clarity, and your reputation as a leader",
            "The best senior contributors are defined as much by who they develop as by what they personally deliver",
        ],
    ],
    "Executive Level": [
        [
            "Focus on business strategy and decisions",
            "Every technical decision should be traceable to a business outcome — make that connection explicit and consistent",
            "Develop a deep understanding of how your domain creates, protects, or erodes business value",
            "At executive level, the quality of your questions often matters more than the quality of your answers",
        ],
        [
            "Align tech with business goals",
            "Build a shared language between technical teams and business stakeholders — translation is a core executive skill",
            "Ensure your team's roadmap is always grounded in commercial and strategic priorities, not just technical ambition",
            "The best technical executives make complex capability trade-offs legible to non-technical decision-makers",
        ],
        [
            "Drive organizational impact",
            "Measure your contribution at the organisational level — revenue, cost, risk, or strategic positioning",
            "Your leverage at this level comes from how you design teams, processes, and incentive structures",
            "Pursue initiatives whose impact is felt company-wide and that leave the organisation durably stronger",
        ],
    ],
}

# --- Role-specific tips ---
# Same structure: first item in each list is the original wording.

ROLE_RECS_POOLS = {
    "Entry Level": {
        "Machine Learning / AI": [
            "Focus on ML basics and statistics",
            "Build fluency in linear algebra, probability, and the mechanics of model training before chasing frameworks",
            "Understand why models work before focusing on which models to use — first principles matter here",
            "Master core concepts: loss functions, overfitting, evaluation metrics, and bias-variance trade-off",
        ],
        "Data Science": [
            "Focus on EDA and statistical thinking",
            "Develop strong habits around exploratory analysis — understand your data before you model it",
            "Statistical intuition is a long-term differentiator: invest in it seriously at this stage",
            "Learn to ask sharp, falsifiable questions of data before reaching for a predictive model",
        ],
        "Data Engineering": [
            "Learn SQL and data pipelines",
            "Build solid SQL skills and a clear understanding of how data moves reliably from source to destination",
            "Learn the fundamentals of ETL design, data quality management, and pipeline testing",
            "Focus on writing clean, maintainable pipeline code and understanding storage system trade-offs",
        ],
        "Analytics": [
            "Learn SQL, Excel, and visualization tools",
            "Master SQL and at least one visualisation tool — these are the foundation of every analytical workflow",
            "Build strong data storytelling ability alongside querying skills: insight without communication has no impact",
            "Develop the habit of presenting findings clearly — analytical value is realised through decisions, not reports",
        ],
    },
    "Mid Level": {
        "Machine Learning / AI": [
            "Learn model optimization and deployment",
            "Bridge the gap between notebook experiments and production-grade ML systems that serve real users",
            "Develop skills in model monitoring, drift detection, retraining pipelines, and serving infrastructure",
            "Shift focus from training accuracy to real-world reliability: latency, reproducibility, and failure modes",
        ],
        "Data Engineering": [
            "Work with Spark, Kafka, distributed systems",
            "Build hands-on experience with distributed compute and streaming data at realistic scale",
            "Understand the trade-offs in distributed storage and compute: when each tool is appropriate",
            "Gain production experience with orchestration frameworks and real-time data systems",
        ],
        "Analytics": [
            "Improve dashboards and business insights",
            "Go beyond building dashboards — help stakeholders understand what the numbers actually mean",
            "Focus on decision-quality insights: the goal is better choices, not more reports",
            "Develop the ability to turn analytical findings into concrete, actionable recommendations",
        ],
    },
    "Senior Level": {
        "Machine Learning / AI": [
            "Work on production ML and MLOps",
            "Own the full ML lifecycle: from feature engineering and training through deployment and ongoing monitoring",
            "Champion MLOps maturity in your team — reproducibility, automated retraining, and robust observability",
            "Make your models reliable and maintainable in production, not just accurate in evaluation",
        ],
        "Data Engineering": [
            "Design large-scale data architecture",
            "Think at the platform level — design infrastructure that scales with the business and survives team growth",
            "Champion data quality and governance across the pipelines and systems you own",
            "Move from building pipelines to designing the standards and patterns that others in your team build on",
        ],
        "Management": [
            "Improve leadership and team management",
            "Invest in developing your people, not just delivering projects — your leverage is entirely through your team",
            "Build psychological safety and a culture of honest, constructive feedback within your team",
            "Learn to delegate meaningfully and measure success by what your team delivers, not what you personally touch",
        ],
        "Analytics": [
            "Drive business decisions using data insights",
            "Position yourself as a strategic partner to business stakeholders, not just an analytical resource",
            "Focus on influencing decisions, not just answering data questions — that is where senior analytics value lives",
            "Build the credibility and confidence to reframe bad questions and challenge assumptions with evidence",
        ],
    },
    "Executive Level": {
        "Management": [
            "Strengthen leadership and vision",
            "Develop a clear, communicable vision that your organisation can execute against with confidence",
            "Leadership at this level is about clarity of direction and consistency of values under pressure",
            "Invest in attracting, retaining, and developing exceptional people — that is your most durable output",
        ],
        "Machine Learning / AI": [
            "Define AI strategy and lead innovation initiatives",
            "Build an AI strategy grounded in real business problems, not technology pursued for its own sake",
            "Identify where AI creates durable competitive advantage versus where it is rapidly becoming table stakes",
            "Champion responsible AI across your organisation — risk governance, fairness, and long-term stakeholder trust",
        ],
        "Data Engineering": [
            "Oversee large-scale data infrastructure decisions",
            "Champion a data platform strategy that balances innovation speed with reliability, security, and governance",
            "Treat your organisation's data infrastructure as a strategic asset, not a cost centre or utility",
            "Lead decisions on build versus buy, open-source versus managed, and centralised versus federated architecture",
        ],
        "Analytics": [
            "Drive data-driven business strategy and decision making",
            "Use analytical capability as a source of strategic competitive advantage, not just operational reporting",
            "Build a culture where evidence-based decision-making is the default across the organisation",
            "Position analytics as a strategic function: connect insights directly and visibly to revenue, cost, and risk",
        ],
        "Data Science": [
            "Lead advanced analytics and modeling initiatives",
            "Champion initiatives that use modelling and rigorous experimentation to drive measurable business outcomes",
            "Set the standard for analytical rigour and responsible use of predictive models across the organisation",
            "Bridge data science capability and executive decision-making — translate complex model outputs into strategy",
        ],
    },
}

# --- Market-position tips ---

MARKET_RECS_POOLS = {
    "warning": [
        "Upskilling or role change may improve salary",
        "Your predicted salary is below the market average — targeted upskilling or a strategic role move could close the gap",
        "Identify the specific skills or credentials driving higher compensation in your field and address those gaps deliberately",
        "A structured move — new employer, a clear specialisation, or a promotion push — is often the fastest path to market parity",
    ],
    "success": [
        "You are well positioned — focus on growth",
        "Your salary is tracking above average for your profile — invest this stability in your next level of capability and impact",
        "Strong market positioning gives you negotiating leverage: use it proactively in your next review or move",
        "You are ahead of the market average — channel that advantage into pursuing higher-leverage opportunities and responsibilities",
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
                "Continuously develop your technical skill set to stay competitive in your field",
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
# MAIN FUNCTION — APP 2
# Signature unchanged.
# =========================================================

def generate_insights_app2(input_dict, prediction, df_app2, title_features_func):

    job_title        = input_dict["Job Title"]
    experience_label = input_dict["Experience Level"]
    company_location = input_dict["Company Location"]

    # mgmt detection only
    _, _, exec_, is_mgmt, _ = title_features_func(job_title)

    # domain detection
    domain = detect_domain_from_title(job_title)

    # role classification
    role = classify_role_app2(domain, is_mgmt, exec_)

    # market insight (with experience)
    market_msg, market_type = compute_market_insight(
        job_title,
        company_location,
        experience_label,
        domain,
        prediction,
        df_app2
    )

    # recommendations
    recs = generate_recommendations(role, experience_label, market_type)

    return {
        "role": role,
        "market_msg": market_msg,
        "market_type": market_type,
        #"recommendations": recs,
    }


# =========================================================
# APP 1 — JOB GROUP CLASSIFICATION (REUSED LOGIC)
# =========================================================

def classify_job_group_app1(job_title):
    if not isinstance(job_title, str):
        return "Operations"

    t = job_title.lower()

    # Marketing / Sales FIRST (to override "manager")
    if any(x in t for x in ["marketing", "sales", "brand", "advertising"]):
        return "Marketing_Sales"

    # HR
    if any(x in t for x in ["hr", "human resources", "recruit"]):
        return "HR"

    # Finance
    if any(x in t for x in ["finance", "financial", "account"]):
        return "Finance"

    # Design
    if any(x in t for x in ["designer", "ux", "graphic", "creative"]):
        return "Design"

    # Management
    if any(x in t for x in ["manager", "director", "vp", "chief", "ceo"]):
        return "Management"

    # Tech LAST
    if any(x in t for x in ["engineer", "developer", "data", "scientist", "analyst", "architect", "it", "network"]):
        return "Tech"

    return "Operations"


# =========================================================
# APP 1 — EXPERIENCE CATEGORY
# =========================================================

def get_experience_category_app1(experience):
    if experience <= 2:
        return "Entry"
    elif experience <= 5:
        return "Mid"
    else:
        return "Senior"


# =========================================================
# APP 1 — BASE RECOMMENDATIONS (pool-based)
# =========================================================

APP1_BASE_RECS_POOLS = {
    "Entry": [
        [
            "Focus on building strong foundational skills",
            "Invest in mastering core concepts before pursuing advanced specialisations",
            "Strong foundations accelerate everything that follows — treat them as a long-term career investment",
            "Depth in fundamentals compounds in value over time: prioritise them above chasing trends",
        ],
        [
            "Work on real-world projects to gain experience",
            "Apply your learning through practical projects — real constraints teach what tutorials cannot",
            "Build tangible deliverables: projects with genuine objectives close the gap between knowledge and readiness",
            "Practical experience communicates capability more effectively than credentials at this stage",
        ],
        [
            "Explore different roles to identify your strengths",
            "Use early career exposure to sample different functions before committing to a specialisation",
            "Early breadth makes later depth more informed — experiment before you optimise",
            "The career directions that suit you best often reveal themselves through exposure, not planning",
        ],
    ],
    "Mid": [
        [
            "Strengthen problem-solving and domain expertise",
            "Pursue complex, ambiguous problems where no obvious solution or playbook exists",
            "Growth at mid-level comes from navigating genuine uncertainty, not just executing known processes",
            "Challenge yourself with problems that have real stakes and require original thinking to solve",
        ],
        [
            "Take ownership of projects and responsibilities",
            "Move from completing tasks to owning outcomes — that distinction is what drives advancement",
            "Treat at least one initiative as fully yours from brief through delivery and retrospective",
            "Ownership is a mindset: take responsibility for results, not just the work you were directly assigned",
        ],
        [
            "Start building a strong professional profile",
            "Make your work visible — internal recognition and external reputation both compound over time",
            "Write, speak, or publish in your domain to establish credibility and open unexpected opportunities",
            "A strong professional profile is leverage in both compensation negotiations and career transitions",
        ],
    ],
    "Senior": [
        [
            "Focus on leadership and decision-making skills",
            "Your impact at senior level is multiplied through others — invest deliberately in leadership capability",
            "Develop the skills to align, motivate, and develop a team, not just deliver excellent individual work",
            "Leadership is a discipline: study it intentionally rather than assuming it comes naturally with seniority",
        ],
        [
            "Mentor junior professionals",
            "Teaching what you know accelerates your team's growth and sharpens your own thinking simultaneously",
            "Structured mentorship is a high-leverage senior activity — your output scales through who you develop",
            "Invest time in others' growth: the best senior contributors are defined as much by who they develop as what they deliver",
        ],
        [
            "Drive impact through strategic contributions",
            "At senior level, identify and pursue the problems with the highest organisational stakes",
            "Look for opportunities where your decisions meaningfully shape the direction of a product, team, or unit",
            "Senior contribution means determining what matters most, not just executing what is asked of you",
        ],
    ],
}

# =========================================================
# APP 1 — ROLE-SPECIFIC TIPS (pool-based)
# =========================================================

APP1_ROLE_RECS_POOLS = {
    "Tech": [
        "Improve technical depth and stay updated with new technologies",
        "Pursue depth in your core stack while maintaining deliberate awareness of adjacent technologies shaping your field",
        "Balance mastery of existing tools with disciplined exploration of genuinely emerging ones",
        "Technical credibility requires both deep expertise and the ability to evaluate new approaches critically and objectively",
    ],
    "Management": [
        "Strengthen leadership and team management skills",
        "Great managers create clarity, remove obstacles, and develop people — invest in all three with equal intention",
        "Learn to deliver honest, constructive feedback and navigate difficult conversations without damaging relationships",
        "Your team's performance is your output at this level: invest as seriously in their development as in your own",
    ],
    "Marketing_Sales": [
        "Improve communication and market understanding",
        "Deepen your understanding of customer psychology and decision-making — it sharpens every commercial skill you have",
        "The best commercial professionals combine sharp instinct with evidence-based decision-making: develop both",
        "Build fluency in data-driven analysis alongside your communication skills — it is increasingly a baseline expectation",
    ],
    "HR": [
        "Focus on people management and organizational development",
        "Invest in understanding organisational behaviour and the systems that shape how people perform and stay",
        "HR professionals who understand business strategy — not just people processes — drive the most organisational value",
        "Build skills in change management and organisational design: they are consistently the highest-leverage HR capabilities",
    ],
    "Finance": [
        "Enhance financial analysis and strategic planning skills",
        "Move beyond reporting: develop the ability to model scenarios and communicate implications to non-finance audiences clearly",
        "Strategic finance is about informing forward-looking decisions, not just tracking historical outcomes",
        "Build proficiency in financial modelling and the ability to translate numerical findings into clear business narratives",
    ],
    "Design": [
        "Build strong design thinking and creativity",
        "Great design solves real problems for real people — keep genuine user empathy at the centre of your practice",
        "Develop fluency in both the craft of design and the ability to articulate design decisions in clear business terms",
        "Creativity is trainable: build systematic habits of observation, structured ideation, and rigorous critique",
    ],
    "Operations": [
        "Improve process efficiency and execution skills",
        "Operational excellence comes from sustained attention to where time, money, and effort are wasted — and eliminating it",
        "Build skills in process mapping, data-driven root cause analysis, and structured change implementation",
        "The best operators combine executional discipline with the curiosity to question whether each process is even the right one",
    ],
}

# =========================================================
# APP 1 — SENIOR TIP (pool-based)
# =========================================================

APP1_SENIOR_TIP_POOL = [
    "Negotiate for leadership responsibilities and higher compensation",
    "Senior roles carry real leverage in compensation discussions — research market rates and negotiate with data, not just tenure",
    "Use your seniority as a platform: actively pursue responsibilities that reflect your level, and ensure your pay does too",
    "Professionals who negotiate consistently earn significantly more over a career than those who rely on automatic progression",
]


def generate_recommendations_app1(job_group, experience_category, senior):
    """
    Signature unchanged.
    Returns a list of recommendation strings.
    Output count: 3 (base) + 1 (role tip) + 0 or 1 (senior tip) = 4 to 5 items.
    """
    pools = APP1_BASE_RECS_POOLS.get(experience_category, [
        ["Improve your skills and experience", "Continuously develop your skill set to stay competitive in your field"],
        ["Work on practical projects", "Seek practical experience that translates directly to professional value"],
    ])
    recs = [_pick(pool) for pool in pools]

    role_pool = APP1_ROLE_RECS_POOLS.get(job_group)
    if role_pool:
        recs.append(_pick(role_pool))

    if senior == 1:
        recs.append(_pick(APP1_SENIOR_TIP_POOL))

    return recs


# =========================================================
# APP 1 — MAIN FUNCTION
# Signature unchanged.
# =========================================================

def generate_insights_app1(input_dict):

    job_title = input_dict["Job Title"]
    experience = input_dict["Years of Experience"]
    senior = 1 if input_dict["Senior Position"] == "Yes" else 0

    # classification
    job_group = classify_job_group_app1(job_title)
    exp_category = get_experience_category_app1(experience)

    # recommendations
    recs = generate_recommendations_app1(job_group, exp_category, senior)

    return {
        "job_group": job_group,
        "experience_category": exp_category,
        #"recommendations": recs
    }


# =========================================================
# RENDER FUNCTION (MATCHES NEGOTIATION TIPS STYLE)
# =========================================================

def render_recommendations(recommendations):
    import streamlit as st

    if not recommendations:
        st.info("No recommendations available.")
        return

    for r in recommendations:
        st.markdown(f"- {r}")
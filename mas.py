#!/usr/bin/env python3
"""
Startup Intelligence Machine - Personal Ideation Tool v4.1
-----------------------------------------------------------
- CLI-only (no FastAPI)
- HITL (Human-in-the-Loop) breakpoints
- Rich terminal output support
- State persistence for resume capability
- Pivot notes caching
- DEBUG MODE: Visualize all AI agent conversations
"""

import os
import uuid
import asyncio
import logging
import time
import json
from typing import List, Literal, Optional, Type, Tuple, Dict, Any
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError
from google import genai
from google.genai.types import GenerateContentConfig
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, before_sleep_log

# Rich imports for beautiful debugging
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.json import JSON
from rich.table import Table
from rich.tree import Tree
from rich import box
from rich.text import Text
from rich.layout import Layout
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.markup import escape  # CRITICAL: Escape user content!

# Optional: DuckDuckGo search
try:
    from ddgs import DDGS
    DDGS_AVAILABLE = True
except ImportError:
    DDGS_AVAILABLE = False

logging.basicConfig(level=logging.WARNING, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

# Global console for debugging
console = Console()

# ==============================================================================
# CONFIGURATION
# ==============================================================================

MAX_TASK_LENGTH = 8000
DDGS_TIMEOUT = 10

def detect_tier():
    api_key = os.getenv("GEMINI_API_KEY", "")
    if "PRO" in api_key.upper() or os.getenv("GEMINI_TIER", "").lower() == "pro":
        return "pro"
    return "free"

# ==============================================================================
# KNOWLEDGE BASES (UNCHANGED - Theory Integrity Preserved)
# ==============================================================================

RESEARCHER_KB = """
=== ZERO-TO-ONE PRINCIPLES (Monopoly & Market Creation) ===

Core Distinction:
- Zero-to-One: Creating something entirely new (vertical progress). High risk, high reward, monopoly potential.
- One-to-N: Copying existing models (horizontal progress). Competes in red oceans, thin margins.

Monopoly Building Blocks (Defensibility Checklist):
When evaluating ideas, ensure at least ONE of these is present in the proposed_solution or unique_value_proposition:
1. Proprietary Technology: 10x improvement over nearest substitute (not marginal)
2. Network Effects: Product becomes more valuable as usage grows (platform dynamics)
3. Economies of Scale: Fixed costs spread over increasing volume without proportional cost growth
4. Branding: Strong cultural/identity component that commands premium pricing

Last-Mover Advantage (Timing Strategy):
- First-mover = often killed by arrows. Last-mover = learns from market mistakes, captures durable monopoly.
- Target: Small markets first (niche domination), then expand to adjacent markets. Never start with "1 percent of a large market."

The Secret Test:
- Valid ideas must rest on a "secret"-a proprietary insight that is true but that most people disagree with or haven't discovered.
- Reject ideas based on "consensus" or "market reports." Seek contrarian truths.

=== BLUE OCEAN STRATEGY (Value Innovation & Market Space) ===

Red Ocean vs. Blue Ocean:
- Red Ocean: Existing industries, known boundaries, rules of competition set, zero-sum (your gain = their loss).
- Blue Ocean: Uncontested market space, demand creation, high profit/growth potential, competition irrelevant.

Value Innovation Formula:
Simultaneous pursuit of DIFFERENTIATION + LOW COST. Never trade one for the other.

Four-Action Framework (Apply to every idea):
When designing the proposed_solution, explicitly address:
1. ELIMINATE: Which factors that the industry takes for granted should be removed? (Reduces cost)
2. REDUCE: Which factors should be reduced well below industry standard? (Reduces cost)  
3. RAISE: Which factors should be raised well above industry standard? (Creates value)
4. CREATE: Which factors should the industry never offered be created? (Creates new demand)

Non-Customer Analysis (Target Market Expansion):
Don't target existing customers. Target non-customers across three tiers:
- Tier 1 (Soon-to-be): Buy minimally, waiting to jump to better alternative
- Tier 2 (Refusing): Consciously reject current market offerings due to price/complexity/barriers
- Tier 3 (Unexplored): Never considered the market's product; distant from current thinking
Insight: Biggest growth comes from Tier 3 non-customers, not market share stealing.

Strategy Canvas Visualization:
Map industry competition on:
- X-axis: Key competing factors (price, features, quality, speed, service)
- Y-axis: Offering level (low to high)
Blue Ocean ideas show a VALUE CURVE that DIVERGES sharply from competitors (eliminating/reducing some factors while raising/creating others).

=== WHERE GOOD IDEAS COME FROM (Innovation Mechanics) ===

Slow Hunch Protocol:
- Breakthroughs incubate over months/years, not epiphanies. 
- Good ideas emerge from "collisions" of partial hunches. The Researcher should generate ideas that feel like "half-formed" opportunities ripe for combination with other domains.
- Favor ideas that allow for gradual maturation and iterative refinement over "big bang" launches.

Liquid Network Requirements:
- Ideas form in "liquid" environments: fluid, heterogeneous, cross-disciplinary, allowing serendipitous collisions.
- When proposing target_market or solution, consider: Does this connect previously separate domains or networks?
- Avoid siloed, single-industry ideas. Look for "adjacent possible"-what becomes possible when Platform A meets Industry B.

Platform/Keystone Strategy:
- Best ideas act as "keystone species"-infrastructure that enables ecosystems of downstream innovation.
- Prioritize ideas that could become platforms (enabling others to build on top) rather than point solutions.
- Stackable: Can this ride on existing platforms while becoming a platform itself?

Exaptation Principle:
- Look for ideas that repurpose existing technology/behavior for new functions (e.g., GPS from military to civilian).
- Favor "cobbled together" MVPs using existing parts over novel inventions requiring new physics.

Error as Mutation:
- Valid ideas often look like "mistakes" or anomalies to incumbents.
- If an idea seems "wrong" to industry experts but solves a real pain point, it's likely valuable.
- Embrace hybrid/contradictory concepts that violate industry orthodoxy.

=== SYNTHESIS PROTOCOL FOR IDEA GENERATION ===

Before finalizing any StartupIdea, verify it satisfies:
1. MONOPOLY POTENTIAL: Can this become the last-mover in a small market then expand? (Zero to One)
2. VALUE INNOVATION: Does it eliminate/reduce some industry standards while raising/creating others? (Blue Ocean)
3. NON-CUSTOMER FOCUS: Does it target people who currently don't buy in this category? (Blue Ocean)
4. LIQUID NETWORK: Does it connect disparate fields or enable new combinations? (Where Good Ideas Come From)
5. PLATFORM DNA: Can others build on top of this, creating network effects? (Where Good Ideas Come From)

REJECTION CRITERIA (Auto-kill these):
- "Uber for X" (One-to-N, Red Ocean)
- "AI-powered [existing tool]" without 10x improvement or new market creation
- Targets "1 percent of a $1B market" (no monopoly potential)
- Requires changing user behavior entirely (no exaptation of existing behavior)
- Competes on price alone in existing category

OUTPUT FORMAT: Generate ideas that feel like "secrets"-obvious in retrospect but contrarian in present. Focus on creating new categories, not improving existing ones.
"""

CRITIC_KB = """
=== 7 POWERS: THE DEFENSIBILITY AUDIT ===
Mission: Identify which power (if any) creates persistent differential returns. A startup without power at origination is a commodity business waiting to die.

Power Checklist (Origination Phase: <$10M revenue):
- COUNTER-POSITIONING: Does the proposed_solution require incumbents to destroy their own core business to replicate? (e.g., Netflix vs Blockbuster retail)
- CORNERED RESOURCE: Is there exclusive access to a patent, proprietary dataset, unique talent, or regulatory license that competitors cannot obtain?
- SCALE ECONOMIES: Are there massive fixed costs that collapse per-unit economics at volume (infrastructure, content, R&D)?
- NETWORK ECONOMIES: Does each additional user non-linearly increase value for all others (platform dynamics, marketplace liquidity)?
- SWITCHING COSTS: Would customers face significant financial/operational/knowledge costs to migrate away (data lock-in, integrations, trained staff)?
- BRANDING: Is there decades-long heritage potential or cultural prestige? (Answer is NO for 99% of startups-mark as absent)
- PROCESS POWER: Are there complex operational systems impossible for smaller rivals to match? (Answer is NO until $100M+ scale)

FATAL FLAW - POWER:
- If ZERO powers are present -> VERDICT: KILL. Reason: "No defensible moat; commodity offering susceptible to price war."
- If UVP relies on "better UX," "first mover," or "AI features" without Counter-positioning/Cornered Resource/Network Effects -> FATAL FLAW: Weak differentiation.

=== THE MOM TEST: PROBLEM VALIDATION ===
Mission: Detect solution bias and false positives. Most startups die building something nobody wants because they asked the wrong questions.

Problem Statement Analysis:
- PROBLEM FOCUS: Does the problem_statement describe the CUSTOMER'S LIFE (current pain, existing workarounds) or the FOUNDER'S SOLUTION (technology, features)?
- GOOD DATA SIGNS: Specific past behaviors ("I currently spend 3 hours manually..."), concrete pain metrics, evidence of current spending to solve this.
- BAD DATA SIGNS: Vague enthusiasm ("Love it!"), hypothetical future behavior ("I would definitely use..."), flattery without commitment.

Target Market Analysis:
- NICHE SPECIFICITY: Is the target_market a narrow, reachable segment (e.g., "men 18-25 training for first marathon") vs broad demographic ("young professionals," "SMBs")?
- ACCESSIBILITY: Can you find and interview 10 of these people tomorrow in a specific physical or digital location?

FATAL FLAW - MOM TEST:
- Problem_statement mentions the technology ("AI platform for...," "App that...") -> VERDICT: KILL. Reason: "Solution bias; violates Mom Test principle of asking about life, not idea."
- Target_market >100,000 people or lacks specific psychographic/behavioral definition -> FATAL FLAW: "Market too broad for actionable validation or beachhead dominance."
- No evidence of current workaround spending -> FATAL FLAW: "Latent need, not active pain; vitamin not painkiller."

=== CROSSING THE CHASM: MARKET TIMING & STRATEGY ===
Mission: Identify "Chasm Death"-the gap between Visionary early adopters and Pragmatist mainstream that kills 90% of tech startups.

Adoption Group Analysis:
- ENTHUSIASTS/VISIONARIES (Early Market): Want strategic breakthrough, willing to tolerate bugs/incompleteness.
- PRAGMATISTS (Mainstream): Want incremental productivity, complete solutions, market leaders, low risk.

Whole Product Audit:
For Pragmatist targets, verify the solution includes:
- Core product
- Installation/training
- Support services  
- Ecosystem alliances (integrations, complementary products)

Beachhead Strategy:
- Can the target_market be dominated (become #1) within 6 months with available resources?
- Is there a specific "dire problem" that forces immediate purchase (not "nice to have")?

FATAL FLAW - CHASM:
- Targeting mainstream (Pragmatists) without Whole Product plan -> VERDICT: KILL. Reason: "Chasm death; pragmatists reject incomplete solutions."
- No 6-month path to niche dominance -> FATAL FLAW: "Cannot generate reference sales to cross chasm."
- Visionary product features (bleeding edge, complex) targeting Pragmatist buyers (conservative, reliability-focused) -> FATAL FLAW: "Adoption group mismatch."
- "Platform strategy" without initial single-use-case beachhead -> FATAL FLAW: "Multi-sided market death spiral."

=== DISRUPTIVE INNOVATION: ASYMMETRIC MOTIVATION ===
Mission: Determine if the idea exploits the "Innovator's Dilemma" or falls into the "sustaining innovation trap."

Innovation Type Classification:
- DISRUPTIVE (GOOD): 
  - Initially underperforms on mainstream metrics (lower quality/fidelity)
  - Offers new value dimension (cheaper, simpler, more convenient, portable)
  - Targets non-consumers OR low-end over-served customers
  - Incumbents motivated to ignore it (low margins, small market)
  
- SUSTAINING (BAD):
  - Better performance on existing metrics for existing high-end customers
  - Targets incumbent's core market with superior features
  - Incumbents motivated to fight (high margins, core business)

Trajectory Analysis:
- Is there evidence the technology/process will improve faster than market demand (performance trajectory)?
- Does the monetization_model avoid direct margin competition with incumbents?

FATAL FLAW - DISRUPTION:
- "Better mousetrap" approach (superior features in same category) -> VERDICT: KILL. Reason: "Sustaining innovation; incumbents will outspend and crush this."
- Targets high-end customers of existing market -> FATAL FLAW: "No asymmetric motivation; incumbent will defend."
- Requires customers to change behavior significantly without extenuating circumstances -> FATAL FLAW: "High adoption friction; not exploiting existing behavior."
- Competes on price in commodity market -> FATAL FLAW: "Race to bottom with entrenched scale players."

=== CRITIQUE SYNTHESIS PROTOCOL ===

SCORING RUBRIC (Confidence Score 1-10):
10: Counter-positioning OR Cornered Resource locked; Mom Test validated with current workarounds; Clear beachhead <6mo; Disruptive trajectory targeting non-consumers.
9: Strong power (Network Effects/Scale potential); Specific niche; Whole product planned; Asymmetric vs incumbents.
7-8: Solid on 2-3 frameworks, minor concerns on power or validation. REVISION may strengthen defensibility.
5-6: Weak power identification OR broad target market OR chasm risk. Requires specific fixes.
<5: Multiple fatal flaws or single unfixable flaw (sustaining innovation, no problem validation). Must specify which framework failed.

VERDICT LOGIC:
PASS (>=7): Clear power source, validated problem in narrow segment, viable chasm-crossing strategy, asymmetric competition.
REVISE (5-6): Fixable flaws identified (e.g., "Narrow target market from 'young professionals' to specific subsegment," "Identify specific switching costs mechanism").
KILL (<5 or unfixable): Sustaining innovation, no power, chasm death inevitable, solution bias in problem statement.

REVISION SUGGESTIONS FORMAT:
When REVISE verdict: Provide specific, actionable fixes:
1. [Framework]: [Current flaw] -> [Required change] (e.g., "Mom Test: Broad demographic -> Specific cohort with dire problem")
2. [Power]: [Missing element] -> [How to build] (e.g., "7 Powers: No moat -> Identify cornered resource or pivot to counter-positioning model")

FATAL FLAWS LIST (Auto-generate):
List any of these detected:
- No Power (Commodity)
- Solution Bias (Mom Test Fail)  
- Chasm Death (No Whole Product)
- Sustaining Innovation Trap
- Broad Target Market (Unvalidatable)
"""

ARCHITECT_KB = """
=== SHAPE UP: PRODUCT DEVELOPMENT EXECUTION ===

Fixed Time, Variable Scope (The Iron Rule):
- The mvp_timeline_weeks is IMMOVABLE; features are negotiable.
- If features exceed capacity, cut scope mercilessly ("scope hammering").
- Never suggest extending deadlines ("we need 2 more weeks"); always cut vertical slices to fit the cycle.
- Valid cycles: 4, 6, or 8 weeks maximum. Anything longer signals waterfall thinking.

Vertical Slicing (Architecture Geometry):
- MVP features must be VERTICAL SLICES (end-to-end user functionality), never horizontal layers.
- WRONG (Horizontal): "Build database schema" -> "Build REST API" -> "Build React frontend" (no user value until week 12).
- RIGHT (Vertical): "User can upload receipt and see extracted total (mock AI if needed)" -> "User can export PDF report."
- Rule of 3s: Maximum 9 vertical slices per cycle (3x3). If more needed, split into a second cycle.
- Each slice must be demonstrable to a non-technical stakeholder (product manager, designer) without explaining "the backend isn't wired yet."

Shaping & De-risking (Pre-Build Phase):
- Architecture_overview must describe the "breadboard": low-fidelity UI sketches/wiring diagrams before pixels or code.
- Identify "fixed vs. variable" elements: What is the "appetite" (time budget) for this slice? What can we cut if it runs long?
- Flag "unshaped work": If a feature has undefined edges or unknown technical dependencies, it is excluded from the current cycle.

The Pitch as Technical Contract:
- The technical roadmap enforces the boundaries defined in the startup's "pitch" (problem + solution scope).
- Acceptance criteria must be binary (done/not done), never vague ("improve performance," "refactor code").

Ugly-but-Working -> Polish Workflow:
- Build sequence: Breadboard (sketch) -> Ugly-but-functional (working UI, no styling) -> Polish (visual refinement).
- Do not build for "production polish" until the vertical slice proves user value in the ugly stage.

=== LEAN STARTUP: VALIDATED LEARNING ARCHITECTURE ===

Build-Measure-Learn Velocity:
- Tech stack must support deployment of vertical slices within 2-3 days (small batch size).
- Architecture must enable continuous delivery; "big bang" releases indicate misalignment.
- Optimize for speed of iteration, not technical elegance.

MVP Type Selection (Riskiest Assumption First):
Match the technical approach to the validation need:
- CONCIERGE MVP: Manual backend processes with automated UI (validate demand before building automation).
- WIZARD OF OZ MVP: Fake AI/automation with humans behind the curtain (validate UX before ML investment).
- VIDEO MVP: Landing page/demo before build (validate value proposition with sign-ups).
- SINGLE-FEATURE MVP: One vertical slice only, cut ruthlessly to the core loop.

Avoiding Waste (Lean Definition):
- "Waste" = any code that does not test a hypothesis about customer risk.
- AUTO-EXCLUDE from MVP: Admin dashboards, analytics pipelines, user management systems, premature microservices, "nice-to-have" optimizations.
- INCLUDE ONLY: Code that delivers end-to-end user value to validate the riskiest assumption.

Engines of Growth (Technical Requirements):
Architecture must instrument the chosen growth engine:
- STICKY: Data models for retention/churn tracking; cohort analysis hooks; onboarding flow instrumentation.
- VIRAL: Referral code systems; sharing APIs; invitation friction reduction; viral coefficient tracking.
- PAID: Conversion funnel tracking; payment gateway integration; CAC/LTV calculation hooks; A/B testing infrastructure.

Pivot/Persevere Enablement:
- Tech stack must support low-cost pivots: Avoid rigid relational schemas early (prefer flexible data models), use modular monoliths over distributed microservices.
- Technical debt is acceptable if it enables faster validated learning; optimize for optionality, not perfection.
- Database migrations should be reversible within the cycle.

=== ARCHITECTURE SYNTHESIS PROTOCOL ===

For TechnicalRoadmap Schema Fields:

architecture_overview:
- Open with the breadboard concept: "We will sketch UI wiring before coding."
- State the fixed timeline commitment: "6-week cycle, variable scope."
- Define shaped boundaries: Explicitly list what is OUT of scope (prevents scope creep).

tech_stack:
- Prioritize "boring technology" (Rails, Django, Next.js, PostgreSQL, Redis)-proven, debugged, easy to hire for.
- AI/ML ONLY if it is the core differentiation AND cannot be faked with Wizard of Oz first.
- Avoid: Kubernetes, microservices, GraphQL (early phase), blockchain (unless absolutely core), trendy frameworks with <3 years maturity.
- Prefer: Full-stack frameworks that enable vertical slicing (single deploy = user value).

mvp_features:
- List exactly 3-7 vertical slices (end-to-end user capabilities).
- Each feature follows format: "[User type] can [action] to achieve [outcome]"
- Sequence by riskiest assumption first (Lean), then dependency order.
- NO backend-only tasks (e.g., "Set up AWS infrastructure" is not a feature; "User can upload file to S3" is).

mvp_timeline_weeks:
- Must be 4, 6, or 8. Never 12, 16, or 24 for initial MVP.
- If the user suggests longer, override to 6 weeks and scope down features accordingly.

scalability_considerations:
- Address "how we survive sudden success" but prioritize "how we learn fast if this fails."
- Specify migration path: When do we move from Concierge/Wizard of Oz to full automation? (e.g., "After 100 manual transactions validated, build automation").
- Database sharding and microservices extraction mentioned only as "Phase 2" post-validation, never in MVP cycle.

key_risks:
- "Scope creep beyond cycle boundaries" (Shape Up violation)
- "Horizontal vs Vertical confusion" (building infrastructure layers before user features)
- "Premature optimization" (caching, microservices, ML models before validation)
- "Unshaped technical work" (unclear boundaries leading to rabbit holes)
- "Platform trap" (building for other developers before validating own product)

=== REJECTION CRITERIA (Auto-fail Architect Output) ===
- Proposes microservices or Kubernetes for MVP phase.
- Timeline >8 weeks for initial MVP.
- Features are horizontal (backend-only/infrastructure tasks) rather than vertical (user-facing end-to-end).
- Includes "admin panel," "analytics dashboard," or "user management system" before core value validation.
- Suggests "building a platform" or "API-first" before validating the first consumer use case.
- Proposes novel/unproven tech stacks when boring alternatives exist.
"""

FULL_KNOWLEDGE_BASE = f"{RESEARCHER_KB}\n\n{CRITIC_KB}\n\n{ARCHITECT_KB}"

# ==============================================================================
# SCHEMAS (UNCHANGED + DeepDiveResult added)
# ==============================================================================

class StartupIdea(BaseModel):
    title: str = Field(..., description="Concise startup name")
    problem_statement: str = Field(..., description="Specific pain point (customer life, not solution)")
    proposed_solution: str = Field(..., description="Product description with Four-Action Framework applied")
    target_market: str = Field(..., description="Specific customer segment with Non-Customer Tier (1/2/3)")
    unique_value_proposition: str = Field(..., description="Defensibility/moat with explicit 7 Power identified")
    monetization_model: str = Field(..., description="Revenue model")

class CritiqueResult(BaseModel):
    confidence_score: int = Field(..., ge=1, le=10, description="VC conviction: >=7 to pass. IMPORTANT: Be harsh. Most ideas are 3-5.")
    technical_feasibility: str = Field(..., description="Build complexity assessment")
    market_size_assessment: str = Field(..., description="TAM/SAM analysis")
    customer_acquisition_analysis: str = Field(..., description="CAC and channel risks")
    fatal_flaws: List[str] = Field(default_factory=list, description="MANDATORY: List at least 2-3 specific flaws if score < 8")
    revision_suggestions: str = Field(..., description="Fixes required if <7 with specific framework references")
    verdict: Literal["PASS", "REVISE", "KILL"] = Field(...)

class TechnicalRoadmap(BaseModel):
    architecture_overview: str = Field(..., description="Breadboard approach and fixed timeline commitment")
    tech_stack: List[str] = Field(..., description="Boring technology list: Django/Rails/Next.js/Postgres")
    mvp_features: List[str] = Field(..., min_length=3, max_length=7, description="Vertical slices only, format: [User] can [action]")
    mvp_timeline_weeks: int = Field(..., ge=4, le=8, description="Fixed: 4, 6, or 8 weeks maximum")
    scalability_considerations: str = Field(..., description="Migration from Concierge/Wizard of Oz to automation")
    key_risks: List[str] = Field(..., description="Shape Up and Lean risks")
    mvp_type: Literal["Concierge", "Wizard of Oz", "Single-Feature", "Video"] = Field(..., description="Validation strategy")

class DeepDiveResult(BaseModel):
    tech_architecture_diagram: str = Field(default="", description="Text-based architecture diagram showing components and data flow")
    cofounder_profiles: List[Dict[str, str]] = Field(default_factory=list, description="List of co-founder profiles with role, background, unique_value")
    first_customers: List[str] = Field(default_factory=list, description="List of first 10 customers to approach")
    risk_mitigation: List[str] = Field(default_factory=list, description="List of risk mitigation strategies")
    six_week_milestones: List[Dict[str, str]] = Field(default_factory=list, description="Weekly milestones with week, goal, success_metric")

# ==============================================================================
# STATE (Modified for CLI persistence)
# ==============================================================================

class StartupState(BaseModel):
    market_query: str
    knowledge_base: str = ""
    market_intelligence: Optional[str] = None
    
    iteration: int = 0
    max_iterations: int = 3
    director_notes: Optional[str] = None
    
    current_idea: Optional[StartupIdea] = None
    last_critique: Optional[CritiqueResult] = None
    critique_history: List[CritiqueResult] = []
    final_roadmap: Optional[TechnicalRoadmap] = None
    
    status: Literal["initialized", "gathering_intelligence", "researching", "critiquing", "awaiting_user", "architecting", "completed", "rejected", "killed"] = "initialized"
    final_message: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_favorite: bool = False
    
    def to_dict(self) -> dict:
        """Serialize to dict for JSON storage"""
        return {
            "market_query": self.market_query,
            "market_intelligence": self.market_intelligence,
            "iteration": self.iteration,
            "max_iterations": self.max_iterations,
            "director_notes": self.director_notes,
            "current_idea": self.current_idea.model_dump() if self.current_idea else None,
            "last_critique": self.last_critique.model_dump() if self.last_critique else None,
            "critique_history": [c.model_dump() for c in self.critique_history],
            "final_roadmap": self.final_roadmap.model_dump() if self.final_roadmap else None,
            "status": self.status,
            "final_message": self.final_message,
            "created_at": self.created_at.isoformat(),
            "is_favorite": self.is_favorite
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "StartupState":
        """Deserialize from dict"""
        state = cls(
            market_query=data["market_query"],
            knowledge_base=data.get("knowledge_base", ""),
            market_intelligence=data.get("market_intelligence"),
            iteration=data.get("iteration", 0),
            max_iterations=data.get("max_iterations", 3),
            director_notes=data.get("director_notes"),
            status=data.get("status", "initialized"),
            final_message=data.get("final_message"),
            is_favorite=data.get("is_favorite", False)
        )
        
        if data.get("current_idea"):
            state.current_idea = StartupIdea(**data["current_idea"])
        if data.get("last_critique"):
            state.last_critique = CritiqueResult(**data["last_critique"])
        if data.get("critique_history"):
            state.critique_history = [CritiqueResult(**c) for c in data["critique_history"]]
        if data.get("final_roadmap"):
            state.final_roadmap = TechnicalRoadmap(**data["final_roadmap"])
        
        return state

# ==============================================================================
# MARKET INTELLIGENCE AGENT (UNCHANGED SAFETY)
# ==============================================================================

class MarketIntelligenceAgent:
    def __init__(self):
        self._cache: Dict[str, Tuple[str, float]] = {}
        self._cache_ttl = 3600
        self._ddgs_available = DDGS_AVAILABLE
        
    def _get_cached(self, key: str) -> Optional[str]:
        if key in self._cache:
            result, timestamp = self._cache[key]
            if time.time() - timestamp < self._cache_ttl:
                return result
            else:
                del self._cache[key]
        return None
    
    def _set_cache(self, key: str, value: str):
        self._cache[key] = (value, time.time())
    
    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        retry=retry_if_exception_type(Exception),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    async def gather_intelligence(self, domain: str) -> Optional[str]:
        cache_key = domain.lower().strip()[:60]
        cached = self._get_cached(cache_key)
        if cached:
            return cached
            
        if not self._ddgs_available:
            return None
            
        try:
            queries = [
                f"{domain} funding rounds March 2026",
                f"{domain} venture capital investment 2026",
                f"{domain} M&A acquisition 2026",
                f"{domain} regulatory changes law 2026",
                f"{domain} market size growth 2026",
                f"{domain} competitor pivot strategy 2026"
            ]
            
            brief_sections = ["=== MARKET INTELLIGENCE BRIEF (As of March 28, 2026) ===\n"]
            
            loop = asyncio.get_event_loop()
            
            for query in queries:
                try:
                    def search():
                        with DDGS() as ddgs:
                            return list(ddgs.text(query, max_results=2))
                    
                    results = await asyncio.wait_for(
                        loop.run_in_executor(None, search),
                        timeout=DDGS_TIMEOUT + 5
                    )
                    
                    if results:
                        category = query.replace(f"{domain} ", "").replace(" 2026", "").title()
                        brief_sections.append(f"--- {category} ---")
                        for i, r in enumerate(results[:2], 1):
                            title = r.get('title', 'No title')
                            body = r.get('body', '')[:200]
                            brief_sections.append(f"{i}. {title}: {body}...")
                        brief_sections.append("")
                        
                except asyncio.TimeoutError:
                    continue
                except Exception:
                    continue
            
            if len(brief_sections) > 1:
                final_brief = "\n".join(brief_sections)
                self._set_cache(cache_key, final_brief)
                return final_brief
            else:
                return None
                
        except Exception:
            return None

# ==============================================================================
# AGENTS (FIXED CRITIC + ESCAPED DEBUG OUTPUT)
# ==============================================================================

class BaseAgent:
    def __init__(self, client: genai.Client, model: str, temperature: float, persona: str, 
                 min_cache_tokens: int = 0, agent_name: str = "Agent", color: str = "white"):
        self.client = client
        self.model = model
        self.temperature = temperature
        self.persona = persona
        self.min_cache_tokens = min_cache_tokens
        self.tier = detect_tier()
        self.agent_name = agent_name
        self.color = color
        
        self.generate = retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=2, max=10),
            retry=retry_if_exception_type(Exception),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=True
        )(self._generate)
    
    def _check_cache_eligibility(self, kb: str):
        estimated_tokens = len(kb) // 4
        if 0 < estimated_tokens < self.min_cache_tokens:
            logger.warning(f"[{self.model}] KB ({estimated_tokens} est. tokens) below cache threshold.")
    
    async def _generate(self, knowledge_base: str, user_task: str, output_schema: Type[BaseModel], system_suffix: str = "") -> BaseModel:
        self._check_cache_eligibility(knowledge_base)
        
        if len(user_task) > MAX_TASK_LENGTH:
            user_task = user_task[:MAX_TASK_LENGTH] + "...[truncated]"
        
        temporal_context = "\n\nCURRENT DATE: March 28, 2026\nAll market references must be current as of this date."
        
        system_instruction = f"{self.persona}{temporal_context}\n\nBUSINESS KNOWLEDGE BASE:\n{knowledge_base}\n{system_suffix}"
        
        # DEBUG: Show what we're sending to the AI (ESCAPED to prevent markup errors)
        safe_agent_name = escape(self.agent_name)
        safe_model = escape(self.model)
        
        console.print(f"\n[bold {self.color}]╭── {safe_agent_name} ({safe_model}) ──{'─' * 40}╮[/bold {self.color}]")
        console.print(f"[{self.color}]│ Temperature: {self.temperature} | Output: {output_schema.__name__}[/{self.color}]")
        
        # Show truncated task preview (ESCAPED)
        task_preview = user_task[:300].replace("\n", " ") + "..." if len(user_task) > 300 else user_task
        safe_preview = escape(task_preview)
        console.print(f"[dim {self.color}]│ Task: {safe_preview}[/dim {self.color}]")
        
        if self.tier == "free":
            await asyncio.sleep(1.0)
        else:
            await asyncio.sleep(0.1)
        
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=user_task,
                config=GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    response_schema=output_schema,
                    temperature=self.temperature
                )
            )
            
            # DEBUG: Show raw response (ESCAPED to prevent bracket issues)
            raw_text = response.text if hasattr(response, 'text') else str(response.parsed)
            safe_raw = escape(raw_text[:200])  # CRITICAL: Escape before printing!
            console.print(f"[dim {self.color}]│ Raw response preview: {safe_raw}...[/dim {self.color}]")
            
            if response.parsed:
                result = response.parsed
            else:
                result = output_schema.model_validate_json(response.text)
            
            # DEBUG: Show parsed result nicely
            result_json = json.dumps(result.model_dump(), indent=2, default=str)
            # Escape any remaining brackets in the JSON for display
            safe_json = escape(result_json)
            syntax = Syntax(safe_json, "json", theme="monokai", line_numbers=False)
            
            console.print(f"[bold {self.color}]│ Parsed Output:[/bold {self.color}]")
            console.print(Panel(syntax, border_style=self.color, expand=False))
            console.print(f"[bold {self.color}]╰{'─' * 60}╯[/bold {self.color}]\n")
            
            return result
            
        except ValidationError as ve:
            console.print(f"[bold red]│ Validation Error: {escape(str(ve))}[/bold red]")
            logger.error(f"[{self.model}] Schema validation failed: {ve}")
            raise ValueError(f"LLM output invalid: {ve}")
        except Exception as e:
            console.print(f"[bold red]│ Generation Error: {escape(str(e))}[/bold red]")
            logger.error(f"[{self.model}] Generation failed: {e}")
            raise ValueError(f"LLM Service Error: {str(e)}")


class VisionaryResearcher(BaseAgent):
    def __init__(self, client: genai.Client):
        super().__init__(
            client=client,
            model="gemini-2.5-flash",
            temperature=0.7,
            persona="""You are a visionary startup researcher operating as of March 28, 2026.

STRICT FRAMEWORK ADHERENCE:
1. FOUR-ACTION FRAMEWORK: In proposed_solution, explicitly state ELIMINATE, REDUCE, RAISE, CREATE vs industry standards.
2. NON-CUSTOMER TIER: In target_market, explicitly identify Tier 1/2/3.
3. 7 POWERS IDENTIFICATION: In UVP, explicitly state the specific Power leveraged.
4. MONOPOLY POTENTIAL: Target small market first, expand later (Zero to One).
5. VALUE INNOVATION: Simultaneous differentiation AND cost reduction.

Reject "Uber for X", "AI-powered [existing tool]" without 10x improvement, or "1% of $1B market" ideas.""",
            min_cache_tokens=1024,
            agent_name="Visionary Researcher",
            color="green"
        )
    
    async def generate_idea(self, state: StartupState) -> StartupIdea:
        iteration_ctx = ""
        if state.iteration > 1 and state.last_critique:
            iteration_ctx = (
                f"\n--- REVISION ROUND {state.iteration} ---\n"
                f"Previous Score: {state.last_critique.confidence_score}/10\n"
                f"Critic Framework Feedback: {state.last_critique.revision_suggestions}\n"
                f"Fatal Flaws to Fix: {', '.join(state.last_critique.fatal_flaws)}\n"
            )
        
        hitl_ctx = ""
        if state.director_notes:
            hitl_ctx = f"\n--- STRATEGIC PIVOT DIRECTIVE ---\n{state.director_notes}\nTreat as board-level directive.\n"
        
        market_ctx = ""
        if state.market_intelligence:
            market_ctx = f"\n=== REAL-TIME MARKET CONTEXT (March 2026) ===\n{state.market_intelligence[:2000]}...\nUse this data to ground your idea in current reality.\n"
        
        user_task = f"""
CURRENT DATE: March 28, 2026
{market_ctx}
MARKET QUERY: {state.market_query}
{iteration_ctx}
{hitl_ctx}

Generate a novel startup idea following STRICT FORMAT RULES:
- Target Non-Customer tier (Tier 1/2/3)
- Use Four-Action Framework (Eliminate/Reduce/Raise/Create)
- Identify 7 Power in UVP
- Zero-to-One monopoly potential

Output strictly valid JSON matching StartupIdea schema.
"""
        return await self.generate(
            knowledge_base=state.knowledge_base,
            user_task=user_task,
            output_schema=StartupIdea
        )
    
    async def generate_variations(self, state: StartupState, num_variations: int = 3) -> List[StartupIdea]:
        """Generate multiple variations of an idea for explore mode"""
        variations = []
        for i in range(num_variations):
            variation_ctx = f"\n--- VARIATION {i+1}/{num_variations} ---\nGenerate a distinct variation with different UVP angle or target tier.\n"
            state_copy = StartupState(
                market_query=state.market_query + variation_ctx,
                knowledge_base=state.knowledge_base,
                market_intelligence=state.market_intelligence,
                iteration=0,
                max_iterations=3
            )
            idea = await self.generate_idea(state_copy)
            variations.append(idea)
        return variations


class AdversarialCritic(BaseAgent):
    def __init__(self, client: genai.Client):
        super().__init__(
            client=client,
            model="gemini-2.5-pro",
            temperature=0.1,
            persona="""You are a ruthless, cynical Venture Capitalist who hates losing money. Your job is to DESTROY bad startup ideas.

MANDATORY CRITICAL STANCE:
- Your DEFAULT is KILL. You must be CONVINCED to pass an idea.
- 90% of ideas should score 3-6. Only truly exceptional ideas get 7+.
- You must ALWAYS identify at least 2-3 fatal flaws unless the idea is perfect (which it never is).
- If you cannot find flaws, you are not looking hard enough.

STRICT FRAMEWORK ENFORCEMENT (Check ALL):
1. 7 POWERS: If no clear Counter-Positioning, Cornered Resource, or Network Effects -> Score <= 4
2. MOM TEST: If problem mentions tech ("AI app for...", "Platform that...") -> Score <= 3, Verdict=KILL
3. CHASM: If targeting "young professionals" or "SMBs" (broad) -> Score <= 5
4. DISRUPTION: If it's a "better mousetrap" (sustaining innovation) -> Score <= 2, Verdict=KILL

SCORING GUIDELINES (BE HARSH):
10: Impossible perfect idea (never give this)
9: Counter-positioning locked, Mom Test perfect, beachhead clear
7-8: Good but concerns remain
5-6: Multiple fixable flaws
3-4: Major unfixable flaws or weak moat
1-2: Sustaining innovation or solution bias

REMEMBER: You are protecting LP capital. Be brutal. Find the holes.""",
            min_cache_tokens=4096,
            agent_name="Adversarial Critic",
            color="red"
        )
    
    async def critique(self, idea: StartupIdea, kb: str) -> CritiqueResult:
        user_task = f"""
EVALUATE THIS STARTUP (March 28, 2026). TEAR IT APART:
Title: {idea.title}
Problem: {idea.problem_statement}
Solution: {idea.proposed_solution}
Target: {idea.target_market}
UVP: {idea.unique_value_proposition}
Monetization: {idea.monetization_model}

YOUR TASK:
1. Identify AT LEAST 2-3 fatal flaws (unless truly exceptional)
2. Check: Does problem statement mention technology? (Bad)
3. Check: Is target market specific and reachable? (If broad = flaw)
4. Check: Is this sustaining or disruptive innovation? (Sustaining = kill)
5. Check: Is there a real 7 Power moat? (No = low score)

SCORING RULES:
- 10 = Never (reserved for perfect ideas)
- 7-9 = Strong pass (rare)
- 5-6 = Revise (common)
- <5 = Kill (most ideas)

Output JSON matching CritiqueResult schema. MANDATORY: If score < 8, list specific fatal_flaws.
"""
        return await self.generate(
            knowledge_base=kb,
            user_task=user_task,
            output_schema=CritiqueResult
        )


class Architect(BaseAgent):
    def __init__(self, client: genai.Client):
        super().__init__(
            client=client,
            model="gemini-2.5-flash",
            temperature=0.3,
            persona="""You are a Staff Engineer/CTO operating as of March 28, 2026.

NON-NEGOTIABLE CONSTRAINTS:
1. TIMELINE: MVP MUST be 4, 6, or 8 weeks maximum. If features don't fit, cut them.
2. VERTICAL SLICING ONLY: End-to-end user capabilities, never horizontal layers.
3. MVP TYPE: Explicitly declare Concierge/Wizard of Oz/Single-Feature/Video.
4. BORING TECHNOLOGY: Django, Rails, Next.js, PostgreSQL, Redis.
   FORBIDDEN: Kubernetes, microservices, GraphQL (early phase), blockchain.
5. VALIDATED LEARNING: Optimize for Build-Measure-Learn speed.

Architecture must enable pivoting (flexible schemas, modular monoliths).""",
            min_cache_tokens=1024,
            agent_name="Architect",
            color="blue"
        )
    
    async def design(self, idea: StartupIdea, kb: str) -> TechnicalRoadmap:
        user_task = f"""
DESIGN ARCHITECTURE (March 28, 2026):
Title: {idea.title}
Solution: {idea.proposed_solution}
Target: {idea.target_market}

REQUIREMENTS:
- MVP Timeline: 4-6 weeks (fixed time, variable scope)
- Vertical Slices: 3-7 end-to-end features (no backend-only tasks)
- Tech Stack: Boring technology (Django/Rails/Next.js/Postgres)
- MVP Type: Select one (Concierge/Wizard of Oz/Single-Feature/Video)
- Migration Path: When to automate from manual validation

Output JSON matching TechnicalRoadmap schema. mvp_timeline_weeks must be 4, 6, or 8.
"""
        return await self.generate(
            knowledge_base=kb,
            user_task=user_task,
            output_schema=TechnicalRoadmap
        )
    
    async def deep_dive(self, idea: StartupIdea, roadmap: TechnicalRoadmap, kb: str) -> DeepDiveResult:
        """Generate deep dive details for passed ideas"""
        user_task = f"""
GENERATE DEEP DIVE ANALYSIS for this validated startup:

Title: {idea.title}
Problem: {idea.problem_statement}
Solution: {idea.proposed_solution}
Target: {idea.target_market}
UVP: {idea.unique_value_proposition}
MVP Type: {roadmap.mvp_type}
Timeline: {roadmap.mvp_timeline_weeks} weeks

Provide detailed analysis in JSON format:
{{
    "tech_architecture_diagram": "Text-based architecture diagram showing components and data flow",
    "cofounder_profiles": [
        {{"role": "CTO/Technical", "background": "Specific profile", "unique_value": "What they bring"}},
        {{"role": "CEO/GTM", "background": "Specific profile", "unique_value": "What they bring"}},
        {{"role": "Domain Expert", "background": "Specific profile", "unique_value": "What they bring"}}
    ],
    "first_customers": [
        "Specific named persona/company 1",
        "Specific named persona/company 2",
        "... (10 total)"
    ],
    "risk_mitigation": [
        "Risk 1: Mitigation strategy",
        "Risk 2: Mitigation strategy",
        "... (3-5 key risks)"
    ],
    "six_week_milestones": [
        {{"week": 1, "goal": "Specific deliverable", "success_metric": "How to verify"}},
        {{"week": 2, "goal": "Specific deliverable", "success_metric": "How to verify"}},
        "... (6 weeks)"
    ]
}}
"""
        return await self.generate(
            knowledge_base=kb,
            user_task=user_task,
            output_schema=DeepDiveResult
        )

# ==============================================================================
# ORCHESTRATOR (Modified for CLI with Debug visibility)
# ==============================================================================

class StartupOrchestrator:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable required.")
        
        self.client = genai.Client(api_key=api_key)
        self.market_agent = MarketIntelligenceAgent()
        self.researcher = VisionaryResearcher(self.client)
        self.critic = AdversarialCritic(self.client)
        self.architect = Architect(self.client)
        
        self.pending_sessions: Dict[str, StartupState] = {}
        logger.info(f"Orchestrator initialized (Tier: {detect_tier().upper()})")
    
    def _extract_domain(self, query: str) -> str:
        try:
            if "faces" in query.lower():
                parts = query.split("faces")[0].strip()
                if len(parts) > 10:
                    return parts[:60]
            words = query.split()[:5]
            domain = " ".join(words)
            return domain[:60]
        except Exception:
            return query[:60].strip()
    
    async def gather_market_intelligence(self, state: StartupState) -> StartupState:
        state.status = "gathering_intelligence"
        domain = self._extract_domain(state.market_query)
        
        console.print(f"[dim]Gathering market intelligence for: {escape(domain)}...[/dim]")
        intelligence = await self.market_agent.gather_intelligence(domain)
        if intelligence:
            state.market_intelligence = intelligence
            console.print(f"[green]✓ Market intelligence gathered ({len(intelligence)} chars)[/green]")
        else:
            state.market_intelligence = "[Market intelligence unavailable - proceed with caution]"
            console.print(f"[yellow]⚠ Market intelligence unavailable[/yellow]")
        
        return state
    
    async def run(self, state: StartupState, hitl_enabled: bool = True, progress=None) -> Tuple[StartupState, Optional[str]]:
        """
        Returns: (final_state, breakpoint_id)
        breakpoint_id is only set when HITL breakpoint is reached (iteration 2, score <7)
        """
        if not state.market_intelligence:
            state = await self.gather_market_intelligence(state)
        
        while state.iteration < state.max_iterations:
            state.iteration += 1
            
            # Pause progress bar while printing debug output
            if progress:
                progress.stop()
            
            # Research Phase
            state.status = "researching"
            console.rule(f"[bold green]Iteration {state.iteration}/{state.max_iterations}: Research Phase[/bold green]")
            try:
                state.current_idea = await self.researcher.generate_idea(state)
            except Exception as e:
                state.status = "rejected"
                state.final_message = f"Researcher failed: {e}"
                return state, None
            
            # Critique Phase
            state.status = "critiquing"
            console.rule(f"[bold red]Iteration {state.iteration}: Critique Phase[/bold red]")
            try:
                critique = await self.critic.critique(state.current_idea, state.knowledge_base)
                state.last_critique = critique
                state.critique_history.append(critique)
            except Exception as e:
                state.status = "rejected"
                state.final_message = f"Critic failed: {e}"
                return state, None
            
            # Debug summary of critique
            console.print(f"\n[bold]Critique Summary:[/bold] Score {critique.confidence_score}/10 | Verdict: {critique.verdict}")
            if critique.fatal_flaws:
                console.print(f"[red]Fatal Flaws ({len(critique.fatal_flaws)}):[/red]")
                for flaw in critique.fatal_flaws:
                    console.print(f"  - {escape(flaw)}")
            
            # Check pass condition
            if critique.confidence_score >= 7:
                console.print(f"[bold green]✓ Idea passed with score {critique.confidence_score}/10[/bold green]")
                break
            
            console.print(f"[yellow]✗ Idea failed with score {critique.confidence_score}/10, iterating...[/yellow]")
            
            # HITL Breakpoint at iteration 2 if score < 7
            if hitl_enabled and state.iteration == 2 and critique.confidence_score < 7:
                state.status = "awaiting_user"
                state_id = str(uuid.uuid4())[:8]
                self.pending_sessions[state_id] = state
                console.print(f"[bold red]HITL BREAKPOINT REACHED (ID: {state_id})[/bold red]")
                return state, state_id
            
            # Continue to next iteration if not at breakpoint
            if state.iteration < state.max_iterations:
                continue
        
        # Final Architecture Phase (only if passed)
        if state.last_critique and state.last_critique.confidence_score >= 7:
            state.status = "architecting"
            console.rule("[bold blue]Architecture Phase[/bold blue]")
            try:
                state.final_roadmap = await self.architect.design(
                    state.current_idea, 
                    state.knowledge_base
                )
                state.status = "completed"
                state.final_message = "Success: Validated and architected."
            except Exception as e:
                state.status = "rejected"
                state.final_message = f"Architect failed: {e}"
        else:
            state.status = "rejected"
            state.final_message = f"Failed after {state.iteration} rounds. Score: {state.last_critique.confidence_score if state.last_critique else 0}"
        
        return state, None
    
    async def resume_with_feedback(self, state_id: str, notes: str, kill: bool = False) -> StartupState:
        """Resume with HITL feedback or kill the idea"""
        if state_id not in self.pending_sessions:
            raise ValueError("Session not found or expired.")
        
        state = self.pending_sessions.pop(state_id)
        
        if kill:
            state.status = "killed"
            state.final_message = f"Killed by user at iteration {state.iteration}. Reason: {notes}"
            return state
        
        state.director_notes = notes
        state.status = "researching"
        
        # Continue from current iteration (don't reset)
        return await self.run(state, hitl_enabled=True)
    
    async def generate_deep_dive(self, state: StartupState) -> DeepDiveResult:
        """Generate deep dive details for a completed idea"""
        if not state.current_idea or not state.final_roadmap:
            raise ValueError("Idea must be completed before deep dive")
        
        console.rule("[bold cyan]Deep Dive Generation[/bold cyan]")
        return await self.architect.deep_dive(
            state.current_idea,
            state.final_roadmap,
            state.knowledge_base
        )


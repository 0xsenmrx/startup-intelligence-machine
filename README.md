# Startup Intelligence Machine v0.1

> **"Zero to One" meets Multi-Agent AI** — A brutal, framework-driven ideation system that kills bad ideas fast and validates good ones faster.

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Gemini API](https://img.shields.io/badge/Gemini%20API-2.5--flash-orange)](https://aistudio.google.com/)

## What Makes This Different?

Unlike generic "AI startup idea generators," SIM uses **adversarial multi-agent systems** grounded in proven venture capital frameworks:

| Agent | Framework | Role |
|-------|-----------|------|
| **Researcher** | *Zero to One* + *Blue Ocean* | Generates contrarian "secrets" targeting non-customers |
| **Critic** | *7 Powers* + *The Mom Test* + *Crossing the Chasm* | Ruthlessly hunts fatal flaws (default: KILL) |
| **Architect** | *Shape Up* + *Lean Startup* | Designs 4-6 week MVPs with vertical slicing |

**Result:** Ideas that survive this process have clear moats, validated problems, and buildable roadmaps.

## Quick Start

### Prerequisites
- Python 3.8+
- Google Gemini API Key ([get free](https://aistudio.google.com/app/apikey))

### Installation

```bash
# Clone and enter
git clone https://github.com/YOUR_USERNAME/startup-intelligence-machine.git
cd startup-intelligence-machine

# Linux/Mac
./run.sh

# Windows
run.bat
```

## Modes of Operation

### EXPLORE Mode (Interactive)

```bash
python runner.py --mode=explore
```

Best for single ideation with human-in-the-loop pivoting.

### BATCH Mode (Automated)

Create `queries.txt` with 10 MADLIBS-style queries:

```plain 
Logistics companies that struggle with last-mile delivery compliance
Healthcare practices drowning in prior authorization paperwork
```

Then run:

```bash 
python runner.py --mode=batch
```

## The Frameworks (Why This Works)

### 1. Zero to One Principles (Thiel)

- Targets Tier 2/3 non-customers (refusing/unexplored)
- Seeks last-mover advantage through proprietary technology
- Validates "secrets" — contrarian truths others miss

### 2. Blue Ocean Strategy (Kim/Mauborgne)

- Four Actions Framework: Eliminate/Reduce/Raise/Create factors
- Value Innovation: Simultaneous differentiation + low cost
- Avoids "Red Ocean" competition (Uber for X = instant kill)

### 3. 7 Powers (Helmer)

The Critic auto-checks for:

- Counter-Positioning (incumbents must destroy core business to copy)
- Cornered Resource (proprietary data, exclusive licenses)
- Network Effects
- Scale Economies

**No Power = Auto-KILL**

4. The Mom Test (Fitzpatrick)

- Problem statements must describe customer's life, not your tech
- "AI platform for..." = instant rejection
- Seeks specific past behaviors, not hypothetical future interest

5. Shape Up (Fried/Heinemeier)

- Fixed time, variable scope: 4-6 week cycles only
- Vertical slicing: End-to-end user features, never horizontal layers
- Ugly-first: Working before polished

> NOTE: There are other resources as well

## Human-in-the-Loop (HITL)

At iteration 2, if confidence < 7/10, the system pauses:

```bash
HUMAN-IN-THE-LOOP BREAKPOINT
Options:
  <pivot notes>  - "Pivot to B2B, focus on compliance angle"
  KILL           - Abandon idea
  SAVE           - Mark favorite, continue anyway
  SKIP           - Move to next query
```

The system caches successful pivot strategies indexed by fatal flaw signatures.

## Output Structure

```plain 
ideas/
├── freight_compliance_a1b2c3d4.md     # Deep dive analysis
├── healthcare_automation_e5f6g7h8.md
└── ...

session_state.json                      # Resume capability
pivot_cache.json                        # Learned strategies
ideas.md                               # Full session log
```

## Configuration

Create `.env` file:

```ini
GEMINI_API_KEY=your_key_here
```

Or set environment variable:

```bash 
export GEMINI_API_KEY=your_key_here  # Linux/Mac
set GEMINI_API_KEY=your_key_here     # Windows
```

## Contributing

This tool is opinionated by design. The frameworks enforce venture-grade rigor.

**Bug reports**: Issues welcome
**Feature requests**: Consider if it strengthens the framework adherence
**Pull requests**: Must maintain the "default to KILL" philosophy of the Critic

## License

MIT - Use responsibly. The ideas generated are yours; the rigor is ours.

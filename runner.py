#!/usr/bin/env python3 ✓✗⚠
"""
Startup Intelligence Machine - Personal CLI Runner v4.1
------------------------------------------------------
Usage:
    python runner.py --mode=batch           # Process queries.txt
    python runner.py --mode=explore       # Interactive single query
    python runner.py --mode=batch --resume  # Continue from last position
"""

import os
import sys
import json
import hashlib
import asyncio
import argparse
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict
from dataclasses import dataclass, asdict

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.markdown import Markdown
from rich.layout import Layout
from rich.syntax import Syntax
from rich import box
from rich.prompt import Prompt, Confirm
from rich.tree import Tree

from mas import (
    StartupOrchestrator, StartupState, FULL_KNOWLEDGE_BASE,
    StartupIdea, CritiqueResult, TechnicalRoadmap, DeepDiveResult,
    console as mas_console  # Import the shared console
)

console = Console()

# ==============================================================================
# STATE PERSISTENCE
# ==============================================================================

class SessionManager:
    def __init__(self):
        self.state_file = Path("session_state.json")
        self.cache_file = Path("pivot_cache.json")
        self.ideas_file = Path("ideas.md")
        self.ideas_dir = Path("ideas")
        self.ideas_dir.mkdir(exist_ok=True)
        
        self.state = self.load_state()
        self.pivot_cache = self.load_pivot_cache()
    
    def load_state(self) -> dict:
        if self.state_file.exists():
            with open(self.state_file) as f:
                return json.load(f)
        return {
            "current_query_idx": 0,
            "completed_ideas": [],
            "abandoned_ideas": [],
            "favorites": [],
            "session_started": datetime.now().isoformat()
        }
    
    def save_state(self):
        with open(self.state_file, "w") as f:
            json.dump(self.state, f, indent=2)
    
    def load_pivot_cache(self) -> Dict[str, List[Dict]]:
        """Cache of fatal flaw patterns to successful pivot strategies"""
        if self.cache_file.exists():
            with open(self.cache_file) as f:
                return json.load(f)
        return {}
    
    def save_pivot_cache(self):
        with open(self.cache_file, "w") as f:
            json.dump(self.pivot_cache, f, indent=2)
    
    def _generate_key(self, fatal_flaws: List[str]) -> str:
        """Create unique hash from sorted fatal flaws"""
        raw = "|".join(sorted(fatal_flaws)).encode('utf-8')
        return hashlib.md5(raw).hexdigest()
    
    def cache_pivot_strategy(self, fatal_flaws: List[str], strategy: str):
        """Store successful pivot strategy indexed by flaw hash"""
        if not fatal_flaws or not strategy:
            return
        key = self._generate_key(fatal_flaws)
        if key not in self.pivot_cache:
            self.pivot_cache[key] = []
        self.pivot_cache[key].append({
            "strategy": strategy,
            "timestamp": datetime.now().isoformat(),
            "success": True,
            "flaws": fatal_flaws
        })
        self.save_pivot_cache()
    
    def suggest_pivot(self, fatal_flaws: List[str]) -> Optional[str]:
        """Retrieve cached pivot strategy for similar flaws"""
        if not fatal_flaws:
            return None
        
        key = self._generate_key(fatal_flaws)
        if key in self.pivot_cache:
            strategies = self.pivot_cache[key]
            if strategies:
                return strategies[-1].get("strategy")
        
        # Partial matching
        current_flaws = set(fatal_flaws)
        best_match = None
        best_overlap = 0
        
        for cached_key, entries in self.pivot_cache.items():
            if isinstance(entries, list) and entries:
                cached_flaws = set(entries[0].get("flaws", []))
                if not cached_flaws:
                    continue
                    
                overlap = len(current_flaws & cached_flaws)
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_match = entries[-1].get("strategy")
        
        return best_match if best_overlap > 0 else None
    
    def add_completed_idea(self, state: StartupState):
        idea_data = {
            "timestamp": datetime.now().isoformat(),
            "title": state.current_idea.title if state.current_idea else "Unknown",
            "score": state.last_critique.confidence_score if state.last_critique else 0,
            "mvp_weeks": state.final_roadmap.mvp_timeline_weeks if state.final_roadmap else 0,
            "mvp_type": state.final_roadmap.mvp_type if state.final_roadmap else "None",
            "is_favorite": state.is_favorite,
            "status": state.status
        }
        self.state["completed_ideas"].append(idea_data)
        self.save_state()
    
    def add_abandoned_idea(self, title: str, reason: str):
        self.state["abandoned_ideas"].append({
            "timestamp": datetime.now().isoformat(),
            "title": title,
            "reason": reason
        })
        self.save_state()
    
    def add_favorite(self, title: str):
        """Mark idea as favorite for persistent tracking"""
        if title not in self.state["favorites"]:
            self.state["favorites"].append(title)
            self.save_state()

# ==============================================================================
# OUTPUT FORMATTING
# ==============================================================================

class IdeaFormatter:
    @staticmethod
    def display_idea_card(state: StartupState):
        """Display beautiful formatted idea card using Rich"""
        if not state.current_idea or not state.last_critique:
            return
        
        idea = state.current_idea
        critique = state.last_critique
        
        # Header Panel
        score_color = "green" if critique.confidence_score >= 7 else "yellow" if critique.confidence_score >= 5 else "red"
        star = " ⭐" if state.is_favorite else ""
        
        header = Panel.fit(
            f"[bold white]{idea.title}{star}[/bold white]\n"
            f"[{score_color}]Score: {critique.confidence_score}/10 ({critique.verdict})[/{score_color}]",
            box=box.ROUNDED,
            border_style=score_color
        )
        console.print(header)
        
        # The Secret (Contrarian Insight)
        if "secret" in idea.unique_value_proposition.lower() or "contrarian" in idea.unique_value_proposition.lower():
            secret_text = idea.unique_value_proposition
        else:
            secret_text = f"The Secret: {idea.unique_value_proposition}"
        
        secret_panel = Panel(
            secret_text,
            title="[bold cyan]The Secret (Contrarian Insight)[/bold cyan]",
            box=box.DOUBLE,
            border_style="cyan"
        )
        console.print(secret_panel)
        
        # Problem & Solution
        grid = Table.grid(expand=True)
        grid.add_column(ratio=1)
        grid.add_column(ratio=1)
        
        problem_md = Markdown(f"**Problem:**\n{idea.problem_statement}")
        solution_md = Markdown(f"**Solution:**\n{idea.proposed_solution}")
        
        grid.add_row(
            Panel(problem_md, title="The Pain", border_style="red"),
            Panel(solution_md, title="The Fix", border_style="green")
        )
        console.print(grid)
        
        # Target Market & UVP
        console.print(Panel(
            f"[bold]Target:[/bold] {idea.target_market}\n"
            f"[bold]Monetization:[/bold] {idea.monetization_model}",
            title="Market & Model",
            border_style="blue"
        ))
        
        # 7 Power Analysis
        if critique.confidence_score >= 7:
            power_text = "✓ Defensibility confirmed via framework analysis"
        else:
            power_text = "⚠ Power analysis incomplete or weak"
        
        console.print(Panel(
            power_text,
            title="7 Powers Assessment",
            border_style="yellow"
        ))
        
        # Fatal Flaws (if any)
        if critique.fatal_flaws:
            flaws_text = "\n".join([f"- {flaw}" for flaw in critique.fatal_flaws])
            console.print(Panel(
                flaws_text,
                title="[bold red]✗ Fatal Flaws Detected[/bold red]",
                border_style="red"
            ))
        
        # Architecture (if available)
        if state.final_roadmap:
            rm = state.final_roadmap
            arch_table = Table(title=f"Architecture ({rm.mvp_type})", box=box.SIMPLE_HEAD)
            arch_table.add_column("Property", style="cyan")
            arch_table.add_column("Value", style="white")
            
            arch_table.add_row("Timeline", f"{rm.mvp_timeline_weeks} weeks")
            arch_table.add_row("Tech Stack", ", ".join(rm.tech_stack[:4]))
            arch_table.add_row("Key Risks", "\n".join(rm.key_risks[:2]))
            
            console.print(arch_table)
            
            # MVP Features
            features_md = "\n".join([f"{i+1}. {feat}" for i, feat in enumerate(rm.mvp_features)])
            console.print(Panel(
                Markdown(features_md),
                title="MVP Features (Vertical Slices)",
                border_style="green"
            ))
    
    @staticmethod
    def export_to_markdown(state: StartupState, filename: Optional[str] = None) -> str:
        """Export idea to markdown file"""
        if not state.current_idea:
            return ""
        
        idea = state.current_idea
        critique = state.last_critique
        
        parts = []
        parts.append(f"# {idea.title}{' ⭐' if state.is_favorite else ''}")
        parts.append("")
        parts.append(f"**Score:** {critique.confidence_score if critique else 0}/10  ")
        parts.append(f"**Status:** {state.status}  ")
        parts.append(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        parts.append("")
        parts.append("---")
        parts.append("")
        parts.append("## The Problem")
        parts.append(idea.problem_statement)
        parts.append("")
        parts.append("## The Solution")
        parts.append(idea.proposed_solution)
        parts.append("")
        parts.append("## Market & UVP")
        parts.append(f"**Target:** {idea.target_market}  ")
        parts.append(f"**UVP:** {idea.unique_value_proposition}  ")
        parts.append(f"**Monetization:** {idea.monetization_model}")
        parts.append("")
        parts.append("## Defensibility Analysis")
        
        if critique:
            parts.append("")
            parts.append(f"**Verdict:** {critique.verdict}  ")
            parts.append(f"**Score:** {critique.confidence_score}/10")
            parts.append("")
            parts.append("### Framework Checks")
            check_7 = "✓" if critique.confidence_score >= 7 else "✗"
            parts.append(f"- **7 Powers:** {check_7} {critique.technical_feasibility}")
            parts.append(f"- **Market Size:** {critique.market_size_assessment}")
            parts.append(f"- **CAC Analysis:** {critique.customer_acquisition_analysis}")
            parts.append("")
            parts.append("### Fatal Flaws")
            if critique.fatal_flaws:
                for flaw in critique.fatal_flaws:
                    parts.append(f"- {flaw}")
            else:
                parts.append("None identified.")
            parts.append("")
            parts.append(f"### Revision Suggestions")
            parts.append(critique.revision_suggestions)
        
        if state.final_roadmap:
            rm = state.final_roadmap
            parts.append("")
            parts.append("## Technical Roadmap")
            parts.append("")
            parts.append(f"**Type:** {rm.mvp_type} MVP  ")
            parts.append(f"**Timeline:** {rm.mvp_timeline_weeks} weeks (Fixed time, variable scope)")
            parts.append("")
            parts.append("### Tech Stack")
            parts.append(", ".join(rm.tech_stack))
            parts.append("")
            parts.append("### MVP Features (Vertical Slices)")
            for i, feat in enumerate(rm.mvp_features, 1):
                parts.append(f"{i}. {feat}")
            parts.append("")
            parts.append("### Scalability & Risks")
            parts.append(rm.scalability_considerations)
            parts.append("")
            parts.append("**Key Risks:**")
            for risk in rm.key_risks:
                parts.append(f"- {risk}")
        
        parts.append("")
        parts.append("---")
        parts.append("*Generated by Startup Intelligence Machine v4.1*")
        
        md_content = "\n".join(parts)
        
        if filename:
            filepath = Path(filename)
            with open(filepath, "w", encoding='utf-8') as f:
                f.write(md_content)
        
        return md_content

# ==============================================================================
# DEEP DIVE GENERATION
# ==============================================================================

async def generate_deep_dive_file(orch: StartupOrchestrator, state: StartupState, session_mgr: SessionManager):
    """Generate and save deep dive markdown"""
    if not state.current_idea:
        return
    
    console.print("\n[bold cyan]Generating Deep Dive Analysis...[/bold cyan]")
    
    try:
        deep_dive = await orch.generate_deep_dive(state)
        
        title_slug = state.current_idea.title.lower().replace(" ", "_")[:20]
        unique_hash = hashlib.md5(state.current_idea.title.encode()).hexdigest()[:8]
        slug = f"{title_slug}_{unique_hash}"
        filename = session_mgr.ideas_dir / f"{slug}.md"
        
        parts = []
        parts.append(f"# Deep Dive: {state.current_idea.title}")
        parts.append("")
        parts.append("*Comprehensive build plan for validated startup idea*")
        parts.append("")
        parts.append("---")
        parts.append("")
        parts.append("## Executive Summary")
        
        score = state.last_critique.confidence_score if state.last_critique else 0
        mvp_type = state.final_roadmap.mvp_type if state.final_roadmap else "Unknown"
        weeks = state.final_roadmap.mvp_timeline_weeks if state.final_roadmap else 0
        date_str = datetime.now().strftime("%Y-%m-%d")
        
        parts.append(f"- **Idea Score:** {score}/10")
        parts.append(f"- **MVP Type:** {mvp_type}")
        parts.append(f"- **Timeline:** {weeks} weeks")
        parts.append(f"- **Validation Date:** {date_str}")
        parts.append("")
        parts.append("---")
        parts.append("")
        parts.append("## Technical Architecture")
        parts.append("")
        parts.append("```")
        parts.append(deep_dive.tech_architecture_diagram or "Architecture diagram not generated")
        parts.append("```")
        parts.append("")
        parts.append("---")
        parts.append("")
        parts.append("## Recommended Co-Founder Profiles")
        parts.append("")
        
        for i, profile in enumerate(deep_dive.cofounder_profiles or [], 1):
            role = profile.get("role", "TBD")
            background = profile.get("background", "N/A")
            unique = profile.get("unique_value", "N/A")
            parts.append(f"### {i}. {role}")
            parts.append(f"**Background:** {background}  ")
            parts.append(f"**Unique Value:** {unique}")
            parts.append("")
        
        parts.append("---")
        parts.append("## First 10 Customers to Approach")
        parts.append("")
        
        for i, customer in enumerate(deep_dive.first_customers or [], 1):
            parts.append(f"{i}. {customer}")
        
        parts.append("")
        parts.append("---")
        parts.append("## ⚠ Risk Mitigation Strategies")
        parts.append("")
        
        for risk in deep_dive.risk_mitigation or []:
            parts.append(f"- {risk}")
        
        parts.append("")
        parts.append("---")
        parts.append("## 6-Week Milestone Breakdown")
        parts.append("")
        parts.append("| Week | Goal | Success Metric |")
        parts.append("|------|------|----------------|")
        
        for week_data in deep_dive.six_week_milestones or []:
            week = week_data.get("week", "?")
            goal = week_data.get("goal", "TBD")
            metric = week_data.get("success_metric", "TBD")
            parts.append(f"| {week} | {goal} | {metric} |")
        
        parts.append("")
        parts.append("---")
        parts.append("## Next Actions (This Week)")
        parts.append("1. [ ] Validate problem with 3 potential customers from the list above")
        parts.append("2. [ ] Set up technical spike for riskiest assumption")
        parts.append("3. [ ] Recruit co-founder matching profile #1")
        parts.append("")
        parts.append("---")
        parts.append("*Generated by Startup Intelligence Machine - Deep Dive Mode*")
        
        content = "\n".join(parts)
        
        with open(filename, "w", encoding='utf-8') as f:
            f.write(content)
        
        console.print(f"[green]✓ Deep dive saved to {filename}[/green]")
        
    except Exception as e:
        console.print(f"[red]✗ Deep dive generation failed: {e}[/red]")

# ==============================================================================
# HITL (Human-in-the-Loop) HANDLING
# ==============================================================================

def handle_hitl_breakpoint(state: StartupState, session_mgr: SessionManager, orch: StartupOrchestrator) -> str:
    """
    Handle HITL breakpoint when score < 7 at iteration 2.
    Returns: pivot notes string, "KILL", "SKIP", or "CONTINUE_ANYWAY"
    """
    if not state.current_idea or not state.last_critique:
        return "KILL"
    
    critique = state.last_critique
    idea = state.current_idea
    
    console.print("\n")
    console.rule("[bold red]HUMAN-IN-THE-LOOP BREAKPOINT[/bold red]", style="red")
    
    IdeaFormatter.display_idea_card(state)
    
    console.print(f"\n[bold yellow]Framework Analysis:[/bold yellow]")
    console.print(f"- Technical Feasibility: {critique.technical_feasibility[:150]}...")
    console.print(f"- Market Assessment: {critique.market_size_assessment[:150]}...")
    console.print(f"- CAC Analysis: {critique.customer_acquisition_analysis[:150]}...")
    
    suggestion = session_mgr.suggest_pivot(critique.fatal_flaws)
    if suggestion:
        console.print(f"\n[dim italic]Based on previous sessions, similar flaws were fixed by:[/dim italic]")
        console.print(f"[dim italic]   '{suggestion}'[/dim italic]")
    
    console.print("\n[bold]Options:[/bold]")
    console.print("  [green]<pivot notes>[/green] - Enter strategy to fix fatal flaws")
    console.print("  [red]KILL[/red] - Abandon this idea and move to next")
    console.print("  [yellow]SAVE[/yellow] - Mark as favorite and continue anyway")
    console.print("  [blue]SKIP[/blue] - Abandon and move to next query")
    
    response = Prompt.ask("\n[bold]Your decision[/bold]", default="").strip()
    
    if response.upper() in ["KILL", "SKIP"]:
        return response.upper()
    elif response.upper() == "SAVE":
        state.is_favorite = True
        session_mgr.add_favorite(idea.title)
        console.print("[yellow]Idea saved to favorites. Continue iterating?[/yellow]")
        cont = Prompt.ask("Enter pivot notes to improve, or 'continue' to keep as-is", default="continue")
        if cont.lower() == "continue":
            return "CONTINUE_ANYWAY"
        return cont
    else:
        if response:
            session_mgr.cache_pivot_strategy(critique.fatal_flaws, response)
        return response if response else "KILL"

# ==============================================================================
# BATCH MODE
# ==============================================================================

async def run_batch_mode(orch: StartupOrchestrator, session_mgr: SessionManager, resume: bool = False):
    """Process queries.txt with full HITL and progress tracking"""
    
    if not os.path.exists("queries.txt"):
        console.print("[red]✗ queries.txt not found. Create it with your 10 MADLIBS queries.[/red]")
        return
    
    with open("queries.txt", encoding='utf-8') as f:
        queries = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    
    if not queries:
        console.print("[red]✗ queries.txt is empty or contains only comments. Add at least one query.[/red]")
        return
    
    if len(queries) < 10:
        console.print(f"[yellow]⚠ Only {len(queries)} queries found (recommended: 10)[/yellow]")
    
    start_idx = session_mgr.state["current_query_idx"] if resume else 0
    
    if resume and start_idx > 0:
        console.print(f"[cyan]↩Resuming from query {start_idx + 1}/{len(queries)}[/cyan]")
    
    completed_ideas = []
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        
        task = progress.add_task(f"[cyan]Processing queries...", total=len(queries))
        
        for i, query in enumerate(queries[start_idx:], start=start_idx):
            progress.update(task, description=f"[cyan]Query {i+1}/{len(queries)}: {query[:50]}...[/cyan]")
            
            state = StartupState(
                market_query=query,
                knowledge_base=FULL_KNOWLEDGE_BASE,
                max_iterations=3
            )

            try:
                final_state, breakpoint_id = await orch.run(state, hitl_enabled=True)
            except Exception as e:
                session_mgr.save_state()
                raise
            
            if breakpoint_id:
                action = handle_hitl_breakpoint(final_state, session_mgr, orch)
                
                if action in ["KILL", "SKIP"]:
                    reason = "User killed at HITL" if action == "KILL" else "User skipped"
                    session_mgr.add_abandoned_idea(
                        final_state.current_idea.title if final_state.current_idea else "Unknown",
                        reason
                    )
                    if action == "SKIP":
                        session_mgr.state["current_query_idx"] = i + 1
                        session_mgr.save_state()
                        continue
                    break
                elif action == "CONTINUE_ANYWAY":
                    final_state.status = "saved_favorite"
                    final_state.is_favorite = True
                    session_mgr.add_favorite(final_state.current_idea.title)
                    session_mgr.add_completed_idea(final_state)
                    completed_ideas.append(final_state)
                else:
                    console.print(f"[yellow]↻ Revising with your strategy: {action[:50]}...[/yellow]")
                    final_state = await orch.resume_with_feedback(breakpoint_id, action)
                    
                    if final_state.status == "completed" or final_state.last_critique.confidence_score >= 7:
                        session_mgr.add_completed_idea(final_state)
                        completed_ideas.append(final_state)
                    else:
                        session_mgr.add_abandoned_idea(
                            final_state.current_idea.title if final_state.current_idea else "Unknown",
                            f"Still failed after pivot: {final_state.last_critique.confidence_score if final_state.last_critique else 0}/10"
                        )
            
            elif final_state.status == "completed":
                session_mgr.add_completed_idea(final_state)
                completed_ideas.append(final_state)
            else:
                session_mgr.add_abandoned_idea(
                    final_state.current_idea.title if final_state.current_idea else "Unknown",
                    final_state.final_message or "Failed validation"
                )
            
            if final_state.current_idea and (final_state.status == "completed" or final_state.is_favorite):
                IdeaFormatter.display_idea_card(final_state)
                
                md_content = IdeaFormatter.export_to_markdown(final_state)
                with open(session_mgr.ideas_file, "a", encoding='utf-8') as f:
                    f.write("\n\n---\n\n" + md_content)
                
                if final_state.last_critique and final_state.last_critique.confidence_score >= 7:
                    if Confirm.ask("\n[bold green]Generate Deep Dive analysis?[/bold green]", default=True):
                        await generate_deep_dive_file(orch, final_state, session_mgr)
            
            session_mgr.state["current_query_idx"] = i + 1
            session_mgr.save_state()
            progress.advance(task)
            
            await asyncio.sleep(0.5)
    
    console.print("\n")
    console.rule("[bold]SESSION SUMMARY[/bold]")
    
    if completed_ideas:
        matrix = Table(title="Idea Comparison Matrix", box=box.DOUBLE_EDGE)
        matrix.add_column("Rank", justify="center", style="cyan")
        matrix.add_column("Title", style="white")
        matrix.add_column("Score", justify="center")
        matrix.add_column("MVP Weeks", justify="center")
        matrix.add_column("Moat", style="green")
        matrix.add_column("Market", style="blue")
        matrix.add_column("Build?", style="bold")
        
        sorted_ideas = sorted(
            completed_ideas, 
            key=lambda x: (x.is_favorite, x.last_critique.confidence_score if x.last_critique else 0),
            reverse=True
        )
        
        for rank, idea_state in enumerate(sorted_ideas, 1):
            idea = idea_state.current_idea
            critique = idea_state.last_critique
            roadmap = idea_state.final_roadmap
            
            score = critique.confidence_score if critique else 0
            score_color = "green" if score >= 7 else "yellow"
            star = "⭐ " if idea_state.is_favorite else ""
            
            weeks = roadmap.mvp_timeline_weeks if roadmap else 0
            moat = "Strong" if score >= 8 else "Mod" if score >= 6 else "Weak"
            market = critique.market_size_assessment[:15] + "..." if critique else "Unknown"
            build = "YES" if score >= 7 else "Maybe"
            
            matrix.add_row(
                str(rank),
                f"{star}{idea.title[:25]}",
                f"[{score_color}]{score}[/{score_color}]",
                str(weeks),
                moat,
                market,
                build
            )
        
        console.print(matrix)
        
        buildable = [i for i in sorted_ideas if i.last_critique and i.last_critique.confidence_score >= 7]
        if buildable:
            console.print(f"\n[bold green]Top Recommendations:[/bold green]")
            for i, idea in enumerate(buildable[:3], 1):
                console.print(f"  {i}. {idea.current_idea.title} (Score: {idea.last_critique.confidence_score}/10)")
        
        console.print(f"\n[dim]All ideas exported to {session_mgr.ideas_file}[/dim]")
    else:
        console.print("[yellow]No completed ideas in this session.[/yellow]")
    
    console.print(f"\n[dim]Session saved. Resume anytime: python runner.py --mode=batch --resume[/dim]")

# ==============================================================================
# EXPLORE MODE
# ==============================================================================

async def run_explore_mode(orch: StartupOrchestrator, session_mgr: SessionManager):
    """Interactive single-query mode with variations"""
    
    console.print(Panel.fit(
        "[bold cyan]EXPLORE MODE[/bold cyan]\n"
        "Single query ideation with manual control",
        border_style="cyan"
    ))
    
    query = Prompt.ask("\n[bold]Enter your market query[/bold]")
    if not query:
        return
    
    console.print(f"\n[cyan]Generating 3 variations...[/cyan]")
    
    base_state = StartupState(
        market_query=query,
        knowledge_base=FULL_KNOWLEDGE_BASE,
        max_iterations=3
    )
    
    variations = await orch.researcher.generate_variations(base_state, num_variations=3)
    
    table = Table(title="Choose a variation to develop", box=box.ROUNDED)
    table.add_column("#", justify="center")
    table.add_column("Title")
    table.add_column("Hook/Angle", style="cyan")
    table.add_column("Tier", style="dim")
    
    for i, idea in enumerate(variations, 1):
        hook = idea.unique_value_proposition[:50] + "..."
        tier = "Tier 2" if "Tier 2" in idea.target_market else "Tier 3" if "Tier 3" in idea.target_market else "Tier 1"
        table.add_row(str(i), idea.title, hook, tier)
    
    console.print(table)
    
    choice = Prompt.ask("Select variation (1-3) or 'q' to quit", choices=["1", "2", "3", "q"], default="1")
    if choice == "q":
        return
    
    selected = variations[int(choice) - 1]
    console.print(f"\n[green]Selected: {selected.title}[/green]")
    
    state = StartupState(
        market_query=query,
        knowledge_base=FULL_KNOWLEDGE_BASE,
        max_iterations=3,
        current_idea=selected
    )
    
    iteration = 0
    while True:
        iteration += 1
        state.iteration = iteration
        
        console.print(f"\n[cyan]Running adversarial critique (iteration {iteration})...[/cyan]")
        critique = await orch.critic.critique(state.current_idea, state.knowledge_base)
        state.last_critique = critique
        state.critique_history.append(critique)
        
        IdeaFormatter.display_idea_card(state)
        
        if critique.confidence_score >= 7:
            console.print(f"\n[bold green]✓ Idea validated! Score: {critique.confidence_score}/10[/bold green]")
            state.status = "completed"
            
            if Confirm.ask("Generate technical roadmap?", default=True):
                state.final_roadmap = await orch.architect.design(state.current_idea, state.knowledge_base)
                IdeaFormatter.display_idea_card(state)
            
            md_content = IdeaFormatter.export_to_markdown(state)
            with open(session_mgr.ideas_file, "a", encoding='utf-8') as f:
                f.write("\n\n---\n\n" + md_content)
            
            if Confirm.ask("Generate Deep Dive file?", default=True):
                await generate_deep_dive_file(orch, state, session_mgr)
            
            break
        
        console.print(f"\n[yellow]Score {critique.confidence_score}/10 below threshold (7)[/yellow]")
        
        action = Prompt.ask(
            "[bold]Enter pivot notes, 'new' for fresh variation, or 'quit'[/bold]",
            default=""
        )
        
        if action.lower() == "quit":
            break
        elif action.lower() == "new":
            console.print("[cyan]Generating new variation...[/cyan]")
            new_variations = await orch.researcher.generate_variations(base_state, num_variations=1)
            if new_variations:
                state.current_idea = new_variations[0]
                state.iteration = 0
                state.critique_history = []
                state.director_notes = None
            continue
        
        if action:
            state.director_notes = action
            console.print("[cyan]Revising with pivot strategy...[/cyan]")
            state.current_idea = await orch.researcher.generate_idea(state)
        else:
            console.print("[yellow]No pivot notes provided. Ending session.[/yellow]")
            break

# ==============================================================================
# MAIN
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(description="Startup Intelligence Machine - Personal CLI")
    parser.add_argument("--mode", choices=["batch", "explore"], default="batch", help="Operation mode")
    parser.add_argument("--resume", action="store_true", help="Resume from last position (batch mode only)")
    args = parser.parse_args()
    
    if not os.getenv("GEMINI_API_KEY"):
        console.print("[red]✗ Set GEMINI_API_KEY environment variable first[/red]")
        console.print("[dim]export GEMINI_API_KEY='your_key_here'[/dim]")
        sys.exit(1)
    
    orch = StartupOrchestrator()
    session_mgr = SessionManager()
    
    try:
        if args.mode == "batch":
            asyncio.run(run_batch_mode(orch, session_mgr, resume=args.resume))
        else:
            asyncio.run(run_explore_mode(orch, session_mgr))
    except KeyboardInterrupt:
        console.print("\n\n[yellow]⚠ Interrupted by user. State saved. Use --resume to continue.[/yellow]")
        session_mgr.save_state()
        sys.exit(0)

if __name__ == "__main__":
    main()

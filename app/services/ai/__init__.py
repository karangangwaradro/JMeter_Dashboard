"""
app.services.ai — AI Studio, prompt generation, findings discovery, context packaging, and multi-provider LLM integrations.
"""

from app.services.ai.prompts import (
    build_insights_prompt,
    build_comparison_prompt,
    build_2run_comparison_prompt,
)
from app.services.ai.findings import (
    generate_findings,
    enrich_findings_with_ai,
    build_performance_intelligence,
    SEVERITY_BADGES,
    SEV_CRITICAL,
    SEV_HIGH,
    SEV_MEDIUM,
    SEV_LOW,
)
from app.services.ai.context_packager import (
    build_section_digest,
    build_chat_system_prompt,
)
from app.services.ai.insights import (
    generate_ai_insights,
    generate_insights,
    generate_comparison_ai_insights,
    generate_2run_comparison_ai_insights,
    execute_gemini_prompt,
    execute_github_prompt,
    execute_openrouter_prompt,
    execute_chat_completion,
    calculate_performance_score,
)

__all__ = [
    "build_insights_prompt",
    "build_comparison_prompt",
    "build_2run_comparison_prompt",
    "generate_findings",
    "enrich_findings_with_ai",
    "build_performance_intelligence",
    "SEVERITY_BADGES",
    "SEV_CRITICAL",
    "SEV_HIGH",
    "SEV_MEDIUM",
    "SEV_LOW",
    "build_section_digest",
    "build_chat_system_prompt",
    "generate_ai_insights",
    "generate_insights",
    "generate_comparison_ai_insights",
    "generate_2run_comparison_ai_insights",
    "execute_gemini_prompt",
    "execute_github_prompt",
    "execute_openrouter_prompt",
    "execute_chat_completion",
    "calculate_performance_score",
]

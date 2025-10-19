"""Investigation endpoints for incident root cause analysis.

This router provides the primary investigation endpoint that accepts incident
context and returns AI-generated root cause analysis with remediation proposals.

Future implementation will integrate with the Claude API using MCP tools to:
1. Query observability data (logs, metrics, traces) via the observability tools
2. Inspect infrastructure state via kubectl and AWS CLI tools
3. Search runbooks for relevant procedures
4. Generate a comprehensive investigation report with confidence scoring
5. Optionally trigger remediation actions (with human approval for high-risk changes)
"""

from fastapi import APIRouter

from agents.investigator import IncidentInvestigator
from models.incident import InvestigationRequest, InvestigationResult

router = APIRouter(prefix="/api/v1", tags=["investigation"])

investigator = IncidentInvestigator()


@router.post("/investigate", response_model=InvestigationResult)
async def investigate_incident(request: InvestigationRequest) -> InvestigationResult:
    """Investigate an incident and return root cause analysis.

    Accepts an incident context with alert data and severity, then runs the
    AI investigation agent to analyze observability data, correlate signals,
    and produce a root cause analysis with remediation recommendations.

    The investigation depth controls how thorough the analysis is:
    - quick: ~5 minutes, checks recent logs and metrics only
    - standard: ~15 minutes, full log/metric/trace correlation
    - deep: ~30 minutes, includes historical pattern analysis and runbook search

    Future Claude API integration:
        The investigator agent will use Claude with MCP tools to autonomously
        query logs, metrics, traces, and infrastructure state. It will iterate
        through multiple tool calls to gather evidence before synthesizing
        findings into a structured investigation result.
    """
    result = await investigator.investigate(request.incident.model_dump())
    return InvestigationResult(**result)

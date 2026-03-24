"""
Workflow templates for AI agent.

Provides predefined prompts and workflow patterns for:
- Load testing with Locust (deterministic workflows)
- Demo scenarios (health checks, repairs, diagnostics)
- Tool chaining examples
"""

from typing import Dict

# ===== Infrastructure/DevOps Workflows =====

HEALTH_CHECK_WORKFLOW = """Check the overall system health and report the status of all services."""

MINIMAL_SINGLE_TOOL = """Your task: Call system_health ONCE, then immediately provide your Final Answer with the results.

STOP after 1 tool call. Do NOT call any other tools. DO NOT verify or check again."""

FORCED_FULL_REPAIR = """Your task has EXACTLY 3 steps — no more, no less.

Step 1: Action: system_health  /  Action Input: {}
Step 2: Action: service_restart  /  Action Input: {"service_name": "api-gateway"}
Step 3: Action: system_health  /  Action Input: {}

After the Observation from Step 3, you MUST immediately output:
Thought: All steps complete
Final Answer: [one-sentence summary of what was done and the result]

CRITICAL: Do NOT call any tool after Step 3. Do NOT add extra checks."""

REPAIR_WORKFLOW_DETERMINISTIC = """
Check system health. If the api-gateway service is degraded or has errors, read its logs
to diagnose the issue, then restart it. Finally, verify that the system is healthy.

If all services are healthy and logs show no errors, respond with "System is healthy, no action needed."
"""

REPAIR_WORKFLOW_OPEN_ENDED = """
Check the system and identify any issues. Diagnose the root cause by examining logs
and diagnostics. Take appropriate corrective actions to restore the system to a healthy state.
If the system is already healthy and no issues are found, report that as your Final Answer.
"""

DIAGNOSTICS_WORKFLOW = """
Run comprehensive diagnostics on the api-gateway service. Check its health,
read recent logs, and verify database connectivity. Report any issues found.
"""

DATABASE_CHECK_WORKFLOW = """
Check the database status and report on connection pool utilization,
query performance, and any slow queries detected.
"""

CONFIG_UPDATE_WORKFLOW = """
Update the api-gateway service configuration: set max_connections to 200.
Note that a restart will be required for this change to take effect.
"""

# ===== Tool Chaining Workflows =====
# These demonstrate multi-step reasoning with dependent tool calls

MULTI_STEP_REPAIR = """
1. First check overall system health
2. If any service is degraded, read its logs to understand why
3. Run diagnostics on the problematic service
4. If the issue is related to database, check database status
5. Take corrective action (restart service or update config)
6. Verify the fix worked
"""

PROGRESSIVE_DIAGNOSIS = """
Diagnose system issues by progressively narrowing down the problem:
1. Check system health to identify failing services
2. For each failing service, read logs to find error patterns
3. Run diagnostics to get detailed health check results
4. Check database if any services report database errors
5. Summarize findings and recommend actions
"""

# ===== Chat/Conversational Workflows =====

EXPLAIN_CAPABILITIES = """
Explain what system operations you can perform and what tools you have available.
"""

STATUS_QUERY = """
What is the current status of the system? Are all services running properly?
"""

SERVICE_INFO_QUERY = """
Tell me about the api-gateway service. Is it running? Are there any recent errors?
"""

# ===== Error Scenarios =====
# These test boundary conditions and error handling

INVALID_SERVICE_NAME = """
Check the health of the "nonexistent-service" and restart it if needed.
"""

MULTIPLE_RESTARTS = """
Restart all services in this order: api-gateway, auth-service, database, cache-service.
Wait 5 seconds between each restart.
"""

# ===== Workflow Templates Registry =====

WORKFLOW_TEMPLATES = {
    # Infrastructure workflows
    "health_check": HEALTH_CHECK_WORKFLOW,
    "minimal_single_tool": MINIMAL_SINGLE_TOOL,
    "forced_full_repair": FORCED_FULL_REPAIR,
    "repair_deterministic": REPAIR_WORKFLOW_DETERMINISTIC,
    "repair_open_ended": REPAIR_WORKFLOW_OPEN_ENDED,
    "diagnostics": DIAGNOSTICS_WORKFLOW,
    "database_check": DATABASE_CHECK_WORKFLOW,
    "config_update": CONFIG_UPDATE_WORKFLOW,

    # Tool chaining
    "multi_step_repair": MULTI_STEP_REPAIR,
    "progressive_diagnosis": PROGRESSIVE_DIAGNOSIS,

    # Chat
    "explain_capabilities": EXPLAIN_CAPABILITIES,
    "status_query": STATUS_QUERY,
    "service_info": SERVICE_INFO_QUERY,

    # Error scenarios
    "invalid_service": INVALID_SERVICE_NAME,
    "multiple_restarts": MULTIPLE_RESTARTS,
}


def get_workflow_prompt(workflow_name: str, **params) -> str:
    """
    Get a workflow prompt template with parameter substitution.

    Args:
        workflow_name: Name of workflow template
        **params: Parameters to substitute into template

    Returns:
        Formatted prompt string

    Raises:
        KeyError: If workflow_name not found

    Examples:
        >>> get_workflow_prompt("health_check")
        "Check the overall system health..."

        >>> get_workflow_prompt("repair_deterministic")
        "Check system health. If the api-gateway..."
    """
    template = WORKFLOW_TEMPLATES[workflow_name]
    return template.format(**params) if params else template


def list_workflows() -> Dict[str, str]:
    """
    List all available workflow templates.

    Returns:
        Dictionary mapping workflow names to their descriptions
    """
    return {
        # Infrastructure
        "health_check": "Check overall system health",
        "repair_deterministic": "Deterministic repair workflow (for load testing)",
        "repair_open_ended": "Open-ended repair workflow (agent decides actions)",
        "diagnostics": "Run diagnostics on a service",
        "database_check": "Check database status",
        "config_update": "Update service configuration",

        # Tool chaining
        "multi_step_repair": "Multi-step repair with progressive diagnosis",
        "progressive_diagnosis": "Progressive diagnosis workflow",

        # Chat
        "explain_capabilities": "Ask agent to explain its capabilities",
        "status_query": "Query system status",
        "service_info": "Query specific service information",

        # Error scenarios
        "invalid_service": "Test with invalid service name",
        "multiple_restarts": "Restart multiple services sequentially",
    }

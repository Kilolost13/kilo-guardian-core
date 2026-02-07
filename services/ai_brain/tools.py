"""
Tool/Function calling system for Kilo AI Brain.

Enables Kilo to execute commands, query services, and gather real-time data.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional, Callable
import httpx

logger = logging.getLogger(__name__)

# Tool registry
TOOLS: Dict[str, Callable] = {}

# Lazy load Kubernetes client
_k8s_client = None
_k8s_core_v1 = None


def _get_k8s_client():
    """Get or initialize Kubernetes client."""
    global _k8s_client, _k8s_core_v1
    if _k8s_client is None:
        try:
            from kubernetes import client, config
            # Load in-cluster config (when running in K8s pod)
            config.load_incluster_config()
            _k8s_client = client.ApiClient()
            _k8s_core_v1 = client.CoreV1Api(_k8s_client)
            logger.info("Kubernetes client initialized (in-cluster)")
        except Exception as e:
            logger.error(f"Failed to initialize K8s client: {e}")
            return None
    return _k8s_core_v1


def register_tool(func: Callable) -> Callable:
    """Decorator to register a tool function."""
    TOOLS[func.__name__] = func
    return func


# ============================================================================
# K8s / Kubectl Tools
# ============================================================================

@register_tool
def kubectl_get_pods(namespace: str = "kilo-guardian") -> Dict[str, Any]:
    """
    Get status of all pods in a namespace.

    Args:
        namespace: K8s namespace (default: kilo-guardian)

    Returns:
        Dictionary with pod names, status, restarts, age
    """
    try:
        k8s = _get_k8s_client()
        if k8s is None:
            return {"error": "Kubernetes client not available"}

        pod_list = k8s.list_namespaced_pod(namespace=namespace)
        pods = []

        for pod in pod_list.items:
            name = pod.metadata.name
            status = pod.status.phase

            # Count restarts
            restarts = 0
            ready_containers = 0
            total_containers = 0

            if pod.status.container_statuses:
                total_containers = len(pod.status.container_statuses)
                for cs in pod.status.container_statuses:
                    restarts += cs.restart_count
                    if cs.ready:
                        ready_containers += 1

            pods.append({
                "name": name,
                "status": status,
                "ready": f"{ready_containers}/{total_containers}",
                "restarts": restarts,
                "age": str(pod.metadata.creation_timestamp) if pod.metadata.creation_timestamp else "unknown"
            })

        return {"pods": pods, "count": len(pods)}

    except Exception as e:
        logger.error(f"kubectl_get_pods error: {e}")
        return {"error": str(e)}


@register_tool
def kubectl_get_services(namespace: str = "kilo-guardian") -> Dict[str, Any]:
    """
    Get status of all services in a namespace.

    Args:
        namespace: K8s namespace (default: kilo-guardian)

    Returns:
        Dictionary with service names, cluster IPs, ports
    """
    try:
        k8s = _get_k8s_client()
        if k8s is None:
            return {"error": "Kubernetes client not available"}

        svc_list = k8s.list_namespaced_service(namespace=namespace)
        services = []

        for svc in svc_list.items:
            name = svc.metadata.name
            cluster_ip = svc.spec.cluster_ip or "None"

            ports = []
            if svc.spec.ports:
                ports = [f"{p.port}/{p.protocol}" for p in svc.spec.ports]

            services.append({
                "name": name,
                "cluster_ip": cluster_ip,
                "ports": ", ".join(ports)
            })

        return {"services": services, "count": len(services)}

    except Exception as e:
        logger.error(f"kubectl_get_services error: {e}")
        return {"error": str(e)}


@register_tool
def kubectl_logs(pod_name: str, namespace: str = "kilo-guardian",
                tail: int = 50) -> Dict[str, Any]:
    """
    Get logs from a pod.

    Args:
        pod_name: Name of the pod
        namespace: K8s namespace (default: kilo-guardian)
        tail: Number of lines to return (default: 50)

    Returns:
        Dictionary with log lines
    """
    try:
        k8s = _get_k8s_client()
        if k8s is None:
            return {"error": "Kubernetes client not available"}

        logs = k8s.read_namespaced_pod_log(
            name=pod_name,
            namespace=namespace,
            tail_lines=tail
        )

        return {
            "pod": pod_name,
            "logs": logs,
            "lines": len(logs.split("\n"))
        }

    except Exception as e:
        logger.error(f"kubectl_logs error: {e}")
        return {"error": str(e)}


@register_tool
def kubectl_describe_pod(pod_name: str, namespace: str = "kilo-guardian") -> Dict[str, Any]:
    """
    Get detailed information about a pod.

    Args:
        pod_name: Name of the pod
        namespace: K8s namespace (default: kilo-guardian)

    Returns:
        Dictionary with pod details, events, status
    """
    try:
        k8s = _get_k8s_client()
        if k8s is None:
            return {"error": "Kubernetes client not available"}

        pod = k8s.read_namespaced_pod(name=pod_name, namespace=namespace)

        # Format pod info
        info = {
            "name": pod.metadata.name,
            "namespace": pod.metadata.namespace,
            "status": pod.status.phase,
            "node": pod.spec.node_name,
            "ip": pod.status.pod_ip,
            "conditions": [
                {
                    "type": c.type,
                    "status": c.status,
                    "reason": c.reason
                }
                for c in (pod.status.conditions or [])
            ],
            "containers": [
                {
                    "name": cs.name,
                    "ready": cs.ready,
                    "restart_count": cs.restart_count,
                    "state": str(cs.state)
                }
                for cs in (pod.status.container_statuses or [])
            ]
        }

        return {"pod": pod_name, "details": info}

    except Exception as e:
        logger.error(f"kubectl_describe_pod error: {e}")
        return {"error": str(e)}


# ============================================================================
# Service Query Tools
# ============================================================================

@register_tool
def query_reminder_service() -> Dict[str, Any]:
    """
    Query the reminder service for all reminders.

    Returns:
        Dictionary with reminders list
    """
    try:
        reminder_url = os.environ.get("REMINDER_URL", "http://kilo-reminder:9002")
        response = httpx.get(f"{reminder_url}/", timeout=10)
        response.raise_for_status()
        return {"reminders": response.json(), "count": len(response.json())}
    except Exception as e:
        logger.error(f"query_reminder_service error: {e}")
        return {"error": str(e)}


@register_tool
def query_financial_service() -> Dict[str, Any]:
    """
    Query the financial service for spending summary.

    Returns:
        Dictionary with financial summary
    """
    try:
        financial_url = os.environ.get("FINANCIAL_URL", "http://kilo-financial:9005")

        # Get summary (better than individual endpoints)
        summary_resp = httpx.get(f"{financial_url}/summary", timeout=10)
        summary_resp.raise_for_status()
        summary = summary_resp.json()

        return {
            "total_expenses": abs(summary.get("total_expenses", 0)),
            "total_income": summary.get("total_income", 0),
            "balance": summary.get("balance", 0),
            "expense_count": summary.get("expense_count", 0),
            "income_count": summary.get("income_count", 0),
            "summary": summary
        }
    except Exception as e:
        logger.error(f"query_financial_service error: {e}")
        return {"error": str(e)}


@register_tool
def query_habits_service() -> Dict[str, Any]:
    """
    Query the habits service for habit tracking.

    Returns:
        Dictionary with habits list and completion status
    """
    try:
        habits_url = os.environ.get("HABITS_URL", "http://kilo-habits:9003")
        response = httpx.get(f"{habits_url}/", timeout=10)  # Fixed: Use / not /habits
        response.raise_for_status()
        habits = response.json()

        return {
            "habits": habits,
            "count": len(habits),
            "completed_today": sum(1 for h in habits if h.get("completed_today", False))
        }
    except Exception as e:
        logger.error(f"query_habits_service error: {e}")
        return {"error": str(e)}


@register_tool
def query_meds_service() -> Dict[str, Any]:
    """
    Query the medications service.

    Returns:
        Dictionary with medications list
    """
    try:
        meds_url = os.environ.get("MEDS_URL", "http://kilo-meds:9001")
        response = httpx.get(f"{meds_url}/", timeout=10)
        response.raise_for_status()
        meds = response.json()

        return {"medications": meds, "count": len(meds)}
    except Exception as e:
        logger.error(f"query_meds_service error: {e}")
        return {"error": str(e)}


# ============================================================================
# Library of Truth Tools
# ============================================================================

@register_tool
def search_library(query: str, limit: int = 5) -> Dict[str, Any]:
    """
    Search the Library of Truth for relevant passages.

    Args:
        query: Search query
        limit: Maximum number of results (default: 5)

    Returns:
        Dictionary with matching passages from books
    """
    try:
        library_url = os.environ.get("LIBRARY_URL", "http://kilo-library:9006")
        response = httpx.get(
            f"{library_url}/search",
            params={"q": query, "limit": limit},
            timeout=10
        )
        response.raise_for_status()
        results = response.json()

        return {
            "results": results,
            "count": len(results),
            "query": query
        }
    except Exception as e:
        logger.error(f"search_library error: {e}")
        return {"error": str(e)}


@register_tool
def list_library_books() -> Dict[str, Any]:
    """
    List all books in the Library of Truth.

    Returns:
        Dictionary with list of books
    """
    try:
        library_url = os.environ.get("LIBRARY_URL", "http://kilo-library:9006")
        response = httpx.get(f"{library_url}/books", timeout=10)
        response.raise_for_status()
        books = response.json()

        return {"books": books, "count": len(books)}
    except Exception as e:
        logger.error(f"list_library_books error: {e}")
        return {"error": str(e)}


# ============================================================================
# ML Engine Tools
# ============================================================================

@register_tool
def detect_patterns(data_type: str, lookback_days: int = 30) -> Dict[str, Any]:
    """
    Use ML engine to detect patterns in user data.

    Args:
        data_type: Type of data to analyze (spending, habits, meds)
        lookback_days: Number of days to analyze (default: 30)

    Returns:
        Dictionary with detected patterns and insights
    """
    try:
        ml_url = os.environ.get("ML_URL", "http://kilo-ml-engine:9007")
        response = httpx.post(
            f"{ml_url}/detect_patterns",
            json={"data_type": data_type, "lookback_days": lookback_days},
            timeout=20
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"detect_patterns error: {e}")
        return {"error": str(e), "patterns": []}


@register_tool
def generate_insights(context: str) -> Dict[str, Any]:
    """
    Use ML engine to generate insights from context.

    Args:
        context: Context string describing what to analyze

    Returns:
        Dictionary with generated insights
    """
    try:
        ml_url = os.environ.get("ML_URL", "http://kilo-ml-engine:9007")
        response = httpx.post(
            f"{ml_url}/generate_insights",
            json={"context": context},
            timeout=20
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"generate_insights error: {e}")
        return {"error": str(e), "insights": []}


# ============================================================================
# Cross-Service Analysis Tools
# ============================================================================

@register_tool
def analyze_spending_habits_correlation() -> Dict[str, Any]:
    """
    Analyze correlation between spending and habit completion.

    Returns:
        Dictionary with correlation analysis
    """
    try:
        # Get financial data
        financial_data = query_financial_service()

        # Get habits data
        habits_data = query_habits_service()

        # Simple correlation analysis
        total_spending = financial_data.get("total_expenses", 0)
        habits_completed = habits_data.get("completed_today", 0)
        total_habits = habits_data.get("count", 1)

        completion_rate = (habits_completed / total_habits * 100) if total_habits > 0 else 0

        return {
            "total_spending": total_spending,
            "habits_completed": habits_completed,
            "total_habits": total_habits,
            "completion_rate": completion_rate,
            "correlation": "High spending may correlate with low habit completion"
                          if total_spending > 1000 and completion_rate < 50
                          else "Spending and habits appear balanced"
        }
    except Exception as e:
        logger.error(f"analyze_spending_habits_correlation error: {e}")
        return {"error": str(e)}


@register_tool
def check_medication_adherence() -> Dict[str, Any]:
    """
    Check medication adherence patterns.

    Returns:
        Dictionary with adherence analysis
    """
    try:
        meds_data = query_meds_service()
        medications = meds_data.get("medications", [])

        # Get reminders for medication context
        reminders_data = query_reminder_service()
        reminders = reminders_data.get("reminders", [])

        med_reminders = [r for r in reminders if "med" in r.get("title", "").lower()
                        or any(m.get("name", "").lower() in r.get("title", "").lower()
                              for m in medications)]

        return {
            "total_medications": len(medications),
            "medication_reminders": len(med_reminders),
            "medications": medications,
            "upcoming_reminders": med_reminders[:3]
        }
    except Exception as e:
        logger.error(f"check_medication_adherence error: {e}")
        return {"error": str(e)}


# ============================================================================
# Tool Execution Engine
# ============================================================================

def get_tool_descriptions() -> List[Dict[str, Any]]:
    """
    Get descriptions of all available tools for LLM.

    Returns:
        List of tool descriptions in function calling format
    """
    descriptions = []

    for name, func in TOOLS.items():
        # Extract docstring
        doc = func.__doc__ or "No description available"

        # Parse function signature
        import inspect
        sig = inspect.signature(func)

        params = {}
        for param_name, param in sig.parameters.items():
            param_type = "string"
            if param.annotation != inspect.Parameter.empty:
                if param.annotation == int:
                    param_type = "integer"
                elif param.annotation == bool:
                    param_type = "boolean"

            params[param_name] = {
                "type": param_type,
                "description": f"Parameter: {param_name}"
            }

        descriptions.append({
            "name": name,
            "description": doc.strip().split("\n\n")[0],  # First paragraph only
            "parameters": {
                "type": "object",
                "properties": params,
                "required": [p for p in sig.parameters.keys()
                           if sig.parameters[p].default == inspect.Parameter.empty]
            }
        })

    return descriptions


def execute_tool(tool_name: str, **kwargs) -> Dict[str, Any]:
    """
    Execute a tool by name with given arguments.

    Args:
        tool_name: Name of the tool to execute
        **kwargs: Arguments to pass to the tool

    Returns:
        Tool execution result
    """
    if tool_name not in TOOLS:
        return {"error": f"Unknown tool: {tool_name}"}

    try:
        logger.info(f"Executing tool: {tool_name} with args: {kwargs}")
        result = TOOLS[tool_name](**kwargs)
        logger.info(f"Tool {tool_name} completed successfully")
        return result
    except Exception as e:
        logger.error(f"Tool execution error ({tool_name}): {e}")
        return {"error": f"Tool execution failed: {str(e)}"}


def detect_needed_tools(query: str) -> List[str]:
    """
    Detect which tools are needed based on user query.

    Args:
        query: User's question

    Returns:
        List of tool names to execute
    """
    query_lower = query.lower()
    needed = []

    # K8s queries
    if any(kw in query_lower for kw in ["pod", "k3s", "cluster", "service", "deployment"]):
        needed.append("kubectl_get_pods")
        if "service" in query_lower:
            needed.append("kubectl_get_services")

    # Service queries
    if any(kw in query_lower for kw in ["reminder", "remind"]):
        needed.append("query_reminder_service")

    if any(kw in query_lower for kw in ["spend", "money", "financial", "budget"]):
        needed.append("query_financial_service")

    if any(kw in query_lower for kw in ["habit"]):
        needed.append("query_habits_service")

    if any(kw in query_lower for kw in ["med", "medication", "prescription"]):
        needed.append("query_meds_service")

    # Library queries
    if any(kw in query_lower for kw in ["book", "library", "knowledge", "learn about"]):
        needed.append("search_library")

    # Cross-service analysis
    if "correlation" in query_lower or ("spending" in query_lower and "habit" in query_lower):
        needed.append("analyze_spending_habits_correlation")

    if "adherence" in query_lower or "taking med" in query_lower:
        needed.append("check_medication_adherence")

    # Pattern detection
    if any(kw in query_lower for kw in ["pattern", "trend", "insight", "analyze"]):
        if "spend" in query_lower:
            needed.append("detect_patterns")

    return needed


if __name__ == "__main__":
    # Test tools
    logging.basicConfig(level=logging.INFO)
    print(f"Registered {len(TOOLS)} tools:")
    for name in TOOLS.keys():
        print(f"  - {name}")

    # Test tool descriptions
    descriptions = get_tool_descriptions()
    print(f"\nTool descriptions: {json.dumps(descriptions[:2], indent=2)}")

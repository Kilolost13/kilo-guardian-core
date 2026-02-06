"""
unified_knowledge.py: Unified knowledge base for Kilo Guardian
Combines user-taught facts (UserContext) and global reference library (Library of Truth)
"""

import os

import requests

from .user_context import UserContext

# Path to the Flask API for Library of Truth
LIBRARY_API_URL = os.environ.get(
    "LIBRARY_OF_TRUTH_API", "http://localhost:5000/api/search"
)


def query_user_fact(user: str, fact_key: str, category: str = "general"):
    ctx = UserContext(user_id=user)
    value = ctx.get_fact(fact_key, category)
    if value is not None:
        return {"result": value, "source": "user_fact", "found": True}
    return None


def query_library_of_truth(query: str):
    try:
        resp = requests.get(LIBRARY_API_URL, params={"q": query}, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if data:
                return {"result": data, "source": "library_of_truth", "found": True}
        return {"result": None, "source": "library_of_truth", "found": False}
    except Exception as e:
        return {
            "result": None,
            "source": "library_of_truth",
            "found": False,
            "error": str(e),
        }


def unified_knowledge_lookup(user: str, query: str, category: str = "general"):
    # 1. Try user-taught fact
    user_fact = query_user_fact(user, query, category)
    if user_fact:
        return user_fact
    # 2. Fallback to Library of Truth
    return query_library_of_truth(query)

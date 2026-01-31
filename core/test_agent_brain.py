#!/usr/bin/env python3
"""
Test script for Kilo Agent with Brain integration
"""

import sys
sys.path.insert(0, '/home/brain_ai/projects/kilo/core')

from kilo_agent_brain import get_kilo_brain

def test_brain_basics():
    """Test basic brain functionality"""
    print("=" * 70)
    print("TESTING KILO AGENT BRAIN")
    print("=" * 70)
    print()

    # Create brain
    print("1. Initializing brain...")
    brain = get_kilo_brain()
    print("   ✓ Brain created")
    print()

    # Test tool schemas
    print("2. Checking tool schemas...")
    schemas = brain.get_tool_schemas()
    print(f"   ✓ {len(schemas)} tools available:")
    for tool in schemas:
        print(f"     - {tool['name']}: {tool['description'][:60]}...")
    print()

    # Test cluster analysis (will only work if Ollama is running)
    print("3. Testing cluster state analysis...")
    test_data = {
        "pods": {
            "nginx-abc": {
                "status": "CrashLoopBackOff",
                "restarts": 5
            },
            "redis-xyz": {
                "status": "Running",
                "restarts": 0
            }
        },
        "nodes": {
            "node1": {"status": "Ready"}
        }
    }

    print("   Analyzing test cluster data...")
    try:
        proposals = brain.analyze_cluster_state(test_data)
        if proposals:
            print(f"   ✓ Brain generated {len(proposals)} proposals:")
            for p in proposals:
                print(f"     - Action: {p['action_type']}")
                print(f"       Tool: {p['tool']}")
                print(f"       Reasoning: {p['reasoning'][:80]}...")
                print()
        else:
            print("   ⚠️ No proposals generated")
            print("      (This is OK if Ollama isn't running or model doesn't support function calling)")
    except Exception as e:
        print(f"   ⚠️ Error: {e}")
        print("      (Make sure Ollama is running: 'ollama serve')")
    print()

    print("=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)
    print()
    print("Next steps:")
    print("1. Make sure Ollama is running: ollama serve")
    print("2. Pull a model: ollama pull llama3.2")
    print("3. Launch agent UI: ~/projects/kilo/scripts/launch_kilo_agent.sh")
    print()

if __name__ == "__main__":
    test_brain_basics()

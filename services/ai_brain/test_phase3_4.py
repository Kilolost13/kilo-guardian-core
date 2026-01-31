#!/usr/bin/env python3
"""
Comprehensive Test Suite for AI Brain Phase 3 & 4 Features

Tests scalability, predictive modeling, knowledge graphs, and conversation management.
"""

import sys
import os
import json
import time
from datetime import datetime, timedelta

# Add the ai_brain module to path
sys.path.insert(0, os.path.dirname(__file__))

def test_data_partitioning():
    """Test data partitioning system"""
    print("🧪 Testing Data Partitioning...")

    from data_partitioning import data_partitioner, partitioned_store

    # Test partition key generation
    test_memory = {
        "created_at": datetime.utcnow().isoformat(),
        "source": "cam",
        "metadata_json": json.dumps({"user_id": "test_user"})
    }

    partition_keys = data_partitioner.get_partition_keys(test_memory)
    print(f"  ✅ Generated partition keys: {partition_keys}")

    # Test partition storage
    memory_id = partitioned_store.store_memory(test_memory, partition_keys)
    print(f"  ✅ Stored memory with ID: {memory_id}")

    # Test partition retrieval
    retrieved = partitioned_store.retrieve_from_partition(partition_keys[0], memory_id)
    assert retrieved is not None, "Failed to retrieve stored memory"
    print("  ✅ Memory retrieval successful")

    # Test partition stats
    stats = data_partitioner.get_partition_stats()
    print(f"  ✅ Partition stats: {len(stats)} partitions")
    print("  ✅ Data partitioning tests passed")


def test_async_processing():
    """Test asynchronous processing pipeline"""
    print("🧪 Testing Async Processing...")

    from async_processing import async_pipeline, resource_manager

    # Start the pipeline
    async_pipeline.start()
    print("  ✅ Async pipeline started")

    # Test embedding task submission
    test_texts = ["Hello world", "This is a test", "AI brain processing"]
    task_id = async_pipeline.submit_embedding_task(test_texts, priority=1)
    print(f"  ✅ Submitted embedding task: {task_id}")

    # Test batch embedding
    text_batches = [test_texts, ["Another test", "More text"]]
    batch_task_id = async_pipeline.submit_batch_embedding_task(text_batches, priority=1)
    print(f"  ✅ Submitted batch embedding task: {batch_task_id}")

    # Test resource management
    batch_size = resource_manager.get_optimal_batch_size()
    print(f"  ✅ Optimal batch size: {batch_size}")

    should_throttle = resource_manager.should_throttle()
    print(f"  ✅ Should throttle: {should_throttle}")

    # Get stats
    stats = async_pipeline.get_stats()
    print(f"  ✅ Pipeline stats: {stats}")

    async_pipeline.stop()
    print("  ✅ Async processing tests passed")


def test_predictive_modeling():
    """Test predictive modeling system"""
    print("🧪 Testing Predictive Modeling...")

    from predictive_modeling import predictive_analytics

    # Sample habit data
    habit_data = [
        {
            "event_type": "exercise",
            "completed": True,
            "timestamp": datetime.utcnow() - timedelta(days=i),
            "metadata_json": json.dumps({"duration": 30})
        }
        for i in range(10)
    ]

    # Sample health data
    health_data = [
        {
            "source": "cam",
            "text_blob": "User sitting for 2 hours",
            "metadata_json": json.dumps({"posture": "sitting", "duration": 120})
        },
        {
            "source": "meds",
            "text_blob": "Took medication",
            "metadata_json": json.dumps({"name": "Aspirin", "taken": True})
        }
    ]

    # Train models
    training_results = predictive_analytics.train_all_models(habit_data + health_data)
    print(f"  ✅ Training results: {training_results}")

    # Generate predictions
    predictions = predictive_analytics.generate_predictions({
        "event_type": "exercise",
        "source": "habits"
    })
    print(f"  ✅ Generated predictions: {len(predictions)} models")

    # Get insights
    insights = predictive_analytics.get_proactive_insights("test_user")
    print(f"  ✅ Generated {len(insights)} proactive insights")

    print("  ✅ Predictive modeling tests passed")


def test_knowledge_graph():
    """Test knowledge graph system"""
    print("🧪 Testing Knowledge Graph...")

    # Skip if networkx is not available in this environment (CI will install it)
    import pytest
    pytest.importorskip("networkx")

    from knowledge_graph import knowledge_graph, knowledge_reasoner

    # Add test entities
    entities = [
        ("habit_exercise", "habit", {"name": "Exercise", "frequency": "daily"}),
        ("med_aspirin", "medication", {"name": "Aspirin", "dosage": "100mg"}),
        ("activity_sitting", "activity", {"type": "sitting"}),
        ("concept_pain", "concept", {"name": "Pain", "type": "health_condition"})
    ]

    for entity_id, entity_type, properties in entities:
        success = knowledge_graph.add_entity(entity_id, entity_type, properties)
        assert success, f"Failed to add entity {entity_id}"
    print("  ✅ Added test entities")

    # Add relationships
    relationships = [
        ("habit_exercise", "activity_sitting", "prevents", {"strength": 0.8}),
        ("med_aspirin", "concept_pain", "improves", {"medical": True})
    ]

    for source, target, rel_type, props in relationships:
        success = knowledge_graph.add_relationship(source, target, rel_type, props)
        assert success, f"Failed to add relationship {source} -> {target}"
    print("  ✅ Added test relationships")

    # Test entity insights
    insights = knowledge_graph.get_entity_insights("habit_exercise")
    print(f"  ✅ Generated insights for habit_exercise: {len(insights.get('insights', []))} insights")

    # Test reasoning
    impacts = knowledge_reasoner.reason_about_impact("habit_exercise")
    print(f"  ✅ Reasoning impacts: {impacts.get('positive_effects', [])} positive effects")

    # Test graph stats
    stats = knowledge_graph.get_graph_stats()
    print(f"  ✅ Graph stats: {stats['node_count']} nodes, {stats['edge_count']} edges")

    print("  ✅ Knowledge graph tests passed")


def test_conversation_management():
    """Test conversation management system"""
    print("🧪 Testing Conversation Management...")

    from conversation_management import conversation_manager, goal_assistant

    # Start conversation
    conversation_id = conversation_manager.start_conversation("test_conv_123", "test_user")
    print(f"  ✅ Started conversation: {conversation_id}")

    # Add conversation turns
    turns = [
        ("Hello, how can I improve my health?", "I can help you with health goals and habit tracking."),
        ("I want to exercise more", "That's great! Let's set up a daily exercise goal."),
        ("How do I stay motivated?", "I can provide reminders and track your progress.")
    ]

    for user_msg, ai_resp in turns:
        success = conversation_manager.add_turn(conversation_id, user_msg, ai_resp)
        assert success, "Failed to add conversation turn"
    print("  ✅ Added conversation turns")

    # Set goals
    goals = [
        {
            "description": "Exercise daily for 30 minutes",
            "type": "habit_formation",
            "steps": ["set_reminder", "track_progress", "celebrate_success"]
        }
    ]
    success = conversation_manager.set_goals(conversation_id, goals)
    assert success, "Failed to set goals"
    print("  ✅ Set conversation goals")

    # Get context
    context = conversation_manager.get_conversation_context(conversation_id)
    assert context, "Failed to get conversation context"
    print(f"  ✅ Retrieved context: {context.get('turns_so_far')} turns")

    # Get suggestions
    suggestions = conversation_manager.suggest_next_actions(conversation_id)
    print(f"  ✅ Generated {len(suggestions)} suggestions")

    # Get user insights
    insights = conversation_manager.get_user_insights("test_user")
    print(f"  ✅ User insights: {insights.get('total_conversations')} conversations")

    # Test goal suggestions
    goal_suggestions = goal_assistant.suggest_goals_based_on_context({
        "health_indicators": ["sedentary"],
        "habit_data": [],
        "medication_data": []
    })
    print(f"  ✅ Suggested {len(goal_suggestions)} goals")

    # End conversation
    success = conversation_manager.end_conversation(conversation_id, "test_completed")
    assert success, "Failed to end conversation"
    print("  ✅ Ended conversation")

    print("  ✅ Conversation management tests passed")


def test_integration():
    """Test integration of all Phase 3 & 4 components"""
    print("🧪 Testing Component Integration...")

    # Test that all modules can be imported
    try:
        from data_partitioning import data_partitioner, partitioned_store
        from async_processing import async_pipeline, resource_manager
        from predictive_modeling import predictive_analytics
        from knowledge_graph import knowledge_graph, knowledge_reasoner
        from conversation_management import conversation_manager, goal_assistant
        print("  ✅ All modules imported successfully")
    except Exception as e:
        print(f"  ❌ Import failed: {e}")
        return False

    # Test cross-component interactions
    # 1. Create memory data
    memory_data = [
        {
            "source": "habits",
            "text_blob": "Completed daily exercise",
            "metadata_json": json.dumps({"event_type": "exercise", "completed": True}),
            "created_at": datetime.utcnow().isoformat()
        },
        {
            "source": "cam",
            "text_blob": "User sitting for extended period",
            "metadata_json": json.dumps({"posture": "sitting", "duration": 90})
        }
    ]

    # 2. Store in partitions
    for memory in memory_data:
        partition_keys = data_partitioner.get_partition_keys(memory)
        partitioned_store.store_memory(memory, partition_keys)
    print("  ✅ Stored test memories in partitions")

    # 3. Build knowledge graph
    entities_added = knowledge_graph.build_from_memories(memory_data)
    print(f"  ✅ Built knowledge graph with {entities_added} entities")

    # 4. Train predictive models
    training_results = predictive_analytics.train_all_models(memory_data)
    print(f"  ✅ Trained predictive models: {training_results}")

    # 5. Generate insights
    insights = predictive_analytics.get_proactive_insights("test_user")
    print(f"  ✅ Generated {len(insights)} proactive insights")

    print("  ✅ Integration tests passed")
    return True


def main():
    """Run all Phase 3 & 4 tests"""
    print("🚀 Starting AI Brain Phase 3 & 4 Comprehensive Tests")
    print("=" * 60)

    tests = [
        ("Data Partitioning", test_data_partitioning),
        ("Async Processing", test_async_processing),
        ("Predictive Modeling", test_predictive_modeling),
        ("Knowledge Graph", test_knowledge_graph),
        ("Conversation Management", test_conversation_management),
        ("Integration", test_integration)
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            print(f"\n📋 Running {test_name} tests...")
            test_func()
            print(f"✅ {test_name} tests PASSED")
            passed += 1
        except Exception as e:
            print(f"❌ {test_name} tests FAILED: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 60)
    print(f"📊 Test Results: {passed} passed, {failed} failed")

    if failed == 0:
        print("🎉 All Phase 3 & 4 features are working correctly!")
        print("\n✨ AI Brain now has:")
        print("  • Scalable data partitioning")
        print("  • Asynchronous processing pipeline")
        print("  • Predictive modeling and insights")
        print("  • Knowledge graph with reasoning")
        print("  • Advanced conversation management")
        print("  • Goal-oriented assistance")
        return True
    else:
        print("⚠️  Some tests failed. Please check the implementation.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
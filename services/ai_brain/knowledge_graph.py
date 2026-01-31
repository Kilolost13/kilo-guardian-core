#!/usr/bin/env python3
"""
Knowledge Graph System for AI Brain

Creates and manages a knowledge graph to connect concepts, entities, and relationships
for enhanced reasoning and context understanding.
"""

import json
from datetime import datetime
from typing import List, Dict, Any, Optional, Set, Tuple
from collections import defaultdict
import networkx as nx
import logging

logger = logging.getLogger(__name__)


class KnowledgeGraph:
    """Knowledge graph for connecting concepts and relationships"""

    def __init__(self):
        self.graph = nx.MultiDiGraph()
        self.entity_types = {
            "person": "People and users",
            "habit": "Habits and routines",
            "medication": "Medications and health",
            "location": "Places and locations",
            "activity": "Activities and events",
            "concept": "Abstract concepts",
            "time": "Time-related entities"
        }
        self.relationship_types = {
            "related_to": "General relationship",
            "causes": "Causal relationship",
            "prevents": "Preventive relationship",
            "improves": "Improvement relationship",
            "worsens": "Negative impact relationship",
            "occurs_at": "Temporal/spatial relationship",
            "belongs_to": "Ownership/containment",
            "similar_to": "Similarity relationship"
        }

    def add_entity(self, entity_id: str, entity_type: str, properties: Dict[str, Any]) -> bool:
        """Add an entity to the knowledge graph"""
        if entity_type not in self.entity_types:
            logger.warning(f"Unknown entity type: {entity_type}")
            return False

        self.graph.add_node(entity_id, **{
            "type": entity_type,
            "properties": properties,
            "created_at": datetime.utcnow(),
            "last_updated": datetime.utcnow()
        })
        return True

    def add_relationship(self, source_id: str, target_id: str,
                        relationship_type: str, properties: Dict[str, Any] = None) -> bool:
        """Add a relationship between entities"""
        if relationship_type not in self.relationship_types:
            logger.warning(f"Unknown relationship type: {relationship_type}")
            return False

        if not self.graph.has_node(source_id) or not self.graph.has_node(target_id):
            logger.warning(f"Source or target entity not found: {source_id} -> {target_id}")
            return False

        self.graph.add_edge(source_id, target_id, **{
            "type": relationship_type,
            "properties": properties or {},
            "created_at": datetime.utcnow(),
            "weight": properties.get("weight", 1.0) if properties else 1.0
        })
        return True

    def find_related_entities(self, entity_id: str, max_depth: int = 2,
                            relationship_types: List[str] = None) -> List[Dict[str, Any]]:
        """Find entities related to the given entity"""
        if not self.graph.has_node(entity_id):
            return []

        related = []

        # Get directly connected entities
        neighbors = list(self.graph.neighbors(entity_id))
        for neighbor in neighbors:
            edge_data = self.graph.get_edge_data(entity_id, neighbor)
            for edge_key, edge_attrs in edge_data.items():
                rel_type = edge_attrs.get("type")
                if relationship_types is None or rel_type in relationship_types:
                    related.append({
                        "entity_id": neighbor,
                        "relationship": rel_type,
                        "properties": edge_attrs.get("properties", {}),
                        "depth": 1
                    })

        # Explore deeper if requested
        if max_depth > 1:
            visited = set([entity_id])
            current_level = set(neighbors)

            for depth in range(2, max_depth + 1):
                next_level = set()
                for node in current_level:
                    if node not in visited:
                        visited.add(node)
                        node_neighbors = set(self.graph.neighbors(node))
                        next_level.update(node_neighbors)

                        for neighbor in node_neighbors:
                            if neighbor not in visited:
                                edge_data = self.graph.get_edge_data(node, neighbor)
                                for edge_key, edge_attrs in edge_data.items():
                                    rel_type = edge_attrs.get("type")
                                    if relationship_types is None or rel_type in relationship_types:
                                        related.append({
                                            "entity_id": neighbor,
                                            "relationship": f"{rel_type} (via {node})",
                                            "properties": edge_attrs.get("properties", {}),
                                            "depth": depth
                                        })

                current_level = next_level

        return related

    def query_path(self, start_entity: str, end_entity: str) -> List[List[str]]:
        """Find paths between two entities"""
        if not (self.graph.has_node(start_entity) and self.graph.has_node(end_entity)):
            return []

        try:
            paths = list(nx.all_simple_paths(self.graph, start_entity, end_entity, cutoff=4))
            return paths
        except:
            return []

    def get_entity_insights(self, entity_id: str) -> Dict[str, Any]:
        """Generate insights about an entity based on its connections"""
        if not self.graph.has_node(entity_id):
            return {}

        node_data = self.graph.nodes[entity_id]
        entity_type = node_data.get("type")

        # Analyze relationships
        incoming = self.graph.in_edges(entity_id, data=True)
        outgoing = self.graph.out_edges(entity_id, data=True)

        relationship_summary = defaultdict(int)
        for _, _, data in incoming:
            relationship_summary[data.get("type", "unknown")] += 1
        for _, _, data in outgoing:
            relationship_summary[data.get("type", "unknown")] += 1

        # Generate insights based on entity type and relationships
        insights = []

        if entity_type == "habit":
            if relationship_summary.get("improves", 0) > 0:
                insights.append("This habit has positive health impacts")
            if relationship_summary.get("related_to", 0) > 2:
                insights.append("This habit is connected to multiple aspects of your life")

        elif entity_type == "medication":
            if relationship_summary.get("prevents", 0) > 0:
                insights.append("This medication helps prevent certain conditions")
            if relationship_summary.get("causes", 0) > 0:
                insights.append("Be aware of potential side effects")

        return {
            "entity_type": entity_type,
            "relationship_count": len(incoming) + len(outgoing),
            "relationship_summary": dict(relationship_summary),
            "insights": insights,
            "properties": node_data.get("properties", {})
        }

    def build_from_memories(self, memories: List[Dict]) -> int:
        """Build knowledge graph from memory data"""
        entities_added = 0
        relationships_added = 0

        for memory in memories:
            try:
                entities, relationships = self._extract_entities_and_relationships(memory)
                entities_added += len(entities)
                relationships_added += len(relationships)

                # Add entities
                for entity in entities:
                    self.add_entity(**entity)

                # Add relationships
                for relationship in relationships:
                    self.add_relationship(**relationship)

            except Exception as e:
                logger.error(f"Failed to process memory for knowledge graph: {e}")
                continue

        logger.info(f"Knowledge graph built: {entities_added} entities, {relationships_added} relationships")
        return entities_added + relationships_added

    def _extract_entities_and_relationships(self, memory: Dict) -> Tuple[List[Dict], List[Dict]]:
        """Extract entities and relationships from a memory"""
        entities = []
        relationships = []

        text_blob = memory.get("text_blob", "")
        source = memory.get("source", "unknown")
        metadata = memory.get("metadata_json")

        if metadata:
            try:
                meta_dict = json.loads(metadata)
            except:
                meta_dict = {}
        else:
            meta_dict = {}

        # Extract entities based on source
        if source == "habits":
            # Extract habit-related entities
            habit_type = meta_dict.get("event_type", "unknown_habit")
            entities.append({
                "entity_id": f"habit_{habit_type}",
                "entity_type": "habit",
                "properties": {
                    "name": habit_type,
                    "source": "habits",
                    "frequency": meta_dict.get("frequency", 0)
                }
            })

        elif source == "meds":
            # Extract medication entities
            med_name = meta_dict.get("name", "unknown_med")
            entities.append({
                "entity_id": f"med_{med_name}",
                "entity_type": "medication",
                "properties": {
                    "name": med_name,
                    "dosage": meta_dict.get("dosage"),
                    "schedule": meta_dict.get("schedule", [])
                }
            })

        elif source == "cam":
            # Extract activity/location entities
            posture = meta_dict.get("posture", "unknown")
            entities.append({
                "entity_id": f"activity_{posture}",
                "entity_type": "activity",
                "properties": {
                    "type": posture,
                    "source": "camera"
                }
            })

        # Create relationships based on patterns
        # This is a simplified implementation - real NLP would extract more sophisticated relationships

        # Link habits to health outcomes
        if source == "habits" and "exercise" in text_blob.lower():
            # Create the activity entity if it doesn't exist
            entities.append({
                "entity_id": "activity_exercise",
                "entity_type": "activity",
                "properties": {"type": "exercise", "source": "inferred"}
            })
            relationships.append({
                "source_id": f"habit_{meta_dict.get('event_type', 'unknown')}",
                "target_id": "activity_exercise",
                "relationship_type": "related_to",
                "properties": {"strength": 0.8}
            })

        # Link medications to health conditions
        if source == "meds" and "blood pressure" in text_blob.lower():
            entities.append({
                "entity_id": "concept_blood_pressure",
                "entity_type": "concept",
                "properties": {"name": "Blood Pressure", "type": "health_metric"}
            })
            relationships.append({
                "source_id": f"med_{meta_dict.get('name', 'unknown')}",
                "target_id": "concept_blood_pressure",
                "relationship_type": "improves",
                "properties": {"medical": True}
            })

        return entities, relationships

    def save_graph(self, filepath: str) -> bool:
        """Save the knowledge graph to file"""
        try:
            graph_data = {
                "nodes": dict(self.graph.nodes(data=True)),
                "edges": list(self.graph.edges(data=True, keys=True))
            }

            with open(filepath, 'w') as f:
                json.dump(graph_data, f, default=str, indent=2)

            logger.info(f"Knowledge graph saved to {filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed to save knowledge graph: {e}")
            return False

    def load_graph(self, filepath: str) -> bool:
        """Load the knowledge graph from file"""
        try:
            with open(filepath, 'r') as f:
                graph_data = json.load(f)

            # Rebuild graph
            self.graph = nx.MultiDiGraph()

            # Add nodes
            for node_id, node_data in graph_data.get("nodes", {}).items():
                self.graph.add_node(node_id, **node_data)

            # Add edges
            for edge_data in graph_data.get("edges", []):
                source, target, key, attrs = edge_data
                self.graph.add_edge(source, target, key=key, **attrs)

            logger.info(f"Knowledge graph loaded from {filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed to load knowledge graph: {e}")
            return False

    def get_graph_stats(self) -> Dict[str, Any]:
        """Get statistics about the knowledge graph"""
        return {
            "node_count": self.graph.number_of_nodes(),
            "edge_count": self.graph.number_of_edges(),
            "entity_types": dict(self.graph.degree()),  # Simplified
            "connected_components": nx.number_connected_components(self.graph.to_undirected())
        }


class KnowledgeReasoner:
    """Reasoning engine using the knowledge graph"""

    def __init__(self, knowledge_graph: KnowledgeGraph):
        self.kg = knowledge_graph

    def reason_about_impact(self, action_entity: str, target_entity: str = None) -> Dict[str, Any]:
        """Reason about the impact of an action on targets"""
        impacts = {
            "positive_effects": [],
            "negative_effects": [],
            "related_entities": [],
            "confidence": 0.0
        }

        if not self.kg.graph.has_node(action_entity):
            return impacts

        # Find related entities and their relationships
        related = self.kg.find_related_entities(action_entity, max_depth=2)

        for rel in related:
            rel_type = rel["relationship"]
            entity_id = rel["entity_id"]

            if "improves" in rel_type or "prevents" in rel_type:
                impacts["positive_effects"].append({
                    "entity": entity_id,
                    "relationship": rel_type,
                    "confidence": rel.get("properties", {}).get("weight", 0.5)
                })
            elif "worsens" in rel_type or "causes" in rel_type:
                impacts["negative_effects"].append({
                    "entity": entity_id,
                    "relationship": rel_type,
                    "confidence": rel.get("properties", {}).get("weight", 0.5)
                })

            impacts["related_entities"].append(entity_id)

        # Calculate overall confidence
        all_effects = impacts["positive_effects"] + impacts["negative_effects"]
        if all_effects:
            avg_confidence = sum(e["confidence"] for e in all_effects) / len(all_effects)
            impacts["confidence"] = min(1.0, avg_confidence)

        return impacts

    def suggest_actions(self, current_state: Dict) -> List[Dict[str, Any]]:
        """Suggest actions based on current state"""
        suggestions = []

        # This would analyze current state and suggest beneficial actions
        # Simplified implementation

        state_indicators = current_state.get("indicators", [])

        if "sedentary" in state_indicators:
            suggestions.append({
                "action": "take_walk",
                "reason": "Reduce sedentary time and improve health",
                "confidence": 0.8,
                "expected_impact": "improves cardiovascular health"
            })

        if "medication_due" in state_indicators:
            suggestions.append({
                "action": "take_medication",
                "reason": "Maintain medication adherence",
                "confidence": 0.9,
                "expected_impact": "prevents health complications"
            })

        return suggestions


# Global instances
knowledge_graph = KnowledgeGraph()
knowledge_reasoner = KnowledgeReasoner(knowledge_graph)
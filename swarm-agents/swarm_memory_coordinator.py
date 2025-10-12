#!/usr/bin/env python3
"""
SAFLA Neural Memory Coordinator for TGE Swarm
Manages shared memory, cross-agent communication, and synthesis
"""

import json
import os
import time
from datetime import datetime
from pathlib import Path
import hashlib
import logging
from typing import Dict, List, Any, Optional

class SwarmMemoryCoordinator:
    """Coordinates memory sharing and synthesis across swarm agents"""
    
    def __init__(self, memory_path: str = "./safla-memory"):
        self.memory_path = Path(memory_path)
        self.memory_path.mkdir(exist_ok=True, parents=True)
        
        # Initialize memory structures
        self.agent_memories = self.memory_path / "agents"
        self.shared_memory = self.memory_path / "shared"
        self.synthesis_memory = self.memory_path / "synthesis"
        
        for path in [self.agent_memories, self.shared_memory, self.synthesis_memory]:
            path.mkdir(exist_ok=True, parents=True)
        
        # Setup logging
        self.setup_logging()
        
        # Initialize coordinator state
        self.coordinator_state = {
            "active_agents": {},
            "memory_updates": [],
            "synthesis_queue": [],
            "cross_pollination_events": [],
            "last_sync": None
        }
        
        self.logger.info("SAFLA Memory Coordinator initialized")

    def setup_logging(self):
        """Setup coordinator logging"""
        log_path = Path("./logs")
        log_path.mkdir(exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_path / "memory-coordinator.log"),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger("SwarmMemoryCoordinator")

    def store_memory(self, agent_id: str, memory_type: str, content: Dict[str, Any]) -> str:
        """Store agent memory with metadata"""
        timestamp = datetime.now().isoformat()
        memory_id = hashlib.md5(f"{agent_id}_{timestamp}_{memory_type}".encode()).hexdigest()[:8]
        
        memory_entry = {
            "memory_id": memory_id,
            "agent_id": agent_id,
            "memory_type": memory_type,
            "timestamp": timestamp,
            "content": content,
            "metadata": {
                "size": len(str(content)),
                "hash": hashlib.md5(str(content).encode()).hexdigest()
            }
        }
        
        # Store in agent-specific memory
        agent_memory_path = self.agent_memories / agent_id
        agent_memory_path.mkdir(exist_ok=True)
        
        memory_file = agent_memory_path / f"{memory_type}_{memory_id}.json"
        with open(memory_file, 'w') as f:
            json.dump(memory_entry, f, indent=2)
        
        # Update coordinator state
        if agent_id not in self.coordinator_state["active_agents"]:
            self.coordinator_state["active_agents"][agent_id] = {
                "first_seen": timestamp,
                "memory_count": 0,
                "last_update": timestamp
            }
        
        self.coordinator_state["active_agents"][agent_id]["memory_count"] += 1
        self.coordinator_state["active_agents"][agent_id]["last_update"] = timestamp
        self.coordinator_state["memory_updates"].append({
            "memory_id": memory_id,
            "agent_id": agent_id,
            "type": memory_type,
            "timestamp": timestamp
        })
        
        self.logger.info(f"Stored memory {memory_id} for agent {agent_id} (type: {memory_type})")
        return memory_id

    def retrieve_memory(self, agent_id: Optional[str] = None, memory_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve memories based on filters"""
        memories = []
        
        if agent_id:
            agent_path = self.agent_memories / agent_id
            if agent_path.exists():
                for memory_file in agent_path.glob("*.json"):
                    if memory_type and not memory_file.name.startswith(f"{memory_type}_"):
                        continue
                    with open(memory_file, 'r') as f:
                        memories.append(json.load(f))
        else:
            # Retrieve from all agents
            for agent_path in self.agent_memories.iterdir():
                if agent_path.is_dir():
                    for memory_file in agent_path.glob("*.json"):
                        if memory_type and not memory_file.name.startswith(f"{memory_type}_"):
                            continue
                        with open(memory_file, 'r') as f:
                            memories.append(json.load(f))
        
        return sorted(memories, key=lambda x: x["timestamp"], reverse=True)

    def create_shared_insight(self, insight_type: str, content: Dict[str, Any], source_agents: List[str]) -> str:
        """Create a shared insight from multiple agent memories"""
        timestamp = datetime.now().isoformat()
        insight_id = hashlib.md5(f"{insight_type}_{timestamp}".encode()).hexdigest()[:8]
        
        shared_insight = {
            "insight_id": insight_id,
            "insight_type": insight_type,
            "timestamp": timestamp,
            "source_agents": source_agents,
            "content": content,
            "confidence": self._calculate_confidence(content, source_agents),
            "cross_references": self._find_cross_references(content)
        }
        
        insight_file = self.shared_memory / f"{insight_type}_{insight_id}.json"
        with open(insight_file, 'w') as f:
            json.dump(shared_insight, f, indent=2)
        
        self.logger.info(f"Created shared insight {insight_id} from agents: {', '.join(source_agents)}")
        return insight_id

    def synthesize_findings(self) -> Dict[str, Any]:
        """Synthesize findings across all agents"""
        all_memories = self.retrieve_memory()
        shared_insights = self._load_shared_insights()
        
        synthesis = {
            "synthesis_timestamp": datetime.now().isoformat(),
            "total_memories": len(all_memories),
            "total_insights": len(shared_insights),
            "agent_summary": self._summarize_agents(),
            "key_patterns": self._identify_patterns(all_memories),
            "cross_cutting_issues": self._find_cross_cutting_issues(all_memories),
            "priority_areas": self._prioritize_findings(all_memories),
            "recommendations": self._generate_recommendations(all_memories)
        }
        
        # Store synthesis
        synthesis_file = self.synthesis_memory / f"synthesis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(synthesis_file, 'w') as f:
            json.dump(synthesis, f, indent=2)
        
        self.logger.info(f"Generated synthesis with {len(all_memories)} memories from {len(self.coordinator_state['active_agents'])} agents")
        return synthesis

    def cross_pollinate(self, target_agent: str, source_agents: List[str], focus_areas: List[str]) -> Dict[str, Any]:
        """Cross-pollinate findings between agents"""
        relevant_memories = []
        
        for source_agent in source_agents:
            agent_memories = self.retrieve_memory(agent_id=source_agent)
            for memory in agent_memories:
                if any(area.lower() in str(memory["content"]).lower() for area in focus_areas):
                    relevant_memories.append(memory)
        
        cross_pollination = {
            "target_agent": target_agent,
            "source_agents": source_agents,
            "focus_areas": focus_areas,
            "relevant_findings": relevant_memories[:10],  # Top 10 most relevant
            "suggested_investigations": self._suggest_investigations(relevant_memories, focus_areas),
            "timestamp": datetime.now().isoformat()
        }
        
        # Store cross-pollination result
        cp_file = self.shared_memory / f"cross_pollination_{target_agent}_{datetime.now().strftime('%H%M%S')}.json"
        with open(cp_file, 'w') as f:
            json.dump(cross_pollination, f, indent=2)
        
        self.logger.info(f"Cross-pollinated {len(relevant_memories)} findings to {target_agent}")
        return cross_pollination

    def get_coordinator_status(self) -> Dict[str, Any]:
        """Get current coordinator status"""
        return {
            "coordinator_state": self.coordinator_state,
            "memory_stats": {
                "agent_count": len(self.coordinator_state["active_agents"]),
                "total_memories": len(self.coordinator_state["memory_updates"]),
                "shared_insights": len(list(self.shared_memory.glob("*.json"))),
                "synthesis_count": len(list(self.synthesis_memory.glob("*.json")))
            },
            "last_sync": self.coordinator_state.get("last_sync"),
            "memory_health": self._check_memory_health()
        }

    def _calculate_confidence(self, content: Dict[str, Any], source_agents: List[str]) -> float:
        """Calculate confidence score for shared insights"""
        # Basic confidence calculation based on agent count and content quality
        agent_factor = min(len(source_agents) / 3.0, 1.0)  # Higher confidence with more agents
        content_factor = min(len(str(content)) / 1000.0, 1.0)  # Higher confidence with more detailed content
        return (agent_factor + content_factor) / 2.0

    def _find_cross_references(self, content: Dict[str, Any]) -> List[str]:
        """Find cross-references in content"""
        # Simple implementation - look for file paths and function names
        content_str = str(content).lower()
        cross_refs = []
        
        # Common file patterns
        if "src/" in content_str:
            cross_refs.append("source_code")
        if "test" in content_str:
            cross_refs.append("testing")
        if "config" in content_str:
            cross_refs.append("configuration")
        if "api" in content_str:
            cross_refs.append("api_integration")
        
        return cross_refs

    def _load_shared_insights(self) -> List[Dict[str, Any]]:
        """Load all shared insights"""
        insights = []
        for insight_file in self.shared_memory.glob("*.json"):
            with open(insight_file, 'r') as f:
                insights.append(json.load(f))
        return insights

    def _summarize_agents(self) -> Dict[str, Any]:
        """Summarize agent activity"""
        summary = {}
        for agent_id, info in self.coordinator_state["active_agents"].items():
            summary[agent_id] = {
                "memory_count": info["memory_count"],
                "last_update": info["last_update"],
                "specialization": self._infer_specialization(agent_id)
            }
        return summary

    def _infer_specialization(self, agent_id: str) -> str:
        """Infer agent specialization from ID"""
        specializations = {
            "scraping": "Web Scraping & Data Collection",
            "keyword": "Keyword Analysis & Matching",
            "api": "API Integration & Reliability",
            "performance": "Performance Optimization",
            "production": "Production Readiness",
            "data": "Data Quality & Validation",
            "concurrency": "Concurrency & Async Patterns",
            "monitoring": "Monitoring & Observability"
        }
        
        for key, spec in specializations.items():
            if key in agent_id.lower():
                return spec
        return "General Analysis"

    def _identify_patterns(self, memories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify patterns across memories"""
        patterns = []
        
        # Pattern: Common issues across agents
        issue_counts = {}
        for memory in memories:
            content_str = str(memory["content"]).lower()
            for issue in ["error", "bug", "performance", "rate limit", "timeout"]:
                if issue in content_str:
                    issue_counts[issue] = issue_counts.get(issue, 0) + 1
        
        for issue, count in issue_counts.items():
            if count >= 2:  # Pattern if found in multiple memories
                patterns.append({
                    "type": "common_issue",
                    "pattern": issue,
                    "frequency": count,
                    "confidence": min(count / len(memories), 1.0)
                })
        
        return patterns

    def _find_cross_cutting_issues(self, memories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Find issues that affect multiple components"""
        cross_cutting = []
        
        # Look for issues mentioned by multiple agents
        issue_agents = {}
        for memory in memories:
            agent_id = memory["agent_id"]
            content_str = str(memory["content"]).lower()
            
            for issue in ["scalability", "monitoring", "error handling", "performance", "security"]:
                if issue in content_str:
                    if issue not in issue_agents:
                        issue_agents[issue] = set()
                    issue_agents[issue].add(agent_id)
        
        for issue, agents in issue_agents.items():
            if len(agents) >= 2:  # Cross-cutting if multiple agents mention it
                cross_cutting.append({
                    "issue": issue,
                    "affected_agents": list(agents),
                    "severity": len(agents)
                })
        
        return cross_cutting

    def _prioritize_findings(self, memories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Prioritize findings by importance"""
        priorities = []
        
        # High priority keywords
        high_priority_terms = ["critical", "security", "data loss", "production", "failure"]
        medium_priority_terms = ["performance", "optimization", "efficiency", "scalability"]
        low_priority_terms = ["documentation", "cleanup", "refactor"]
        
        for memory in memories:
            content_str = str(memory["content"]).lower()
            priority = "low"
            
            if any(term in content_str for term in high_priority_terms):
                priority = "high"
            elif any(term in content_str for term in medium_priority_terms):
                priority = "medium"
            
            if priority in ["high", "medium"]:
                priorities.append({
                    "agent_id": memory["agent_id"],
                    "memory_id": memory["memory_id"],
                    "priority": priority,
                    "summary": str(memory["content"])[:200] + "..."
                })
        
        return sorted(priorities, key=lambda x: {"high": 3, "medium": 2, "low": 1}[x["priority"]], reverse=True)

    def _generate_recommendations(self, memories: List[Dict[str, Any]]) -> List[str]:
        """Generate high-level recommendations"""
        recommendations = []
        
        # Count agent specializations
        specializations = {}
        for memory in memories:
            spec = self._infer_specialization(memory["agent_id"])
            specializations[spec] = specializations.get(spec, 0) + 1
        
        # Generate recommendations based on findings
        if specializations.get("Performance Optimization", 0) > 0:
            recommendations.append("Review and implement performance optimization recommendations")
        
        if specializations.get("Production Readiness", 0) > 0:
            recommendations.append("Address production readiness gaps before deployment")
        
        if specializations.get("API Integration & Reliability", 0) > 0:
            recommendations.append("Strengthen API error handling and rate limiting")
        
        return recommendations

    def _suggest_investigations(self, memories: List[Dict[str, Any]], focus_areas: List[str]) -> List[str]:
        """Suggest further investigations based on memories"""
        suggestions = []
        
        for focus_area in focus_areas:
            relevant_count = sum(1 for memory in memories 
                               if focus_area.lower() in str(memory["content"]).lower())
            if relevant_count > 0:
                suggestions.append(f"Deep dive into {focus_area} - {relevant_count} related findings")
        
        return suggestions

    def _check_memory_health(self) -> Dict[str, Any]:
        """Check memory system health"""
        return {
            "storage_healthy": self.memory_path.exists(),
            "agent_directories": len(list(self.agent_memories.iterdir())),
            "shared_insights": len(list(self.shared_memory.glob("*.json"))),
            "synthesis_files": len(list(self.synthesis_memory.glob("*.json"))),
            "last_activity": max([info["last_update"] for info in self.coordinator_state["active_agents"].values()]) if self.coordinator_state["active_agents"] else None
        }


if __name__ == "__main__":
    import sys
    
    coordinator = SwarmMemoryCoordinator()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "status":
            status = coordinator.get_coordinator_status()
            print(json.dumps(status, indent=2))
        
        elif command == "synthesize":
            synthesis = coordinator.synthesize_findings()
            print("Synthesis complete. Results saved to synthesis memory.")
            print(f"Found {synthesis['total_memories']} memories from {len(synthesis['agent_summary'])} agents")
        
        elif command == "test":
            # Test memory storage
            test_memory = {
                "finding": "Test finding for memory system",
                "severity": "low",
                "component": "memory-coordinator"
            }
            memory_id = coordinator.store_memory("test-agent", "analysis", test_memory)
            print(f"Test memory stored with ID: {memory_id}")
            
            # Test retrieval
            memories = coordinator.retrieve_memory("test-agent")
            print(f"Retrieved {len(memories)} memories for test-agent")
    
    else:
        print("SwarmMemoryCoordinator Commands:")
        print("  status     - Show coordinator status")
        print("  synthesize - Generate synthesis of all findings")
        print("  test       - Run memory system test")
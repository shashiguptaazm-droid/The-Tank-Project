"""TankOS AI Evolution Layer — intelligent, self-improving engines.

Contains:
- Reflection Engine — daily learning loop, mistake analysis, self-improvement
- Reasoning Engine — logical decision-making with LLM + rules + memory
- Behavior Tree System — composable autonomous behavior control
- Vision Understanding — visual scene description and Q&A with VLM
- Habit Learning Engine — pattern tracking, routine learning, predictive assistance
- Self-Coding System — autonomous code maintenance, generation, testing, and deployment
- Safe Workspace — secure AI code modification with policies and rollback
- Experience Engine — structured recording of all interactions for learning
- Knowledge Graph — entity relationship graph for contextual reasoning
- Curiosity Engine — idle-time exploration and knowledge gap detection
- World Model — evolving spatial/environmental understanding
- Continuous Learning Engine — automatic pattern and preference discovery
- Learning Scheduler — orchestrates background learning activities
"""

from tank_os.ai.reflection_engine import (
    ReflectionEngine, ActionRecord, Reflection, ImprovementGoal
)
from tank_os.ai.reasoning_engine import (
    ReasoningEngine, ReasoningContext, ReasoningResult, Decision,
    ReasoningDepth, ReasoningRule
)
from tank_os.ai.behavior_tree import (
    BehaviorTree, BehaviorFactory, Blackboard,
    Node, Sequence, Selector, Parallel,
    ConditionNode, ActionNode,
    InvertDecorator, RetryDecorator, TimeoutDecorator,
    NodeStatus,
)
from tank_os.ai.vision_understanding import (
    VisionUnderstandingEngine, SceneDescription, VisualQA
)
from tank_os.ai.habit_learner import (
    HabitLearningEngine, Habit, Observation, Prediction
)
from tank_os.ai.self_coding import (
    SelfCodingSystem, ChangeSet, ImprovementTask, HealthReport,
    ChangeStatus,
)
from tank_os.ai.safe_workspace import (
    SafeWorkspace, FilePolicy, FileAction, SessionState, FileRecord,
)
from tank_os.ai.experience_engine import (
    ExperienceEngine, Experience, ExperienceSummary,
)
from tank_os.ai.knowledge_graph import (
    KnowledgeGraph, Entity, Relationship, GraphQuery,
)
from tank_os.ai.curiosity_engine import (
    CuriosityEngine, Exploration, KnowledgeGap, CapabilityDiscovery,
    ExplorationType,
)
from tank_os.ai.world_model import (
    WorldModel, Room, WorldObject, Zone, EnvironmentChange,
)
from tank_os.ai.continuous_learning import (
    ContinuousLearningEngine, LearnedPattern, LearnedPreference,
    LearningInsight,
)
from tank_os.ai.learning_scheduler import (
    LearningScheduler, ScheduledTask, LearningTaskType,
    LearningPriority, LearningWindow, LearningBudget, TaskResult,
)

__all__ = [
    # Reflection Engine
    "ReflectionEngine", "ActionRecord", "Reflection", "ImprovementGoal",
    # Reasoning Engine
    "ReasoningEngine", "ReasoningContext", "ReasoningResult", "Decision",
    "ReasoningDepth", "ReasoningRule",
    # Behavior Tree
    "BehaviorTree", "BehaviorFactory", "Blackboard",
    "Node", "Sequence", "Selector", "Parallel",
    "ConditionNode", "ActionNode",
    "InvertDecorator", "RetryDecorator", "TimeoutDecorator",
    "NodeStatus",
    # Vision Understanding
    "VisionUnderstandingEngine", "SceneDescription", "VisualQA",
    # Habit Learning
    "HabitLearningEngine", "Habit", "Observation", "Prediction",
    # Self Coding
    "SelfCodingSystem", "ChangeSet", "ImprovementTask", "HealthReport",
    "ChangeStatus",
    # Safe Workspace
    "SafeWorkspace", "FilePolicy", "FileAction", "SessionState", "FileRecord",
    # Experience Engine
    "ExperienceEngine", "Experience", "ExperienceSummary",
    # Knowledge Graph
    "KnowledgeGraph", "Entity", "Relationship", "GraphQuery",
    # Curiosity Engine
    "CuriosityEngine", "Exploration", "KnowledgeGap", "CapabilityDiscovery",
    "ExplorationType",
    # World Model
    "WorldModel", "Room", "WorldObject", "Zone", "EnvironmentChange",
    # Continuous Learning
    "ContinuousLearningEngine", "LearnedPattern", "LearnedPreference",
    "LearningInsight",
    # Learning Scheduler
    "LearningScheduler", "ScheduledTask", "LearningTaskType",
    "LearningPriority", "LearningWindow", "LearningBudget", "TaskResult",
]

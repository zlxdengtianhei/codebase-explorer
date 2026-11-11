"""Install the CBE skill and its Claude Code subagent from the self-contained distribution."""

PRODUCT = "codebase-explorer"
BUSINESS_MODULE = "cbe.cli"
SKILLS = ("codebase-explorer",)
SOURCE_PARENT_LEVEL = 2
SOURCE_SKILL_BASE = "plugin/skills"
SOURCE_AGENT_BASE = "plugin/agents"
AGENTS_RESOURCE = "agents"
RUNTIME_SKILLS = ("codebase-explorer",)
RUNTIME_MODULES = ("cbe",)

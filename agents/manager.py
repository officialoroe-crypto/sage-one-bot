from dataclasses import dataclass


@dataclass
class AgentDefinition:

    name: str
    description: str
    capabilities: list[str]
    preferred_tools: list[str]


class AgentManager:

    def __init__(self):

        self.agents = {

            "general": AgentDefinition(
                name="general",
                description=(
                    "General purpose SAGE execution agent."
                ),
                capabilities=[
                    "planning",
                    "reasoning",
                    "task_execution"
                ],
                preferred_tools=[]
            ),

            "world": AgentDefinition(
                name="world",
                description=(
                    "Maintains bounded public-world intelligence refreshes."
                ),
                capabilities=[
                    "world_intelligence",
                    "public_source_refresh",
                    "knowledge_update",
                ],
                preferred_tools=[]
            ),

            "research": AgentDefinition(
                name="research",
                description=(
                    "Researches information, "
                    "cross-checks sources, "
                    "and produces evidence-based results."
                ),
                capabilities=[
                    "research",
                    "web_search",
                    "source_analysis",
                    "synthesis"
                ],
                preferred_tools=[
                    "web_search"
                ]
            ),

            "sales": AgentDefinition(
                name="sales",
                description="Audits businesses, scores leads, prepares approval-gated outreach.",
                capabilities=["business_discovery","website_audit","social_audit","content_audit","lead_scoring","outreach"],
                preferred_tools=["web_read"],
            ),

            "business": AgentDefinition(
                name="business",
                description=(
                    "Handles business, income, "
                    "marketing, sales, and opportunity work."
                ),
                capabilities=[
                    "business",
                    "marketing",
                    "sales",
                    "income",
                    "strategy"
                ],
                preferred_tools=[]
            ),

            "creative": AgentDefinition(
                name="creative",
                description=(
                    "Handles creative production "
                    "and content workflows."
                ),
                capabilities=[
                    "writing",
                    "design",
                    "video",
                    "music",
                    "branding",
                    "content"
                ],
                preferred_tools=[]
            )
        }

    def get(
        self,
        name: str
    ):

        return self.agents.get(name)

    def exists(
        self,
        name: str
    ):

        return name in self.agents

    def list(self):

        return [
            {
                "name": agent.name,
                "description": agent.description,
                "capabilities": agent.capabilities,
                "preferred_tools": agent.preferred_tools
            }
            for agent in self.agents.values()
        ]

    def choose(
        self,
        task_description: str
    ):

        text = task_description.lower()

        if any(
            word in text
            for word in [
                "world intelligence",
                "world refresh",
                "refresh world knowledge",
                "public-world refresh",
            ]
        ):

            return "world"

        if any(
            word in text
            for word in [
                "research",
                "find out",
                "compare",
                "investigate",
                "study"
            ]
        ):

            return "research"

        if any(
            word in text
            for word in [
                "sales audit",
                "lead audit",
                "prospect audit",
                "outreach draft",
                "qualify this business",
                "audit this business",
                "find prospects",
                "discover businesses",
            ]
        ):
            return "sales"

        if any(
            word in text
            for word in [
                "business",
                "money",
                "earn",
                "client",
                "marketing",
                "sales",
                "income"
            ]
        ):

            return "business"

        if any(
            word in text
            for word in [
                "video",
                "image",
                "song",
                "design",
                "thumbnail",
                "brand",
                "content"
            ]
        ):

            return "creative"

        return "general"


agents = AgentManager()

"""Team business logic."""

from ..config.models import AgentRole
from ..models.team import TeamConfiguration, TeamMember


class Team:
    """Team business logic and management."""

    def __init__(self, team_config: TeamConfiguration):
        self.config = team_config

    def get_member_by_role(self, role: AgentRole) -> list[TeamMember]:
        """Get team members by role."""
        return self.config.get_members_by_role(role)

    def get_available_members(self) -> list[TeamMember]:
        """Get available team members."""
        return self.config.get_available_members()

    def get_team_capacity(self) -> dict[AgentRole, int]:
        """Get team capacity by role."""
        return self.config.get_team_capacity()

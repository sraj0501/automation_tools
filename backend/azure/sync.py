"""
Azure DevOps Bidirectional Sync

Synchronizes local ProjectManager projects with Azure DevOps work items.
All operations are async. Configuration is read from backend.config.

Mapping strategy:
  - Local Project  <->  Azure DevOps Area Path (or Iteration)
  - Local ProjectGoal  <->  Azure DevOps Work Item (Task)
  - Project status  <->  Work item state (via configurable mapping)
  - External tracking stored in Project.external_id / external_source / metadata
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from backend import config as cfg
from backend.azure.client import AzureDevOpsClient, AzureWorkItem
from backend.models.project import (
    Project, ProjectGoal, ProjectStatus, RiskLevel,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants — class-level, not magic strings scattered in logic
# ---------------------------------------------------------------------------

EXTERNAL_SOURCE_NAME = "azure_devops"

# Metadata keys stored in Project.metadata for sync bookkeeping
META_GOAL_WORK_ITEM_MAP = "azure_goal_work_item_map"  # {goal_id: work_item_id}
META_AREA_PATH = "azure_area_path"
META_ITERATION_PATH = "azure_iteration_path"


class StatusMapping:
    """Bidirectional mapping between local ProjectStatus and Azure DevOps states.

    Values read from config at construction time so they are never hardcoded.
    """

    def __init__(self) -> None:
        # Local -> Azure  (configurable via env vars)
        closed_state = (
            cfg.get("AZURE_SYNC_STATE_CLOSED")
            or cfg.get("AZURE_SYNC_DONE_STATE", "Done")
        )
        self._local_to_azure: Dict[ProjectStatus, str] = {
            ProjectStatus.SETUP: cfg.get("AZURE_SYNC_STATE_SETUP", "New"),
            ProjectStatus.ACTIVE: cfg.get("AZURE_SYNC_STATE_ACTIVE", "Active"),
            ProjectStatus.CLOSED: closed_state,
        }
        # Build reverse map
        self._azure_to_local: Dict[str, ProjectStatus] = {
            v.lower(): k for k, v in self._local_to_azure.items()
        }

    def to_azure(self, status: ProjectStatus) -> str:
        return self._local_to_azure.get(status, "New")

    def to_local(self, azure_state: str) -> ProjectStatus:
        return self._azure_to_local.get(
            azure_state.lower(), ProjectStatus.ACTIVE
        )


class GoalStatusMapping:
    """Maps local goal status strings to Azure work-item states and back."""

    def __init__(self) -> None:
        completed_state = (
            cfg.get("AZURE_SYNC_GOAL_STATE_COMPLETED")
            or cfg.get("AZURE_SYNC_GOAL_STATE_DONE", "Done")
        )
        self._goal_to_azure: Dict[str, str] = {
            "pending": cfg.get("AZURE_SYNC_GOAL_STATE_PENDING", "New"),
            "in_progress": cfg.get("AZURE_SYNC_GOAL_STATE_IN_PROGRESS", "Active"),
            "completed": completed_state,
        }
        self._azure_to_goal: Dict[str, str] = {
            v.lower(): k for k, v in self._goal_to_azure.items()
        }

    def to_azure(self, goal_status: str) -> str:
        return self._goal_to_azure.get(goal_status, "New")

    def to_local(self, azure_state: str) -> str:
        return self._azure_to_goal.get(azure_state.lower(), "pending")


# ---------------------------------------------------------------------------
# Main sync class
# ---------------------------------------------------------------------------

class AzureProjectSync:
    """Bidirectional sync between local ProjectManager and Azure DevOps.

    Usage::

        from backend.project_manager import ProjectManager
        from backend.azure.client import AzureDevOpsClient
        from backend.azure.sync import AzureProjectSync

        pm = ProjectManager()
        azure = AzureDevOpsClient()
        sync = AzureProjectSync(pm, azure)

        result = await sync.full_sync()
    """

    def __init__(
        self,
        project_manager: Any,  # ProjectManager — Any to avoid circular import
        azure_client: AzureDevOpsClient,
    ) -> None:
        self.pm = project_manager
        self.azure = azure_client
        self._status_map = StatusMapping()
        self._goal_status_map = GoalStatusMapping()
        self._work_item_type = cfg.get("AZURE_SYNC_WORK_ITEM_TYPE", "Task")
        self._default_area_path = cfg.get("AZURE_SYNC_DEFAULT_AREA_PATH", "")
        self._default_iteration_path = cfg.get("AZURE_SYNC_DEFAULT_ITERATION_PATH", "")
        self._auto_create = cfg.is_azure_create_on_no_match()
        self._sync_tag = cfg.get("AZURE_SYNC_TAG", "devtrack-managed")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def sync_project_to_azure(self, project_id: str) -> bool:
        """Push local project state to Azure DevOps.

        Creates or updates Azure work items for each project goal.

        Returns True on success, False on failure.
        """
        if not self._preflight_check():
            return False

        project = self.pm.get_project(project_id)
        if not project:
            logger.warning(
                "sync_project_to_azure: project %s not found", project_id
            )
            return False

        logger.info(
            "Starting local->Azure sync for project %s (%s)",
            project_id, project.name,
        )

        try:
            goal_map = self._get_goal_map(project)
            area_path = self._resolve_area_path(project)
            iteration_path = self._resolve_iteration_path(project)

            synced_count = 0
            for goal in project.goals:
                existing_wi_id = goal_map.get(goal.id)

                if existing_wi_id:
                    success = await self._update_goal_work_item(
                        existing_wi_id, goal, project, area_path, iteration_path,
                    )
                else:
                    wi = await self._create_goal_work_item(
                        goal, project, area_path, iteration_path,
                    )
                    if wi:
                        goal_map[goal.id] = wi.id
                        success = True
                    else:
                        success = False

                if success:
                    synced_count += 1

            # Persist updated goal map
            self._set_goal_map(project, goal_map)
            project.external_source = EXTERNAL_SOURCE_NAME
            project.external_sync_at = datetime.utcnow()
            if not project.external_id and area_path:
                project.external_id = area_path
            project.updated_at = datetime.utcnow()

            logger.info(
                "local->Azure sync complete for %s: %d/%d goals synced",
                project_id, synced_count, len(project.goals),
            )
            return True

        except Exception as exc:
            logger.error(
                "sync_project_to_azure failed for %s: %s",
                project_id, exc, exc_info=True,
            )
            return False

    async def sync_azure_to_local(
        self, iteration_path: Optional[str] = None
    ) -> bool:
        """Pull Azure DevOps work items into local projects.

        Fetches work items tagged with the sync tag (or from the given
        iteration path) and creates / updates local projects.

        Returns True on success, False on failure.
        """
        if not self._preflight_check():
            return False

        target_path = iteration_path or self._default_iteration_path
        logger.info(
            "Starting Azure->local sync (iteration_path=%s)", target_path
        )

        try:
            work_items = await self._fetch_syncable_work_items(target_path)
            if not work_items:
                logger.info("Azure->local sync: no work items found")
                return True

            # Group work items by area path (each area path -> one project)
            groups: Dict[str, List[AzureWorkItem]] = {}
            for wi in work_items:
                key = wi.area_path or "default"
                groups.setdefault(key, []).append(wi)

            for area_path_key, items in groups.items():
                project = self._find_project_by_external_id(area_path_key)
                if project:
                    await self._merge_work_items_into_project(project, items)
                elif self._auto_create:
                    await self._create_project_from_work_items(
                        area_path_key, items,
                    )
                else:
                    logger.info(
                        "Azure->local: no local project for area '%s' "
                        "(auto-create disabled, %d items skipped)",
                        area_path_key, len(items),
                    )

            logger.info("Azure->local sync complete")
            return True

        except Exception as exc:
            logger.error(
                "sync_azure_to_local failed: %s", exc, exc_info=True,
            )
            return False

    async def handle_webhook_update(self, event_data: Dict[str, Any]) -> bool:
        """Handle an inbound webhook event and update the local project.

        ``event_data`` is the dict already parsed by WebhookEventHandler
        (contains ``work_item_id``, ``changes``, etc.).

        Returns True if a local project was updated, False otherwise.
        """
        if not self.pm:
            return False

        work_item_id = event_data.get("work_item_id")
        if not work_item_id:
            logger.debug("handle_webhook_update: no work_item_id in event")
            return False

        project, goal = self._find_project_by_work_item_id(int(work_item_id))
        if not project:
            logger.debug(
                "handle_webhook_update: no local project for WI #%s",
                work_item_id,
            )
            return False

        logger.info(
            "Webhook update for WI #%s -> project %s", work_item_id, project.id,
        )

        changes = event_data.get("changes", {})
        updated = False

        # State change on the work item -> update goal status
        state_change = changes.get("System.State", {})
        if state_change and goal:
            new_azure_state = state_change.get("newValue", "")
            if new_azure_state:
                new_local_status = self._goal_status_map.to_local(new_azure_state)
                if goal.status != new_local_status:
                    goal.status = new_local_status
                    updated = True
                    logger.info(
                        "Goal '%s' status -> %s (from Azure state '%s')",
                        goal.title, new_local_status, new_azure_state,
                    )

        # Title change -> update goal title
        title_change = changes.get("System.Title", {})
        if title_change and goal:
            new_title = title_change.get("newValue", "")
            if new_title and new_title != goal.title:
                goal.title = new_title
                updated = True

        if updated:
            project.updated_at = datetime.utcnow()
            project.external_sync_at = datetime.utcnow()
            logger.info("Local project %s updated from webhook", project.id)

        return updated

    async def full_sync(self) -> Dict[str, Any]:
        """Run a full bidirectional sync.

        1. Push local projects that have an external_id to Azure.
        2. Pull Azure work items that are not yet tracked locally.

        Returns a summary dict with counts.
        """
        results: Dict[str, Any] = {
            "pushed": 0,
            "push_errors": 0,
            "pulled": False,
            "pull_error": None,
        }

        if not self._preflight_check():
            results["pull_error"] = "preflight check failed"
            return results

        # 1. Push local -> Azure for projects with external tracking
        for project in self.pm.list_projects():
            if project.external_source == EXTERNAL_SOURCE_NAME:
                ok = await self.sync_project_to_azure(project.id)
                if ok:
                    results["pushed"] += 1
                else:
                    results["push_errors"] += 1

        # 2. Pull Azure -> local
        try:
            results["pulled"] = await self.sync_azure_to_local()
        except Exception as exc:
            results["pull_error"] = str(exc)
            logger.error("full_sync pull phase failed: %s", exc, exc_info=True)

        logger.info("full_sync results: %s", results)
        return results

    # ------------------------------------------------------------------
    # Private — preflight & helpers
    # ------------------------------------------------------------------

    def _preflight_check(self) -> bool:
        """Verify that both sides of the sync are available."""
        if not self.pm:
            logger.warning("Sync skipped: ProjectManager unavailable")
            return False
        if not self.azure or not self.azure.is_configured():
            logger.warning("Sync skipped: AzureDevOpsClient not configured")
            return False
        if not cfg.is_project_sync_enabled():
            logger.info("Sync skipped: PROJECT_SYNC_ENABLED is false")
            return False
        return True

    # -- goal <-> work-item map -------------------------------------------

    def _get_goal_map(self, project: Project) -> Dict[str, int]:
        """Return {goal_id: azure_work_item_id} from project metadata."""
        raw = project.metadata.get(META_GOAL_WORK_ITEM_MAP, {})
        # Ensure values are ints
        return {k: int(v) for k, v in raw.items()}

    def _set_goal_map(self, project: Project, goal_map: Dict[str, int]) -> None:
        project.metadata[META_GOAL_WORK_ITEM_MAP] = goal_map

    # -- path resolution --------------------------------------------------

    def _resolve_area_path(self, project: Project) -> str:
        return (
            project.metadata.get(META_AREA_PATH)
            or project.external_id
            or self._default_area_path
            or ""
        )

    def _resolve_iteration_path(self, project: Project) -> str:
        return (
            project.metadata.get(META_ITERATION_PATH)
            or self._default_iteration_path
            or ""
        )

    # -- local -> Azure operations ----------------------------------------

    async def _create_goal_work_item(
        self,
        goal: ProjectGoal,
        project: Project,
        area_path: str,
        iteration_path: str,
    ) -> Optional[AzureWorkItem]:
        """Create an Azure work item from a local goal."""
        description = self._build_work_item_description(goal, project)
        tags = [self._sync_tag, f"project:{project.id}"]

        wi = await self.azure.create_work_item(
            title=goal.title,
            description=description,
            work_item_type=self._work_item_type,
            area_path=area_path or None,
            iteration_path=iteration_path or None,
            tags=tags,
        )
        if wi:
            logger.info(
                "Created Azure WI #%d for goal '%s' (project %s)",
                wi.id, goal.title, project.id,
            )
        return wi

    async def _update_goal_work_item(
        self,
        work_item_id: int,
        goal: ProjectGoal,
        project: Project,
        area_path: str,
        iteration_path: str,
    ) -> bool:
        """Update an existing Azure work item to match local goal state."""
        azure_state = self._goal_status_map.to_azure(goal.status)
        description = self._build_work_item_description(goal, project)

        fields: Dict[str, Any] = {
            "System.Title": goal.title,
            "System.Description": description,
            "System.State": azure_state,
        }
        if area_path:
            fields["System.AreaPath"] = area_path
        if iteration_path:
            fields["System.IterationPath"] = iteration_path

        ok = await self.azure.update_work_item_fields(work_item_id, fields)
        if ok:
            logger.debug(
                "Updated Azure WI #%d for goal '%s'", work_item_id, goal.title,
            )
        return ok

    @staticmethod
    def _build_work_item_description(
        goal: ProjectGoal, project: Project,
    ) -> str:
        parts = []
        if goal.description:
            parts.append(goal.description)
        parts.append(f"Project: {project.name}")
        parts.append(f"Priority: {goal.priority}")
        return "<br>".join(parts)

    # -- Azure -> local operations ----------------------------------------

    async def _fetch_syncable_work_items(
        self, iteration_path: Optional[str],
    ) -> List[AzureWorkItem]:
        """Fetch work items from Azure eligible for sync."""
        sync_states = cfg.get_azure_sync_states()
        items = await self.azure.get_my_work_items(
            states=sync_states,
            types=[self._work_item_type],
        )
        # Filter by iteration path if specified
        if iteration_path:
            items = [
                wi for wi in items
                if wi.iteration_path and wi.iteration_path.startswith(iteration_path)
            ]
        # Further filter to sync-tagged items only
        if self._sync_tag:
            items = [
                wi for wi in items
                if self._sync_tag in wi.tags
            ]
        return items

    def _find_project_by_external_id(
        self, external_id: str,
    ) -> Optional[Project]:
        """Find a local project mapped to this Azure external_id."""
        for project in self.pm.list_projects():
            if (
                project.external_source == EXTERNAL_SOURCE_NAME
                and project.external_id == external_id
            ):
                return project
        return None

    def _find_project_by_work_item_id(
        self, work_item_id: int,
    ) -> Tuple[Optional[Project], Optional[ProjectGoal]]:
        """Find project + goal that maps to the given Azure work item ID."""
        for project in self.pm.list_projects():
            if project.external_source != EXTERNAL_SOURCE_NAME:
                continue
            goal_map = self._get_goal_map(project)
            for goal_id, wi_id in goal_map.items():
                if wi_id == work_item_id:
                    goal = project.get_goal_by_id(goal_id)
                    return project, goal
        return None, None

    async def _merge_work_items_into_project(
        self, project: Project, work_items: List[AzureWorkItem],
    ) -> None:
        """Update existing project goals from Azure work items."""
        goal_map = self._get_goal_map(project)
        # Reverse map: wi_id -> goal_id
        wi_to_goal = {v: k for k, v in goal_map.items()}

        for wi in work_items:
            goal_id = wi_to_goal.get(wi.id)
            if goal_id:
                goal = project.get_goal_by_id(goal_id)
                if goal:
                    self._update_goal_from_work_item(goal, wi)
            else:
                # New work item not tracked locally -> create goal
                new_goal = self._goal_from_work_item(wi)
                project.add_goal(new_goal)
                goal_map[new_goal.id] = wi.id
                logger.info(
                    "Added goal '%s' from Azure WI #%d to project %s",
                    new_goal.title, wi.id, project.id,
                )

        self._set_goal_map(project, goal_map)
        project.external_sync_at = datetime.utcnow()
        project.updated_at = datetime.utcnow()

    async def _create_project_from_work_items(
        self, area_path: str, work_items: List[AzureWorkItem],
    ) -> Project:
        """Create a new local project from a set of Azure work items."""
        # Derive project name from area path
        name = area_path.rsplit("\\", 1)[-1] if "\\" in area_path else area_path

        goals = [self._goal_from_work_item(wi) for wi in work_items]
        goal_descriptions = [g.title for g in goals]

        project = self.pm.create_project(
            name=name,
            description=f"Auto-imported from Azure DevOps area: {area_path}",
            goals=goal_descriptions,
            ai_enhance=False,
        )

        # Re-map goals (create_project generates new goal objects with new IDs)
        goal_map: Dict[str, int] = {}
        for idx, goal in enumerate(project.goals):
            if idx < len(work_items):
                goal_map[goal.id] = work_items[idx].id
                # Carry over status from Azure
                self._update_goal_from_work_item(goal, work_items[idx])

        project.external_id = area_path
        project.external_source = EXTERNAL_SOURCE_NAME
        project.external_sync_at = datetime.utcnow()
        project.metadata[META_AREA_PATH] = area_path
        self._set_goal_map(project, goal_map)

        logger.info(
            "Created project '%s' from Azure area '%s' with %d goals",
            project.name, area_path, len(goals),
        )
        return project

    def _goal_from_work_item(self, wi: AzureWorkItem) -> ProjectGoal:
        """Build a ProjectGoal from an Azure work item."""
        return ProjectGoal(
            id=str(uuid.uuid4()),
            title=wi.title,
            description=wi.description or "",
            status=self._goal_status_map.to_local(wi.state),
        )

    def _update_goal_from_work_item(
        self, goal: ProjectGoal, wi: AzureWorkItem,
    ) -> None:
        """Update a local goal's fields from an Azure work item."""
        goal.title = wi.title
        if wi.description:
            goal.description = wi.description
        goal.status = self._goal_status_map.to_local(wi.state)

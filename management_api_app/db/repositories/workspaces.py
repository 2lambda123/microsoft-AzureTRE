import uuid
from typing import List

from azure.cosmos import CosmosClient
from pydantic import UUID4

from core import config
from db.errors import EntityDoesNotExist
from db.repositories.base import BaseRepository
from db.repositories.workspace_templates import WorkspaceTemplateRepository
from models.domain.resource import Status
from models.domain.workspace import Workspace
from models.schemas.workspace import WorkspaceInCreate


class WorkspaceRepository(BaseRepository):
    def __init__(self, client: CosmosClient):
        super().__init__(client, config.STATE_STORE_RESOURCES_CONTAINER)

    @staticmethod
    def _active_workspaces_query():
        return 'SELECT * FROM c WHERE c.resourceType = "workspace" AND c.isDeleted = false'

    def _get_template_version(self, template_name):
        wt_repo = WorkspaceTemplateRepository(self._client)
        template = wt_repo.get_current_workspace_template_by_name(template_name)
        print(template)
        return template["version"]

    def get_all_active_workspaces(self) -> List[Workspace]:
        query = self._active_workspaces_query()
        return self._query(query=query)

    def get_workspace_by_workspace_id(self, workspace_id: UUID4) -> Workspace:
        query = self._active_workspaces_query() + f' AND c.id="{workspace_id}"'
        workspaces = self._query(query=query)
        if len(workspaces) != 1:
            raise EntityDoesNotExist
        return workspaces[0]

    def create_workspace_item(self, workspace_create: WorkspaceInCreate) -> Workspace:
        full_workspace_id = str(uuid.uuid4())

        try:
            template_version = self._get_template_version(workspace_create.workspaceType)
        except EntityDoesNotExist:
            raise ValueError(f'The workspace type "{workspace_create.workspaceType}" does not exist')

        resource_spec_parameters = {
            "location": config.RESOURCE_LOCATION,
            "workspace_id": full_workspace_id[-4:],
            "tre_id": config.TRE_ID,
            "address_space": "10.2.1.0/24"  # TODO: Calculate this value - Issue #52
        }

        workspace = Workspace(
            id=full_workspace_id,
            displayName=workspace_create.displayName,
            description=workspace_create.description,
            resourceSpecName=workspace_create.workspaceType,
            resourceSpecVersion=template_version,
            resourceSpecParameters=resource_spec_parameters,
            status=Status.NotDeployed
        )

        return workspace

    def save_workspace(self, workspace: Workspace):
        self._create_item(workspace)

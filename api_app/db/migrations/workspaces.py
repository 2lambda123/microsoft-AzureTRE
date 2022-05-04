from azure.cosmos import CosmosClient
from db.repositories.workspaces import WorkspaceRepository
import semantic_version


class WorkspaceMigration(WorkspaceRepository):
    def __init__(self, client: CosmosClient):
        super().__init__(client)

    async def moveAuthInformationToProperties(self):
        for item in self.query(query=WorkspaceRepository.workspaces_query_string()):
            template_version = semantic_version.Version(item["templateVersion"])
            if (template_version > semantic_version.Version('0.3.0') and "authInformation" in item):
                print(f'Found workspace {item["id"]} that needs migrating')

                # Rename app_id to be client_id
                item["properties"]["client_id"] = item["properties"]["app_id"]
                del item["properties"]["app_id"]

                # Copy authInformation into properties
                item["properties"]["sp_id"] = item["authInformation"]["sp_id"]
                item["properties"]["app_role_id_workspace_researcher"] = item["authInformation"]["roles"]["WorkspaceResearcher"]
                item["properties"]["app_role_id_workspace_owner"] = item["authInformation"]["roles"]["WorkspaceOwner"]

                # cleanup
                del item["authInformation"]
                self.update_item_dict(item)
                print(f'Upgraded authentication info for workspace id {item["id"]}')

import logging

from azure.cosmos import CosmosClient
from db.repositories.shared_services import SharedServiceRepository
from db.repositories.resources import IS_NOT_DELETED_CLAUSE


class SharedServiceMigration(SharedServiceRepository):
    def __init__(self, client: CosmosClient):
        super().__init__(client)

    def deleteDuplicatedSharedServices(self) -> bool:
        template_names = ['tre-shared-service-firewall', 'tre-shared-service-nexus', 'tre-shared-service-gitea']

        migrated = False
        for template_name in template_names:
            # This query needs to be kept up to date with
            for item in self.query(query=f'SELECT * FROM c WHERE c.resourceType = "shared-service" \
                                           AND c.templateName = "{template_name}" AND {IS_NOT_DELETED_CLAUSE} \
                                           ORDER BY c.updatedWhen ASC OFFSET 1 LIMIT 10000'):
                logging.info(f'Deleting element {item["id"]}')
                self.delete_item(item["id"])
                migrated = True

        return migrated

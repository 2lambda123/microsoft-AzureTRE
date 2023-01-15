from datetime import datetime, timedelta
import logging

from azure.storage.blob import generate_container_sas, ContainerSasPermissions, BlobServiceClient
from fastapi import HTTPException, status
from core import config, credentials
from models.domain.airlock_request import AirlockRequest, AirlockRequestStatus, AirlockRequestType, AirlockReviewUserResource
from models.domain.authentication import User
from models.domain.workspace import Workspace
from models.domain.user_resource import UserResource
from models.domain.operation import Operation
from typing import Tuple
from models.schemas.user_resource import UserResourceInCreate
from services.azure_resource_status import get_azure_resource_status
from resources import strings, constants

from airlock_resource_helpers import delete_review_user_resource, update_and_publish_event_airlock_request
from resource_helpers import save_and_deploy_resource

from db.repositories.user_resources import UserResourceRepository
from db.repositories.workspace_services import WorkspaceServiceRepository
from db.repositories.operations import OperationRepository
from db.repositories.airlock_requests import AirlockRequestRepository
from db.repositories.resource_templates import ResourceTemplateRepository
from db.repositories.resources_history import ResourceHistoryRepository


def get_account_by_request(airlock_request: AirlockRequest, workspace: Workspace) -> str:
    tre_id = config.TRE_ID
    short_workspace_id = workspace.id[-4:]
    if airlock_request.type == constants.IMPORT_TYPE:
        if airlock_request.status == AirlockRequestStatus.Draft:
            return constants.STORAGE_ACCOUNT_NAME_IMPORT_EXTERNAL.format(tre_id)
        elif airlock_request.status == AirlockRequestStatus.Submitted:
            return constants.STORAGE_ACCOUNT_NAME_IMPORT_INPROGRESS.format(tre_id)
        elif airlock_request.status == AirlockRequestStatus.InReview:
            return constants.STORAGE_ACCOUNT_NAME_IMPORT_INPROGRESS.format(tre_id)
        elif airlock_request.status == AirlockRequestStatus.Approved:
            return constants.STORAGE_ACCOUNT_NAME_IMPORT_APPROVED.format(short_workspace_id)
        elif airlock_request.status == AirlockRequestStatus.Rejected:
            return constants.STORAGE_ACCOUNT_NAME_IMPORT_REJECTED.format(tre_id)
        elif airlock_request.status == AirlockRequestStatus.Blocked:
            return constants.STORAGE_ACCOUNT_NAME_IMPORT_BLOCKED.format(tre_id)
    else:
        if airlock_request.status == AirlockRequestStatus.Draft:
            return constants.STORAGE_ACCOUNT_NAME_EXPORT_INTERNAL.format(short_workspace_id)
        elif airlock_request.status in AirlockRequestStatus.Submitted:
            return constants.STORAGE_ACCOUNT_NAME_EXPORT_INPROGRESS.format(short_workspace_id)
        elif airlock_request.status == AirlockRequestStatus.InReview:
            return constants.STORAGE_ACCOUNT_NAME_EXPORT_INPROGRESS.format(short_workspace_id)
        elif airlock_request.status == AirlockRequestStatus.Approved:
            return constants.STORAGE_ACCOUNT_NAME_EXPORT_APPROVED.format(tre_id)
        elif airlock_request.status == AirlockRequestStatus.Rejected:
            return constants.STORAGE_ACCOUNT_NAME_EXPORT_REJECTED.format(short_workspace_id)
        elif airlock_request.status == AirlockRequestStatus.Blocked:
            return constants.STORAGE_ACCOUNT_NAME_EXPORT_BLOCKED.format(short_workspace_id)


def validate_user_allowed_to_access_storage_account(user: User, airlock_request: AirlockRequest):
    if "WorkspaceResearcher" not in user.roles and airlock_request.status != AirlockRequestStatus.InReview:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=strings.AIRLOCK_UNAUTHORIZED_TO_SA)

    if "WorkspaceOwner" not in user.roles and "AirlockManager" not in user.roles and airlock_request.status == AirlockRequestStatus.InReview:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=strings.AIRLOCK_UNAUTHORIZED_TO_SA)
    return


def validate_request_status(airlock_request: AirlockRequest):
    if airlock_request.status in [AirlockRequestStatus.ApprovalInProgress,
                                  AirlockRequestStatus.RejectionInProgress,
                                  AirlockRequestStatus.BlockingInProgress]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=strings.AIRLOCK_REQUEST_IN_PROGRESS)
    elif airlock_request.status == AirlockRequestStatus.Cancelled:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=strings.AIRLOCK_REQUEST_IS_CANCELED)
    elif airlock_request.status in [AirlockRequestStatus.Failed,
                                    AirlockRequestStatus.Rejected,
                                    AirlockRequestStatus.Blocked]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=strings.AIRLOCK_REQUEST_UNACCESSIBLE)
    else:
        return


def get_required_permission(airlock_request: AirlockRequest) -> ContainerSasPermissions:
    if airlock_request.status == AirlockRequestStatus.Draft:
        return ContainerSasPermissions(read=True, write=True, list=True, delete=True)
    else:
        return ContainerSasPermissions(read=True, list=True)


def get_airlock_request_container_sas_token(account_name: str,
                                            airlock_request: AirlockRequest):
    blob_service_client = BlobServiceClient(account_url=get_account_url(account_name),
                                            credential=credentials.get_credential())
    expiry = datetime.utcnow() + timedelta(hours=config.AIRLOCK_SAS_TOKEN_EXPIRY_PERIOD_IN_HOURS)
    udk = blob_service_client.get_user_delegation_key(datetime.utcnow(), expiry)
    required_permission = get_required_permission(airlock_request)

    token = generate_container_sas(container_name=airlock_request.id,
                                   account_name=account_name,
                                   user_delegation_key=udk,
                                   permission=required_permission,
                                   expiry=expiry)

    return "https://{}.blob.core.windows.net/{}?{}" \
        .format(account_name, airlock_request.id, token)


def get_account_url(account_name: str) -> str:
    return f"https://{account_name}.blob.core.windows.net/"


def get_airlock_container_link(airlock_request: AirlockRequest, user, workspace):
    validate_user_allowed_to_access_storage_account(user, airlock_request)
    validate_request_status(airlock_request)
    account_name: str = get_account_by_request(airlock_request, workspace)
    return get_airlock_request_container_sas_token(account_name, airlock_request)


async def create_review_vm(airlock_request: AirlockRequest, user: User, workspace: Workspace, user_resource_repo: UserResourceRepository, workspace_service_repo: WorkspaceServiceRepository,
                           operation_repo: OperationRepository, airlock_request_repo: AirlockRequestRepository, resource_template_repo: ResourceTemplateRepository, resource_history_repo: ResourceHistoryRepository) -> Tuple[UserResource, Operation]:
    if airlock_request.type == AirlockRequestType.Import:
        config = workspace.properties["airlock_review_config"]["import"]
        workspace_id = config["import_vm_workspace_id"]
        workspace_service_id = config["import_vm_workspace_service_id"]
        user_resource_template_name = config["import_vm_user_resource_template_name"]
    else:
        assert airlock_request.type == AirlockRequestType.Export
        config = workspace.properties["airlock_review_config"]["export"]
        workspace_id = workspace.id
        workspace_service_id = config["export_vm_workspace_service_id"]
        user_resource_template_name = config["export_vm_user_resource_template_name"]

    # Check whether the user already has a healthy VM deployed for the request
    resource_already_exists = user.id in airlock_request.reviewUserResources
    if resource_already_exists:
        existing_resource = airlock_request.reviewUserResources[user.id]
        existing_resource = await user_resource_repo.get_user_resource_by_id(workspace_id=existing_resource.workspaceId, service_id=existing_resource.workspaceServiceId, resource_id=existing_resource.userResourceId)
        logging.info("User already has an existing review resource")
        await _handle_existing_review_resource(existing_resource, user, user_resource_repo, workspace_service_repo, operation_repo, resource_template_repo, resource_history_repo)

    # Create the VM
    user_resource, operation = await _deploy_vm(airlock_request, user, workspace, workspace_service_id, user_resource_template_name, user_resource_repo, workspace_service_repo, operation_repo, resource_template_repo, resource_history_repo, workspace_id)

    # Update the Airlock Request with the information on the VM
    updated_resource = await update_and_publish_event_airlock_request(
        airlock_request,
        airlock_request_repo,
        user,
        workspace,
        review_user_resource=AirlockReviewUserResource(
            workspaceId=workspace_id,
            workspaceServiceId=workspace_service_id,
            userResourceId=user_resource.id
        ))

    logging.info(f"Airlock Request {updated_resource.id} updated to include {updated_resource.reviewUserResources}")
    return updated_resource, operation


async def _deploy_vm(airlock_request: AirlockRequest, user: User, workspace: Workspace, workspace_service_id: str, user_resource_template_name: str,
                     user_resource_repo: UserResourceRepository, workspace_service_repo: WorkspaceServiceRepository, operation_repo: OperationRepository,
                     resource_template_repo: ResourceTemplateRepository, resource_history_repo: ResourceHistoryRepository):
    workspace_service = await workspace_service_repo.get_workspace_service_by_id(workspace_id=workspace.id, service_id=workspace_service_id)
    airlock_request_sas_url = get_airlock_container_link(airlock_request, user, workspace)

    user_resource_create = UserResourceInCreate(
        templateName=user_resource_template_name,
        properties={
            "display_name": "Airlock Review VM",
            "description": f"{airlock_request.title} (ID {airlock_request.id})",
            "airlock_request_sas_url": airlock_request_sas_url
        }
    )

    logging.info(f"Creating a user resource in {workspace.id} {workspace_service_id} {user_resource_template_name}")
    user_resource, resource_template = await user_resource_repo.create_user_resource_item(
        user_resource_create, workspace.id, workspace_service_id, workspace_service.templateName, user.id, user.roles)

    operation = await save_and_deploy_resource(
        resource=user_resource,
        resource_repo=user_resource_repo,
        operations_repo=operation_repo,
        resource_template_repo=resource_template_repo,
        resource_history_repo=resource_history_repo,
        user=user,
        resource_template=resource_template)

    return user_resource, operation


async def _handle_existing_review_resource(existing_resource: AirlockReviewUserResource, user: User, user_resource_repo: UserResourceRepository, workspace_service_repo: WorkspaceServiceRepository,
                                           operation_repo: OperationRepository, resource_template_repo: ResourceTemplateRepository, resource_history_repo: ResourceHistoryRepository):
    # Is the existing resource enabled, deployed, and can we get its power state information
    if existing_resource.isEnabled and existing_resource.deploymentStatus == "deployed" and 'azure_resource_id' in existing_resource.properties:
        resource_status = get_azure_resource_status(existing_resource.properties['azure_resource_id'])
        if "powerState" in resource_status and resource_status["powerState"] == "VM running":
            logging.info("Existing review resource is enabled, in a succeeded state and running. Returning a conflict error.")
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail="A healthy review resource is already deployed for the current user. "
                                "You may only have a single review resource.")

    # If it wasn't healthy or running, we'll delete the existing resource if not already deleted, and then create a new one
    logging.info("Existing review resource is in an unhealthy state.")
    if existing_resource.deploymentStatus != "deleted":
        logging.info("Deleting existing user resource...")
        _ = await delete_review_user_resource(
            user_resource=existing_resource,
            user_resource_repo=user_resource_repo,
            workspace_service_repo=workspace_service_repo,
            resource_template_repo=resource_template_repo,
            operations_repo=operation_repo,
            resource_history_repo=resource_history_repo,
            user=user
        )

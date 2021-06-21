import base64
import logging
from typing import List

import jwt
import requests
import rsa
from fastapi import Request, HTTPException, status
from fastapi.security import OAuth2AuthorizationCodeBearer
from pydantic import BaseModel, Field, parse_obj_as

from core import config
from resources import strings


class User(BaseModel):
    oid: str
    name: str
    email: str
    roles: List[str] = Field([])


class AzureADAuthorization(OAuth2AuthorizationCodeBearer):
    _jwt_keys: dict = {}

    def __init__(self, aad_instance: str, aad_tenant: str, auto_error: bool = True):
        super(AzureADAuthorization, self).__init__(
            authorizationUrl=f"{aad_instance}/{aad_tenant}/oauth2/v2.0/authorize",
            tokenUrl=f"{aad_instance}/{aad_tenant}/oauth2/v2.0/token",
            refreshUrl=f"{aad_instance}/{aad_tenant}/oauth2/v2.0/token",
            scheme_name="oauth2", scopes={f"api://{config.API_CLIENT_ID}/user_impersonation": "Access TRE API"},
            auto_error=auto_error
        )

    async def __call__(self, request: Request) -> User:
        token: str = await super(AzureADAuthorization, self).__call__(request)

        try:
            decoded_token = self._decode_token(token)
            return parse_obj_as(User, decoded_token)
        except Exception as e:
            logging.debug(e)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=strings.AUTH_COULD_NOT_VALIDATE_CREDENTIALS, headers={"WWW-Authenticate": "Bearer"})

    def _decode_token(self, token: str) -> dict:
        key_id = self._get_key_id(token)
        key = self._get_token_key(key_id)
        return jwt.decode(token, key, verify=True, algorithms=['RS256'], audience=config.API_AUDIENCE)

    @staticmethod
    def _get_key_id(token: str) -> str:
        headers = jwt.get_unverified_header(token)
        return headers['kid'] if headers and 'kid' in headers else None

    # The base64 encoded keys are not always correctly padded, so pad with the right number of =
    @staticmethod
    def _ensure_b64padding(key: str) -> str:
        key = key.encode('utf-8')
        missing_padding = len(key) % 4
        for _ in range(missing_padding):
            key = key + b'='
        return key

    # Rather tha use PyJWKClient.get_signing_key_from_jwt every time, we'll get all the keys from AAD and cache them.
    def _get_token_key(self, key_id: str) -> str:
        # TODO: Refactor this -- also - do we need all keys or only the one given by key_id? does this change?
        if key_id not in self._jwt_keys:
            response = requests.get(f"{config.AAD_INSTANCE}/{config.TENANT_ID}/v2.0/.well-known/openid-configuration")
            aad_metadata = response.json() if response.ok else None
            jwks_uri = aad_metadata['jwks_uri'] if aad_metadata and 'jwks_uri' in aad_metadata else None
            if jwks_uri:
                response = requests.get(jwks_uri)
                keys = response.json() if response.ok else None
                if keys and 'keys' in keys:
                    for key in keys['keys']:
                        n = int.from_bytes(base64.urlsafe_b64decode(self._ensure_b64padding(key['n'])), "big")
                        e = int.from_bytes(base64.urlsafe_b64decode(self._ensure_b64padding(key['e'])), "big")
                        pub_key = rsa.PublicKey(n, e)
                        # Cache the PEM formatted public key.
                        self._jwt_keys[key['kid']] = pub_key.save_pkcs1()

        return self._jwt_keys[key_id]


authorize = AzureADAuthorization(config.AAD_INSTANCE, config.TENANT_ID)

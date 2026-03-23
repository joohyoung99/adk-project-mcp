from __future__ import annotations

import base64
import hashlib
import json
import secrets
import threading
import time
import webbrowser
from dataclasses import asdict, dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse

import httpx

from app.config.settings import settings


USER_AGENT = "adk-project-mcp/0.1.0"
EXPIRY_SKEW_SECONDS = 60


@dataclass(slots=True)
class OAuthMetadata:
    issuer: str
    authorization_endpoint: str
    token_endpoint: str
    registration_endpoint: str | None = None


@dataclass(slots=True)
class ClientCredentials:
    client_id: str
    client_secret: str | None = None
    redirect_uri: str | None = None
    client_id_issued_at: int | None = None
    client_secret_expires_at: int | None = None


@dataclass(slots=True)
class TokenSet:
    access_token: str
    token_type: str = "Bearer"
    refresh_token: str | None = None
    scope: str | None = None
    expires_at: float | None = None

    @property
    def authorization_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.access_token}"}

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return self.expires_at <= time.time() + EXPIRY_SKEW_SECONDS


@dataclass(slots=True)
class OAuthStore:
    client: ClientCredentials | None = None
    tokens: TokenSet | None = None


class OAuthCallbackServer:
    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port
        self.event = threading.Event()
        self.params: dict[str, str] = {}
        self._server = ThreadingHTTPServer((host, port), self._make_handler())
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    def _make_handler(self) -> type[BaseHTTPRequestHandler]:
        parent = self

        class CallbackHandler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
                parsed = urlparse(self.path)
                if parsed.path != "/callback":
                    self.send_response(404)
                    self.end_headers()
                    return

                query = {key: values[0] for key, values in parse_qs(parsed.query).items() if values}
                parent.params = query
                parent.event.set()

                body = (
                    "Notion OAuth login complete. "
                    "You can return to the terminal and close this tab."
                ).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
                return

        return CallbackHandler

    def start(self) -> None:
        self._thread.start()

    def wait_for_callback(self, timeout: float) -> dict[str, str]:
        if not self.event.wait(timeout):
            raise TimeoutError("OAuth callback timed out. 브라우저 인증을 완료하지 못했습니다.")
        return self.params

    def close(self) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=2)


class NotionOAuthService:
    def __init__(self, store_path: Path | None = None) -> None:
        self.store_path = store_path or settings.notion_oauth_store_path

    def load_store(self) -> OAuthStore:
        if not self.store_path.exists():
            return OAuthStore()

        data = json.loads(self.store_path.read_text(encoding="utf-8"))
        client_data = data.get("client")
        token_data = data.get("tokens")
        return OAuthStore(
            client=ClientCredentials(**client_data) if client_data else None,
            tokens=TokenSet(**token_data) if token_data else None,
        )

    def save_store(self, store: OAuthStore) -> None:
        payload = {
            "client": asdict(store.client) if store.client else None,
            "tokens": asdict(store.tokens) if store.tokens else None,
        }
        self.store_path.write_text(
            json.dumps(payload, ensure_ascii=True, indent=2),
            encoding="utf-8",
        )
        self.store_path.chmod(0o600)

    def discover_oauth_metadata(self) -> OAuthMetadata:
        base_url = f"{urlparse(settings.notion_mcp_url).scheme}://{urlparse(settings.notion_mcp_url).netloc}"
        protected_resource_url = f"{base_url}/.well-known/oauth-protected-resource"

        with httpx.Client(timeout=10.0, headers={"User-Agent": USER_AGENT}) as client:
            protected_response = client.get(protected_resource_url)
            protected_response.raise_for_status()
            protected_resource = protected_response.json()
            auth_servers = protected_resource.get("authorization_servers") or []
            if not auth_servers:
                raise ValueError("Notion MCP 보호 리소스에서 authorization_servers를 찾지 못했습니다.")

            auth_server_url = auth_servers[0].rstrip("/")
            metadata_url = f"{auth_server_url}/.well-known/oauth-authorization-server"
            metadata_response = client.get(metadata_url)
            metadata_response.raise_for_status()
            metadata = metadata_response.json()

        if not metadata.get("authorization_endpoint") or not metadata.get("token_endpoint"):
            raise ValueError("OAuth 메타데이터에 필수 endpoint가 없습니다.")

        return OAuthMetadata(
            issuer=metadata["issuer"],
            authorization_endpoint=metadata["authorization_endpoint"],
            token_endpoint=metadata["token_endpoint"],
            registration_endpoint=metadata.get("registration_endpoint"),
        )

    def ensure_client_credentials(
        self,
        metadata: OAuthMetadata,
        redirect_uri: str,
    ) -> ClientCredentials:
        store = self.load_store()
        if store.client and store.client.client_id and store.client.redirect_uri == redirect_uri:
            return store.client

        if not metadata.registration_endpoint:
            raise ValueError("OAuth 서버가 dynamic client registration을 지원하지 않습니다.")

        registration_request = {
            "client_name": settings.notion_client_name,
            "redirect_uris": [redirect_uri],
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            "token_endpoint_auth_method": "none",
        }

        with httpx.Client(timeout=10.0, headers={"User-Agent": USER_AGENT}) as client:
            response = client.post(
                metadata.registration_endpoint,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
                json=registration_request,
            )
            response.raise_for_status()
            credentials = response.json()

        client_credentials = ClientCredentials(
            client_id=credentials["client_id"],
            client_secret=credentials.get("client_secret"),
            redirect_uri=redirect_uri,
            client_id_issued_at=credentials.get("client_id_issued_at"),
            client_secret_expires_at=credentials.get("client_secret_expires_at"),
        )
        store.client = client_credentials
        self.save_store(store)
        return client_credentials

    def build_authorization_url(
        self,
        metadata: OAuthMetadata,
        client_id: str,
        redirect_uri: str,
        code_challenge: str,
        state: str,
    ) -> str:
        params = urlencode(
            {
                "response_type": "code",
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "state": state,
                "code_challenge": code_challenge,
                "code_challenge_method": "S256",
                "prompt": "consent",
            }
        )
        return f"{metadata.authorization_endpoint}?{params}"

    def login_via_browser(self, timeout: float = 300.0) -> TokenSet:
        metadata = self.discover_oauth_metadata()
        redirect_uri = settings.notion_redirect_uri
        client_credentials = self.ensure_client_credentials(metadata, redirect_uri)

        code_verifier = self._generate_code_verifier()
        code_challenge = self._generate_code_challenge(code_verifier)
        state = secrets.token_hex(32)
        authorization_url = self.build_authorization_url(
            metadata=metadata,
            client_id=client_credentials.client_id,
            redirect_uri=redirect_uri,
            code_challenge=code_challenge,
            state=state,
        )

        callback_server = OAuthCallbackServer(
            host=settings.notion_redirect_host,
            port=settings.notion_redirect_port,
        )
        callback_server.start()
        try:
            opened = webbrowser.open(authorization_url)
            if not opened:
                print("브라우저를 자동으로 열지 못했습니다. 아래 URL을 직접 여세요.")
                print(authorization_url)

            params = callback_server.wait_for_callback(timeout)
        finally:
            callback_server.close()

        if params.get("error"):
            description = params.get("error_description", "unknown error")
            raise ValueError(f"OAuth 승인 실패: {params['error']} - {description}")
        if params.get("state") != state:
            raise ValueError("OAuth state 검증에 실패했습니다.")
        if "code" not in params:
            raise ValueError("OAuth callback에 authorization code가 없습니다.")

        tokens = self.exchange_code_for_tokens(
            code=params["code"],
            code_verifier=code_verifier,
            metadata=metadata,
            client_credentials=client_credentials,
            redirect_uri=redirect_uri,
        )
        store = self.load_store()
        store.client = client_credentials
        store.tokens = tokens
        self.save_store(store)
        return tokens

    def get_valid_access_token(self) -> TokenSet | None:
        store = self.load_store()
        if not store.tokens:
            return None
        if not store.tokens.is_expired:
            return store.tokens
        if not store.tokens.refresh_token or not store.client:
            return None

        metadata = self.discover_oauth_metadata()
        refreshed = self.refresh_tokens(metadata, store.client, store.tokens.refresh_token)
        store.tokens = refreshed
        self.save_store(store)
        return refreshed

    def exchange_code_for_tokens(
        self,
        code: str,
        code_verifier: str,
        metadata: OAuthMetadata,
        client_credentials: ClientCredentials,
        redirect_uri: str,
    ) -> TokenSet:
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": client_credentials.client_id,
            "redirect_uri": redirect_uri,
            "code_verifier": code_verifier,
        }
        if client_credentials.client_secret:
            payload["client_secret"] = client_credentials.client_secret

        with httpx.Client(timeout=10.0, headers={"User-Agent": USER_AGENT}) as client:
            response = client.post(
                metadata.token_endpoint,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data=payload,
            )
            response.raise_for_status()
            data = response.json()

        return self._token_set_from_response(data)

    def refresh_tokens(
        self,
        metadata: OAuthMetadata,
        client_credentials: ClientCredentials,
        refresh_token: str,
    ) -> TokenSet:
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": client_credentials.client_id,
        }
        if client_credentials.client_secret:
            payload["client_secret"] = client_credentials.client_secret

        with httpx.Client(timeout=10.0, headers={"User-Agent": USER_AGENT}) as client:
            response = client.post(
                metadata.token_endpoint,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data=payload,
            )

        if response.is_error:
            body = response.text
            if response.status_code == 400:
                try:
                    error = response.json().get("error")
                except json.JSONDecodeError:
                    error = None
                if error == "invalid_grant":
                    raise ValueError("Notion refresh token이 만료되었거나 취소되었습니다. 다시 login-notion을 실행하세요.")
            response.raise_for_status()

        data = response.json()
        if "refresh_token" not in data:
            data["refresh_token"] = refresh_token
        return self._token_set_from_response(data)

    def _generate_code_verifier(self) -> str:
        return secrets.token_urlsafe(64)

    def _generate_code_challenge(self, verifier: str) -> str:
        digest = hashlib.sha256(verifier.encode("utf-8")).digest()
        return base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")

    def _token_set_from_response(self, data: dict[str, Any]) -> TokenSet:
        expires_at = None
        expires_in = data.get("expires_in")
        if expires_in is not None:
            expires_at = time.time() + float(expires_in)

        return TokenSet(
            access_token=data["access_token"],
            token_type=data.get("token_type", "Bearer"),
            refresh_token=data.get("refresh_token"),
            scope=data.get("scope"),
            expires_at=expires_at,
        )

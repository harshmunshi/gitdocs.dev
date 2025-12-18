"""Secrets management for API tokens using keyring with encrypted file fallback."""

import base64
import hashlib
import json
import logging
import os
from pathlib import Path

from gitdocs.core.paths import get_credentials_path
from gitdocs.core.errors import AuthError

logger = logging.getLogger(__name__)

# Service names for keyring
JIRA_SERVICE = "gitdocs-jira"
CONFLUENCE_SERVICE = "gitdocs-confluence"
OPENAI_SERVICE = "gitdocs-openai"

# Environment variable overrides
ENV_JIRA_TOKEN = "GITDOCS_JIRA_TOKEN"
ENV_CONFLUENCE_TOKEN = "GITDOCS_CONFLUENCE_TOKEN"
ENV_OPENAI_KEY = "GITDOCS_OPENAI_KEY"


def _get_keyring():
    """Get keyring module if available."""
    try:
        import keyring
        # Test if keyring backend is available
        keyring.get_keyring()
        return keyring
    except Exception:
        return None


def _get_machine_key() -> bytes:
    """Generate a machine-specific key for fallback encryption."""
    # Use a combination of username and machine ID for basic encryption
    import getpass
    import platform
    
    key_material = f"{getpass.getuser()}-{platform.node()}-gitdocs"
    return hashlib.sha256(key_material.encode()).digest()


def _simple_encrypt(data: str) -> str:
    """Simple XOR-based encryption (not cryptographically secure, just obfuscation)."""
    key = _get_machine_key()
    encrypted = bytes(b ^ key[i % len(key)] for i, b in enumerate(data.encode()))
    return base64.b64encode(encrypted).decode()


def _simple_decrypt(encrypted: str) -> str:
    """Decrypt data encrypted with _simple_encrypt."""
    key = _get_machine_key()
    data = base64.b64decode(encrypted.encode())
    decrypted = bytes(b ^ key[i % len(key)] for i, b in enumerate(data))
    return decrypted.decode()


def _load_fallback_credentials() -> dict[str, str]:
    """Load credentials from fallback encrypted file."""
    creds_path = get_credentials_path()
    if not creds_path.exists():
        return {}
    
    try:
        encrypted = creds_path.read_text()
        decrypted = _simple_decrypt(encrypted)
        return json.loads(decrypted)
    except Exception as e:
        logger.warning(f"Failed to load fallback credentials: {e}")
        return {}


def _save_fallback_credentials(creds: dict[str, str]) -> None:
    """Save credentials to fallback encrypted file."""
    creds_path = get_credentials_path()
    try:
        data = json.dumps(creds)
        encrypted = _simple_encrypt(data)
        creds_path.write_text(encrypted)
        creds_path.chmod(0o600)
    except Exception as e:
        logger.error(f"Failed to save fallback credentials: {e}")
        raise AuthError(f"Failed to save credentials: {e}")


def set_secret(service: str, username: str, secret: str) -> None:
    """
    Store a secret using keyring or fallback to encrypted file.
    
    Args:
        service: Service identifier (e.g., 'gitdocs-jira')
        username: Username/key for the secret
        secret: The secret value to store
    """
    keyring = _get_keyring()
    
    if keyring:
        try:
            keyring.set_password(service, username, secret)
            logger.debug(f"Stored secret for {service}/{username} in keyring")
            return
        except Exception as e:
            logger.warning(f"Keyring failed, using fallback: {e}")
    
    # Fallback to encrypted file
    creds = _load_fallback_credentials()
    creds[f"{service}:{username}"] = secret
    _save_fallback_credentials(creds)
    logger.debug(f"Stored secret for {service}/{username} in fallback file")


def get_secret(service: str, username: str) -> str | None:
    """
    Retrieve a secret from keyring or fallback.
    
    Args:
        service: Service identifier
        username: Username/key for the secret
        
    Returns:
        The secret value or None if not found.
    """
    keyring = _get_keyring()
    
    if keyring:
        try:
            secret = keyring.get_password(service, username)
            if secret:
                return secret
        except Exception as e:
            logger.warning(f"Keyring retrieval failed: {e}")
    
    # Try fallback
    creds = _load_fallback_credentials()
    return creds.get(f"{service}:{username}")


def delete_secret(service: str, username: str) -> None:
    """Delete a secret from storage."""
    keyring = _get_keyring()
    
    if keyring:
        try:
            keyring.delete_password(service, username)
        except Exception:
            pass
    
    # Also try to remove from fallback
    creds = _load_fallback_credentials()
    key = f"{service}:{username}"
    if key in creds:
        del creds[key]
        _save_fallback_credentials(creds)


def get_jira_api_token() -> str:
    """Get Jira API token from environment or secure storage."""
    # Check environment first
    if token := os.environ.get(ENV_JIRA_TOKEN):
        return token
    
    # Check keyring/fallback
    if token := get_secret(JIRA_SERVICE, "api_token"):
        return token
    
    raise AuthError(
        "Jira API token not found. "
        f"Set {ENV_JIRA_TOKEN} environment variable or run 'gitdocs auth login'"
    )


def set_jira_api_token(token: str) -> None:
    """Store Jira API token."""
    set_secret(JIRA_SERVICE, "api_token", token)


def get_confluence_api_token() -> str:
    """Get Confluence API token from environment or secure storage."""
    # Check environment first
    if token := os.environ.get(ENV_CONFLUENCE_TOKEN):
        return token
    
    # Check keyring/fallback
    if token := get_secret(CONFLUENCE_SERVICE, "api_token"):
        return token
    
    raise AuthError(
        "Confluence API token not found. "
        f"Set {ENV_CONFLUENCE_TOKEN} environment variable or run 'gitdocs auth login'"
    )


def set_confluence_api_token(token: str) -> None:
    """Store Confluence API token."""
    set_secret(CONFLUENCE_SERVICE, "api_token", token)


def get_openai_api_key() -> str | None:
    """Get OpenAI API key from environment or secure storage."""
    if key := os.environ.get(ENV_OPENAI_KEY):
        return key
    
    if key := os.environ.get("OPENAI_API_KEY"):
        return key
    
    return get_secret(OPENAI_SERVICE, "api_key")


def set_openai_api_key(key: str) -> None:
    """Store OpenAI API key."""
    set_secret(OPENAI_SERVICE, "api_key", key)


def clear_all_secrets() -> None:
    """Clear all stored secrets."""
    # Delete from keyring
    for service in [JIRA_SERVICE, CONFLUENCE_SERVICE, OPENAI_SERVICE]:
        try:
            delete_secret(service, "api_token")
            delete_secret(service, "api_key")
        except Exception:
            pass
    
    # Clear fallback file
    creds_path = get_credentials_path()
    if creds_path.exists():
        creds_path.unlink()


class SecretsManager:
    """
    High-level interface for managing secrets.
    
    Provides a convenient class-based API for storing and retrieving
    API tokens and credentials.
    """
    
    def get_jira_token(self, base_url: str | None = None) -> str | None:
        """Get Jira API token."""
        try:
            return get_jira_api_token()
        except AuthError:
            return None
    
    def store_jira_token(self, base_url: str, token: str) -> None:
        """Store Jira API token."""
        set_jira_api_token(token)
    
    def get_confluence_token(self, base_url: str | None = None) -> str | None:
        """Get Confluence API token."""
        try:
            return get_confluence_api_token()
        except AuthError:
            return None
    
    def store_confluence_token(self, base_url: str, token: str) -> None:
        """Store Confluence API token."""
        set_confluence_api_token(token)
    
    def get_openai_key(self) -> str | None:
        """Get OpenAI API key."""
        return get_openai_api_key()
    
    def store_openai_key(self, key: str) -> None:
        """Store OpenAI API key."""
        set_openai_api_key(key)
    
    def clear_all(self) -> None:
        """Clear all stored secrets."""
        clear_all_secrets()


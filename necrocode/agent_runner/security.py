"""
Security utilities for Agent Runner.

This module provides security-related functionality including:
- Credential management (environment variables, secret mounts)
- Secret masking in logs
- Permission validation

Requirements: 1.4, 10.1, 10.2, 10.4, 10.5
"""

import logging
import os
import re
from pathlib import Path
from typing import Optional, Dict, Any, Set

from necrocode.agent_runner.exceptions import SecurityError

logger = logging.getLogger(__name__)


class CredentialManager:
    """
    Manages authentication credentials for Agent Runner.
    
    Supports loading credentials from:
    - Environment variables
    - Secret mount files (Kubernetes secrets, Docker secrets)
    
    Requirements: 1.4, 10.1
    """
    
    def __init__(self):
        """Initialize CredentialManager."""
        self._credentials: Dict[str, str] = {}
        self._secret_mount_paths: Dict[str, Path] = {}
    
    def get_git_token(self, env_var: str = "GIT_TOKEN") -> Optional[str]:
        """
        Get Git authentication token.
        
        Attempts to load the token from:
        1. Environment variable
        2. Secret mount file (if configured)
        
        Args:
            env_var: Environment variable name for Git token
            
        Returns:
            Git token if found, None otherwise
            
        Raises:
            SecurityError: If token is required but not found
            
        Requirements: 1.4, 10.1
        """
        # Try environment variable first
        token = os.getenv(env_var)
        if token:
            logger.debug(f"Git token loaded from environment variable: {env_var}")
            self._credentials["git_token"] = token
            return token
        
        # Try secret mount if configured
        secret_path = self._secret_mount_paths.get("git_token")
        if secret_path:
            token = self._load_secret_from_file(secret_path)
            if token:
                logger.debug(f"Git token loaded from secret mount: {secret_path}")
                self._credentials["git_token"] = token
                return token
        
        logger.warning("Git token not found in environment or secret mount")
        return None
    
    def get_api_key(
        self,
        service: str,
        env_var: Optional[str] = None
    ) -> Optional[str]:
        """
        Get API key for a service.
        
        Args:
            service: Service name (e.g., "artifact_store", "kiro")
            env_var: Environment variable name. If None, uses default naming
            
        Returns:
            API key if found, None otherwise
            
        Requirements: 1.4, 10.1
        """
        # Use provided env_var or construct default
        if env_var is None:
            env_var = f"{service.upper()}_API_KEY"
        
        # Try environment variable
        api_key = os.getenv(env_var)
        if api_key:
            logger.debug(f"API key for {service} loaded from environment: {env_var}")
            self._credentials[f"{service}_api_key"] = api_key
            return api_key
        
        # Try secret mount
        secret_path = self._secret_mount_paths.get(f"{service}_api_key")
        if secret_path:
            api_key = self._load_secret_from_file(secret_path)
            if api_key:
                logger.debug(f"API key for {service} loaded from secret mount: {secret_path}")
                self._credentials[f"{service}_api_key"] = api_key
                return api_key
        
        logger.warning(f"API key for {service} not found")
        return None
    
    def configure_secret_mount(self, secret_name: str, mount_path: Path) -> None:
        """
        Configure a secret mount path.
        
        Used for Kubernetes secrets or Docker secrets that are mounted
        as files in the container filesystem.
        
        Args:
            secret_name: Name of the secret (e.g., "git_token", "artifact_store_api_key")
            mount_path: Path to the mounted secret file
            
        Requirements: 1.4, 10.1
        """
        if not mount_path.exists():
            logger.warning(f"Secret mount path does not exist: {mount_path}")
        
        self._secret_mount_paths[secret_name] = mount_path
        logger.debug(f"Configured secret mount: {secret_name} -> {mount_path}")
    
    def _load_secret_from_file(self, path: Path) -> Optional[str]:
        """
        Load secret from a file.
        
        Args:
            path: Path to secret file
            
        Returns:
            Secret value if file exists and is readable, None otherwise
        """
        try:
            if not path.exists():
                return None
            
            with open(path, "r") as f:
                secret = f.read().strip()
            
            if not secret:
                logger.warning(f"Secret file is empty: {path}")
                return None
            
            return secret
            
        except Exception as e:
            logger.error(f"Failed to load secret from {path}: {e}")
            return None
    
    def clear_credentials(self) -> None:
        """
        Clear all loaded credentials from memory.
        
        Should be called during cleanup to ensure credentials
        are not left in memory after task execution.
        
        Requirements: 10.3
        """
        # Overwrite credential values before clearing
        for key in self._credentials:
            self._credentials[key] = "X" * len(self._credentials[key])
        
        self._credentials.clear()
        logger.debug("Credentials cleared from memory")
    
    def validate_credentials(self, required: Set[str]) -> None:
        """
        Validate that required credentials are available.
        
        Args:
            required: Set of required credential names
            
        Raises:
            SecurityError: If required credentials are missing
            
        Requirements: 1.4, 10.1
        """
        missing = required - set(self._credentials.keys())
        if missing:
            error_msg = f"Missing required credentials: {', '.join(missing)}"
            logger.error(error_msg)
            raise SecurityError(error_msg)


class SecretMasker:
    """
    Masks sensitive information in logs and output.
    
    Automatically detects and masks:
    - Tokens (Bearer tokens, API keys)
    - Passwords
    - Other sensitive patterns
    
    Requirements: 10.5
    """
    
    # Patterns for detecting secrets
    SECRET_PATTERNS = [
        # Bearer tokens
        (re.compile(r'Bearer\s+([A-Za-z0-9\-._~+/]+=*)'), 'Bearer ***'),
        # API keys (various formats)
        (re.compile(r'api[_-]?key["\']?\s*[:=]\s*["\']?([A-Za-z0-9\-._~+/]{20,})'), 'api_key=***'),
        # Generic tokens
        (re.compile(r'token["\']?\s*[:=]\s*["\']?([A-Za-z0-9\-._~+/]{20,})'), 'token=***'),
        # Passwords
        (re.compile(r'password["\']?\s*[:=]\s*["\']?([^\s"\']+)'), 'password=***'),
        # GitHub tokens (ghp_, gho_, ghs_, ghr_)
        (re.compile(r'gh[psor]_[A-Za-z0-9]{36,}'), 'gh*_***'),
        # AWS access keys
        (re.compile(r'AKIA[0-9A-Z]{16}'), 'AKIA***'),
        # Generic base64-like secrets (40+ chars)
        (re.compile(r'["\']([A-Za-z0-9+/]{40,}={0,2})["\']'), '***'),
    ]
    
    def __init__(self):
        """Initialize SecretMasker."""
        self._known_secrets: Set[str] = set()
    
    def add_secret(self, secret: str) -> None:
        """
        Add a known secret to be masked.
        
        Args:
            secret: Secret value to mask in logs
            
        Requirements: 10.5
        """
        if secret and len(secret) >= 8:  # Only mask reasonably long secrets
            self._known_secrets.add(secret)
    
    def mask(self, text: str) -> str:
        """
        Mask secrets in text.
        
        Replaces detected secrets with masked placeholders.
        
        Args:
            text: Text that may contain secrets
            
        Returns:
            Text with secrets masked
            
        Requirements: 10.5
        """
        if not text:
            return text
        
        masked_text = text
        
        # Mask known secrets first (exact matches)
        for secret in self._known_secrets:
            if secret in masked_text:
                # Replace with asterisks, keeping first and last 4 chars if long enough
                if len(secret) > 12:
                    replacement = f"{secret[:4]}***{secret[-4:]}"
                else:
                    replacement = "***"
                masked_text = masked_text.replace(secret, replacement)
        
        # Apply pattern-based masking
        for pattern, replacement in self.SECRET_PATTERNS:
            masked_text = pattern.sub(replacement, masked_text)
        
        return masked_text
    
    def mask_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Mask secrets in a dictionary (recursive).
        
        Args:
            data: Dictionary that may contain secrets
            
        Returns:
            Dictionary with secrets masked
            
        Requirements: 10.5
        """
        masked = {}
        
        for key, value in data.items():
            # Check if key suggests sensitive data
            key_lower = key.lower()
            is_sensitive = any(
                keyword in key_lower
                for keyword in ["token", "password", "secret", "key", "credential"]
            )
            
            if is_sensitive and isinstance(value, str):
                # Mask the entire value
                masked[key] = "***"
            elif isinstance(value, dict):
                # Recursively mask nested dicts
                masked[key] = self.mask_dict(value)
            elif isinstance(value, str):
                # Mask patterns in string values
                masked[key] = self.mask(value)
            else:
                # Keep other types as-is
                masked[key] = value
        
        return masked


class PermissionValidator:
    """
    Validates and enforces permission restrictions.
    
    Ensures that Agent Runner operates with minimal required permissions:
    - Task-scoped Git operations only
    - Restricted workspace access
    - No system-level operations
    
    Requirements: 10.2, 10.4
    """
    
    def __init__(self, workspace_root: Path):
        """
        Initialize PermissionValidator.
        
        Args:
            workspace_root: Root path of the workspace (access boundary)
        """
        self.workspace_root = workspace_root.resolve()
    
    def validate_path_access(self, path: Path, operation: str = "read") -> None:
        """
        Validate that a path is within allowed boundaries.
        
        Ensures that file operations are restricted to the workspace
        and do not access system files or other sensitive locations.
        
        Args:
            path: Path to validate
            operation: Operation type ("read", "write", "execute")
            
        Raises:
            SecurityError: If path access is not allowed
            
        Requirements: 10.2, 10.4
        """
        try:
            resolved_path = path.resolve()
        except Exception as e:
            raise SecurityError(f"Invalid path: {path}: {e}")
        
        # Check if path is within workspace
        try:
            resolved_path.relative_to(self.workspace_root)
        except ValueError:
            raise SecurityError(
                f"Path access denied: {path} is outside workspace {self.workspace_root}"
            )
        
        # Additional checks for write/execute operations
        if operation in ("write", "execute"):
            # Prevent writing to .git directory (except through git commands)
            if ".git" in resolved_path.parts:
                raise SecurityError(
                    f"Direct access to .git directory not allowed: {path}"
                )
        
        logger.debug(f"Path access validated: {path} ({operation})")
    
    def validate_git_operation(self, operation: str, **kwargs) -> None:
        """
        Validate that a Git operation is allowed.
        
        Restricts Git operations to task-scoped actions:
        - Branch creation/checkout
        - Commit
        - Push to feature branches
        - No force push
        - No tag operations
        - No remote manipulation
        
        Args:
            operation: Git operation name
            **kwargs: Operation-specific parameters
            
        Raises:
            SecurityError: If operation is not allowed
            
        Requirements: 10.2, 10.4
        """
        allowed_operations = {
            "checkout", "fetch", "pull", "rebase",
            "branch", "commit", "push", "diff", "status"
        }
        
        if operation not in allowed_operations:
            raise SecurityError(f"Git operation not allowed: {operation}")
        
        # Validate push operations
        if operation == "push":
            branch = kwargs.get("branch", "")
            force = kwargs.get("force", False)
            
            if force:
                raise SecurityError("Force push not allowed")
            
            # Only allow pushing to feature branches
            if not branch.startswith(("feature/", "task/")):
                raise SecurityError(
                    f"Push only allowed to feature/task branches, got: {branch}"
                )
        
        # Validate branch operations
        if operation == "branch":
            branch_name = kwargs.get("branch_name", "")
            delete = kwargs.get("delete", False)
            
            if delete:
                raise SecurityError("Branch deletion not allowed")
            
            # Ensure branch follows naming convention
            if not branch_name.startswith(("feature/", "task/")):
                logger.warning(
                    f"Branch name does not follow convention: {branch_name}"
                )
        
        logger.debug(f"Git operation validated: {operation}")
    
    def validate_command_execution(self, command: str) -> None:
        """
        Validate that a command execution is safe.
        
        Prevents execution of dangerous commands that could:
        - Access system resources
        - Modify system configuration
        - Execute arbitrary code
        - Access network resources (except allowed services)
        
        Args:
            command: Command to validate
            
        Raises:
            SecurityError: If command is not allowed
            
        Requirements: 10.2, 10.4
        """
        # List of dangerous command patterns
        dangerous_patterns = [
            r'\brm\s+-rf\s+/',  # Recursive delete from root
            r'\bsudo\b',  # Privilege escalation
            r'\bsu\b',  # User switching
            r'\bchmod\s+777',  # Overly permissive permissions
            r'\bcurl\b.*\|\s*bash',  # Pipe to shell
            r'\bwget\b.*\|\s*bash',  # Pipe to shell
            r'\beval\b',  # Code evaluation
            r'\bexec\b',  # Code execution
            r'/etc/',  # System configuration
            r'/sys/',  # System files
            r'/proc/',  # Process information
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                raise SecurityError(
                    f"Command contains dangerous pattern: {pattern}"
                )
        
        logger.debug(f"Command execution validated: {command[:50]}...")


def create_secure_environment(
    credential_manager: CredentialManager,
    workspace_root: Path
) -> Dict[str, str]:
    """
    Create a secure environment for subprocess execution.
    
    Builds an environment dictionary with:
    - Minimal required environment variables
    - Credentials from credential manager
    - No sensitive system variables
    
    Args:
        credential_manager: Credential manager with loaded credentials
        workspace_root: Workspace root path
        
    Returns:
        Environment dictionary for subprocess execution
        
    Requirements: 10.2, 10.4
    """
    # Start with minimal environment
    env = {
        "HOME": str(Path.home()),
        "PATH": os.getenv("PATH", "/usr/local/bin:/usr/bin:/bin"),
        "LANG": os.getenv("LANG", "en_US.UTF-8"),
    }
    
    # Add Git token if available
    git_token = credential_manager._credentials.get("git_token")
    if git_token:
        env["GIT_TOKEN"] = git_token
    
    # Add workspace-specific variables
    env["WORKSPACE_ROOT"] = str(workspace_root)
    
    return env

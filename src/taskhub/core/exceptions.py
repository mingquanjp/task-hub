"""Domain exceptions representing business logic errors across the application."""


class DomainError(Exception):
    """Base exception for all domain-specific errors."""


class AuthenticationError(DomainError):
    """Base exception for identity and authentication failures."""


class InvalidCredentialsError(AuthenticationError):
    """Raised without revealing whether an email or password was incorrect."""


class InvalidTokenError(AuthenticationError):
    """Raised when an access or refresh token is malformed, invalid, or expired."""


class IncorrectCurrentPasswordError(AuthenticationError):
    """Raised when attempting to change a password with an incorrect current password."""


class TokenRevokedError(AuthenticationError):
    """Raised when attempting to use a token that has been explicitly revoked."""


class InactiveUserError(AuthenticationError):
    """Raised when an inactive identity attempts authentication or access."""


class UserNotFoundError(AuthenticationError):
    """Raised when the user identity associated with a request or token no longer exists."""


class ConflictError(DomainError):
    """Base exception for data conflicts."""


class UserAlreadyExistsError(ConflictError):
    """Raised when registration or update uses an existing email."""


class AuthorizationError(DomainError):
    """Base exception for permission and authorization failures."""


class PermissionDeniedError(AuthorizationError):
    """Raised when an authenticated user attempts an action without sufficient roles."""


class ResourceNotFoundError(DomainError):
    """Base exception for when a requested domain resource does not exist."""


class WorkspaceMemberAlreadyExistsError(ConflictError):
    """Raised when attempting to add a user to a workspace they are already a member of."""


class WorkspaceOwnerRemovalError(ConflictError):
    """Raised when attempting to remove the owner of a workspace."""


class InvalidWorkspaceRoleError(DomainError):
    """Raised when an invalid role is used for a workspace operation."""

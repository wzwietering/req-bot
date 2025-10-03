"""User session management functions."""

from sqlalchemy.orm import Session as DBSession

from requirements_bot.api.auth import JWTService, OAuth2Providers
from requirements_bot.core.logging import log_event, mask_text, span
from requirements_bot.core.services.user_registration_service import UserRegistrationService
from requirements_bot.core.services.user_service import UserService


async def process_oauth_user(
    oauth_providers: OAuth2Providers, provider: str, token: dict, db_session: DBSession, jwt_service: JWTService
):
    """Process OAuth user information and create session."""
    with span(
        "oauth.process_user",
        component="auth",
        operation="process_user",
        provider=provider,
    ):
        log_event(
            "oauth.user_info_request_start",
            component="auth",
            operation="get_user_info",
            provider=provider,
        )

        user_create = await oauth_providers.get_user_info(provider, token)

        log_event(
            "oauth.user_info_retrieved",
            component="auth",
            operation="get_user_info",
            provider=provider,
            has_email=bool(user_create and getattr(user_create, "email", None)),
            has_name=bool(user_create and getattr(user_create, "name", None)),
            user_email_domain=mask_text(getattr(user_create, "email", "").split("@")[-1])
            if user_create and getattr(user_create, "email", None)
            else None,
        )

        return create_user_session(user_create, db_session, jwt_service)


def create_user_session(user_create, db_session: DBSession, jwt_service: JWTService):
    """Create user and generate session tokens."""
    with span(
        "oauth.create_user_session",
        component="auth",
        operation="create_user_session",
    ):
        log_event(
            "oauth.user_registration_start",
            component="auth",
            operation="get_or_create_user",
        )

        registration_service = UserRegistrationService(db_session)
        user = registration_service.get_or_create_user(user_create)

        log_event(
            "oauth.user_registration_complete",
            component="auth",
            operation="get_or_create_user",
            user_id=user.id,
            user_email_masked=mask_text(user.email) if user.email else None,
        )

        log_event(
            "oauth.jwt_creation_start",
            component="auth",
            operation="create_token_pair",
            user_id=user.id,
        )

        user_service = UserService(db_session)
        token_data = jwt_service.create_token_pair(user.id, user.email)

        log_event(
            "oauth.jwt_creation_complete",
            component="auth",
            operation="create_token_pair",
            user_id=user.id,
            has_access_token=bool(token_data.get("access_token")),
            has_refresh_token=bool(token_data.get("refresh_token")),
            expires_in=token_data.get("expires_in"),
        )

        response = token_data.copy()
        response["user"] = user_service.to_response(user)
        return response

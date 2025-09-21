from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session as DBSession

from requirements_bot.api.auth import JWTService, OAuth2Providers, get_jwt_service, get_oauth_providers
from requirements_bot.api.dependencies import get_database_session
from requirements_bot.core.models import UserResponse
from requirements_bot.core.services.user_service import UserService

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.get("/login/{provider}")
async def oauth_login(
    provider: str,
    request: Request,
    oauth_providers: Annotated[OAuth2Providers, Depends(get_oauth_providers)],
):
    """Initiate OAuth login with specified provider."""
    try:
        oauth_client = oauth_providers.get_provider(provider)

        # Generate state for CSRF protection
        state = oauth_providers.generate_state()

        # Build callback URL
        callback_url = str(request.url_for("oauth_callback", provider=provider))

        # Redirect to provider's authorization URL
        redirect_url = await oauth_client.authorize_redirect(request, callback_url, state=state)

        return redirect_url

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to initiate OAuth login: {str(e)}"
        )


@router.get("/callback/{provider}")
async def oauth_callback(
    provider: str,
    request: Request,
    db_session: Annotated[DBSession, Depends(get_database_session)],
    oauth_providers: Annotated[OAuth2Providers, Depends(get_oauth_providers)],
    jwt_service: Annotated[JWTService, Depends(get_jwt_service)],
):
    """Handle OAuth callback and create user session."""
    try:
        oauth_client = oauth_providers.get_provider(provider)

        # Get state parameter from query
        state = request.query_params.get("state")
        if not state or not oauth_providers.verify_state(state):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired state parameter")

        # Exchange authorization code for token
        token = await oauth_client.authorize_access_token(request)
        if not token:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to obtain access token")

        # Get user info from provider
        user_create = await oauth_providers.get_user_info(provider, token)

        # Create or get existing user
        user_service = UserService(db_session)
        user = user_service.create_user(user_create)

        # Commit the transaction
        db_session.commit()

        # Generate JWT token
        access_token = jwt_service.create_access_token(user.id, user.email)

        # In a real application, you might redirect to frontend with token
        # For now, return the token directly
        return {"access_token": access_token, "token_type": "bearer", "user": user_service.to_response(user)}

    except HTTPException:
        raise
    except Exception as e:
        db_session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"OAuth callback failed: {str(e)}"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    request: Request,
    db_session: Annotated[DBSession, Depends(get_database_session)],
):
    """Get current authenticated user profile."""
    # User info is set by AuthenticationMiddleware
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    user_service = UserService(db_session)
    user = user_service.get_user_by_id(user_id)

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return user_service.to_response(user)


@router.post("/logout")
async def logout():
    """Logout user (invalidate token on client side)."""
    # With JWT, logout is typically handled client-side by removing the token
    # In a more sophisticated setup, you might maintain a token blacklist
    return {"message": "Logged out successfully"}

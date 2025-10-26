"""Usage tracking and quota management routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from specscribe.api.dependencies import get_current_user_id, get_usage_tracking_service
from specscribe.core.services.exceptions import UserNotFoundError
from specscribe.core.services.usage_tracking_service import UsageTrackingService

router = APIRouter(prefix="/usage", tags=["usage"])


class UsageStatsResponse(BaseModel):
    """Usage statistics response."""

    questions_generated: int
    answers_submitted: int
    quota_limit: int
    quota_remaining: int
    window_days: int


@router.get("/me", response_model=UsageStatsResponse)
async def get_my_usage(
    user_id: Annotated[str, Depends(get_current_user_id)],
    usage_service: Annotated[UsageTrackingService, Depends(get_usage_tracking_service)],
) -> UsageStatsResponse:
    """Get current user's usage statistics."""
    try:
        stats = usage_service.get_user_usage_stats(user_id)
        return UsageStatsResponse(**stats)
    except UserNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

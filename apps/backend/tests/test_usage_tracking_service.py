"""Tests for UsageTrackingService."""

from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import pytest

from specscribe.core.database_models import UsageEventTable, UserTable
from specscribe.core.services.exceptions import QuotaExceededError, UserNotFoundError
from specscribe.core.services.usage_tracking_service import UsageTrackingService


class TestUsageTrackingService:
    """Test usage tracking and quota enforcement."""

    @pytest.fixture(autouse=True)
    def set_test_env(self, monkeypatch):
        """Set environment variables for quota limits."""
        monkeypatch.setenv("FREE_TIER_QUESTION_LIMIT", "10")
        monkeypatch.setenv("PRO_TIER_QUESTION_LIMIT", "10000")

    @pytest.fixture
    def mock_storage(self):
        """Create mock DatabaseManager."""
        storage = Mock()
        mock_session = Mock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)
        storage.SessionLocal = Mock(return_value=mock_session)
        storage._mock_session = mock_session  # Store for test access
        return storage

    @pytest.fixture
    def usage_service(self, mock_storage):
        """Create usage tracking service."""
        return UsageTrackingService(mock_storage)

    @pytest.fixture
    def free_tier_user(self):
        """Create a free tier user."""
        user = Mock(spec=UserTable)
        user.id = "user-123"
        user.tier = "free"
        return user

    @pytest.fixture
    def pro_tier_user(self):
        """Create a pro tier user."""
        user = Mock(spec=UserTable)
        user.id = "user-456"
        user.tier = "pro"
        return user

    def test_record_question_generated(self, usage_service, mock_storage):
        """Test recording question generation event."""
        usage_service.record_question_generated("user-123", "question-1")

        mock_session = mock_storage._mock_session
        mock_session.add.assert_called_once()
        event = mock_session.add.call_args[0][0]
        assert isinstance(event, UsageEventTable)
        assert event.user_id == "user-123"
        assert event.event_type == "question_generated"
        assert event.entity_id == "question-1"

    def test_record_answer_submitted(self, usage_service, mock_storage):
        """Test recording answer submission event."""
        usage_service.record_answer_submitted("user-123", "answer-1")

        mock_session = mock_storage._mock_session
        mock_session.add.assert_called_once()
        event = mock_session.add.call_args[0][0]
        assert isinstance(event, UsageEventTable)
        assert event.user_id == "user-123"
        assert event.event_type == "answer_submitted"
        assert event.entity_id == "answer-1"

    def test_get_quota_limit_free_tier(self, usage_service):
        """Test quota limit for free tier."""
        limit = usage_service.get_quota_limit("free")
        assert limit == 10

    def test_get_quota_limit_pro_tier(self, usage_service):
        """Test quota limit for pro tier."""
        limit = usage_service.get_quota_limit("pro")
        assert limit == 10000

    def test_count_questions_no_usage(self, usage_service, mock_storage):
        """Test question count with no usage."""
        mock_session = mock_storage._mock_session
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 0
        mock_session.query.return_value = mock_query

        count = usage_service.count_questions_in_window("user-123", days=30)
        assert count == 0

    def test_count_questions_with_usage(self, usage_service, mock_storage):
        """Test question count with usage."""
        mock_session = mock_storage._mock_session
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 5
        mock_session.query.return_value = mock_query

        count = usage_service.count_questions_in_window("user-123", days=30)
        assert count == 5

    def test_check_quota_available_within_limit(self, usage_service, mock_storage):
        """Test quota check when within limit."""
        mock_session = mock_storage._mock_session
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 5  # Below limit of 10
        mock_session.query.return_value = mock_query

        # Should not raise exception
        usage_service.check_quota_available("user-123", "free")

    def test_check_quota_available_at_limit(self, usage_service, mock_storage):
        """Test quota check when at limit."""
        mock_session = mock_storage._mock_session
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 10  # At limit
        mock_session.query.return_value = mock_query

        with pytest.raises(QuotaExceededError) as exc_info:
            usage_service.check_quota_available("user-123", "free")

        assert exc_info.value.current == 10
        assert exc_info.value.limit == 10
        assert "quota exceeded" in str(exc_info.value).lower()

    def test_check_quota_available_over_limit(self, usage_service, mock_storage):
        """Test quota check when over limit."""
        mock_session = mock_storage._mock_session
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 15  # Over limit
        mock_session.query.return_value = mock_query

        with pytest.raises(QuotaExceededError) as exc_info:
            usage_service.check_quota_available("user-123", "free")

        assert exc_info.value.current == 15
        assert exc_info.value.limit == 10

    def test_get_user_usage_stats(self, usage_service, mock_storage, free_tier_user):
        """Test getting user usage statistics."""
        mock_session = mock_storage._mock_session
        mock_session.get.return_value = free_tier_user

        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        # Mock two separate query calls (questions and answers)
        mock_query.count.side_effect = [5, 3]  # 5 questions, 3 answers
        mock_query.order_by.return_value = mock_query
        mock_query.first.return_value = None  # No oldest event when under limit
        mock_session.query.return_value = mock_query

        stats = usage_service.get_user_usage_stats("user-123")

        assert stats["questions_generated"] == 5
        assert stats["answers_submitted"] == 3
        assert stats["quota_limit"] == 10
        assert stats["quota_remaining"] == 5
        assert stats["window_days"] == 30
        assert stats["next_quota_available_at"] is None  # Not at limit

    def test_get_user_usage_stats_at_limit_with_reset_date(self, usage_service, mock_storage, free_tier_user):
        """Test getting user stats when at quota limit includes next_quota_available_at."""
        mock_session = mock_storage._mock_session
        mock_session.get.return_value = free_tier_user

        # Create mock for oldest event timestamp
        oldest_event_time = datetime.now(UTC) - timedelta(days=25)
        expected_reset = oldest_event_time + timedelta(days=30)

        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        # Mock three query calls: questions count, answers count, oldest event
        mock_query.count.side_effect = [10, 8]  # 10 questions (at limit), 8 answers
        mock_query.order_by.return_value = mock_query
        mock_query.first.return_value = (oldest_event_time,)  # Return oldest event
        mock_session.query.return_value = mock_query

        stats = usage_service.get_user_usage_stats("user-123")

        assert stats["questions_generated"] == 10
        assert stats["answers_submitted"] == 8
        assert stats["quota_limit"] == 10
        assert stats["quota_remaining"] == 0
        assert stats["window_days"] == 30
        assert stats["next_quota_available_at"] is not None
        assert stats["next_quota_available_at"] == expected_reset

    def test_pro_tier_has_high_quota(self, usage_service, mock_storage):
        """Test that pro tier has effectively unlimited quota."""
        mock_session = mock_storage._mock_session
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 100  # Many questions
        mock_session.query.return_value = mock_query

        # Pro users should not hit quota
        usage_service.check_quota_available("user-456", "pro")

    def test_user_not_found_raises_404(self, usage_service, mock_storage):
        """Test that missing user raises UserNotFoundError."""
        mock_session = mock_storage._mock_session
        mock_session.get.return_value = None

        with pytest.raises(UserNotFoundError) as exc_info:
            usage_service.get_user_usage_stats("nonexistent-user")

        assert exc_info.value.user_id == "nonexistent-user"

    def test_record_question_empty_user_id_raises_error(self, usage_service):
        """Test that empty user_id raises ValueError."""
        with pytest.raises(ValueError, match="user_id cannot be empty"):
            usage_service.record_question_generated("", "question-123")

        with pytest.raises(ValueError, match="user_id cannot be empty"):
            usage_service.record_question_generated("   ", "question-123")

    def test_record_question_empty_question_id_raises_error(self, usage_service):
        """Test that empty question_id raises ValueError."""
        with pytest.raises(ValueError, match="entity_id cannot be empty"):
            usage_service.record_question_generated("user-123", "")

        with pytest.raises(ValueError, match="entity_id cannot be empty"):
            usage_service.record_question_generated("user-123", "   ")

    def test_record_questions_batch_empty_user_id_raises_error(self, usage_service):
        """Test that empty user_id in batch raises ValueError."""
        with pytest.raises(ValueError, match="user_id cannot be empty"):
            usage_service.record_questions_batch("", ["q1", "q2"])

    def test_record_questions_batch_empty_question_id_raises_error(self, usage_service):
        """Test that empty question_id in batch raises ValueError."""
        with pytest.raises(ValueError, match="entity_id cannot be empty"):
            usage_service.record_questions_batch("user-123", ["q1", "", "q3"])

    def test_record_answer_empty_user_id_raises_error(self, usage_service):
        """Test that empty user_id in answer submission raises ValueError."""
        with pytest.raises(ValueError, match="user_id cannot be empty"):
            usage_service.record_answer_submitted("", "answer-123")

    def test_record_answer_empty_answer_id_raises_error(self, usage_service):
        """Test that empty answer_id raises ValueError."""
        with pytest.raises(ValueError, match="entity_id cannot be empty"):
            usage_service.record_answer_submitted("user-123", "")

    def test_count_questions_empty_user_id_raises_error(self, usage_service):
        """Test that empty user_id in count raises ValueError."""
        with pytest.raises(ValueError, match="user_id cannot be empty"):
            usage_service.count_questions_in_window("")

    def test_count_questions_negative_days_raises_error(self, usage_service):
        """Test that negative days raises ValueError."""
        with pytest.raises(ValueError, match="days must be positive"):
            usage_service.count_questions_in_window("user-123", days=-1)

        with pytest.raises(ValueError, match="days must be positive"):
            usage_service.count_questions_in_window("user-123", days=0)

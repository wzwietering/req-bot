import json
import logging
import os
import tempfile
import time
from contextlib import contextmanager
from io import StringIO
from unittest.mock import patch

import pytest

from requirements_bot.core.logging import (
    ContextFilter,
    JsonFormatter,
    _coerce_level,
    get_run_id,
    get_trace_id,
    init_logging,
    is_masking,
    log_event,
    mask_text,
    set_masking,
    set_run_id,
    set_trace_id,
    short_uuid,
    span,
)

# Test constants
SMALL_DELAY = 0.01
TEST_USER_ID = 123
TEST_TRACE_ID = "trace-123"
TEST_RUN_ID = "run-456"
TEST_SPAN_ID = "span-789"
SENSITIVE_TEXT = "password123"
TEST_LOG_LINENO = 42


@contextmanager
def clean_logging_context():
    """Reset logging context between tests."""
    # Clear all context variables
    set_trace_id(None)
    set_run_id("")
    set_masking(False)

    # Clear existing handlers
    root_logger = logging.getLogger()
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    yield

    # Clean up after test
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)


@pytest.fixture
def json_logger_output():
    """Fixture that captures and parses JSON logger output."""
    with clean_logging_context():
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            logger = init_logging(fmt="json")
            yield logger, mock_stdout


def parse_log_output(mock_stdout, line_index=0):
    """Helper to parse JSON log output."""
    lines = [line for line in mock_stdout.getvalue().strip().split("\n") if line]
    if line_index >= len(lines):
        raise IndexError(
            f"Requested line {line_index} but only {len(lines)} lines available"
        )
    return json.loads(lines[line_index])


def get_all_log_outputs(mock_stdout):
    """Helper to parse all JSON log outputs."""
    lines = [line for line in mock_stdout.getvalue().strip().split("\n") if line]
    return [json.loads(line) for line in lines]


class TestContextVariableManagement:
    """Test context variable getter/setter functions."""

    def test_trace_id_management(self):
        with clean_logging_context():
            # Initially None
            assert get_trace_id() is None

            # Can set and get trace ID
            set_trace_id(TEST_TRACE_ID)
            assert get_trace_id() == TEST_TRACE_ID

            # Can clear trace ID
            set_trace_id(None)
            assert get_trace_id() is None

    def test_run_id_management(self):
        with clean_logging_context():
            # Initially None or empty string after context cleanup
            initial_run_id = get_run_id()
            assert initial_run_id is None or initial_run_id == ""

            # Can set and get run ID
            set_run_id(TEST_RUN_ID)
            assert get_run_id() == TEST_RUN_ID

    def test_masking_management(self):
        with clean_logging_context():
            # Initially False
            assert is_masking() is False

            # Can enable masking
            set_masking(True)
            assert is_masking() is True

            # Can disable masking
            set_masking(False)
            assert is_masking() is False


class TestPrivacyMasking:
    """Test privacy masking functionality."""

    def test_mask_text_when_masking_disabled(self):
        with clean_logging_context():
            set_masking(False)

            text = "sensitive information"
            result = mask_text(text)

            assert result == text  # Returns original when masking disabled

    def test_mask_text_when_masking_enabled(self):
        with clean_logging_context():
            set_masking(True)

            text = "sensitive information"
            result = mask_text(text)

            assert result == f"[masked len={len(text)}]"
            assert "sensitive" not in result

    def test_mask_text_with_empty_string(self):
        with clean_logging_context():
            set_masking(True)

            result = mask_text("")

            assert result == "[masked len=0]"


class TestUtilityFunctions:
    """Test utility functions."""

    def test_short_uuid_format(self):
        uuid_str = short_uuid()

        assert len(uuid_str) == 12
        assert all(c in "0123456789abcdef" for c in uuid_str)

    def test_short_uuid_uniqueness(self):
        uuid1 = short_uuid()
        uuid2 = short_uuid()

        assert uuid1 != uuid2

    def test_coerce_level_with_int(self):
        assert _coerce_level(20) == 20
        assert _coerce_level(logging.DEBUG) == logging.DEBUG

    def test_coerce_level_with_string(self):
        assert _coerce_level("DEBUG") == logging.DEBUG
        assert _coerce_level("info") == logging.INFO
        assert _coerce_level("WARNING") == logging.WARNING
        assert _coerce_level("error") == logging.ERROR

    def test_coerce_level_with_invalid_input(self):
        assert _coerce_level("invalid") == logging.INFO
        assert _coerce_level(None) == logging.INFO
        assert _coerce_level("") == logging.INFO


class TestContextFilter:
    """Test ContextFilter class behavior."""

    def test_filter_adds_context_variables(self):
        with clean_logging_context():
            set_trace_id("trace-123")
            set_run_id("run-456")

            filter_instance = ContextFilter()
            record = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="",
                lineno=0,
                msg="test message",
                args=(),
                exc_info=None,
            )

            result = filter_instance.filter(record)

            assert result is True
            assert record.trace_id == "trace-123"
            assert record.run_id == "run-456"
            assert record.span_id is None
            assert record.parent_span_id is None

    def test_filter_preserves_existing_attributes(self):
        with clean_logging_context():
            filter_instance = ContextFilter()
            record = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="",
                lineno=0,
                msg="test message",
                args=(),
                exc_info=None,
            )
            record.component = "test_component"
            record.operation = "test_operation"

            filter_instance.filter(record)

            assert record.component == "test_component"
            assert record.operation == "test_operation"


class TestJsonFormatter:
    """Test JsonFormatter class behavior."""

    def test_json_formatter_includes_required_fields(self):
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="test message",
            args=(),
            exc_info=None,
        )
        record.created = time.time()

        result = formatter.format(record)
        parsed = json.loads(result)

        assert parsed["level"] == "info"
        assert parsed["message"] == "test message"
        assert "timestamp" in parsed
        assert parsed["timestamp"].endswith("Z")

    def test_json_formatting_with_correlation_fields(self):
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="test message",
            args=(),
            exc_info=None,
        )
        record.created = time.time()
        record.trace_id = "trace-123"
        record.span_id = "span-456"
        record.event = "test.event"

        result = formatter.format(record)
        parsed = json.loads(result)

        assert parsed["trace_id"] == "trace-123"
        assert parsed["span_id"] == "span-456"
        assert parsed["event"] == "test.event"

    def test_json_formatting_with_custom_extras(self):
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="test message",
            args=(),
            exc_info=None,
        )
        record.created = time.time()
        record.custom_field = "custom_value"
        record.user_id = TEST_USER_ID

        result = formatter.format(record)
        parsed = json.loads(result)

        assert parsed["custom_field"] == "custom_value"
        assert parsed["user_id"] == TEST_USER_ID

    def test_json_formatting_excludes_builtin_fields(self):
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="/path/file.py",
            lineno=42,
            msg="test message",
            args=(),
            exc_info=None,
        )
        record.created = time.time()

        result = formatter.format(record)
        parsed = json.loads(result)

        # Should not include these built-in fields
        assert "pathname" not in parsed
        assert "lineno" not in parsed
        assert "filename" not in parsed
        assert "funcName" not in parsed


class TestInitLogging:
    """Test init_logging function."""

    def test_init_logging_with_defaults(self):
        with clean_logging_context():
            logger = init_logging()

            assert logger.name == "requirements_bot"
            assert get_run_id() is not None
            assert len(get_run_id()) == 12

    def test_init_logging_with_explicit_level(self):
        with clean_logging_context():
            init_logging(level=logging.DEBUG)

            root_logger = logging.getLogger()
            assert root_logger.level == logging.DEBUG

    def test_init_logging_with_string_level(self):
        with clean_logging_context():
            init_logging(level="WARNING")

            root_logger = logging.getLogger()
            assert root_logger.level == logging.WARNING

    def test_init_logging_with_json_format(self):
        with clean_logging_context():
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                logger = init_logging(fmt="json")
                logger.info("test message", extra={"event": "test"})

                output = mock_stdout.getvalue()
                parsed = json.loads(output.strip())
                assert parsed["message"] == "test message"
                assert parsed["level"] == "info"

    def test_init_logging_with_file_output(self):
        with clean_logging_context():
            with tempfile.NamedTemporaryFile(mode="w", delete=False) as tmp_file:
                tmp_path = tmp_file.name

            try:
                logger = init_logging(file_path=tmp_path, fmt="json")
                logger.info("file test", extra={"event": "file.test"})

                with open(tmp_path, "r") as f:
                    content = f.read().strip()
                    parsed = json.loads(content)
                    assert parsed["message"] == "file test"
                    assert parsed["event"] == "file.test"
            finally:
                os.unlink(tmp_path)

    def test_init_logging_with_environment_variables(self):
        with clean_logging_context():
            env_vars = {
                "REQBOT_LOG_LEVEL": "DEBUG",
                "REQBOT_LOG_FORMAT": "json",
                "REQBOT_LOG_MASK": "true",
            }

            with patch.dict(os.environ, env_vars):
                init_logging()

                root_logger = logging.getLogger()
                assert root_logger.level == logging.DEBUG
                assert is_masking() is True

    def test_init_logging_removes_existing_handlers(self):
        with clean_logging_context():
            # Add a handler first
            root_logger = logging.getLogger()
            initial_handler = logging.StreamHandler()
            root_logger.addHandler(initial_handler)

            assert len(root_logger.handlers) == 1

            # Init logging should remove it
            init_logging()

            # Should have only the new handler
            assert len(root_logger.handlers) == 1
            assert root_logger.handlers[0] != initial_handler


class TestSpanFunctionality:
    """Test span context manager."""

    def test_span_logs_success_with_duration(self):
        with clean_logging_context():
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                init_logging(fmt="json")

                with span("test.operation", component="test", operation="basic"):
                    time.sleep(SMALL_DELAY)  # Ensure measurable duration

                output = mock_stdout.getvalue().strip()
                parsed = json.loads(output)

                assert parsed["event"] == "test.operation"
                assert parsed["component"] == "test"
                assert parsed["operation"] == "basic"
                assert parsed["status"] == "ok"
                assert "duration_ms" in parsed
                assert parsed["duration_ms"] > 0

    def test_span_with_exception(self):
        with clean_logging_context():
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                init_logging(fmt="json")

                with pytest.raises(ValueError):
                    with span("test.error", component="test"):
                        raise ValueError("test error")

                output = mock_stdout.getvalue().strip()
                parsed = json.loads(output)

                assert parsed["status"] == "error"
                assert parsed["error_type"] == "ValueError"
                assert parsed["error_msg"] == "test error"

    def test_span_creates_hierarchical_logs(self):
        with clean_logging_context():
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                init_logging(fmt="json")
                set_trace_id(TEST_TRACE_ID)

                with span("outer.operation", component="outer"):
                    with span("inner.operation", component="inner"):
                        pass  # Inner span completes first

                all_logs = get_all_log_outputs(mock_stdout)

                # Should have inner span log, outer span log, plus init log
                span_logs = [log for log in all_logs if "duration_ms" in log]
                assert len(span_logs) == 2

                inner_log, outer_log = span_logs
                assert inner_log["event"] == "inner.operation"
                assert outer_log["event"] == "outer.operation"
                assert inner_log["trace_id"] == TEST_TRACE_ID
                assert outer_log["trace_id"] == TEST_TRACE_ID


class TestLogEvent:
    """Test log_event function."""

    def test_log_event_basic(self):
        with clean_logging_context():
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                init_logging(fmt="json")

                log_event("user.login", user_id=TEST_USER_ID, method="oauth")

                output = mock_stdout.getvalue().strip()
                parsed = json.loads(output)

                assert parsed["event"] == "user.login"
                assert parsed["message"] == "user.login"
                assert parsed["user_id"] == TEST_USER_ID
                assert parsed["method"] == "oauth"

    def test_log_event_with_custom_level(self):
        with clean_logging_context():
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                init_logging(fmt="json", level=logging.DEBUG)

                log_event("debug.info", level=logging.DEBUG, details="debug info")

                output_lines = [
                    line for line in mock_stdout.getvalue().strip().split("\n") if line
                ]
                # Get the last line (the debug event, not the init log)
                debug_output = output_lines[-1]
                parsed = json.loads(debug_output)

                assert parsed["level"] == "debug"
                assert parsed["details"] == "debug info"


class TestIntegrationScenarios:
    """Test integration between different logging components."""

    def test_trace_correlation_across_operations(self):
        """Test that trace IDs flow correctly across different operations."""
        with clean_logging_context():
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                init_logging(fmt="json")
                integration_trace_id = "integration-trace"
                set_trace_id(integration_trace_id)

                log_event("workflow.start", step="initialization")

                all_logs = get_all_log_outputs(mock_stdout)
                event_logs = [
                    log for log in all_logs if log.get("event") == "workflow.start"
                ]

                assert len(event_logs) == 1
                assert event_logs[0]["trace_id"] == integration_trace_id

    def test_masking_integration_with_logging(self):
        """Test that privacy masking works correctly within logging context."""
        with clean_logging_context():
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                init_logging(fmt="json", mask=True)

                masked_value = mask_text(SENSITIVE_TEXT)
                log_event("data.masked", masked_value=masked_value)

                all_logs = get_all_log_outputs(mock_stdout)
                mask_logs = [
                    log for log in all_logs if log.get("event") == "data.masked"
                ]

                assert len(mask_logs) == 1
                expected_length = len(SENSITIVE_TEXT)
                assert mask_logs[0]["masked_value"] == f"[masked len={expected_length}]"

    def test_span_timing_with_correlation(self):
        """Test that spans properly track timing and maintain correlation."""
        with clean_logging_context():
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                init_logging(fmt="json")
                set_trace_id("timing-trace")

                with span("data.process", component="processor", operation="transform"):
                    time.sleep(SMALL_DELAY)  # Ensure measurable duration

                all_logs = get_all_log_outputs(mock_stdout)
                span_logs = [log for log in all_logs if "duration_ms" in log]

                assert len(span_logs) == 1
                span_log = span_logs[0]
                assert span_log["event"] == "data.process"
                assert span_log["status"] == "ok"
                assert span_log["duration_ms"] > 0
                assert span_log["trace_id"] == "timing-trace"


class TestEdgeCasesAndErrorScenarios:
    """Test edge cases and error scenarios identified in code review."""

    def test_span_with_nested_exceptions(self):
        """Test span behavior when nested spans have exceptions."""
        with clean_logging_context():
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                init_logging(fmt="json")

                with pytest.raises(RuntimeError):
                    with span("outer.operation", component="outer"):
                        with pytest.raises(ValueError):
                            with span("inner.operation", component="inner"):
                                raise ValueError("inner error")
                        raise RuntimeError("outer error")

                all_logs = get_all_log_outputs(mock_stdout)
                span_logs = [log for log in all_logs if "duration_ms" in log]

                assert len(span_logs) == 2
                inner_log, outer_log = span_logs

                # Both spans should show error status
                assert inner_log["status"] == "error"
                assert inner_log["error_type"] == "ValueError"
                assert outer_log["status"] == "error"
                assert outer_log["error_type"] == "RuntimeError"

    def test_json_formatter_with_none_values(self):
        """Test JSON formatter handles None values gracefully."""
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="test message",
            args=(),
            exc_info=None,
        )
        record.created = time.time()
        record.trace_id = None
        record.custom_field = None

        result = formatter.format(record)
        parsed = json.loads(result)

        # The formatter includes None values as null in JSON
        assert parsed["trace_id"] is None
        assert parsed["custom_field"] is None
        assert parsed["message"] == "test message"

    def test_init_logging_with_invalid_file_permissions(self):
        """Test init_logging handles file permission scenarios."""
        with clean_logging_context():
            # Test with a directory path (should fail gracefully)
            with tempfile.TemporaryDirectory() as temp_dir:
                with pytest.raises(IsADirectoryError):
                    init_logging(file_path=temp_dir)

    def test_coerce_level_with_edge_cases(self):
        """Test level coercion with various edge case inputs."""
        assert _coerce_level(0) == 0  # NOTSET level
        assert _coerce_level(-1) == -1  # Negative level
        assert _coerce_level("NOTSET") == logging.NOTSET
        assert _coerce_level("critical") == logging.CRITICAL
        assert _coerce_level("FATAL") == logging.FATAL

    def test_short_uuid_hex_characters_only(self):
        """Test that short_uuid only contains valid hexadecimal characters."""
        for _ in range(10):  # Test multiple generations
            uuid_str = short_uuid()
            assert len(uuid_str) == 12
            # Should only contain lowercase hex characters
            assert all(c in "0123456789abcdef" for c in uuid_str)
            # Should not be all zeros (extremely unlikely)
            assert uuid_str != "000000000000"

    def test_context_filter_with_missing_attributes(self):
        """Test ContextFilter when record lacks expected attributes."""
        with clean_logging_context():
            filter_instance = ContextFilter()
            record = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="",
                lineno=0,
                msg="test message",
                args=(),
                exc_info=None,
            )
            # Don't set component or operation attributes

            result = filter_instance.filter(record)

            assert result is True
            assert record.component is None
            assert record.operation is None
            assert hasattr(record, "trace_id")  # Should be added by filter

    def test_mask_text_with_unicode_characters(self):
        """Test masking with unicode and special characters."""
        with clean_logging_context():
            set_masking(True)

            unicode_text = "🔐 secret данные 密码"
            result = mask_text(unicode_text)

            expected_length = len(unicode_text)
            assert result == f"[masked len={expected_length}]"
            assert "🔐" not in result
            assert "secret" not in result

    def test_span_with_zero_duration(self):
        """Test span behavior with very fast operations."""
        with clean_logging_context():
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                init_logging(fmt="json")

                with span("fast.operation", component="test"):
                    pass  # Immediate completion

                all_logs = get_all_log_outputs(mock_stdout)
                span_logs = [log for log in all_logs if "duration_ms" in log]

                assert len(span_logs) == 1
                span_log = span_logs[0]
                assert span_log["status"] == "ok"
                # Duration should be >= 0, even for very fast operations
                assert span_log["duration_ms"] >= 0

"""
Comprehensive tests for enhanced error handling system

Tests the improved error handling, logging, and monitoring capabilities.
"""

import unittest
import tempfile
import json
import os
import time
import sys
from unittest.mock import patch, MagicMock

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.error_handling import (
    ErrorCategory, LogLevel, ErrorInfo, PerformanceMetrics, EnhancedLogger,
    create_error, log_and_raise, handle_errors, monitor_performance,
    validate_input, is_positive_number, is_valid_image_dimensions,
    is_non_empty_string, CommonErrors, create_debug_report
)


class TestErrorInfo(unittest.TestCase):
    """Test ErrorInfo dataclass."""

    def test_error_info_creation(self):
        """Test creating ErrorInfo instance."""
        error = ErrorInfo(
            category=ErrorCategory.VALIDATION,
            message="Test error",
            user_message="User-friendly message",
            technical_details={"param": "value"},
            suggestions=["Try this", "Or that"]
        )
        
        self.assertEqual(error.category, ErrorCategory.VALIDATION)
        self.assertEqual(error.message, "Test error")
        self.assertEqual(error.user_message, "User-friendly message")
        self.assertEqual(error.technical_details["param"], "value")
        self.assertEqual(len(error.suggestions), 2)
        self.assertIsNotNone(error.timestamp)


class TestEnhancedLogger(unittest.TestCase):
    """Test enhanced logging system."""

    def setUp(self):
        """Set up test logger."""
        self.logger = EnhancedLogger("test_logger")

    def test_logger_initialization(self):
        """Test logger initialization."""
        self.assertIsNotNone(self.logger.logger)
        self.assertEqual(len(self.logger.performance_metrics), 0)
        self.assertEqual(len(self.logger.error_history), 0)

    def test_error_logging(self):
        """Test error logging functionality."""
        error_info = ErrorInfo(
            category=ErrorCategory.VALIDATION,
            message="Test validation error",
            user_message="Invalid input"
        )
        
        self.logger.log_error(error_info)
        
        self.assertEqual(len(self.logger.error_history), 1)
        self.assertEqual(self.logger.error_history[0].message, "Test validation error")

    def test_performance_logging(self):
        """Test performance metrics logging."""
        metrics = PerformanceMetrics(
            operation="test_operation",
            start_time=time.time(),
            end_time=time.time() + 1.0,
            duration=1.0
        )
        
        self.logger.log_performance(metrics)
        
        self.assertEqual(len(self.logger.performance_metrics), 1)
        self.assertEqual(self.logger.performance_metrics[0].operation, "test_operation")

    def test_error_summary(self):
        """Test error summary generation."""
        # Add some test errors
        for i in range(5):
            error_info = ErrorInfo(
                category=ErrorCategory.VALIDATION,
                message=f"Test error {i}",
                user_message="Test user message"
            )
            self.logger.log_error(error_info)
        
        summary = self.logger.get_error_summary()
        
        self.assertEqual(summary['total_errors'], 5)
        self.assertEqual(summary['recent_errors'], 5)
        self.assertIn('validation', summary['category_breakdown'])
        self.assertEqual(summary['category_breakdown']['validation'], 5)

    def test_performance_summary(self):
        """Test performance summary generation."""
        # Add some test metrics
        for i in range(3):
            metrics = PerformanceMetrics(
                operation="test_op",
                start_time=time.time(),
                duration=1.0 + i * 0.1
            )
            self.logger.log_performance(metrics)
        
        summary = self.logger.get_performance_summary()
        
        self.assertEqual(summary['total_operations'], 3)
        self.assertIn('test_op', summary['operation_stats'])
        self.assertEqual(summary['operation_stats']['test_op']['count'], 3)


class TestErrorCreation(unittest.TestCase):
    """Test error creation functions."""

    def test_create_error(self):
        """Test create_error function."""
        error = create_error(
            ErrorCategory.PROCESSING,
            "Processing failed",
            "An error occurred during processing",
            technical_details={"step": "validation"},
            suggestions=["Check input"],
            error_code="PROC001"
        )
        
        self.assertEqual(error.category, ErrorCategory.PROCESSING)
        self.assertEqual(error.message, "Processing failed")
        self.assertEqual(error.user_message, "An error occurred during processing")
        self.assertEqual(error.technical_details["step"], "validation")
        self.assertEqual(error.suggestions[0], "Check input")
        self.assertEqual(error.error_code, "PROC001")

    def test_log_and_raise(self):
        """Test log_and_raise function."""
        with self.assertRaises(ValueError) as context:
            log_and_raise(
                ValueError,
                ErrorCategory.VALIDATION,
                "Invalid parameter",
                "The parameter is invalid"
            )
        
        self.assertEqual(str(context.exception), "The parameter is invalid")


class TestDecorators(unittest.TestCase):
    """Test error handling decorators."""

    def test_handle_errors_decorator_success(self):
        """Test handle_errors decorator with successful function."""
        @handle_errors(ErrorCategory.PROCESSING, "Test error", reraise=False)
        def successful_function(x):
            return x * 2
        
        result = successful_function(5)
        self.assertEqual(result, 10)

    def test_handle_errors_decorator_failure(self):
        """Test handle_errors decorator with failing function."""
        @handle_errors(ErrorCategory.PROCESSING, "Test error", reraise=False)
        def failing_function():
            raise ValueError("Test exception")
        
        result = failing_function()
        self.assertIsNone(result)  # Should return None when reraise=False

    def test_monitor_performance_decorator(self):
        """Test monitor_performance decorator."""
        @monitor_performance("test_operation")
        def timed_function():
            time.sleep(0.01)  # Small delay
            return "result"
        
        result = timed_function()
        self.assertEqual(result, "result")

    def test_validate_input_decorator_success(self):
        """Test validate_input decorator with valid input."""
        @validate_input({
            'x': is_positive_number,
            'name': is_non_empty_string
        })
        def validated_function(x, name):
            return f"{name}: {x}"
        
        result = validated_function(5, "test")
        self.assertEqual(result, "test: 5")

    def test_validate_input_decorator_failure(self):
        """Test validate_input decorator with invalid input."""
        @validate_input({
            'x': is_positive_number
        })
        def validated_function(x):
            return x
        
        with self.assertRaises(ValueError):
            validated_function(-5)


class TestValidationFunctions(unittest.TestCase):
    """Test validation helper functions."""

    def test_is_positive_number(self):
        """Test positive number validation."""
        self.assertTrue(is_positive_number(5))
        self.assertTrue(is_positive_number(3.14))
        self.assertFalse(is_positive_number(-1))
        self.assertFalse(is_positive_number(0))
        self.assertFalse(is_positive_number("not a number"))

    def test_is_valid_image_dimensions(self):
        """Test image dimension validation."""
        self.assertTrue(is_valid_image_dimensions(512))
        self.assertTrue(is_valid_image_dimensions(1024))
        self.assertFalse(is_valid_image_dimensions(0))
        self.assertFalse(is_valid_image_dimensions(-100))
        self.assertFalse(is_valid_image_dimensions(10000))
        self.assertFalse(is_valid_image_dimensions("not a number"))

    def test_is_non_empty_string(self):
        """Test non-empty string validation."""
        self.assertTrue(is_non_empty_string("valid string"))
        self.assertTrue(is_non_empty_string("a"))
        self.assertFalse(is_non_empty_string(""))
        self.assertFalse(is_non_empty_string("   "))
        self.assertFalse(is_non_empty_string(123))
        self.assertFalse(is_non_empty_string(None))


class TestCommonErrors(unittest.TestCase):
    """Test common error patterns."""

    def test_invalid_image_format_error(self):
        """Test invalid image format error."""
        error = CommonErrors.invalid_image_format("unsupported format")
        
        self.assertEqual(error.category, ErrorCategory.VALIDATION)
        self.assertIn("unsupported format", error.message)
        self.assertIn("PNG, JPG", error.user_message)
        self.assertTrue(len(error.suggestions) > 0)

    def test_insufficient_memory_error(self):
        """Test insufficient memory error."""
        error = CommonErrors.insufficient_memory("image processing")
        
        self.assertEqual(error.category, ErrorCategory.MEMORY)
        self.assertIn("image processing", error.message)
        self.assertIn("memory", error.user_message)
        self.assertIn("Close other applications", error.suggestions[0])

    def test_model_loading_failed_error(self):
        """Test model loading failed error."""
        error = CommonErrors.model_loading_failed("test_model")
        
        self.assertEqual(error.category, ErrorCategory.MODEL_LOADING)
        self.assertIn("test_model", error.message)
        self.assertIn("model could not be loaded", error.user_message)
        self.assertTrue(any("internet connection" in s for s in error.suggestions))

    def test_gpu_not_available_error(self):
        """Test GPU not available error."""
        error = CommonErrors.gpu_not_available()
        
        self.assertEqual(error.category, ErrorCategory.GPU)
        self.assertIn("GPU", error.message)
        self.assertIn("CPU processing", error.user_message)
        self.assertTrue(any("GPU drivers" in s for s in error.suggestions))


class TestDebugReport(unittest.TestCase):
    """Test debug report generation."""

    @patch('modules.error_handling.get_system_info')
    def test_create_debug_report(self, mock_system_info):
        """Test debug report creation."""
        mock_system_info.return_value = {
            'platform': 'test_platform',
            'python_version': '3.8.0'
        }
        
        report = create_debug_report()
        
        self.assertIn('timestamp', report)
        self.assertIn('system_info', report)
        self.assertIn('error_summary', report)
        self.assertIn('performance_summary', report)
        self.assertEqual(report['system_info']['platform'], 'test_platform')


class TestErrorCategories(unittest.TestCase):
    """Test error category enumeration."""

    def test_error_categories_exist(self):
        """Test that all expected error categories exist."""
        expected_categories = [
            'AUTHENTICATION', 'VALIDATION', 'PROCESSING', 'NETWORK',
            'FILE_IO', 'MEMORY', 'GPU', 'MODEL_LOADING', 
            'IMAGE_GENERATION', 'CONFIGURATION', 'UNKNOWN'
        ]
        
        for category_name in expected_categories:
            self.assertTrue(hasattr(ErrorCategory, category_name))

    def test_error_category_values(self):
        """Test error category string values."""
        self.assertEqual(ErrorCategory.AUTHENTICATION.value, "authentication")
        self.assertEqual(ErrorCategory.VALIDATION.value, "validation")
        self.assertEqual(ErrorCategory.GPU.value, "gpu")


if __name__ == '__main__':
    unittest.main()
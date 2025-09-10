"""
Enhanced Error Handling and Logging System for Fooorkus

Provides comprehensive error handling, logging, and monitoring capabilities:
- Structured logging with different levels
- Error categorization and reporting
- Performance monitoring
- User-friendly error messages
- Debug information collection
"""

import logging
import traceback
import time
import functools
from typing import Dict, Any, Optional, Callable, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
import os
from datetime import datetime
import sys


class ErrorCategory(Enum):
    """Categories for different types of errors."""
    AUTHENTICATION = "authentication"
    VALIDATION = "validation"
    PROCESSING = "processing"
    NETWORK = "network"
    FILE_IO = "file_io"
    MEMORY = "memory"
    GPU = "gpu"
    MODEL_LOADING = "model_loading"
    IMAGE_GENERATION = "image_generation"
    CONFIGURATION = "configuration"
    UNKNOWN = "unknown"


class LogLevel(Enum):
    """Enhanced log levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
    SECURITY = "SECURITY"
    PERFORMANCE = "PERFORMANCE"


@dataclass
class ErrorInfo:
    """Structured error information."""
    category: ErrorCategory
    message: str
    user_message: str
    technical_details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    traceback: Optional[str] = None
    suggestions: List[str] = field(default_factory=list)
    error_code: Optional[str] = None


@dataclass
class PerformanceMetrics:
    """Performance monitoring data."""
    operation: str
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    memory_usage: Optional[Dict[str, Any]] = None
    additional_data: Dict[str, Any] = field(default_factory=dict)


class EnhancedLogger:
    """Enhanced logging system with structured error handling."""
    
    def __init__(self, name: str = "fooorkus", log_file: Optional[str] = None):
        self.logger = logging.getLogger(name)
        self.performance_metrics: List[PerformanceMetrics] = []
        self.error_history: List[ErrorInfo] = []
        self.setup_logging(log_file)
    
    def setup_logging(self, log_file: Optional[str] = None):
        """Setup logging configuration."""
        self.logger.setLevel(logging.DEBUG)
        
        # Check if handlers already exist to avoid duplication
        if self.logger.handlers:
            return
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # File handler if specified
        if log_file:
            try:
                file_handler = logging.FileHandler(log_file)
                file_handler.setLevel(logging.DEBUG)
                file_handler.setFormatter(formatter)
                self.logger.addHandler(file_handler)
            except Exception as e:
                self.logger.warning(f"Could not setup file logging: {e}")
    
    def log_error(self, error_info: ErrorInfo):
        """Log structured error information."""
        self.error_history.append(error_info)
        
        # Create log message
        log_msg = f"[{error_info.category.value.upper()}] {error_info.message}"
        if error_info.technical_details:
            log_msg += f" | Details: {json.dumps(error_info.technical_details, default=str)}"
        
        # Log with appropriate level
        self.logger.error(log_msg)
        
        # Log traceback if available
        if error_info.traceback:
            self.logger.debug(f"Traceback: {error_info.traceback}")
    
    def log_performance(self, metrics: PerformanceMetrics):
        """Log performance metrics."""
        self.performance_metrics.append(metrics)
        
        if metrics.duration is not None:
            self.logger.info(f"PERFORMANCE: {metrics.operation} took {metrics.duration:.3f}s")
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of recent errors."""
        category_counts = {}
        for error in self.error_history[-100:]:  # Last 100 errors
            category = error.category.value
            category_counts[category] = category_counts.get(category, 0) + 1
        
        return {
            'total_errors': len(self.error_history),
            'recent_errors': len(self.error_history[-100:]),
            'category_breakdown': category_counts,
            'last_error': self.error_history[-1].__dict__ if self.error_history else None
        }
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance metrics summary."""
        if not self.performance_metrics:
            return {'message': 'No performance data available'}
        
        recent_metrics = self.performance_metrics[-50:]  # Last 50 operations
        
        # Calculate averages by operation
        operation_stats = {}
        for metric in recent_metrics:
            if metric.duration is not None:
                op = metric.operation
                if op not in operation_stats:
                    operation_stats[op] = {'durations': [], 'count': 0}
                operation_stats[op]['durations'].append(metric.duration)
                operation_stats[op]['count'] += 1
        
        # Calculate averages
        for op, stats in operation_stats.items():
            durations = stats['durations']
            stats['avg_duration'] = sum(durations) / len(durations)
            stats['min_duration'] = min(durations)
            stats['max_duration'] = max(durations)
            del stats['durations']  # Remove raw data for cleaner output
        
        return {
            'total_operations': len(self.performance_metrics),
            'recent_operations': len(recent_metrics),
            'operation_stats': operation_stats
        }


# Global logger instance
enhanced_logger = EnhancedLogger()


def create_error(
    category: ErrorCategory,
    message: str,
    user_message: str,
    technical_details: Optional[Dict[str, Any]] = None,
    suggestions: Optional[List[str]] = None,
    error_code: Optional[str] = None
) -> ErrorInfo:
    """Create structured error information."""
    return ErrorInfo(
        category=category,
        message=message,
        user_message=user_message,
        technical_details=technical_details or {},
        traceback=traceback.format_exc() if sys.exc_info()[0] else None,
        suggestions=suggestions or [],
        error_code=error_code
    )


def log_and_raise(
    exception_class: type,
    category: ErrorCategory,
    message: str,
    user_message: str,
    technical_details: Optional[Dict[str, Any]] = None,
    suggestions: Optional[List[str]] = None,
    error_code: Optional[str] = None
):
    """Log error and raise exception."""
    error_info = create_error(
        category, message, user_message, technical_details, suggestions, error_code
    )
    enhanced_logger.log_error(error_info)
    raise exception_class(user_message)


def handle_errors(
    category: ErrorCategory,
    user_message: str = "An error occurred during processing",
    suggestions: Optional[List[str]] = None,
    reraise: bool = True
):
    """Decorator for comprehensive error handling."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_info = create_error(
                    category=category,
                    message=f"Error in {func.__name__}: {str(e)}",
                    user_message=user_message,
                    technical_details={
                        'function': func.__name__,
                        'args': str(args)[:200],  # Limit size
                        'kwargs': str(kwargs)[:200],
                        'exception_type': type(e).__name__
                    },
                    suggestions=suggestions or [
                        "Check your input parameters",
                        "Ensure all dependencies are installed",
                        "Check system resources (memory, disk space)"
                    ]
                )
                enhanced_logger.log_error(error_info)
                
                if reraise:
                    raise
                else:
                    return None
        return wrapper
    return decorator


def monitor_performance(operation_name: str):
    """Decorator for performance monitoring."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            metrics = PerformanceMetrics(
                operation=f"{operation_name} ({func.__name__})",
                start_time=time.time()
            )
            
            try:
                result = func(*args, **kwargs)
                metrics.end_time = time.time()
                metrics.duration = metrics.end_time - metrics.start_time
                enhanced_logger.log_performance(metrics)
                return result
            except Exception as e:
                metrics.end_time = time.time()
                metrics.duration = metrics.end_time - metrics.start_time
                metrics.additional_data['error'] = str(e)
                enhanced_logger.log_performance(metrics)
                raise
        return wrapper
    return decorator


def validate_input(
    validation_rules: Dict[str, Callable],
    error_category: ErrorCategory = ErrorCategory.VALIDATION
):
    """Decorator for input validation with structured error handling."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Combine positional and keyword arguments
            func_args = {}
            
            # Get function signature to map positional args
            import inspect
            sig = inspect.signature(func)
            param_names = list(sig.parameters.keys())
            
            # Map positional arguments
            for i, arg in enumerate(args):
                if i < len(param_names):
                    func_args[param_names[i]] = arg
            
            # Add keyword arguments
            func_args.update(kwargs)
            
            # Validate arguments
            validation_errors = []
            for param_name, validator in validation_rules.items():
                if param_name in func_args:
                    try:
                        if not validator(func_args[param_name]):
                            validation_errors.append(f"Invalid value for {param_name}")
                    except Exception as e:
                        validation_errors.append(f"Validation error for {param_name}: {e}")
            
            if validation_errors:
                error_info = create_error(
                    category=error_category,
                    message=f"Validation failed for {func.__name__}: {', '.join(validation_errors)}",
                    user_message="Invalid input parameters provided",
                    technical_details={
                        'function': func.__name__,
                        'validation_errors': validation_errors,
                        'provided_args': {k: str(v)[:100] for k, v in func_args.items()}
                    },
                    suggestions=[
                        "Check parameter types and values",
                        "Refer to documentation for valid parameter ranges",
                        "Ensure all required parameters are provided"
                    ]
                )
                enhanced_logger.log_error(error_info)
                raise ValueError("Invalid input parameters")
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


# Common validation functions
def is_positive_number(value) -> bool:
    """Validate that value is a positive number."""
    try:
        return isinstance(value, (int, float)) and value > 0
    except:
        return False


def is_valid_image_dimensions(value) -> bool:
    """Validate image dimensions."""
    try:
        return isinstance(value, (int, float)) and 1 <= value <= 8192
    except:
        return False


def is_non_empty_string(value) -> bool:
    """Validate non-empty string."""
    return isinstance(value, str) and len(value.strip()) > 0


def get_system_info() -> Dict[str, Any]:
    """Get system information for debugging."""
    import psutil
    import platform
    
    try:
        return {
            'platform': platform.platform(),
            'python_version': platform.python_version(),
            'cpu_count': psutil.cpu_count(),
            'memory_total': psutil.virtual_memory().total,
            'memory_available': psutil.virtual_memory().available,
            'disk_usage': {
                'total': psutil.disk_usage('/').total,
                'free': psutil.disk_usage('/').free
            }
        }
    except Exception as e:
        return {'error': f"Could not collect system info: {e}"}


def create_debug_report() -> Dict[str, Any]:
    """Create comprehensive debug report."""
    return {
        'timestamp': datetime.now().isoformat(),
        'system_info': get_system_info(),
        'error_summary': enhanced_logger.get_error_summary(),
        'performance_summary': enhanced_logger.get_performance_summary(),
        'recent_errors': [
            error.__dict__ for error in enhanced_logger.error_history[-10:]
        ]
    }


# Export common error categories for convenience
class CommonErrors:
    """Common error patterns with predefined messages."""
    
    @staticmethod
    def invalid_image_format(details: str = ""):
        return create_error(
            ErrorCategory.VALIDATION,
            f"Invalid image format: {details}",
            "The provided image format is not supported. Please use PNG, JPG, or other common formats.",
            suggestions=["Convert image to PNG or JPG format", "Check file integrity"]
        )
    
    @staticmethod
    def insufficient_memory(operation: str = ""):
        return create_error(
            ErrorCategory.MEMORY,
            f"Insufficient memory for {operation}",
            "Not enough memory available to complete this operation.",
            suggestions=[
                "Close other applications to free memory",
                "Reduce image resolution or batch size",
                "Restart the application"
            ]
        )
    
    @staticmethod
    def model_loading_failed(model_name: str = ""):
        return create_error(
            ErrorCategory.MODEL_LOADING,
            f"Failed to load model: {model_name}",
            "The AI model could not be loaded. This might be due to missing files or insufficient resources.",
            suggestions=[
                "Check internet connection for model download",
                "Verify sufficient disk space",
                "Restart the application"
            ]
        )
    
    @staticmethod
    def gpu_not_available():
        return create_error(
            ErrorCategory.GPU,
            "GPU not available or compatible",
            "GPU acceleration is not available. The application will use CPU processing, which is slower.",
            suggestions=[
                "Install compatible GPU drivers",
                "Check CUDA installation",
                "Verify GPU compatibility"
            ]
        )
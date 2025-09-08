"""
Enhanced Configuration Management System for Fooorkus

Provides comprehensive configuration handling with:
- Type validation and constraints
- Environment variable support
- Configuration validation and suggestions
- Hot-reloading capabilities
- Backup and recovery
- Schema validation
"""

import json
import os
import shutil
from typing import Any, Dict, List, Optional, Union, Callable, Type
from dataclasses import dataclass, field, asdict
from pathlib import Path
from datetime import datetime
import logging
from copy import deepcopy

from modules.error_handling import (
    ErrorCategory, create_error, enhanced_logger, handle_errors
)

logger = enhanced_logger.logger


@dataclass
class ConfigField:
    """Configuration field definition with validation."""
    name: str
    default_value: Any
    field_type: Type
    description: str
    validator: Optional[Callable[[Any], bool]] = None
    constraints: Optional[Dict[str, Any]] = None
    env_var: Optional[str] = None
    required: bool = False
    sensitive: bool = False  # For passwords, API keys, etc.


@dataclass
class ConfigSection:
    """Configuration section containing related fields."""
    name: str
    description: str
    fields: List[ConfigField] = field(default_factory=list)
    required: bool = True


class ConfigurationError(Exception):
    """Custom exception for configuration errors."""
    pass


class ConfigurationManager:
    """Enhanced configuration management with validation and safety features."""
    
    def __init__(self, config_file: str = "config.json", schema_file: Optional[str] = None):
        self.config_file = Path(config_file)
        self.schema_file = Path(schema_file) if schema_file else None
        self.config_data: Dict[str, Any] = {}
        self.schema: Dict[str, ConfigSection] = {}
        self.backup_dir = Path("config_backups")
        self.change_listeners: List[Callable] = []
        
        # Ensure backup directory exists
        self.backup_dir.mkdir(exist_ok=True)
        
        # Load configuration
        self._setup_default_schema()
        self.load_configuration()
    
    def _setup_default_schema(self):
        """Setup default configuration schema."""
        # UI Configuration
        ui_section = ConfigSection(
            name="ui",
            description="User Interface Settings",
            fields=[
                ConfigField(
                    name="theme",
                    default_value="auto",
                    field_type=str,
                    description="UI theme (light, dark, auto)",
                    validator=lambda x: x in ["light", "dark", "auto"]
                ),
                ConfigField(
                    name="language",
                    default_value="default",
                    field_type=str,
                    description="UI language",
                    env_var="FOOORKUS_LANGUAGE"
                ),
                ConfigField(
                    name="enable_analytics",
                    default_value=True,
                    field_type=bool,
                    description="Enable usage analytics"
                )
            ]
        )
        
        # Performance Configuration
        performance_section = ConfigSection(
            name="performance",
            description="Performance and Resource Settings",
            fields=[
                ConfigField(
                    name="max_workers",
                    default_value=4,
                    field_type=int,
                    description="Maximum number of worker threads",
                    validator=lambda x: 1 <= x <= 16,
                    constraints={"min": 1, "max": 16}
                ),
                ConfigField(
                    name="memory_limit_gb",
                    default_value=8,
                    field_type=int,
                    description="Memory limit in GB",
                    validator=lambda x: x > 0,
                    env_var="FOOORKUS_MEMORY_LIMIT"
                ),
                ConfigField(
                    name="enable_gpu",
                    default_value=True,
                    field_type=bool,
                    description="Enable GPU acceleration if available"
                ),
                ConfigField(
                    name="cache_size_mb",
                    default_value=1024,
                    field_type=int,
                    description="Cache size in MB",
                    validator=lambda x: 100 <= x <= 10240,
                    constraints={"min": 100, "max": 10240}
                )
            ]
        )
        
        # Security Configuration
        security_section = ConfigSection(
            name="security",
            description="Security and Authentication Settings",
            fields=[
                ConfigField(
                    name="enable_auth",
                    default_value=False,
                    field_type=bool,
                    description="Enable user authentication"
                ),
                ConfigField(
                    name="session_timeout",
                    default_value=3600,
                    field_type=int,
                    description="Session timeout in seconds",
                    validator=lambda x: 300 <= x <= 86400,
                    constraints={"min": 300, "max": 86400}
                ),
                ConfigField(
                    name="max_login_attempts",
                    default_value=5,
                    field_type=int,
                    description="Maximum login attempts before lockout",
                    validator=lambda x: 1 <= x <= 20
                ),
                ConfigField(
                    name="api_key",
                    default_value="",
                    field_type=str,
                    description="API key for external services",
                    sensitive=True,
                    env_var="FOOORKUS_API_KEY"
                )
            ]
        )
        
        # Model Configuration
        model_section = ConfigSection(
            name="models",
            description="AI Model Settings",
            fields=[
                ConfigField(
                    name="default_model",
                    default_value="",
                    field_type=str,
                    description="Default AI model to use"
                ),
                ConfigField(
                    name="model_cache_dir",
                    default_value="./models",
                    field_type=str,
                    description="Directory for model storage"
                ),
                ConfigField(
                    name="auto_download",
                    default_value=True,
                    field_type=bool,
                    description="Automatically download missing models"
                ),
                ConfigField(
                    name="generation_timeout",
                    default_value=300,
                    field_type=int,
                    description="Generation timeout in seconds",
                    validator=lambda x: 30 <= x <= 1800,
                    constraints={"min": 30, "max": 1800}
                )
            ]
        )
        
        # Add sections to schema
        for section in [ui_section, performance_section, security_section, model_section]:
            self.schema[section.name] = section
    
    @handle_errors(ErrorCategory.CONFIGURATION, "Failed to load configuration")
    def load_configuration(self) -> bool:
        """Load configuration from file with validation."""
        # Load from environment variables first
        self._load_from_environment()
        
        # Load from file if exists
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    file_config = json.load(f)
                
                # Merge with environment variables
                self._merge_config(file_config)
                
                # Validate configuration
                validation_errors = self.validate_configuration()
                if validation_errors:
                    logger.warning(f"Configuration validation issues: {validation_errors}")
                
                logger.info(f"Configuration loaded from {self.config_file}")
                return True
                
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in configuration file: {e}")
                self._use_defaults()
                return False
            except Exception as e:
                logger.error(f"Error loading configuration: {e}")
                self._use_defaults()
                return False
        else:
            logger.info("No configuration file found, using defaults")
            self._use_defaults()
            return True
    
    def _load_from_environment(self):
        """Load configuration values from environment variables."""
        for section_name, section in self.schema.items():
            if section_name not in self.config_data:
                self.config_data[section_name] = {}
            
            for field in section.fields:
                if field.env_var and field.env_var in os.environ:
                    env_value = os.environ[field.env_var]
                    
                    # Convert to appropriate type
                    try:
                        if field.field_type == bool:
                            value = env_value.lower() in ('true', '1', 'yes', 'on')
                        elif field.field_type == int:
                            value = int(env_value)
                        elif field.field_type == float:
                            value = float(env_value)
                        else:
                            value = env_value
                        
                        self.config_data[section_name][field.name] = value
                        logger.debug(f"Loaded {field.name} from environment variable {field.env_var}")
                    except ValueError as e:
                        logger.warning(f"Invalid environment variable {field.env_var}: {e}")
    
    def _merge_config(self, file_config: Dict[str, Any]):
        """Merge file configuration with existing config."""
        for section_name, section_data in file_config.items():
            if section_name not in self.config_data:
                self.config_data[section_name] = {}
            
            if isinstance(section_data, dict):
                self.config_data[section_name].update(section_data)
            else:
                logger.warning(f"Invalid configuration section format: {section_name}")
    
    def _use_defaults(self):
        """Use default values for all configuration."""
        self.config_data = {}
        for section_name, section in self.schema.items():
            self.config_data[section_name] = {}
            for field in section.fields:
                self.config_data[section_name][field.name] = field.default_value
    
    @handle_errors(ErrorCategory.CONFIGURATION, "Failed to save configuration")
    def save_configuration(self, backup: bool = True) -> bool:
        """Save configuration to file with optional backup."""
        if backup and self.config_file.exists():
            self._create_backup()
        
        try:
            # Create sanitized config for saving (exclude sensitive data)
            safe_config = self._sanitize_for_save()
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(safe_config, f, indent=2, sort_keys=True)
            
            logger.info(f"Configuration saved to {self.config_file}")
            
            # Notify change listeners
            self._notify_change_listeners()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            return False
    
    def _sanitize_for_save(self) -> Dict[str, Any]:
        """Create a sanitized copy of config for saving (excludes sensitive data)."""
        safe_config = deepcopy(self.config_data)
        
        for section_name, section in self.schema.items():
            if section_name in safe_config:
                for field in section.fields:
                    if field.sensitive and field.name in safe_config[section_name]:
                        # Replace sensitive values with placeholder
                        if safe_config[section_name][field.name]:
                            safe_config[section_name][field.name] = "[REDACTED]"
        
        return safe_config
    
    def _create_backup(self):
        """Create a backup of the current configuration file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = self.backup_dir / f"config_backup_{timestamp}.json"
        
        try:
            shutil.copy2(self.config_file, backup_file)
            logger.info(f"Configuration backup created: {backup_file}")
            
            # Clean up old backups (keep last 10)
            self._cleanup_old_backups()
            
        except Exception as e:
            logger.warning(f"Failed to create configuration backup: {e}")
    
    def _cleanup_old_backups(self, keep_count: int = 10):
        """Clean up old backup files."""
        try:
            backup_files = sorted(
                self.backup_dir.glob("config_backup_*.json"),
                key=lambda x: x.stat().st_mtime,
                reverse=True
            )
            
            for old_backup in backup_files[keep_count:]:
                old_backup.unlink()
                logger.debug(f"Removed old backup: {old_backup}")
                
        except Exception as e:
            logger.warning(f"Failed to cleanup old backups: {e}")
    
    def validate_configuration(self) -> List[str]:
        """Validate current configuration against schema."""
        errors = []
        
        for section_name, section in self.schema.items():
            if section.required and section_name not in self.config_data:
                errors.append(f"Required section '{section_name}' is missing")
                continue
            
            section_data = self.config_data.get(section_name, {})
            
            for field in section.fields:
                if field.required and field.name not in section_data:
                    errors.append(f"Required field '{section_name}.{field.name}' is missing")
                    continue
                
                if field.name in section_data:
                    value = section_data[field.name]
                    
                    # Type validation
                    if not isinstance(value, field.field_type):
                        errors.append(f"Field '{section_name}.{field.name}' should be {field.field_type.__name__}, got {type(value).__name__}")
                    
                    # Custom validation
                    if field.validator and not field.validator(value):
                        constraint_info = ""
                        if field.constraints:
                            constraint_info = f" (constraints: {field.constraints})"
                        errors.append(f"Field '{section_name}.{field.name}' failed validation{constraint_info}")
        
        return errors
    
    def get(self, section: str, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return self.config_data.get(section, {}).get(key, default)
    
    def set(self, section: str, key: str, value: Any, save: bool = True) -> bool:
        """Set configuration value with validation."""
        # Find field in schema for validation
        field_def = None
        if section in self.schema:
            for field in self.schema[section].fields:
                if field.name == key:
                    field_def = field
                    break
        
        if field_def:
            # Type validation
            if not isinstance(value, field_def.field_type):
                logger.error(f"Invalid type for {section}.{key}: expected {field_def.field_type.__name__}")
                return False
            
            # Custom validation
            if field_def.validator and not field_def.validator(value):
                logger.error(f"Value validation failed for {section}.{key}")
                return False
        
        # Set value
        if section not in self.config_data:
            self.config_data[section] = {}
        
        old_value = self.config_data[section].get(key)
        self.config_data[section][key] = value
        
        logger.info(f"Configuration updated: {section}.{key} = {value}")
        
        if save:
            return self.save_configuration()
        
        return True
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """Get entire configuration section."""
        return self.config_data.get(section, {}).copy()
    
    def get_schema_info(self, section: Optional[str] = None) -> Dict[str, Any]:
        """Get schema information for configuration documentation."""
        if section:
            if section in self.schema:
                schema_section = self.schema[section]
                return {
                    'name': schema_section.name,
                    'description': schema_section.description,
                    'fields': [
                        {
                            'name': field.name,
                            'type': field.field_type.__name__,
                            'default': field.default_value,
                            'description': field.description,
                            'required': field.required,
                            'constraints': field.constraints,
                            'env_var': field.env_var
                        }
                        for field in schema_section.fields
                    ]
                }
            else:
                return {}
        else:
            return {
                section_name: self.get_schema_info(section_name)
                for section_name in self.schema.keys()
            }
    
    def add_change_listener(self, callback: Callable):
        """Add callback for configuration changes."""
        self.change_listeners.append(callback)
    
    def _notify_change_listeners(self):
        """Notify all change listeners."""
        for callback in self.change_listeners:
            try:
                callback(self.config_data)
            except Exception as e:
                logger.warning(f"Configuration change listener failed: {e}")
    
    def export_config(self, export_path: str, include_sensitive: bool = False) -> bool:
        """Export configuration to file."""
        try:
            config_to_export = self.config_data if include_sensitive else self._sanitize_for_save()
            
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(config_to_export, f, indent=2, sort_keys=True)
            
            logger.info(f"Configuration exported to {export_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export configuration: {e}")
            return False
    
    def import_config(self, import_path: str, validate: bool = True) -> bool:
        """Import configuration from file."""
        try:
            with open(import_path, 'r', encoding='utf-8') as f:
                imported_config = json.load(f)
            
            # Backup current config
            self._create_backup()
            
            # Update configuration
            self.config_data = imported_config
            
            if validate:
                validation_errors = self.validate_configuration()
                if validation_errors:
                    logger.warning(f"Imported configuration has validation issues: {validation_errors}")
            
            # Save the imported configuration
            self.save_configuration(backup=False)
            
            logger.info(f"Configuration imported from {import_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to import configuration: {e}")
            return False
    
    def reset_to_defaults(self, section: Optional[str] = None) -> bool:
        """Reset configuration to defaults."""
        if section:
            if section in self.schema:
                self.config_data[section] = {}
                for field in self.schema[section].fields:
                    self.config_data[section][field.name] = field.default_value
                logger.info(f"Section '{section}' reset to defaults")
            else:
                logger.error(f"Unknown section: {section}")
                return False
        else:
            self._use_defaults()
            logger.info("All configuration reset to defaults")
        
        return self.save_configuration()
    
    def get_configuration_summary(self) -> Dict[str, Any]:
        """Get a summary of current configuration."""
        summary = {
            'total_sections': len(self.config_data),
            'sections': {},
            'validation_status': 'valid' if not self.validate_configuration() else 'invalid',
            'last_modified': datetime.fromtimestamp(
                self.config_file.stat().st_mtime
            ).isoformat() if self.config_file.exists() else None
        }
        
        for section_name, section_data in self.config_data.items():
            summary['sections'][section_name] = {
                'field_count': len(section_data),
                'has_sensitive_data': any(
                    field.sensitive for field in self.schema.get(section_name, ConfigSection("", "")).fields
                    if field.name in section_data
                )
            }
        
        return summary


# Global configuration manager instance
config_manager = ConfigurationManager()
"""
Model configuration loader with environment support and versioning.

This module loads model constants configuration files based on the environment,
validates them against the schema, and provides version tracking.
"""

import json
import os
from pathlib import Path
from typing import Optional

from src.utils.custom_logger import log_handler
from src.models.model_config_schemas import ModelConstantsConfig


class ModelConfigLoader:
    """Loader for model constants configuration with environment support."""
    
    def __init__(self, environment: Optional[str] = None):
        """
        Initialize the configuration loader.
        
        Parameters:
            environment (str): Environment to load (dev, staging, prod). 
                            Defaults to MODEL_ENV environment variable or 'dev'.
        """
        self.environment = environment or os.getenv("MODEL_ENV", "dev")
        self._config: Optional[ModelConstantsConfig] = None
        self._config_path: Optional[Path] = None
    
    def load_config(self) -> ModelConstantsConfig:
        """
        Load and validate model configuration for the current environment.
        
        Returns:
            ModelConstantsConfig: Validated configuration object.
        
        Raises:
            FileNotFoundError: If configuration file not found.
            ValueError: If configuration validation fails.
        """
        if self._config is not None:
            return self._config
        
        # Determine config file path
        config_dir = Path(__file__).parent
        config_filename = f"model_constants_{self.environment}.json"
        config_path = config_dir / config_filename
        
        # Fallback to default if environment-specific file doesn't exist
        if not config_path.exists():
            config_path = config_dir / "model_constants.json"
            log_handler.warning(
                "Environment-specific config not found, using default: %s",
                config_path
            )
        
        if not config_path.exists():
            raise FileNotFoundError(f"Model configuration file not found: {config_path}")
        
        # Load and parse JSON
        with config_path.open() as f:
            config_data = json.load(f)
        
        # Validate against schema
        try:
            config = ModelConstantsConfig(**config_data)
        except Exception as e:
            raise ValueError(f"Configuration validation failed: {e}")
        
        self._config = config
        self._config_path = config_path
        
        log_handler.info(
            "Loaded model configuration: version=%s, type=%s, environment=%s",
            config.model_version,
            config.model_type,
            self.environment,
        )
        
        return config
    
    def get_config(self) -> ModelConstantsConfig:
        """Get the current configuration (loads if not already loaded)."""
        if self._config is None:
            return self.load_config()
        return self._config
    
    def reload_config(self) -> ModelConstantsConfig:
        """Force reload the configuration from file."""
        self._config = None
        return self.load_config()
    
    def get_version(self) -> str:
        """Get the current model version."""
        return self.get_config().model_version
    
    def get_environment(self) -> str:
        """Get the current environment."""
        return self.environment
    
    def validate_config(self, config_data: dict) -> bool:
        """
        Validate configuration data against schema.
        
        Parameters:
            config_data (dict): Configuration data to validate.
        
        Returns:
            bool: True if valid, False otherwise.
        """
        try:
            ModelConstantsConfig(**config_data)
            return True
        except Exception:
            return False
    
    def log_version_info(self):
        """Log version and environment information."""
        config = self.get_config()
        log_handler.info(
            "Model Configuration Info:\n"
            "  Version: %s\n"
            "  Type: %s\n"
            "  Environment: %s\n"
            "  Description: %s\n"
            "  Config Path: %s",
            config.model_version,
            config.model_type,
            self.environment,
            config.description,
            self._config_path,
        )


# Singleton instance
_config_loader: Optional[ModelConfigLoader] = None


def get_model_config_loader(environment: Optional[str] = None) -> ModelConfigLoader:
    """
    Get the singleton model configuration loader instance.
    
    Parameters:
        environment (str): Environment to load (dev, staging, prod).
    
    Returns:
        ModelConfigLoader: Configuration loader instance.
    """
    global _config_loader
    if _config_loader is None or (environment is not None and environment != _config_loader.get_environment()):
        _config_loader = ModelConfigLoader(environment)
    return _config_loader


def get_model_config() -> ModelConstantsConfig:
    """
    Get the current model configuration.
    
    Returns:
        ModelConstantsConfig: Current model configuration.
    """
    return get_model_config_loader().get_config()

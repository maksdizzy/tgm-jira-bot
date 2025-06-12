"""Logging configuration and utilities."""

import logging
import logging.config
import yaml
import os
from pathlib import Path
from typing import Optional


def setup_logging(
    config_path: Optional[str] = None,
    log_level: Optional[str] = None,
    logs_dir: str = "logs"
) -> None:
    """
    Setup logging configuration.
    
    Args:
        config_path: Path to logging configuration file
        log_level: Override log level
        logs_dir: Directory for log files
    """
    # Create logs directory if it doesn't exist
    Path(logs_dir).mkdir(exist_ok=True)
    
    # Default config path
    if config_path is None:
        config_path = "config/logging.yaml"
    
    # Load logging configuration
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            # Override log level if provided
            if log_level:
                config['root']['level'] = log_level.upper()
                for logger_name in config.get('loggers', {}):
                    config['loggers'][logger_name]['level'] = log_level.upper()
            
            logging.config.dictConfig(config)
        except Exception as e:
            # Fallback to basic configuration
            logging.basicConfig(
                level=getattr(logging, log_level.upper() if log_level else 'INFO'),
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                handlers=[
                    logging.StreamHandler(),
                    logging.FileHandler(f'{logs_dir}/app.log')
                ]
            )
            logging.warning(f"Failed to load logging config from {config_path}: {e}")
    else:
        # Basic configuration if no config file found
        logging.basicConfig(
            level=getattr(logging, log_level.upper() if log_level else 'INFO'),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(f'{logs_dir}/app.log')
            ]
        )
        logging.warning(f"Logging config file not found at {config_path}, using basic configuration")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


class StructuredLogger:
    """Wrapper for structured logging with context."""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self._context = {}
    
    def with_context(self, **kwargs) -> "StructuredLogger":
        """Add context to logger."""
        new_logger = StructuredLogger(self.logger)
        new_logger._context = {**self._context, **kwargs}
        return new_logger
    
    def _format_message(self, message: str) -> str:
        """Format message with context."""
        if self._context:
            context_str = " | ".join([f"{k}={v}" for k, v in self._context.items()])
            return f"{message} | {context_str}"
        return message
    
    def debug(self, message: str, **kwargs):
        """Log debug message with context."""
        self.logger.debug(self._format_message(message), extra=kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message with context."""
        self.logger.info(self._format_message(message), extra=kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message with context."""
        self.logger.warning(self._format_message(message), extra=kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message with context."""
        self.logger.error(self._format_message(message), extra=kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message with context."""
        self.logger.critical(self._format_message(message), extra=kwargs)


def get_structured_logger(name: str) -> StructuredLogger:
    """
    Get a structured logger instance.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        StructuredLogger instance
    """
    return StructuredLogger(get_logger(name))
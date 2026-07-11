import logging
import logging.config
import os
import sys
from config.settings import settings

def setup_logging():
    os.makedirs(settings.log_dir, exist_ok=True)
    log_file = os.path.join(settings.log_dir, "app.log")
    
    log_level = settings.log_level.upper()
    log_format = settings.log_format.lower()
    
    is_json = log_format == "json"
    
    log_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            },
            "json": {
                "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
                "format": "%(asctime)s %(name)s %(levelname)s %(message)s"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "json" if is_json else "default",
                "stream": "ext://sys.stdout"
            },
            "file": {
                "class": "logging.FileHandler",
                "formatter": "json" if is_json else "default",
                "filename": log_file
            }
        },
        "loggers": {
            "trackr": {
                "handlers": ["console", "file"],
                "level": log_level,
                "propagate": False
            },
            "uvicorn": {
                "handlers": ["console", "file"],
                "level": "INFO",
                "propagate": False
            },
            "uvicorn.access": {
                "handlers": ["console", "file"],
                "level": "INFO",
                "propagate": False
            }
        },
        "root": {
            "handlers": ["console", "file"],
            "level": log_level
        }
    }
    
    logging.config.dictConfig(log_config)
    return logging.getLogger("trackr")

logger = setup_logging()

import asyncio
from typing import Callable, Dict, List, Any, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    JOB_CREATED = "JobCreated"
    JOB_STARTED = "JobStarted"
    FRAME_PROCESSED = "FrameProcessed"
    JOB_COMPLETED = "JobCompleted"
    JOB_FAILED = "JobFailed"
    JOB_UPDATED = "JobUpdated"
    ANALYTICS_GENERATED = "AnalyticsGenerated"
    PLUGIN_LOADED = "PluginLoaded"
    MODEL_LOADED = "ModelLoaded"


class EventBus:
    """
    A simple in-memory event bus for decoupled component communication.
    Supports both synchronous and asynchronous callbacks.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EventBus, cls).__new__(cls)
            cls._instance._subscribers = {}
        return cls._instance

    def subscribe(self, event_type: EventType, callback: Callable):
        """Subscribe a callback to a specific event type."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)
        logger.debug(f"Subscribed to event: {event_type}")

    def publish(self, event_type: EventType, payload: Any = None):
        """Publish an event to all subscribers."""
        if event_type not in self._subscribers:
            return

        logger.debug(f"Publishing event: {event_type}")
        for callback in self._subscribers[event_type]:
            try:
                if asyncio.iscoroutinefunction(callback):
                    # We create a task for async callbacks so we don't block
                    try:
                        loop = asyncio.get_running_loop()
                        loop.create_task(callback(payload))
                    except RuntimeError:
                        # If no running loop, run it in a new thread to avoid blocking or crashing
                        import threading

                        threading.Thread(
                            target=lambda: asyncio.run(callback(payload)), daemon=True
                        ).start()
                else:
                    callback(payload)
            except Exception as e:
                logger.error(f"Error executing callback for {event_type}: {e}")


# Global event bus instance
event_bus = EventBus()

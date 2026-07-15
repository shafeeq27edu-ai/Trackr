import importlib
import pkgutil
import inspect
from typing import Dict, Type, List, Any
import logging
from abc import ABC, abstractmethod

from core.events import event_bus, EventType

logger = logging.getLogger(__name__)


class BasePlugin(ABC):
    """Base class for all plugins."""

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        pass

    @property
    def category(self) -> str:
        return "general"

    def initialize(self):
        """Called when the plugin is loaded."""
        pass


class PluginManager:
    """Manages the discovery, loading, and lifecycle of plugins."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PluginManager, cls).__new__(cls)
            cls._instance._plugins: Dict[str, BasePlugin] = {}
            cls._instance._plugin_classes: Dict[str, Type[BasePlugin]] = {}
        return cls._instance

    def discover_plugins(self, package_name: str = "plugins"):
        """Discovers and loads plugins from a given package directory."""
        logger.info(f"Discovering plugins in {package_name}...")
        try:
            package = importlib.import_module(package_name)
        except ImportError:
            logger.warning(f"Package {package_name} not found. Skipping plugin discovery.")
            return

        for _, module_name, _ in pkgutil.iter_modules(package.__path__):
            full_module_name = f"{package_name}.{module_name}"
            self._load_module(full_module_name)

    def _load_module(self, module_name: str):
        try:
            module = importlib.import_module(module_name)
            for name, obj in inspect.getmembers(module):
                if inspect.isclass(obj) and issubclass(obj, BasePlugin) and obj is not BasePlugin:
                    # Ignore abstract classes
                    if not inspect.isabstract(obj):
                        self.register_plugin(obj)
        except Exception as e:
            logger.error(f"Failed to load plugin module {module_name}: {e}")

    def register_plugin(self, plugin_class: Type[BasePlugin]):
        """Registers and initializes a plugin class."""
        try:
            plugin_instance = plugin_class()
            name = plugin_instance.name

            if name in self._plugins:
                logger.warning(f"Plugin {name} is already registered. Skipping.")
                return

            plugin_instance.initialize()
            self._plugins[name] = plugin_instance
            self._plugin_classes[name] = plugin_class

            logger.info(
                f"Registered plugin: {name} v{plugin_instance.version} ({plugin_instance.category})"
            )
            event_bus.publish(
                EventType.PLUGIN_LOADED, {"name": name, "version": plugin_instance.version}
            )

        except Exception as e:
            logger.error(f"Failed to register plugin {plugin_class.__name__}: {e}")

    def get_plugin(self, name: str) -> BasePlugin:
        """Retrieves an initialized plugin by name."""
        return self._plugins.get(name)

    def get_plugins_by_category(self, category: str) -> List[BasePlugin]:
        """Retrieves all loaded plugins of a specific category."""
        return [p for p in self._plugins.values() if p.category == category]

    def list_plugins(self) -> List[Dict[str, Any]]:
        """Returns metadata for all loaded plugins."""
        return [
            {"name": p.name, "version": p.version, "category": p.category, "status": "enabled"}
            for p in self._plugins.values()
        ]


# Global plugin manager instance
plugin_manager = PluginManager()

from abc import ABC, abstractmethod
from typing import Any
from utils.logger import logger


class BaseAgent(ABC):
    """Abstract Base Class for modular AI agents."""

    def __init__(self, name: str):
        self.name = name
        self.logger = logger

    @abstractmethod
    def run(self, *args, **kwargs) -> Any:
        """Executes agent step logic."""
        pass

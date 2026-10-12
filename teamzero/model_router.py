"""Multi-Provider Model Router for TeamZero.

Routes micro-tasks to appropriate capability tiers (Lite, Standard, Frontier)
and allows the user to select preferred LLM providers (OpenAI, Anthropic, Gemini, Local Ollama).
Configured via .teamzero/providers.yaml or CLI.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional
import yaml

from teamzero.config import PROVIDERS_FILE

DEFAULT_CONFIG: Dict[str, Any] = {
    "default_provider": "gemini",
    "tiers": {
        "lite": {
            "description": "Fast log parsing, formatting, schema validation",
            "provider": "gemini",
            "model": "gemini-2.5-flash",
            "estimated_cost_per_1k": 0.0001,
        },
        "standard": {
            "description": "Test generation, inbox triage, refactoring",
            "provider": "anthropic",
            "model": "claude-3-5-haiku",
            "estimated_cost_per_1k": 0.001,
        },
        "frontier": {
            "description": "Security red-teaming, ADR synthesis, architecture review",
            "provider": "anthropic",
            "model": "claude-3-5-sonnet",
            "estimated_cost_per_1k": 0.015,
        },
    },
    "providers": {
        "gemini": {
            "env_key": "GEMINI_API_KEY",
            "available_models": ["gemini-2.5-flash", "gemini-1.5-pro", "gemini-2.5-pro"],
        },
        "anthropic": {
            "env_key": "ANTHROPIC_API_KEY",
            "available_models": ["claude-3-5-haiku", "claude-3-5-sonnet", "claude-3-opus"],
        },
        "openai": {
            "env_key": "OPENAI_API_KEY",
            "available_models": ["gpt-4o-mini", "gpt-4o", "o1", "o3-mini"],
        },
        "ollama": {
            "endpoint": "http://localhost:11434",
            "available_models": ["llama3.3", "qwen2.5-coder", "deepseek-r1:8b"],
        },
    },
}


class ModelRouter:
    """Manages model configuration and task tier resolution."""

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or PROVIDERS_FILE
        self.config = self._load_or_init_config()

    def _load_or_init_config(self) -> Dict[str, Any]:
        if self.config_path.exists():
            try:
                data = yaml.safe_load(self.config_path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return data
            except Exception:
                pass
        # Initialize default config file
        self.save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG

    def save_config(self, cfg: Dict[str, Any]) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(yaml.dump(cfg, sort_keys=False), encoding="utf-8")
        self.config = cfg

    def resolve_tier(self, task_type: str, severity: str = "LOW") -> str:
        """Determines the appropriate tier for a task based on complexity and severity."""
        if severity.upper() in ["CRITICAL", "HIGH"] or task_type in ["redteam", "adr", "architecture"]:
            return "frontier"
        if severity.upper() == "MEDIUM" or task_type in ["triage", "test_gen", "refactor"]:
            return "standard"
        return "lite"

    def get_tier_target(self, tier: str) -> Dict[str, Any]:
        """Returns the provider and model configured for the tier."""
        tier = tier.lower()
        tiers = self.config.get("tiers", {})
        if tier in tiers:
            return tiers[tier]
        return tiers.get("standard", DEFAULT_CONFIG["tiers"]["standard"])

    def set_tier_model(self, tier: str, provider: str, model: str) -> None:
        """Updates user preference for a specific tier."""
        tier = tier.lower()
        if tier not in self.config.get("tiers", {}):
            raise ValueError(f"Unknown tier '{tier}'. Must be one of: lite, standard, frontier.")
        self.config["tiers"][tier]["provider"] = provider
        self.config["tiers"][tier]["model"] = model
        self.save_config(self.config)

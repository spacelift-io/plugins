"""Tests for PluginGenerator hook detection."""

from spaceforge.generator import PluginGenerator
from spaceforge.plugin import SpaceforgePlugin


class TestPluginGeneratorHooks:
    """Test hook method detection functionality."""

    def test_should_detect_overridden_hook_methods(self) -> None:
        """Should identify hook methods that have been overridden in plugin."""

        # Arrange
        class HookedPlugin(SpaceforgePlugin):
            def after_plan(self) -> None:
                pass

            def before_apply(self) -> None:
                pass

        generator = PluginGenerator()
        generator.plugin_class = HookedPlugin

        # Act
        hooks = generator.get_available_hooks()

        # Assert
        assert "after_plan" in hooks
        assert "before_apply" in hooks
        assert len(hooks) == 2

    def test_should_return_empty_list_when_no_hooks_overridden(self) -> None:
        """Should return empty list when plugin has no overridden hook methods."""

        # Arrange
        class NoHooksPlugin(SpaceforgePlugin):
            pass

        generator = PluginGenerator()
        generator.plugin_class = NoHooksPlugin

        # Act
        hooks = generator.get_available_hooks()

        # Assert
        assert hooks == []

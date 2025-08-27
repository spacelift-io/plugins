"""Tests for SpaceforgePlugin hook system."""

from spaceforge.plugin import SpaceforgePlugin


class TestSpaceforgePluginHooks:
    """Test hook method detection and execution."""

    def test_should_provide_all_expected_hook_methods(self) -> None:
        """Should define all standard Spacelift hook methods as callable."""
        # Arrange
        plugin = SpaceforgePlugin()
        expected_hooks = [
            "before_init",
            "after_init",
            "before_plan",
            "after_plan",
            "before_apply",
            "after_apply",
            "before_perform",
            "after_perform",
            "before_destroy",
            "after_destroy",
            "after_run",
        ]

        # Act & Assert
        for hook_name in expected_hooks:
            assert hasattr(plugin, hook_name)
            hook_method = getattr(plugin, hook_name)
            assert callable(hook_method)
            # Should be able to call without error (default implementation is pass)
            hook_method()

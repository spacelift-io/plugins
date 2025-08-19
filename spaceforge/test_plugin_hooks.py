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

    def test_should_return_all_available_hooks_for_base_class(self) -> None:
        """Should detect and return all hook methods defined in base class."""
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

        # Act
        hooks = plugin.get_available_hooks()

        # Assert
        for expected_hook in expected_hooks:
            assert expected_hook in hooks

    def test_should_detect_overridden_hooks_in_custom_plugin(self) -> None:
        """Should include all hooks including overridden ones in custom plugins."""

        # Arrange
        class TestPluginWithHooks(SpaceforgePlugin):
            def after_plan(self) -> None:
                pass

            def before_apply(self) -> None:
                pass

            def custom_method(self) -> None:  # Not a hook
                pass

        plugin = TestPluginWithHooks()

        # Act
        hooks = plugin.get_available_hooks()

        # Assert
        assert "after_plan" in hooks
        assert "before_apply" in hooks
        assert "custom_method" not in hooks  # Not a recognized hook

        # Should still have all the expected hooks from the base class
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

        for expected_hook in expected_hooks:
            assert expected_hook in hooks

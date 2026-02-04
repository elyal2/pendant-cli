"""Tests for pendant CLI commands."""

import pytest
from click.testing import CliRunner


@pytest.fixture
def runner():
    """Create a Click CLI test runner."""
    return CliRunner()


class TestCLIHelp:
    """Test CLI help output."""

    def test_main_help(self, runner):
        """Test main CLI help output."""
        from pendant.cli import cli
        
        result = runner.invoke(cli, ['--help'])
        assert result.exit_code == 0
        assert 'Pendant BLE Client' in result.output

    def test_settings_help(self, runner):
        """Test settings group help output."""
        from pendant.cli import cli
        
        result = runner.invoke(cli, ['settings', '--help'])
        assert result.exit_code == 0
        assert 'Device settings commands' in result.output

    def test_settings_led_help(self, runner):
        """Test settings led command help."""
        from pendant.cli import cli
        
        result = runner.invoke(cli, ['settings', 'led', '--help'])
        assert result.exit_code == 0
        assert 'Set LED state' in result.output

    def test_settings_brightness_help(self, runner):
        """Test settings brightness command help."""
        from pendant.cli import cli
        
        result = runner.invoke(cli, ['settings', 'brightness', '--help'])
        assert result.exit_code == 0
        assert 'Set LED brightness' in result.output

    def test_settings_vad_help(self, runner):
        """Test settings vad command help."""
        from pendant.cli import cli
        
        result = runner.invoke(cli, ['settings', 'vad', '--help'])
        assert result.exit_code == 0
        assert 'Voice Activity Detection' in result.output

    def test_listen_help(self, runner):
        """Test listen command help."""
        from pendant.cli import cli
        
        result = runner.invoke(cli, ['listen', '--help'])
        assert result.exit_code == 0
        assert 'Listen for device events' in result.output


class TestSettingsValidation:
    """Test settings command input validation."""

    def test_brightness_range_low(self, runner):
        """Test brightness rejects values below 0."""
        from pendant.cli import cli
        
        result = runner.invoke(cli, ['settings', 'brightness', '-1'])
        assert result.exit_code != 0

    def test_brightness_range_high(self, runner):
        """Test brightness rejects values above 100."""
        from pendant.cli import cli
        
        result = runner.invoke(cli, ['settings', 'brightness', '101'])
        assert result.exit_code != 0

    def test_vad_range_low(self, runner):
        """Test VAD threshold rejects values below 0.0."""
        from pendant.cli import cli
        
        result = runner.invoke(cli, ['settings', 'vad', '--', '-0.1'])
        assert result.exit_code != 0

    def test_vad_range_high(self, runner):
        """Test VAD threshold rejects values above 1.0."""
        from pendant.cli import cli
        
        result = runner.invoke(cli, ['settings', 'vad', '1.5'])
        assert result.exit_code != 0


class TestRegisteredCommands:
    """Test that all commands are properly registered."""

    def test_status_registered(self, runner):
        """Test status command is registered."""
        from pendant.cli import cli
        
        result = runner.invoke(cli, ['status', '--help'])
        assert result.exit_code == 0

    def test_info_registered(self, runner):
        """Test info command is registered."""
        from pendant.cli import cli
        
        result = runner.invoke(cli, ['info', '--help'])
        assert result.exit_code == 0

    def test_download_registered(self, runner):
        """Test download command is registered."""
        from pendant.cli import cli
        
        result = runner.invoke(cli, ['download', '--help'])
        assert result.exit_code == 0

    def test_decode_registered(self, runner):
        """Test decode command is registered."""
        from pendant.cli import cli
        
        result = runner.invoke(cli, ['decode', '--help'])
        assert result.exit_code == 0

    def test_record_registered(self, runner):
        """Test record command is registered."""
        from pendant.cli import cli
        
        result = runner.invoke(cli, ['record', '--help'])
        assert result.exit_code == 0

    def test_stop_registered(self, runner):
        """Test stop command is registered."""
        from pendant.cli import cli
        
        result = runner.invoke(cli, ['stop', '--help'])
        assert result.exit_code == 0

    def test_clear_registered(self, runner):
        """Test clear command is registered."""
        from pendant.cli import cli
        
        result = runner.invoke(cli, ['clear', '--help'])
        assert result.exit_code == 0

    def test_listen_registered(self, runner):
        """Test listen command is registered."""
        from pendant.cli import cli
        
        result = runner.invoke(cli, ['listen', '--help'])
        assert result.exit_code == 0

    def test_bt_group_registered(self, runner):
        """Test bt command group is registered."""
        from pendant.cli import cli
        
        result = runner.invoke(cli, ['bt', '--help'])
        assert result.exit_code == 0

    def test_crypto_group_registered(self, runner):
        """Test crypto command group is registered."""
        from pendant.cli import cli
        
        result = runner.invoke(cli, ['crypto', '--help'])
        assert result.exit_code == 0

    def test_settings_group_registered(self, runner):
        """Test settings command group is registered."""
        from pendant.cli import cli
        
        result = runner.invoke(cli, ['settings', '--help'])
        assert result.exit_code == 0

    def test_explore_registered(self, runner):
        """Test explore command is registered."""
        from pendant.cli import cli
        
        result = runner.invoke(cli, ['explore', '--help'])
        assert result.exit_code == 0

    def test_debug_registered(self, runner):
        """Test debug command is registered."""
        from pendant.cli import cli
        
        result = runner.invoke(cli, ['debug', '--help'])
        assert result.exit_code == 0


class TestSettingsSubcommands:
    """Test all settings subcommands are registered."""

    def test_settings_name_registered(self, runner):
        """Test settings name command is registered."""
        from pendant.cli import cli
        
        result = runner.invoke(cli, ['settings', 'name', '--help'])
        assert result.exit_code == 0
        assert 'Set the device name' in result.output

    def test_settings_wifi_add_registered(self, runner):
        """Test settings wifi-add command is registered."""
        from pendant.cli import cli
        
        result = runner.invoke(cli, ['settings', 'wifi-add', '--help'])
        assert result.exit_code == 0

    def test_settings_wifi_connect_registered(self, runner):
        """Test settings wifi-connect command is registered."""
        from pendant.cli import cli
        
        result = runner.invoke(cli, ['settings', 'wifi-connect', '--help'])
        assert result.exit_code == 0

    def test_settings_wifi_disconnect_registered(self, runner):
        """Test settings wifi-disconnect command is registered."""
        from pendant.cli import cli
        
        result = runner.invoke(cli, ['settings', 'wifi-disconnect', '--help'])
        assert result.exit_code == 0

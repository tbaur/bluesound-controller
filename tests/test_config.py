"""
Tests for config module.
"""
import pytest
import json
import os
import tempfile
from unittest.mock import patch, mock_open
import config as config_module

from config import Config
from constants import CONFIG_FILE_JSON, CONFIG_FILE


class TestConfig:
    """Test Config class."""
    
    def test_loads_json_config(self, temp_config_dir):
        """Test loading JSON configuration."""
        config_file = os.path.join(temp_config_dir, "config.json")
        config_data = {
            "BLUOS_SERVICE": "_musc._tcp",
            "DISCOVERY_TIMEOUT": "5",
            "CACHE_TTL": "300",
            "DEFAULT_SAFE_VOL": "14",
            "UNIFI_ENABLED": "false"
        }
        
        with open(config_file, 'w') as f:
            json.dump(config_data, f)
        
        with patch('config.CONFIG_FILE_JSON', config_file):
            config = Config()
            assert config.get('BLUOS_SERVICE') == "_musc._tcp"
            assert config.get('DISCOVERY_TIMEOUT') == "5"
            assert config.get('CACHE_TTL') == "300"
    
    def test_creates_default_config(self, temp_config_dir):
        """Test creation of default config when missing."""
        config_file = os.path.join(temp_config_dir, "config.json")
        
        with patch('config.CONFIG_FILE_JSON', config_file):
            config = Config()
            # Should create default config
            assert os.path.exists(config_file)
            assert config.get('BLUOS_SERVICE') == "_musc._tcp"
    
    def test_validates_config_values(self, temp_config_dir):
        """Test that config values are validated."""
        config_file = os.path.join(temp_config_dir, "config.json")
        config_data = {
            "DISCOVERY_TIMEOUT": "200",  # Invalid, should be clamped
            "DEFAULT_SAFE_VOL": "150",  # Invalid, should be clamped
            "CACHE_TTL": "5000"  # Invalid, should be clamped
        }
        
        with open(config_file, 'w') as f:
            json.dump(config_data, f)
        
        with patch('config.CONFIG_FILE_JSON', config_file):
            config = Config()
            # Values should be validated/clamped
            timeout = int(config.get('DISCOVERY_TIMEOUT', '5'))
            assert 1 <= timeout <= 60
    
    def test_get_with_default(self, temp_config_dir):
        """Test get method with default value."""
        config_file = os.path.join(temp_config_dir, "config.json")
        config_data = {"BLUOS_SERVICE": "_musc._tcp"}
        
        with open(config_file, 'w') as f:
            json.dump(config_data, f)
        
        with patch('config.CONFIG_FILE_JSON', config_file):
            config = Config()
            assert config.get('MISSING_KEY', 'default') == 'default'
            assert config.get('BLUOS_SERVICE') == "_musc._tcp"
    
    def test_case_insensitive_keys(self, temp_config_dir):
        """Test that keys are case-insensitive."""
        config_file = os.path.join(temp_config_dir, "config.json")
        config_data = {"bluos_service": "_musc._tcp"}
        
        with open(config_file, 'w') as f:
            json.dump(config_data, f)
        
        with patch('config.CONFIG_FILE_JSON', config_file):
            config = Config()
            assert config.get('BLUOS_SERVICE') == "_musc._tcp"
            assert config.get('bluos_service') == "_musc._tcp"
    
    def test_handles_invalid_json(self, temp_config_dir):
        """Test handling of invalid JSON."""
        config_file = os.path.join(temp_config_dir, "config.json")
        
        with open(config_file, 'w') as f:
            f.write("invalid json {")
        
        with patch('config.CONFIG_FILE_JSON', config_file):
            config = Config()
            # Should handle error gracefully
            assert config.data == {}
    
    def test_fallback_to_ini(self, temp_config_dir):
        """Test fallback to INI format."""
        ini_file = os.path.join(temp_config_dir, "config.ini")
        json_file = os.path.join(temp_config_dir, "config.json")
        
        with open(ini_file, 'w') as f:
            f.write('BLUOS_SERVICE="_musc._tcp"\n')
            f.write('DISCOVERY_TIMEOUT=5\n')
        
        with patch('config.CONFIG_FILE', ini_file), \
             patch('config.CONFIG_FILE_JSON', json_file):
            config = Config()
            assert config.get('BLUOS_SERVICE') == "_musc._tcp"
            assert config.get('DISCOVERY_TIMEOUT') == "5"
    
    def test_get_unifi_api_key_from_keychain(self, temp_config_dir):
        """Test that UNIFI_API_KEY is retrieved from Keychain first."""
        config_file = os.path.join(temp_config_dir, "config.json")
        config_data = {
            "UNIFI_API_KEY": "config-file-key"
        }
        
        with open(config_file, 'w') as f:
            json.dump(config_data, f)
        
        # Patch both the config file path and the keychain function
        # Use patch.object to ensure we patch the function in the config module
        with patch('config.CONFIG_FILE_JSON', config_file), \
             patch.object(config_module, 'get_api_key', return_value="keychain-key"):
            # Create Config instance after patches are applied
            config = Config()
            # Should get from Keychain, not config file
            result = config.get('UNIFI_API_KEY')
            assert result == "keychain-key", f"Expected 'keychain-key' but got '{result}'"
    
    def test_get_unifi_api_key_fallback_to_config(self, temp_config_dir):
        """Test that UNIFI_API_KEY falls back to config file if not in Keychain."""
        config_file = os.path.join(temp_config_dir, "config.json")
        config_data = {
            "UNIFI_API_KEY": "config-file-key"
        }
        
        with open(config_file, 'w') as f:
            json.dump(config_data, f)
        
        # Patch both the config file path and the keychain function
        # Use patch.object to ensure we patch the function in the config module
        with patch('config.CONFIG_FILE_JSON', config_file), \
             patch.object(config_module, 'get_api_key', return_value=None):
            # Create Config instance after patches are applied
            config = Config()
            # Should fall back to config file
            result = config.get('UNIFI_API_KEY')
            assert result == "config-file-key", f"Expected 'config-file-key' but got '{result}'"


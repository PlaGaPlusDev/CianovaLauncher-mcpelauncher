import json
import os
from src.core.config_manager import ConfigManager
from src import constants as c

TEST_CONFIG_PATH = "test_config.json"

def run_verification():
    # Ensure a clean slate
    if os.path.exists(TEST_CONFIG_PATH):
        os.remove(TEST_CONFIG_PATH)

    # Create a ConfigManager that points to our test file
    cm = ConfigManager(config_file=TEST_CONFIG_PATH)

    # Overwrite the config with a specific non-default value
    cm.set(c.CONFIG_KEY_CLOSE_ON_LAUNCH, False)
    print(f"Value before restore: {cm.get(c.CONFIG_KEY_CLOSE_ON_LAUNCH)}")

    # Call the restore method
    cm.restore_defaults()
    print(f"Value after restore: {cm.get(c.CONFIG_KEY_CLOSE_ON_LAUNCH)}")

    # Verify
    default_value = cm.default_config[c.CONFIG_KEY_CLOSE_ON_LAUNCH]
    current_value = cm.get(c.CONFIG_KEY_CLOSE_ON_LAUNCH)

    if current_value == default_value:
        print("SUCCESS: 'Restore Defaults' functionality is working correctly.")
    else:
        print(f"FAILURE: Value is '{current_value}', but expected default was '{default_value}'.")
        exit(1)

    # Clean up
    if os.path.exists(TEST_CONFIG_PATH):
        os.remove(TEST_CONFIG_PATH)

if __name__ == "__main__":
    run_verification()

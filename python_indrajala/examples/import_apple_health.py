import sys
sys.path.append('../src')
from IndrajalaImporters import AppleHealthImporter

config_file = "./indrajala_apple_health_config.json"

iit=AppleHealthImporter(config_file)
iit.import_data()


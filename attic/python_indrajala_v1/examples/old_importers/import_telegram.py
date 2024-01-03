import sys
sys.path.append('../src')
from IndrajalaImporters import TelegramImporter

config_file = "./indrajala_telegram_import_config.json"

iit=TelegramImporter(config_file)
iit.import_data()



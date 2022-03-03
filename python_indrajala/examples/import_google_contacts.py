import sys
sys.path.append('../src')
from IndrajalaImporters import GoogleContactsImporter

config_file = "./indrajala_google_contacts_import_config.json"

iit=GoogleContactsImporter(config_file)
iit.import_data()



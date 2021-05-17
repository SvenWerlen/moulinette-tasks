# Instructions for local testing

* Create test folder
* Put your zip file in test folder
* Execute command

`AZURE_STORAGE_MOUNT=test LOCAL_TYPE="extract" LOCAL_FILE="JB2A_DnD5e-0.1.8.zip" python3 processTask.py`

# Extracting fabs from compendium

* Create tmp folder
* Execute command

`python3 processFabs.py ~/.local/share/FoundryVTT/Data/modules/baileywiki-maps-premium/packs/baileywikipremium-actors.db tmp/`

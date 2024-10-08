## OmegaT scripts to get text from MyBible modules

### `utils_BibleSetup.groovy`

This is a script that would help OmegaT users in proper selection of the `mybible-cli` script/executable  
![Select exe](../../screenshots/omt_SelectMyBibleCLI.png)  
and the MyBible module for the current project.  
![Select_module](../../screenshots/omt_selectMyBibleModule.png)  
These settings are stored in `<script_folder>/.ini/bible.ini` (`mybible-cli` path) and `<project_folder>/.ini/bible.ini` (selected module). `mybible-cli` needs to be set up prior to being used in OmegaT via scripts.

### `utils_BibleReset.groovy`

This script resets the setup done by `utils_BibleSetup.groovy`, and runs the setup again (therefore `utils_BibleSetup.groovy` must be present in the scripts folder).

### `utils_showBibleVerseInGlossary.groovy`

When this script in invoked, it checks the current source text for biblical references, and if found, gets the text of those references in the selected MyBible module and writes it to a file named `<project_folder>/glossary/bible.utf8` so the text could be seen in OmegaT glossary pane.
![Bible Verse in OmegaT Glossary](../../screenshots/omt_showBibleVerse.png)
The user needs to run the script without doing anything with the references: no need to select and copy them or enter any text into the target field. If references could be found in the source text and the selected module contains text for them, they will be added to glossary.  
This script requires `utils_BibleSetup.groovy` to be present in the scripts folder, and `mybible-cli` to be configured.

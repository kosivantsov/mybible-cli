# OmegaT scripts to get text from MyBible modules

## `utils_BibleSetup.groovy`

This is a script that would help OmegaT user in proper selection of the `mybible-cli` script/executable (filechooser) and the MyBible module for the current project (dropdown list). These settings are stored in `<script_folder>/.ini/bible.ini` (`mybible-cli` path) and `<project_folder>/.ini/bible.ini` (selected module). `mybible-cli` needs to be set up prior to being used in OmegaT via scripts.

## `utils_showBibleVerseInGlossary.groovy`

When this script in invoked, it checks the current source text for biblical references, and if found, get the text of those references in the selected MyBible module and writes it to a file named `<project_folder>/glossary/bible.utf8` so the text could be seen in OmegaT glossary pane.
<div align="center"><img scr="https://github-production-user-asset-6210df.s3.amazonaws.com/6378324/358643997-dd4a8795-915d-4270-9ea8-6f7fedc38d77.png" width="50%" alt="Bible in Glossary" title="Bible in Glossary"></div>

This script requires `utils_BibleSetup.groovy` to be present in the scripts folder and `mybible-cli` to be configured.


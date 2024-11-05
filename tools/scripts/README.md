## `clip2bible.cmd`

A CMD script for MS Windows that launches `mybible-cli.exe` in GUI mode and passes the contents of the system clipboard to it.  
The script is included in the [Windows build](https://github.com/kosivantsov/mybible-cli/releases/latest/). To make it convenient to use, open the folder where `mybible-cli.exe` is copied to, right click on the script and send it to Desktop (create shortcut).
Then on the Desktop, right click on the shortcut, select **Properties**, and set a shortcut that will launch it even if Desktop is not in view. It's best to use a unique shortcut not used elsewhere.

## `clip2bible.sh`

A bash script for macOS and GNU/Linux (or other Unix-like systems) that launches `mybible-cli` in GUI mode and passes the contents of the system clipboard to it.  
The script assumes `mybible-cli` to be found in your `$PATH`.  
On macOS it doesn't have any additional dependancies.  
On other systems it needs `xsel` to be available.  
Depending on the OS and DE/WM used, there are numerous ways to register a system-wide keyboard shortcut to launch the script. On macOS, for instance, [`skhd`](https://github.com/koekeishiya/skhd) could be used. In most WM's a shortcut to launch an application or script could be added without using third-party tools.

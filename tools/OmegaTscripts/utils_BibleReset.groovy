/* :name = Utils - Bible Reset :description=Setup bible.ini globally and per-project to use mybible-cli and a desired module
 * @author  Kos Ivantsov
 * @date    2024-08-16
 * @version 0.2
 */

import org.omegat.util.Preferences
prop = project.getProjectProperties()

if (!prop) {
    console.println("No project open...")
    exit = true
    return
} else {
    exit = false
    genIniDir = new File(Preferences.getPreferenceDefault(Preferences.SCRIPTS_DIRECTORY, "") + File.separator + ".ini")
    genIniFile =  new File(genIniDir.toString() + File.separator + "bible.ini")
    projectIniDir = new File(prop.getProjectRoot().toString() + File.separator + ".ini")
    projectIniFile = new File(projectIniDir.toString() + File.separator + "bible.ini")
    genIniFile.delete()
    projectIniFile.delete()
    setupScriptFile = new File(Preferences.getPreferenceDefault(Preferences.SCRIPTS_DIRECTORY, "") + File.separator + "utils_BibleSetup.groovy")
    if (setupScriptFile.exists()) {
        evaluate(setupScriptFile)
    }
    if (exit) {
        return
    }
}
return

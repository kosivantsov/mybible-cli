/* :name = Utils - Bible Setup :description=Setup bible.ini globally and per-project to use mybible-cli and a desired module
 * @author  Kos Ivantsov
 * @date    2024-08-16
 * @version 0.4
 * 
 * @update  2024-08-17 // Check for MyBible modules path
 * @update  2024-09-10 // Fix UTF-8 output on Windows
 */

import groovy.json.JsonOutput
import groovy.json.JsonSlurper
import java.nio.file.Paths
import javax.swing.JComboBox
import javax.swing.JFileChooser
import javax.swing.JOptionPane
import org.omegat.util.Preferences

APP_NAME = 'mybible-cli'
exit = false
def getDefaultConfigPath() {
    if (System.properties['os.name'].toLowerCase().contains('windows')) {
        return Paths.get(System.getenv('APPDATA'), APP_NAME).toString()
    } else if (System.properties['os.name'].toLowerCase().contains('mac')) {
        return Paths.get(System.getProperty('user.home'), 'Library', 'Application Support', APP_NAME).toString()
    } else { 
        return Paths.get(System.getProperty('user.home'), '.config', APP_NAME).toString()
    }
}

def getConfigFilePath() {
    return Paths.get(getDefaultConfigPath(), 'config.json').toString()
}

def createConfigFile(configFile) {
    def configDir = new File(configFile).parentFile
    if (!configDir.exists()) {
        configDir.mkdirs()
    }

    def defaultConfig = [modules_path: ""]
    new File(configFile).withWriter('UTF-8') { writer ->
        writer.write(JsonOutput.prettyPrint(JsonOutput.toJson(defaultConfig)))
    }
    console.println "Created default config file at $configFile"
}

def checkAndUpdateModulesPath() {
    def configFile = getConfigFilePath()

    if (!new File(configFile).exists()) {
        createConfigFile(configFile)
    }

    def config = new JsonSlurper().parse(new File(configFile))

    def modulesPath = config.modules_path
    if (!modulesPath || !new File(modulesPath).isDirectory()) {
        console.println "modules_path is not set or points to an invalid directory."

        JFileChooser fc = new JFileChooser()
        fc.setFileSelectionMode(JFileChooser.DIRECTORIES_ONLY)
        fc.setFileHidingEnabled(false)
        returnValue = fc.showDialog(null, "Select modules directory")

        if (returnValue == JFileChooser.APPROVE_OPTION) {
            selectedDir = fc.getSelectedFile().absolutePath
            config.modules_path = selectedDir
            new File(configFile).withWriter('UTF-8') { writer ->
                writer.write(JsonOutput.prettyPrint(JsonOutput.toJson(config)))
            }
            console.println("modules_path updated to: $selectedDir")
            exit = false
            return exit
        } else {
            console.println("No directory selected. modules_path remains unset.")
            exit = true
            return exit
        }
    }
}

prop = project.getProjectProperties()
if (!prop) {
    console.println("No project open...")
    exit = true
    return
} else {
    exit = checkAndUpdateModulesPath()
    if (exit) {
        return
    }
    exit = false
    genIniDir = new File(Preferences.getPreferenceDefault(Preferences.SCRIPTS_DIRECTORY, "") + File.separator + ".ini")
    genIniFile =  new File(genIniDir.toString() + File.separator + "bible.ini")
    projectIniDir = new File(prop.getProjectRoot().toString() + File.separator + ".ini")
    projectIniFile = new File(projectIniDir.toString() + File.separator + "bible.ini")
    genIniDir.mkdirs()
    projectIniDir.mkdirs()
    // Parse the general ini file
    String genIniText = ""
    if (genIniFile.exists()) {
        genIniText = genIniFile.text
    }
    // Check if there's a line that starts with 'bible_executable' in the ini file
    bibleExeLine = genIniText.split('\n').find { line -> line ==~ ~/^bible_executable.*/ }
    def exePath
    if (bibleExeLine) {
        exePath = bibleExeLine.split('=')[1].strip()
    }
    exeFile = new File(exePath.toString())
    // If the path in the ini file is not valid, select the path to mybible-cli
    if (!exePath || !exeFile.exists() || !exeFile.isFile()) {
        def loop = true
        while (loop) {
            JFileChooser fc = new JFileChooser()
                fc.setFileSelectionMode(JFileChooser.FILES_ONLY)
                fc.setMultiSelectionEnabled(false)
                fc.setFileHidingEnabled(false)
            if (fc.showDialog(null, "Select mybible-cli") != JFileChooser.APPROVE_OPTION) {
                console.println "Cancelled"
                return
            } else {
                exePath = fc.getSelectedFile()
                if (new File(exePath.toString()).name ==~ ~/^mybible.*/) {
                    loop = false
                }
            }
        }
    }
    // write the ini file with the new path
    updatedGenIniText = genIniText.readLines().findAll { ! (it ==~ ~/^bible_executable.*/) }
    updatedGenIniText.add("bible_executable = ${exePath}")
    genIniFile.write(updatedGenIniText.join('\n'), 'UTF-8')

    // Parse the project ini file
    String projectIniText = ""
    if (projectIniFile.exists()) {
        projectIniText = projectIniFile.text
    }

    moduleLine = projectIniText.split('\n').find { line -> line ==~ ~/^module.*/ }
    formatLine = projectIniText.split('\n').find { line -> line ==~ ~/^format.*/ }
    module = moduleLine ? moduleLine.split('=')[1].trim() : ""
    format = formatLine ? formatLine.split('=')[1].trim() : ""
    processList = [exePath, '--simple-list'].execute()
    outputStream = new StringBuffer()
    errorStream = new StringBuffer()
    output = processList.inputStream.getText("UTF-8")
    error = processList.errorStream.getText("UTF-8")
    
    processList.consumeProcessOutput(outputStream, errorStream)
    watcher = Thread.start {
        processList.waitFor()
    }
    timeout =  1000
    watcher.join(timeout)
    if (watcher.isAlive()) {
        processList.destroy()
        watcher.join()
    }

    int exitCode = processList.exitValue()
    if (exitCode > 0) {
        console.print("MyBible-CLI is not properly set up")
        exit = true
        return
    } else {
        allModuleList = output.toString()
        exit = false
    }

    listItems = allModuleList.split('\n')
    allModules = []
    allModuleList.readLines().each {
        allModules.add(it.split('\t')[1].trim())
    }

    if (!module || ! allModules.contains(module)) {
        dropdown = new JComboBox(listItems as Object[])
        result = JOptionPane.showConfirmDialog(null, dropdown, "Bible module for this project", JOptionPane.OK_CANCEL_OPTION, JOptionPane.PLAIN_MESSAGE)
        if (result == JOptionPane.OK_OPTION) {
            module = dropdown.getSelectedItem().split('\t')[1].trim()
        } else {
            console.println "Canceled"
            return
        }
    }
    updatedProjectIniText = projectIniText.readLines().findAll { ! (it ==~ ~/^module.*/) }
    updatedProjectIniText.add("module = ${module.trim()}")
    projectIniFile.text = updatedProjectIniText.join('\n')
    if (!(format ==~ ~/.*%\p{L}.*/)) {
        format = ""
    }
}
return

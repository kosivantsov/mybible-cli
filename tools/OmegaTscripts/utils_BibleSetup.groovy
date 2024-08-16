/* :name = Utils - Bible Setup :description=Setup bible.ini globally and per-project to use mybible-cli and a desired module
 * @author  Kos Ivantsov
 * @date    2024-08-16
 * @version 0.2
 */

import org.omegat.util.Preferences
import javax.swing.JFileChooser
import javax.swing.JOptionPane
import javax.swing.JComboBox


prop = project.getProjectProperties()
exit = true
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
            JFileChooser fc = new JFileChooser(
                dialogTitle: "Select mybible-cli",
                fileSelectionMode: JFileChooser.FILES_ONLY, 
                multiSelectionEnabled: false)
            if (fc.showOpenDialog() != JFileChooser.APPROVE_OPTION) {
                console.println "Canceled"
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
    output = new StringBuffer()
    error = new StringBuffer()
    processList.consumeProcessOutput(output, error)
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

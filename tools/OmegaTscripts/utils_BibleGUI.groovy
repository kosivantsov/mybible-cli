/* :name=Utils - Show Bible GUI :description=Shows Bible verse in the glossary pane
 * @author  Kos Ivantsov
 *          Yu Tang (KeyListener part is taken from activate_source_text.groovy)
 * 
 * @date    2021-11-13 (based on diatheke and Sword modules)
 * @version 0.5
 * 
 * @update  2024-08-16 (uses utils_BibleSetup.groovy to set up mybible-cli and a MyBible module for the project)
 * @update  2024-08-17 (improved logic to determine Bible references)
 * @update  2024-09-07 (register a key shortcut to pop up the Bible window)
 * @update  2024-09-10 (fix HTML output on Windows, remove/readd keyListener on reload)
 */

import groovy.transform.Field

import java.awt.*
import java.awt.Dimension
import java.awt.Point
import java.awt.Robot
import java.awt.event.ActionEvent
import java.awt.event.ActionListener
import java.awt.event.ComponentAdapter
import java.awt.event.ComponentEvent
import java.awt.event.InputEvent
import java.awt.event.KeyAdapter
import java.awt.event.KeyEvent
import java.awt.event.KeyListener

import java.io.File
import java.io.FileWriter
import java.io.IOException

import javax.swing.*
import javax.swing.ImageIcon
import javax.swing.JDialog
import javax.swing.JEditorPane

import org.omegat.core.Core
import org.omegat.core.CoreEvents
import org.omegat.core.data.ProjectProperties
import org.omegat.core.events.IProjectEventListener
import org.omegat.core.search.SearchMode
import org.omegat.util.OStrings
import org.omegat.util.Preferences
import org.omegat.util.StaticUtils
import org.omegat.util.StringUtil
import org.omegat.util.gui.StaticUIUtils
import org.omegat.util.gui.UIThreadsUtil

@Field final int TRIGGER_KEY = KeyEvent.VK_F10
SCRIPT_NAME = "Show Bible GUI"

KeyListener createEditorKeyListener() {
    [
        keyPressed  : { KeyEvent e ->
            int ctrl_alt = KeyEvent.CTRL_DOWN_MASK | KeyEvent.ALT_DOWN_MASK
            int ctrl_alt_shift = KeyEvent.CTRL_DOWN_MASK | KeyEvent.ALT_DOWN_MASK | KeyEvent.SHIFT_DOWN_MASK
            switch(true) {
                case StaticUtils.isKey(e, TRIGGER_KEY, 0):
                    showDialog()
                    break

                case StaticUtils.isKey(e, TRIGGER_KEY, ctrl_alt_shift):
                    resetBible()
                    break

                case StaticUtils.isKey(e, TRIGGER_KEY, ctrl_alt):
                    getInput()
                    break
            }
        }
    ] as KeyAdapter
}

pngData = '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'
tmpDir = System.getProperty("java.io.tmpdir")
outImg = { base64, name ->
    outFile = new File(tmpDir + File.separator + name + ".png")
    System.setProperty("omegat.bible.icon", outFile.toString())
    if (! outFile.exists()){
        outFile.createNewFile()
    }
    imageOutFile = new FileOutputStream(outFile)
    imageByteArray = Base64.getDecoder().decode(base64)
    imageOutFile.write(imageByteArray)
}
outImg(pngData, "mybible")


class BibleGUIKeyListener extends KeyAdapter {
    String name
    KeyAdapter keyListener

    BibleGUIKeyListener(String name, KeyAdapter keyListener) {
        this.name = name
        this.keyListener = keyListener
    }

    // Override methods to delegate to the actual keyListener
    @Override
    void keyPressed(KeyEvent e) {
        keyListener.keyPressed(e)
    }

    @Override
    void keyReleased(KeyEvent e) {
        keyListener.keyReleased(e)
    }

    @Override
    void keyTyped(KeyEvent e) {
        keyListener.keyTyped(e)
    }
}

class OutputWindow {
    // Method to save the dialog's geometry to a file
    void saveDialogGeometry(JDialog dialog) {
        int x = dialog.getX()
        int y = dialog.getY()
        int width = dialog.getWidth()
        int height = dialog.getHeight()

        String geometryData = "x=${x}\ny=${y}\nwidth=${width}\nheight=${height}"
        try {
            FileWriter writer = new FileWriter(System.getProperty("omegat.bible.geometryfile"))
            writer.write(geometryData)
            writer.close()
            println("Geometry saved: $geometryData")
        } catch (IOException e) {
            println("Error saving dialog geometry: $e")
        }
    }

    // Method to run the external program and display the output in a dialog
    void showOutput(String outputText) {
        File geometryFile = new File(System.getProperty("omegat.bible.geometryfile"))
        Map<String, Integer> geometry = [:]
        if (geometryFile.exists()) {
            geometryFile.eachLine { line ->
                def (key, value) = line.split("=")
                geometry[key] = value.toInteger()
            }
        }
        // Create a thread to run the external program
        // Create and show the dialog box with the output
        SwingUtilities.invokeLater {

            JDialog dialog = new JDialog()
            dialog.setTitle("Bible")
            dialog.setDefaultCloseOperation(JDialog.DISPOSE_ON_CLOSE)

            // Set icon
            ImageIcon icon = new ImageIcon(System.getProperty("omegat.bible.icon"))
            dialog.setIconImage(icon.image)

            // Create a JEditorPane and set it to display HTML
            JEditorPane editorPane = new JEditorPane("text/html", outputText)
            editorPane.setEditable(false)
            // Wrap the JEditorPane in a JScrollPane
            JScrollPane scrollPane = new JScrollPane(editorPane)
            scrollPane.setPreferredSize(new Dimension(geometry['width'] ?: 800 , geometry['height'] ?: 500))

            // Add the JScrollPane to the JDialog
            dialog.add(scrollPane)

            dialog.addComponentListener(new ComponentAdapter() {
                @Override
                void componentResized(ComponentEvent e) {
                    saveDialogGeometry(dialog)
                }

                @Override
                void componentMoved(ComponentEvent e) {
                    saveDialogGeometry(dialog)
                }
            })

            dialog.getRootPane().registerKeyboardAction(e -> dialog.dispose(),
                                                        KeyStroke.getKeyStroke(KeyEvent.VK_ESCAPE, 0),
                                                        JComponent.WHEN_IN_FOCUSED_WINDOW)

            // Add a key listener to close the dialog on Esc key press
            dialog.addKeyListener(new KeyAdapter() {
                @Override
                void keyPressed(KeyEvent e) {
                    if (e.getKeyCode() == KeyEvent.VK_ESCAPE) {
                        dialog.dispose()
                    }
                }
            })

            // Ensure the text area also listens for key events
            editorPane.addKeyListener(new KeyAdapter() {
                @Override
                void keyPressed(KeyEvent e) {
                    if (e.getKeyCode() == KeyEvent.VK_ESCAPE) {
                        dialog.dispose()
                    }
                }
            })

            // dialog.setSize(new Dimension(geometry['width'], geometry['height']))
            dialog.setLocation(new Point(geometry['x'] ?: 0, geometry['y'] ?: 0))
            dialog.pack()
            dialog.setAlwaysOnTop(true)
            dialog.setVisible(true)
            resetModifiers()
        }
    }
}

def setupBible() {
    setupScriptFile = new File(Preferences.getPreferenceDefault(Preferences.SCRIPTS_DIRECTORY, "") + File.separator + "utils_BibleSetup.groovy")
    if (setupScriptFile.exists()) {
        evaluate(setupScriptFile)
    }
}

void showDialog() {
    // Get fonts and colors
    textFont = Preferences.getPreference("source_font")
    if ( ! textFont || textFont == "__DEFAULT__") {
        textFont = "Dialog"
    }
    textFontSize = Preferences.getPreference("source_font_size")
    if ( ! textFontSize || textFontSize == "__DEFAULT__") {
        textFontSize = 12
    }
    bgColor = Preferences.getPreference("COLOR_BACKGROUND")
    if ( ! bgColor || bgColor == "__DEFAULT__") {
        bgColor = "#FFFFFF"
    }
    fgColor =Preferences.getPreference("COLOR_UNTRANSLATED_FG")
    if ( ! fgColor || fgColor == "__DEFAULT__") {
        fgColor = "#000000"
    }
    verseNumberColor = Preferences.getPreference("COLOR_PLACEHOLDER")
    if ( ! verseNumberColor || verseNumberColor == "__DEFAULT__") {
        verseNumberColor = "#7F7F7F"
    }
    try {
        SwingUtilities.invokeLater {
            // check if project is open
            prop = project.getProjectProperties()
            if (! prop) {
                def title = SCRIPT_NAME
                def msg = "No project open"
                console.println("${SCRIPT_NAME} >> $msg")
                //JOptionPane.showMessageDialog(null, msg, title,
                //                              JOptionPane.INFORMATION_MESSAGE)
                //return
            } else {
                projectIniDir = new File(prop.getProjectRoot().toString() + File.separator + ".ini")
                geometryFile =  projectIniDir.toString() + File.separator + 'bible.geometry'
                System.setProperty("omegat.bible.geometryfile", geometryFile)
            }

            setupBible()
            if (exit) {
                return
            }

            // Collect Refs in the source text
            if (System.getProperty("omegat.bible.input")) {
                sourceText = System.getProperty("omegat.bible.input")
            } else {
                sourceText = editor.currentEntry ? editor.currentEntry.getSrcText().replaceAll(/<\/?\w+\d+\/?>/, '') : null
            }
            if (!sourceText){
                console.println("No source text")
                return
            }
            System.clearProperty("omegat.bible.input")
            initial_refs = []
            refs = []
            // Find references without leading numbers (Corinthians instead of 1 Corinthians)
            regex = /\p{L}+\.?\s+\d+(([:\-]\d+)*([\,\;]\s*\d+)*)*/
            matcher = sourceText =~ regex
            matcher.each { match ->
                initial_refs.add(match[0])
            }
            initial_refs = initial_refs.unique()
            // Find if the reference had a leading number and add it with the found number
            initial_refs.each { ref ->
                possible_match = sourceText.findAll("[1-5I]+\\s*${ref}").join(', ')
                if (possible_match) {
                    refs.add(possible_match.toString())
                } else {
                    refs.add(ref)
                }
            }
            refs = refs.unique()
            if (refs.size() == 0) {
                console.println("Nothing to do in this segment")
                return
            } else {
                console.println("References in the segment: ${refs.join('; ')}")
            }
            collectedText = ["<html><body style=\"font-family: \'${textFont}\'; background-color: ${bgColor};\">"]
            refs.each() {
                ref = it
                ref = ref.replaceAll(/–/, /\-/)
                ref = ref.trim()
                ref = ref.replaceAll(/[\:\;\.\,]$/, '')
                format = """-f %a %c:%v %t"""
                htmlBeforeNumbers = """<p style="font-size: ${textFontSize.toInteger() - 2}px; color: ${fgColor};"><span style="font-size: ${textFontSize.toInteger() - 5}px; font-style: italic; color: ${verseNumberColor};"><sup>"""
                htmlAfterNumbers = """</sup></span>"""
                htmlAfterText = "</p>"
                command = [exeFile, "-m", module, "-r", ref, format]
                process = command.execute()
                text = process.in.newReader('UTF-8').text.readLines()
                modifiedText = []
                text.each {
                    verse = it.replaceAll(/^(.+\d+:\d+)/) { match ->
                        "<p style=\"font-size: ${textFontSize.toInteger() - 2}px; color: ${fgColor};\">" +
                        "<span style=\"font-size: ${textFontSize.toInteger() - 4}px; font-style: italic; color: ${verseNumberColor};\">" +
                        "<sup>${match[1]}</sup></span>"
                    }
                    verse = verse.replaceAll(/(.)$/, /$1<\/p>/)
                    modifiedText.add(verse)
                }
                text = modifiedText.join('\n')

                // check for errors in the output (it would contain an ANSI seq.)
                if (text.contains('✘')) {
                    console.println("Couldn't find text for this reference: ${ref}")
                } else {
                    collectedText.add(text)
                }
            }
            if (collectedText.size() > 0) {
                collectedText.add("</font></body></html>")
                outWindow = new OutputWindow()
                outWindow.showOutput(collectedText.join('\n\n'))
            }
        }
    } catch(ex) {
        console.println "$SCRIPT_NAME >> $ex"
    }
}

void getInput() {
    JDialog dialog = new JDialog()
    dialog.setTitle("Bible Reference")
    dialog.setSize(400, 100)
    dialog.setLocationRelativeTo(null) // Center the dialog

    // Create input field
    JTextField inputField = new JTextField()
    dialog.add(inputField)

    // Create buttons
    JPanel buttonPanel = new JPanel()
    JButton runButton = new JButton("Show text")

    buttonPanel.add(runButton)
    dialog.add(buttonPanel, BorderLayout.SOUTH)

    // Action for "Run" button
    runButton.addActionListener(new ActionListener() {
        @Override
        void actionPerformed(ActionEvent e) {
            String inputText = inputField.getText()
            if (!inputText.isEmpty()) {
                runAction(inputText) // Pass the input string to a function
                dialog.dispose() // Close the dialog after action is performed
            } else {
                JOptionPane.showMessageDialog(dialog, "Input field cannot be empty.", "Error", JOptionPane.ERROR_MESSAGE)
            }
        }
    })

    dialog.addKeyListener(new KeyAdapter() {
        @Override
        void keyPressed(KeyEvent e) {
            if (e.getKeyCode() == KeyEvent.VK_ESCAPE) {
                dialog.dispose()
            }
            if (e.getKeyCode() == KeyEvent.VK_ENTER) {
                runButton.doClick() // Trigger the run button's action
            }
        }
    })

    inputField.addKeyListener(new KeyAdapter() {
        @Override
        void keyPressed(KeyEvent e) {
            if (e.getKeyCode() == KeyEvent.VK_ESCAPE) {
                dialog.dispose()
            }
            if (e.getKeyCode() == KeyEvent.VK_ENTER) {
                runButton.doClick() // Trigger the run button's action
            }
        }
    })

    // Make the dialog visible
    dialog.setVisible(true)
    resetModifiers()
}

void runAction(String input) {
    System.setProperty("omegat.bible.input", input)
    showDialog()
}

void resetBible() {
    projectIniFile = new File(projectIniDir.toString() + File.separator + "bible.ini")
    if (projectIniFile.exists()) {
        projectIniFile.delete()
    }
    setupBible()
}

void resetModifiers() {
    def keyMap = [
        "SHIFT": KeyEvent.VK_SHIFT,
        "CTRL": KeyEvent.VK_CONTROL,
        "CONTROL": KeyEvent.VK_CONTROL,
        "ALT": KeyEvent.VK_ALT,
        "META": KeyEvent.VK_META,
        "WINDOWS": KeyEvent.VK_WINDOWS
    ]
    robot = new Robot()
    keyMap.each() {
        try {
            robot.keyPress(it.value)
            robot.keyRelease(it.value)
        }
        catch (java.lang.IllegalArgumentException iae) {
            //If the modifier is not available, report it in the console
            console.println("$it: key not avalable")
        }
    }
}

boolean isAvailable() {
    // OmegaT 4.x or later
    (OStrings.VERSION =~/^\d+/)[0].toInteger() >= 4
}

// controller class
class BibleWindowController implements IProjectEventListener {
    KeyListener _listener
    BibleWindowController(KeyListener listener) {
        _listener = new BibleGUIKeyListener("BibleKeyListener", listener)
        if (Core.project.isProjectLoaded()) {
            uninstallKeyListener()
            installKeyListener()
        }
    }

    void onProjectChanged(PROJECT_CHANGE_TYPE eventType) {
        switch(eventType) {
            case PROJECT_CHANGE_TYPE.CREATE:
            case PROJECT_CHANGE_TYPE.LOAD:
                // Lazy adding listener for waiting the opening documents process will be complete.
                Runnable doRun = {
                    uninstallKeyListener()
                    installKeyListener()
                } as Runnable
                SwingUtilities.invokeLater doRun
                System.setProperty("omegat.bible.status", "Script is activated for the current session.")
                break
            case PROJECT_CHANGE_TYPE.CLOSE:
                uninstallKeyListener()
                System.setProperty("omegat.bible.status", "Script is deactivated for the current session.")
                break
            case PROJECT_CHANGE_TYPE.SAVE:
                System.setProperty("omegat.bible.status", "Project saved...")

                break
        }
    }

    void installKeyListener() {
        Core.editor.editor.addKeyListener _listener
    }

    void uninstallKeyListener() {
        def keyListeners = Core.editor.editor.getKeyListeners()
        keyListeners.each { listener ->
            // Check if the class name contains 'BibleGUIKeyListener' and remove it from Core.editor.editor
            if (listener.getClass().getName().contains("BibleGUIKeyListener")) {
                Core.editor.editor.removeKeyListener(listener)
            }
        }
    }
}

// verify OmegaT version
if (! isAvailable()) {
    return "$SCRIPT_NAME >> This script cannot run in OmegaT versions earlier than 4."
}

CoreEvents.registerProjectChangeListener(new BibleWindowController(createEditorKeyListener()))
System.getProperty("omegat.bible.status") ? ((System.getProperty("omegat.bible.status")) ? "Project saved..." : "$SCRIPT_NAME >> ${System.getProperty("omegat.bible.status")}") : ""

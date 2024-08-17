/* :name=Utils - Show Bible Verse :description=Shows Bible verse in the glossary pane
 * @author  Kos Ivantsov
 * @date    2021-11-13 (based on diatheke and Sword modules)
 * @update  2024-08-16 (uses utils_BibleSetup.groovy to set up mybible-cli and a MyBible module for the project)
 * @update  2024-08-17 (improved logic to determine Bible references)
 * @version 0.3
 */

import javax.swing.JOptionPane
import org.omegat.util.Preferences
import java.util.regex.Matcher
import java.util.regex.Pattern

def gui() {
    // check if project is open
    prop = project.getProjectProperties()
    if (! prop) {
        def title = "Bible Glossary"
        def msg = "No project open"
        JOptionPane.showMessageDialog(null, msg, title,
        JOptionPane.INFORMATION_MESSAGE)
        return
    }

    setupScriptFile = new File(Preferences.getPreferenceDefault(Preferences.SCRIPTS_DIRECTORY, "") + File.separator + "utils_BibleSetup.groovy")
    if (setupScriptFile.exists()) {
        evaluate(setupScriptFile)
    }
    if (exit) {
        return
    }
    // get glossary dir to store another file with verses
    glosroot = prop.getGlossaryRoot()
    // get project languages
    sourceLang = prop.getSourceLanguage().getLanguageCode()
    targetLang = prop.getTargetLanguage().getLanguageCode()
    // This is the glossary file where the verse is going to be stored
    bibleGlossary =  new File(glosroot + "bible.utf8")
    // This will contain new glossary items which will be written to the file in one go
    def glossaryContent = new StringWriter()
    if (bibleGlossary.exists()) {
        glossaryContent << bibleGlossary.text
    }
    prescripGlossaryContent = new StringWriter()
    prescripGlossaryContent << glossaryContent.toString()

    // Collect Refs in the source text
    sourceText = editor.currentEntry ? editor.currentEntry.getSrcText().replaceAll(/<\/?\w+\d+\/?>/, '') : null
    if (!sourceText){
        console.println("No source text")
        return
    }
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

    refs.each() {
        ref = it
        ref = ref.replaceAll(/–/, /\-/)
        ref = ref.trim()
        ref = ref.replaceAll(/[\:\;\.\,]$/, '')
        format = '-f %t'
        command = [exeFile, "-m", module, "-r", ref, format]
        process = command.execute()
        text = process.in.newReader('UTF-8').text.readLines()
        text = text.join(' ')

        // check for errors in the output (it would contain an ANSI seq.)
        if (text.contains('[1m')) {
            console.println("Couldn't find text for ${ref}")
            //glossaryItem = ""
        } else {
            // build an entry to be stored in the glossary file
            glossaryItem = ref + "\t" + text + "\n"
            // then check if the file already contains the valid item, and if so, skip it
            if (! glossaryContent.toString().contains(glossaryItem)) {
                // add it to the container which will be written to the file
                glossaryContent << glossaryItem
            } else {
                console.println("Item was already added:\n$glossaryItem")
            }
        }
    }
    if (prescripGlossaryContent.toString() != glossaryContent.toString()) {
        bibleGlossary.write(glossaryContent.toString(), 'UTF-8')
        return
    } else {
        return
    }
}

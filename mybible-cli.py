#!/usr/bin/env python3
import argparse
import csv
import hashlib
import json
import locale
import os
import re
import sqlite3
import subprocess
import textwrap
import unicodedata
import warnings

# Config location (APP_NAME) is a folder name under ~/.config
APP_NAME = 'mybible-cli'

warnings.filterwarnings("ignore", category=DeprecationWarning)
def get_default_config_path():
    if os.name == 'nt':
        return os.path.join(os.getenv('APPDATA'), APP_NAME)
    elif os.name == 'posix':
        if 'darwin' in os.sys.platform:
            return os.path.join(os.path.expanduser('~'), 'Library', 'Application Support', APP_NAME)
        else:
            return os.path.join(os.path.expanduser('~'), '.config', APP_NAME)

# Get system locale to get the language, set language to 'en' if not set
language_country = locale.getdefaultlocale()[0]
if not language_country:
    language_country = "en_US"
language, country = [part.lower() for part in re.split(r'[_\-]', language_country)]

# Parse the *.properties file
def read_properties(properties_file):
    properties = {}
    if not os.path.exists(properties_file):
        return properties

    def normalize_value(value):
        value = value.strip().replace('\\\\', '<doubleslash>')
        value = value.replace(r'\n', '\n')
        value = value.replace(r'\t', '\t')
        value = value.replace('<doubleslash>', '\\')
        value = value.strip()
        return value

    with open(properties_file, 'r', encoding='utf-8') as file:
        key = None
        value = ""
        for line in file:
            line = line.rstrip()

            # Skip comments and blank lines
            if not line or line.startswith('#') or line.startswith('!'):
                continue

            # Handle line continuation with a backslash
            if line.endswith('\\'):
                line = line[:-1].rstrip()
                # First part of a multi-line value
            if '=' in line:
                key, value = line.split('=')
                key = key.strip()
                value = value.strip()
            else:
                # Continuing a multi-line value
                value += ' ' + line.strip()
            properties[key] = normalize_value(value)

    return properties

CONFIG_FILE = os.path.join(get_default_config_path(), 'config.json')
BOOKMAPPING_FILE = os.path.join(get_default_config_path(), 'mapping.json')
INSTALLED_MODULES_FILE = os.path.join(get_default_config_path(), 'installed_modules.json')
L10N_FILE = os.path.join(get_default_config_path(), 'l10n', f'{language}.properties',)

# Default UI strings if l10n data not found
default_l10n_strings = {
    'invalid_path': '\nCannot find the folder with MyBible modules: {modules_path}',
    'empty_path': '\nNo MyBible modules found found in {modules_path}',
    'in_path': '\nFull path to the folder with MyBible modules:\n',
    'no_module': '\nNo module named \'{module_name}\' found in \'{modules_path}\'',
    'exit_now': '\nExiting now...',
    'available_modules': '\nAvailable MyBible modules: {number}',
    'invalid_reference': '\nInvalid reference for this module',
    'no_verse_ouput': '\nCannon output {bold}{reference}{normal}:',
    'error': 'Error!',
    'folder_fail': 'Failed to open the folder: {error}',
    'file_fail': 'Failed to open {file}',
    'file_created': 'File created: {file}',
    'help_description': 'Command line tool to query MyBible modules.',
    'help_epilog': 'Parameter containing several tokens should be quoted: {bold}mybible-cli -b \"NIV\'11\" -r \"1 Pet 1:1\"{normal}',
    'help_path': 'path to the folder with MyBible module',
    'help_list': 'lists available MyBilbe modules',
    'help_simplelist': 'lists available MyBible modules in a simple format',
    'help_modulename': 'name of the MyBible module to use',
    'help_reference': 'Bible reference to output',
    'help_abbr': 'reads Bible book names and abbreviations from a non-default file. With {bold}{italics}--abbr uk{normal} a file named {bold}{italics}uk_mapping.json{normal} located in the configuration folder will be used',
    'help_selfabbr': 'reads Bible book names and abbreviations from the module itself',
    'help_format': 'formats output with %%-prefixed format string. Available placeholders: f, a, c, v, t, T, z, A, Z, m',
    'help_saveformat': 'specified format string will be applied and saved as default',
    'help_helpformat': 'detailed info on the format string',
    'help_noansi': 'clears out any ANSI escape sequences in the Bible verses output (if %%A or %%Z were used)',
    'help_open_config': 'opens the config folder',
    'help_open_module': 'opens the folder with MyBible modules',
    'help_j2t': 'converts a json file to tsv (to edit a mapping file)',
    'help_checktsv': 'reports duplicates in the specified tsv file',
    'help_t2j': 'converts a tsv file to json (to use as a mapping file)',
    'help_helpformat_message': '''\nAvailable placeholders for the format string:\n\
    \t  %f \t full book name\n\
    \t  %a \t abbreviated book name\n\
    \t  %b \t book number as per MyBible format specifications\n\
    \t  %c \t chapter number\n\
    \t  %v \t verse number\n\
    \t  %T \t raw text of the verse from the module\n\
    \t  %t \t text of the verse without markers; notes and line breaks are kept\n\
    \t  %z \t the same as above, but without notes and line breaks\n\
    \t  %A \t text of the verse with color output for console; Strong\' numbers are included\n\
    \t  %Z \t the same as above, but without Strong\'s numbers\n\
    \t  %m \t module name\n\
Current default format is {bold}{format_string}{normal}\n\
To save a new default, provide the format with {bold}-F{normal}\n\
Format string may contain {bold}\\t{normal} and {bold}\\n{normal}\n\
Each verse in the output is printed on a new line and is formatted individually''',
        'parser_error': 'Run with the arguments -b/--module_name and -r/--reference, or use one of the following: -L/--list-modules, --simple-list, --helpformat, --open-config-folder, --open-module-folder, --j2t/--json-to-tsv, --check-tsv, --t2j/--tsv-to-json',
    'file_exists_prompt': 'The file \'{file}\' already exists. Do you want to overwrite it? (yes/no): ',
    'yes_no_prompt': 'Please enter \'yes\' or \'no\'',
    'repeated_in_line': 'Repetitions in row {row}: {repeated_string}',
    'repeated_in_file': 'Repetitions of {element} in rows {rows}'
}

# Load l10n data or use defaults
l10n_strings = read_properties(L10N_FILE)
invalid_path = l10n_strings.get('invalid_path', default_l10n_strings['invalid_path'])
empty_path = l10n_strings.get('empty_path', default_l10n_strings['empty_path'])
in_path = l10n_strings.get('in_path', default_l10n_strings['in_path'])
no_module = l10n_strings.get('no_module', default_l10n_strings['no_module'])
exit_now = l10n_strings.get('exit_now', default_l10n_strings['exit_now'])
invalid_reference = l10n_strings.get('invalid_reference', default_l10n_strings['invalid_reference'])
no_verse_ouput = l10n_strings.get('no_verse_ouput', default_l10n_strings['no_verse_ouput'])
available_modules = l10n_strings.get('available_modules', default_l10n_strings['available_modules'])
error = l10n_strings.get('error', default_l10n_strings['error'])
folder_fail = l10n_strings.get('folder_fail', default_l10n_strings['folder_fail'])
file_fail = l10n_strings.get('file_fail', default_l10n_strings['file_fail'])
file_created = l10n_strings.get('file_created', default_l10n_strings['file_created'])
help_description = l10n_strings.get('help_description', default_l10n_strings['help_description'])
help_epilog = l10n_strings.get('help_epilog', default_l10n_strings['help_epilog'])
help_path = l10n_strings.get('help_path', default_l10n_strings['help_path'])
help_list = l10n_strings.get('help_list', default_l10n_strings['help_list'])
help_simplelist = l10n_strings.get('help_simplelist', default_l10n_strings['help_simplelist'])
help_modulename = l10n_strings.get('help_modulename', default_l10n_strings['help_modulename'])
help_reference = l10n_strings.get('help_reference', default_l10n_strings['help_reference'])
help_abbr = l10n_strings.get('help_abbr', default_l10n_strings['help_abbr'])
help_selfabbr = l10n_strings.get('help_selfabbr', default_l10n_strings['help_selfabbr'])
help_format = l10n_strings.get('help_format', default_l10n_strings['help_format'])
help_saveformat = l10n_strings.get('help_saveformat', default_l10n_strings['help_saveformat'])
help_helpformat = l10n_strings.get('help_helpformat', default_l10n_strings['help_helpformat'])
help_noansi = l10n_strings.get('help_noansi', default_l10n_strings['help_noansi'])
help_open_config = l10n_strings.get('help_open_config', default_l10n_strings['help_open_config'])
help_open_module = l10n_strings.get('help_open_module', default_l10n_strings['help_open_module'])
help_j2t = l10n_strings.get('help_j2t', default_l10n_strings['help_j2t'])
help_checktsv = l10n_strings.get('help_checktsv', default_l10n_strings['help_checktsv'])
help_t2j = l10n_strings.get('help_t2j', default_l10n_strings['help_t2j'])
help_helpformat_message = l10n_strings.get('help_helpformat_message', default_l10n_strings['help_helpformat_message'])
parser_error = l10n_strings.get('parser_error', default_l10n_strings['parser_error'])
file_exists_prompt = l10n_strings.get('file_exists_prompt', default_l10n_strings['file_exists_prompt'])
yes_no_prompt = l10n_strings.get('yes_no_prompt', default_l10n_strings['yes_no_prompt'])
repeated_in_line = l10n_strings.get('repeated_in_line', default_l10n_strings['repeated_in_line'])
repeated_in_file = l10n_strings.get('repeated_in_file', default_l10n_strings['repeated_in_file'])

# Default book mapping content
DEFAULT_BOOK_MAPPING = \
{
    "10": ["Genesis", "1 Moses", "I Moses", "Gen", "Ge", "Gn", "1M"],
    "20": ["Exodus", "2 Moses", "II Moses", "Exo", "Exod", "Ex", "2M"],
    "30": ["Leviticus", "3 Moses", "III Moses", "Lev", "Lv", "Le", "3M"],
    "40": ["Numbers", "4 Moses", "IV Moses", "Num", "Nu", "Nm", "Nb", "4M"],
    "50": ["Deuteronomy", "5 Moses", "V Moses", "Deu", "Deut", "Dt", "5M"],
    "60": ["Joshua", "Jos", "Josh", "Jsh"],
    "70": ["Judges", "Jdg", "Judg", "Jdgs"],
    "80": ["Ruth", "Rut", "Ru", "Rth"],
    "90": ["1 Samuel", "I Samuel", "1Sa", "1Sam", "1 Sm", "I Sam", "I Sm"],
    "100": ["2 Samuel", "II Samuel", "2Sa", "2Sam", "2 Sm", "II Sam", "II Sm"],
    "110": ["1 Kings", "I Kings", "1Ki", "1Kgs", "1Kin", "I Ki", "I Kgs", "I Kin"],
    "120": ["2 Kings", "II Kings", "2Ki", "2Kgs", "2Kin", "II Ki", "II Kgs", "II Kin"],
    "130": ["1 Chronicles", "I Chronicles", "1Ch", "1Chr", "1 Ch", "1 Chron", "I Ch", "I Chr", "I Chron"],
    "140": ["2 Chronicles", "II Chronicles", "2Ch", "2Chr", "2 Ch", "2 Chron", "II Ch", "II Chr", "II Chron"],
    "150": ["Ezra", "Ezr", "Ez"],
    "160": ["Nehemiah", "Neh", "Ne"],
    "165": ["1 Esdras", "I Esdras", "1Es", "1Esd", "I Es", "I Esd"],
    "166": ["2 Esdras", "II Esdras", "2Es", "2Esd", "II Es", "II Esd"],
    "170": ["Tobit", "Tob"],
    "180": ["Judith", "Jdt", "Jdth"],
    "190": ["Esther", "Est", "Esth", "Es"],
    "192": ["Greek Esther", "Additions to Esther", "Esg", "AddEsth", "EstGr", "GrEsth"],
    "220": ["Job", "Jb"],
    "230": ["Psalms", "Psalm", "Psa", "Ps", "Pslm"],
    "232": ["Psalm 151", "Ps2", "Ps151"],
    "235": ["Psalms of Solomon", "PSS"],
    "240": ["Proverbs", "Pro", "Prov", "Prv", "Pr"],
    "245": ["Odae", "Odas", "Oda"],
    "250": ["Ecclesiastes", "Qoholeth", "Ecc", "Eccl", "Qoh", "Eccles"],
    "260": ["Song of Songs", "Song of Solomon", "Canticles of Canticles", "Sng", "Song", "Sg", "SOS", "Cant", "COC"],
    "270": ["Wisdom of Solomon", "Wis", "Wisd"],
    "280": ["Sirach", "Ecclesiasticus", "Sir", "Ecclus"],
    "290": ["Isaiah", "Isa", "Is"],
    "300": ["Jeremiah", "Jer", "Je", "Jr", "Jrm"],
    "305": ["Prayer of Azariah", "Azariah", "Aza", "PrAzar", "PrAz", "Azar"],
    "310": ["Lamentations", "Lam", "La", "Lament"],
    "315": ["Letter of Jeremiah", "Epistle of Jeremiah", "Lje", "EpJer", "LetJer", "LJ"],
    "320": ["Baruch", "1 Baruch", "I Baruch", "Bar", "Br"],
    "321": ["2 Baruch", "2Ba"],
    "322": ["3 Baruch", "3Ba"],
    "323": ["Song of the 3 Young Men", "Song of the Three Young Men", "S3Y", "SgThree", "Sg3"],
    "325": ["Susanna", "Sus"],
    "330": ["Ezekiel", "Ezk", "Ezek", "Eze"],
    "340": ["Daniel", "Dan", "Da", "Dn"],
    "345": ["Bel and the Dragon", "Bel"],
    "350": ["Hosea", "Hos", "Ho"],
    "360": ["Joel", "Jol", "Jl"],
    "370": ["Amos", "Amo", "Am"],
    "380": ["Obadiah", "Oba", "Obad", "Ob"],
    "390": ["Jonah", "Jon", "Jona"],
    "400": ["Micah", "Mic", "Mi", "Mc"],
    "410": ["Nahum", "Nam", "Nah", "Na"],
    "420": ["Habakkuk", "Hab", "Hb"],
    "430": ["Zephaniah", "Zep", "Zp"],
    "440": ["Haggai", "Hag", "Hg"],
    "450": ["Zechariah", "Zec", "Zech", "Zch"],
    "460": ["Malachi", "Mal", "Ml"],
    "462": ["1 Maccabees", "1Ma", "1Macc", "1Mac", "I Mac", "I Macc"],
    "464": ["2 Maccabees", "2Ma", "2Macc", "2Mac", "II Mac", "II Macc"],
    "466": ["3 Maccabees", "3Ma", "3Macc", "3Mac", "III Mac", "III Macc"],
    "467": ["4 Maccabees", "4Ma", "4Macc", "4Mac", "IV Mac", "IV Macc"],
    "468": ["2 Esdras", "2Es", "2Esd", "II Es", "II Esd"],
    "470": ["Matthew", "Mat", "Matt", "Mt"],
    "480": ["Mark", "Mrk", "Mar", "Mk"],
    "490": ["Luke", "Luk", "Lk", "Lu"],
    "500": ["John", "Jhn", "Jn"],
    "510": ["Acts", "Act", "Ac"],
    "511": ["Didache", "Did"],
    "520": ["Romans", "Rom", "Ro", "Rm"],
    "530": ["1 Corinthians", "I Corinthians", "1Co", "1Cor", "I Co", "I Cor"],
    "540": ["2 Corinthians", "II Corinthians", "2Co", "2Cor", "II Co", "II Cor"],
    "550": ["Galatians", "Gal", "Ga"],
    "560": ["Ephesians", "Eph"],
    "570": ["Philippians", "Php", "Phil", "Phlp"],
    "580": ["Colossians", "Col"],
    "590": ["1 Thessalonians", "I Thessalonians", "1Th", "1Thess", "1Ths", "1 Thes", "I Th", "I Thess", "I Ths", "I Thes"],
    "600": ["2 Thessalonians", "II Thessalonians", "2Th", "2Thess", "2Ths", "2 Thes", "II Th", "II Thess", "II Ths", "II Thes"],
    "610": ["1 Timothy", "I Timothy", "1Ti", "1Tim", "I Ti", "I Tim"],
    "620": ["2 Timothy", "II Timothy", "2Ti", "2Tim", "II Ti", "II Tim"],
    "630": ["Titus", "Tit", "Tt"],
    "640": ["Philemon", "Phm", "Phlm"],
    "650": ["Hebrews", "Heb", "He"],
    "660": ["James", "Jas", "Jam", "Jms", "Ja"],
    "670": ["1 Peter", "I Peter", "1Pe", "1Pet", "1 Pt", "I Pe", "I Pet", "I Pt"],
    "680": ["2 Peter", "II Peter", "2Pe", "2Pet", "2 Pt", "II Pe", "II Pet", "II Pt"],
    "690": ["1 John", "I John", "1Jn", "I Jn"],
    "700": ["2 John", "II John", "2Jn", "II Jn"],
    "710": ["3 John", "III John", "3Jn", "III Jn"],
    "720": ["Jude", "Jud", "Jd"],
    "730": ["Revelation", "Apocalypse", "Rev", "Re", "Revel", "Apoc"],
    "780": ["Letter to the Laodiceans", "Laodiceans", "Lao"],
    "790": ["Prayer of Manasseh", "Man", "PrMan"]
}

# Format json data so that each key with its values are on the same separate line
def custom_json_dump(data):
    # Create a custom JSON string with each list on the same line as its key
    json_parts = []
    for key, value_list in data.items():
        values = ', '.join(json.dumps(v, ensure_ascii=False) for v in value_list)
        json_parts.append(f'  "{key}": [{values}]')
    return '{\n' + ',\n'.join(json_parts) + '\n}'

# Variables for prettier text in the console output
start_bold = "\033[1m"
start_lightgrey = "\033[0;37m"
start_lightblue = "\033[94m"
start_red = "\033[0;31m"
start_italics = "\033[3m"
reset_to_normal = "\033[0m"

def ensure_book_mapping_exists(json_file):
    """Check if the JSON file exists, and if not, write the default content to it."""
    if not os.path.exists(json_file):
        with open(json_file, 'w', encoding='utf-8') as file:
            json_data = custom_json_dump(DEFAULT_BOOK_MAPPING)
            file.write(json_data)

def load_mapping(json_file):
    """Load the book mapping from a JSON file."""
    with open(json_file, 'r', encoding='utf-8') as file:
        # return json.load(file)
        mapping = json.load(file)

        normalized_mapping = {}
        for book_number, names in mapping.items():
            normalized_mapping[book_number] = [normalize_book_name(name).lower() for name in names]

        return normalized_mapping

# Read config
def read_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as file:
            config = json.load(file)
    else:
        config = {'modules_path': ''}
        write_config(config)
    return config

# Write config
def write_config(config):
    config_path = get_default_config_path()
    if not os.path.exists(config_path):
        os.makedirs(config_path)
    with open(CONFIG_FILE, 'w', encoding='utf-8') as file:
        json.dump(config, file, ensure_ascii=False, indent=2)

# Check if folder with modules exists and if it contains sqlite3 files
def validate_path(path):
    return os.path.isdir(path) and any(fname.lower().endswith('.sqlite3') for fname in os.listdir(path))

# Get only sqlite3 files in the specified directory
def find_sqlite_files(path):
    return [f for f in os.listdir(path) if f.lower().endswith('.sqlite3')]

def get_file_hash(file_path):
    """Generate a hash for the file content."""
    hasher = hashlib.sha256()
    with open(file_path, 'rb') as file:
        buffer = file.read()
        hasher.update(buffer)
    return hasher.hexdigest()

def update_installed_modules_file(files_info):
    """Update the installed_modules.json file with the current file info."""
    with open(INSTALLED_MODULES_FILE, 'w', encoding='utf-8') as file:
        json_data = custom_json_dump(files_info)
        file.write(json_data)

def load_installed_modules_file():
    """Load the installed_modules.json file, if it exists."""
    if os.path.exists(INSTALLED_MODULES_FILE):
        with open(INSTALLED_MODULES_FILE, 'r', encoding='utf-8') as file:
            return json.load(file)
    return None

# Print all bible modules when -L or --list_modules is used
def list_sqlite_files(path, view):
    # Load installed modules info if available
    installed_modules = load_installed_modules_file()

    # Get current files
    files = find_sqlite_files(path)

    # Remove non-bible modules from the list
    files = [file for file in files if not any(sub in file for sub in ['crossreferences',
                                                                       'dictionary',
                                                                       'subheadings',
                                                                       'commentaries',
                                                                       'subheadings',
                                                                       'plan',
                                                                       'devotions',
                                                                       'dictionaries_lookup',
                                                                       'ReferenceData',
                                                                       ])]

    # Output with an extra line break and the number of installed modules
    def output_table(data, headers, files):
        print(available_modules.format(number = len(files)), "\n")
        print_table(data, headers)

    # Create a list of file names for comparison
    file_names = [os.path.basename(file) for file in files]

    # Check if installed_modules.json exists and contains the same files
    if installed_modules and set(file_names) == set(installed_modules.keys()):
        data = [installed_modules[file] for file in file_names]
        headers = ["Language", "Module", "Description"]
        data = sorted(data, key=lambda x: x[0])
        if view == 'fancy':
            output_table(data, headers, files)
        else:
            for bookinfo in data:
                print('\t'.join([element.replace('\n', ' ') for element in bookinfo]))
    else:
        # Collect new info from each module
        data = []
        headers = ["Language", "Module", "Description"]
        files_info = {}
        for file in files:
            module_path = os.path.join(path, file)
            name = os.path.splitext(os.path.basename(file))[0]
            description = get_info(module_path, 'description') if get_info(module_path, 'description') else "N/A"
            language = get_info(module_path, 'language') if get_info(module_path, 'language') else "N/A"
            module_info = [language, name, description]
            data.append(module_info)
            files_info[file] = module_info

        # Save new info to installed_modules.json
        update_installed_modules_file(files_info)

        # Print the collected data
        data = sorted(data, key=lambda x: x[0])
        if view == 'fancy':
            output_table(data, headers, files)
        else:
            for bookinfo in data:
                print('\t'.join([element.replace('\n', ' ') for element in bookinfo]))

# Get info (language and description) from the specified module
def get_info(module, field_name):
    # Connect to the SQLite database
    conn = sqlite3.connect(module)
    try:
        cur = conn.cursor()
        cur.execute("SELECT value FROM info WHERE name=?", (field_name,))
        value = cur.fetchone()
        if value:  # Check if a result was found
            return value[0]  # fetchone() returns a tuple, so get the first element
        else:
            return None  # No result found
    except sqlite3.OperationalError as e:
        return None
    finally:
        conn.close()

# Format long text by providing the width in characters
def wrap_text(text, width):
    # Split text into words
    words = text.split()
    wrapped_lines = []
    current_line = []
    current_length = 0

    for word in words:
        if current_length + len(word) + len(current_line) > width:
            wrapped_lines.append(" ".join(current_line))
            current_line = [word]
            current_length = len(word)
        else:
            current_line.append(word)
            current_length += len(word)

    if current_line:
        wrapped_lines.append(" ".join(current_line))

    return wrapped_lines

# Print table (used to list the available modules). max_width sets the formatting width
def print_table(data, headers, max_width=50):
    # Determine the width of each column
    column_widths = [len(header) for header in headers]
    for row in data:
        for i, cell in enumerate(row):
            wrapped_cell = wrap_text(str(cell), max_width)
            max_line_length = max(len(line) for line in wrapped_cell)
            column_widths[i] = max(column_widths[i], max_line_length)
    # Create format string for the table
    format_str = " ".join(["{{:<{}}}".format(width) for width in column_widths])
    separator = "〰".join(["〰" * width for width in column_widths])
    # Print the header
    print(format_str.format(*headers))
    print(separator)
    # Print the data rows
    for row in data:
        # Wrap text in each cell and print row by row
        wrapped_rows = [wrap_text(str(cell), max_width) for cell in row]
        max_lines = max(len(cell) for cell in wrapped_rows)

        for line_index in range(max_lines):
            line = [
                wrapped_rows[i][line_index] if line_index < len(wrapped_rows[i]) else ""
                for i in range(len(row))
            ]
            print(format_str.format(*line))
        print(separator)

def get_abbrs_file_path(module_name):
    """Return the path to the JSON file with book names for the given module name."""
    abbr_dir = os.path.join(get_default_config_path(), 'moduledata')
    if not os.path.exists(abbr_dir):
        os.makedirs(abbr_dir)
    return os.path.join(abbr_dir, f"{module_name}.abbr.json")

def guess_encoding_and_decode(data):
    # If the data is already a string, just return it
    if isinstance(data, str):
        return data, 'original'

    encodings = [
        'utf-8', 'cp1251', 'latin1', 'cp1252', 'iso-8859-1', 'iso-8859-2', 'iso-8859-5',
        'iso-8859-15', 'ascii', 'macroman', 'cp850', 'cp437', 'utf-16', 'utf-16le',
        'utf-16be', 'utf-32', 'utf-32le', 'utf-32be', 'big5', 'gb2312', 'gbk', 'gb18030',
        'shift_jis', 'euc-jp', 'euc-kr', 'iso-2022-jp', 'iso-2022-kr', 'iso-2022-cn',
        'koi8-r', 'koi8-u', 'cp1250', 'cp1253', 'cp1254', 'cp1255', 'cp1256', 'cp1257',
        'cp1258', 'cp852', 'cp866', 'cp874', 'iso-8859-3', 'iso-8859-4', 'iso-8859-6',
        'iso-8859-7', 'iso-8859-8', 'iso-8859-9', 'windows-1251', 'windows-1250',
        'windows-1253', 'windows-1254'
    ]

    for encoding in encodings:
        try:
            return data.decode(encoding), encoding
        except (UnicodeDecodeError, AttributeError):
            continue
    return data.decode('utf-8', errors='replace'), 'utf-8'  # Fallback to UTF-8 with error replacement

def extract_abbrs_to_json(module_path, output_path):
    """Extract verses from the module and write them to the specified JSON file."""
    abbrs = {}
    conn = sqlite3.connect(module_path)
    try:
        cur = conn.cursor()
        cur.execute("SELECT book_number, short_name, long_name FROM books")
        rows = cur.fetchall()
        for book_number, short_name, long_name in rows:
            book_str = str(book_number)
            short_str, short_encoding = guess_encoding_and_decode(short_name)
            long_str, long_encoding = guess_encoding_and_decode(long_name)
            abbrs[book_str] = [long_str, short_str]
    finally:
        conn.close()

    with open(output_path, 'w', encoding='utf-8') as file:
        json_data = custom_json_dump(abbrs)
        file.write(json_data)

def ensure_abbrs_file(module_name, module_path):
    """Ensure the the JSON file with book names exists for the given module."""
    abbrs_file_path = get_abbrs_file_path(module_name)
    if not os.path.exists(abbrs_file_path):
        extract_abbrs_to_json(module_path, abbrs_file_path)
    return abbrs_file_path

def get_allverses_file_path(module_name):
    """Return the path to the allverses JSON file for the given module name."""
    allverses_dir = os.path.join(get_default_config_path(), 'moduledata')
    if not os.path.exists(allverses_dir):
        os.makedirs(allverses_dir)
    return os.path.join(allverses_dir, f"{module_name}.allverses.json")

def extract_verses_to_json(module_path, output_path):
    """Extract verses from the module and write them to the specified JSON file."""
    verses_data = {}
    conn = sqlite3.connect(module_path)
    try:
        cur = conn.cursor()
        cur.execute("SELECT book_number, chapter, verse FROM verses")
        rows = cur.fetchall()
        for book_number, chapter, verse in rows:
            book_str = str(book_number)
            chapter_str = str(chapter)
            if book_str not in verses_data:
                verses_data[book_str] = {}
            if chapter_str not in verses_data[book_str]:
                verses_data[book_str][chapter_str] = 0
            verses_data[book_str][chapter_str] += 1
    finally:
        conn.close()

    with open(output_path, 'w', encoding='utf-8') as file:
        json.dump(verses_data, file, ensure_ascii=False, indent=2)

def ensure_allverses_file(module_name, module_path):
    """Ensure the allverses JSON file exists for the given module."""
    allverses_file_path = get_allverses_file_path(module_name)
    if not os.path.exists(allverses_file_path):
        extract_verses_to_json(module_path, allverses_file_path)
    return allverses_file_path

def load_verses_count(filename):
    with open(filename, 'r', encoding='utf-8') as file:
        return json.load(file)

# Helper function to get book number
def get_book_number(book_name, mapping):
    for book_number, names in mapping.items():
        for name in names:
            if book_name == normalize_book_name(name):
                return int(book_number)
    raise ValueError(f"Unknown book name: {book_name}")

# Helper function to get the last verse of a chapter
def get_last_verse(book_number, chapter, verses_count):
    return verses_count[str(book_number)].get(str(chapter), 1)

# Helper function to get the last chapter of a book
def get_last_chapter(book_number, verses_count):
    return max(int(chapter) for chapter in verses_count[str(book_number)].keys())

# Normalize book name by removing spaces and periods
def normalize_book_name(book_name):
    book_name = re.sub(r'[\u0020\u00A0\u1680\u2000-\u200A\u202F\u205F\u3000\u200B\u200C\u200D\u2060\uFEFF]+|\.', '', book_name)
    return book_name

# A reference could be copied from somewhere and contain different spaces and dashes.
def replace_funny_spaces(string):
    string = re.sub(r'[\u0020\u00A0\u1680\u2000-\u200A\u202F\u205F\u3000\u200B\u200C\u200D\u2060\uFEFF]+', ' ', string)
    string = re.sub(r'[\u2010\u2013\u2014-]', '-', string)
    string = re.sub(r'[\u2018\u2019\u201B\u2032\u02BC\u275C\uFF07\'`]', "'", string)
    return string

# Parse a reference part to get book, chapter, and verse
def parse_reference_part(part, mapping, verses_count, abbrs_mapping, prev_book=None, prev_chapter=None, prev_verse=None, prev_was_verse=False, book_explicit=False):
    tokens = part.strip().split()

    if not tokens:
        raise ValueError("Invalid reference format")

    book_number = None
    for i in range(len(tokens), 0, -1):
        possible_book_name = ' '.join(tokens[:i])
        possible_book_name_normalized = normalize_book_name(possible_book_name)
        try:
            book_number = get_book_number(possible_book_name_normalized, mapping)
            book_explicit = True
            tokens = tokens[i:]
            break
        except ValueError:
            continue

    if not book_number:
        if prev_book:
            book_number = prev_book
            book_explicit = False
        else:
            return invalid_reference, None, None, None, None, None

    if str(book_number) not in abbrs_mapping.keys():
        return invalid_reference, None, None, None, None, None

    chapter = None
    verse = None

    if tokens:
        chapter_verse = tokens[0]
        if ':' in chapter_verse:
            chapter, verse = map(int, chapter_verse.split(':'))
            prev_was_verse = True
        else:
            if book_number != prev_book or book_explicit:
                chapter = int(chapter_verse)
                verse = 1
                prev_was_verse = False
            elif prev_was_verse:
                verse = int(chapter_verse)
                chapter = prev_chapter
            else:
                chapter = int(chapter_verse)
    else:
        if book_number != prev_book or book_explicit:
            chapter = 1
            verse = 1
        else:
            if prev_chapter:
                chapter = prev_chapter
            else:
                chapter = 1
            if prev_verse:
                verse = prev_verse
            else:
                verse = 1

    if verse is None:
        verse = 1

    if chapter is None:
        chapter = 1

    if ':' in part:
        end_chapter = chapter
        end_verse = verse
        prev_was_verse = True
    else:
        if book_number != prev_book or book_explicit:
            if len(tokens) > 0:
                end_chapter = chapter
            else:
                end_chapter = get_last_chapter(book_number, verses_count)
            end_verse = get_last_verse(book_number, end_chapter, verses_count)
        else:
            if prev_was_verse:
                end_chapter = chapter
                end_verse = verse
            else:
                end_chapter = chapter
                end_verse = get_last_verse(book_number, chapter, verses_count)
                prev_was_verse = False

    return book_number, chapter, verse, end_chapter, end_verse, prev_was_verse

# Substitute semicolons with commas and the closest book name to the left
def substitute_semicolons(reference):
    parts = reference.split(';')
    if len(parts) == 1:
        return reference
    def is_letter(char):
        return unicodedata.category(char).startswith('L')
    pattern = r'^\d*\w+'
    book_names =[]
    new_reference = ''
    for index, part in enumerate(parts):
        part = part.strip()
        matches = re.findall(pattern, part)
        filtered_matches = [match for match in matches if is_letter(match[-1])]
        if filtered_matches:
            book_names.append(filtered_matches[-1])
            new_reference += f"{part}, "
        else:
            book_name = book_names[index-1]
            book_names.append(book_name)
            new_reference += f"{book_name} {part}, "
    new_reference = new_reference.strip()[:-1]
    return new_reference

# Calculate the range
def parse_range(reference, mapping, verses_count, abbrs_mapping):
    reference = substitute_semicolons(reference)
    parts = reference.split(',')
    ranges = []
    prev_end_book = prev_end_chapter = prev_end_verse = None
    start_book = start_chapter = start_verse = end_book = end_chapter = end_verse = None
    prev_was_verse = False
    book_explicit = False

    for part in parts:
        subranges = part.split('-')
        subrange_results = []

        for i, subrange in enumerate(subranges):
            if i == 0:
                result = parse_reference_part(subrange, mapping, verses_count, abbrs_mapping, prev_end_book, prev_end_chapter, prev_end_verse, prev_was_verse)
                if result[0] == invalid_reference:
                    return invalid_reference
                start_book, start_chapter, start_verse, end_chapter, end_verse, prev_was_verse = result
            else:
                if ' ' in subrange or subrange.isalpha():
                    result = parse_reference_part(subrange, mapping, verses_count, abbrs_mapping)
                    if result[0] == invalid_reference:
                        return invalid_reference
                    start_book, start_chapter, start_verse, end_chapter, end_verse, prev_was_verse = result
                else:
                    start_book = prev_end_book
                    if ':' in subrange:
                        chapter, verse = map(int, subrange.split(':'))
                        start_chapter = end_chapter = chapter
                        start_verse = end_verse = verse
                        prev_was_verse = True
                    else:
                        number = int(subrange)
                        if start_book != prev_end_book or book_explicit:
                            start_chapter = number
                            start_verse = 1
                            end_chapter = get_last_chapter(start_book, verses_count)
                            end_verse = get_last_verse(start_book, end_chapter, verses_count)
                            prev_was_verse = False
                        else:
                            if prev_was_verse:
                                start_chapter = prev_end_chapter
                                start_verse = end_verse = number
                            else:
                                start_chapter = end_chapter = number
                                start_verse = 1
                                end_verse = get_last_verse(start_book, number, verses_count)
                                prev_was_verse = False

            subrange_results.append({
                "start": {"book": start_book, "chapter": start_chapter, "verse": start_verse},
                "end": {"book": start_book, "chapter": end_chapter, "verse": end_verse}
            })
            prev_end_book, prev_end_chapter, prev_end_verse = start_book, end_chapter, end_verse

        if subrange_results:
            ranges.append({
                "start": subrange_results[0]["start"],
                "end": subrange_results[-1]["end"]
            })

    return ranges

def calculate_verses_in_range(ranges, allverses_data):
    def verses_in_book(book, start_chapter=1, start_verse=1, end_chapter=None, end_verse=None):
        total_verses = 0
        chapters = allverses_data[str(book)]

        if end_chapter is None:
            end_chapter = max(int(ch) for ch in chapters.keys())
        if end_verse is None:
            end_verse = chapters[str(end_chapter)]

        for chapter in range(start_chapter, end_chapter + 1):
            chapter_str = str(chapter)
            if chapter == start_chapter and chapter == end_chapter:
                total_verses += end_verse - start_verse + 1
            elif chapter == start_chapter:
                total_verses += chapters[chapter_str] - start_verse + 1
            elif chapter == end_chapter:
                total_verses += end_verse
            else:
                total_verses += chapters[chapter_str]

        return total_verses

    verses_counts = []

    for range_ in ranges:
        start = range_['start']
        end = range_['end']

        if start['book'] == end['book']:
            verses_count = verses_in_book(start['book'], start['chapter'], start['verse'], end['chapter'], end['verse'])
        else:
            total_verses = 0
            total_verses += verses_in_book(start['book'], start['chapter'], start['verse'])
            current_book = start['book'] + 1

            while current_book < end['book']:
                if str(current_book) in allverses_data:
                    total_verses += verses_in_book(current_book)
                current_book += 1

            total_verses += verses_in_book(end['book'], 1, 1, end['chapter'], end['verse'])
            verses_count = total_verses

        verses_counts.append(verses_count)

    return verses_counts

def query_verses(module_path, ranges):
    conn = sqlite3.connect(module_path)
    cur = conn.cursor()

    def query_single_verse(book, chapter, verse):
        cur.execute("""
            SELECT book_number, chapter, verse, text
            FROM verses
            WHERE book_number=? AND chapter=? AND verse=?
            ORDER BY book_number, chapter, verse
        """, (book, chapter, verse))
        return cur.fetchall()

    def query_multi_verse(book, start_chapter, start_verse, end_chapter=None, end_verse=None):
        if end_chapter is None:
            end_chapter = start_chapter
        if end_verse is None:
            end_verse = start_verse

        cur.execute("""
            SELECT book_number, chapter, verse, text
            FROM verses
            WHERE book_number=? AND (chapter > ? OR (chapter = ? AND verse >= ?))
            AND (chapter < ? OR (chapter = ? AND verse <= ?))
            ORDER BY book_number, chapter, verse
        """, (book, start_chapter, start_chapter, start_verse, end_chapter, end_chapter, end_verse))
        return cur.fetchall()

    def query_book(book):
        cur.execute("""
            SELECT book_number, chapter, verse, text
            FROM verses
            WHERE book_number=?
            ORDER BY book_number, chapter, verse
        """, (book,))
        return cur.fetchall()

    verses_data = []

    for range_ in ranges:
        start = range_['start']
        end = range_['end']

        if start['book'] == end['book']:
            verses_data.extend(query_multi_verse(start['book'], start['chapter'], start['verse'], end['chapter'], end['verse']))
        else:
            # Query from start verse to the end of the start book
            verses_data.extend(query_multi_verse(start['book'], start['chapter'], start['verse']))

            # Query all intermediate books
            current_book = start['book'] + 1
            while current_book < end['book']:
                verses_data.extend(query_book(current_book))
                current_book += 1

            # Query from start of end book to the end verse
            verses_data.extend(query_multi_verse(end['book'], 1, 1, end['chapter'], end['verse']))

    conn.close()
    return verses_data

def format_output(format_string, data, abbrs_file_path, module_name):
    # Define the mapping for known format specifiers
    book_number = data[0]
    chapter = data[1]
    verse = data[2]
    raw_text = data[3]
    format_map = {
        '%b': book_number,
        '%c': chapter,
        '%v': verse,
        '%T': raw_text,
        '%m': module_name
    }

    # Replace format specifiers in the format_string
    result = format_string
    for key, value in format_map.items():
        if key in result:
            result = result.replace(key, str(value))

    book_names = get_book_name(abbrs_file_path, book_number)
    # Handle custom format specifiers
    result = result.replace('%f', book_names[0])  # full book name
    result = result.replace('%a', book_names[1])  # abbreviated book name
    result = result.replace('%z', zap_full(raw_text))
    result = result.replace('%t', zap_text(raw_text))
    result = result.replace('%A', ansi_format_text(raw_text))
    result = result.replace('%Z', ansi_format_no_strong(raw_text))
    result = re.sub(r'\\t', '\t', result)
    result = re.sub(r'\\n', '\n', result)

    return result

def get_book_name(abbrs_file_path, book_number):
    with open(abbrs_file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    values = data.get(str(book_number))
    if values is not None:
        return values
    else:
        return book_number

def remove_ansi_esc_seq(string):
    ansi_escape = re.compile(r'\x1B\[[0-9;]*[mK]')
    return ansi_escape.sub('', string)

def zap_text(string):
    """Remove everything from the verse except the actual biblical text"""
    paragraph_break = r'<pb/>'
    line_break = r'<br/>'
    strong_numbers = r'<([SGH])>[^>]*</\1>'
    j_words = r'</?J>'
    note_markers = r'</?n>'
    emph_markers = r'</?e>'
    insert_markers = r'</?i>'
    footnotes = r'<f>\[[^\]]*\]</f>'
    headings = r'<h>[^>]*</h>'
    indent_end = r'</t>'
    indent_begin = r'<t>'

    string = re.sub(paragraph_break, '\n', string).strip()
    string = re.sub(line_break, '\n', string).strip()
    string = re.sub(strong_numbers, '', string)
    string = re.sub(j_words, '', string)
    string = re.sub(note_markers, '', string)
    string = re.sub(emph_markers, '', string)
    string = re.sub(insert_markers, '', string)
    string = re.sub(footnotes, '', string)
    string = re.sub(headings, '', string)
    string = re.sub(indent_end, '', string)
    string = re.sub(indent_begin, '\n    ', string)

    return string

def zap_full(string):
    string =  zap_text(string)

    notes = r'\{[^}]*\}'
    line_break = r'\n'
    multiple_spaces =r'\s+'

    string = re.sub(notes, '', string)
    string = re.sub(line_break, '', string)
    string = re.sub(multiple_spaces, ' ', string)

    return string.strip()

def ansi_format_text(string):
    """Format text with ANSI escape sequences for pretty console output"""
    paragraph_break = r'<pb/>'
    line_break = r'<br/>'
    strong_begin = r'<([SGH])>'
    strong_end = r'</[SGH]>'
    j_words_begin = r'<J>'
    j_words_end = r'</J>'
    note_begin = r'<n>'
    note_end = r'</n>'
    emph_begin = r'<e>'
    emph_end = r'</e>'
    insert_begin = r'<i>'
    insert_end = r'</i>'
    footnotes = r'<f>\[\d+\]</f>'
    headings = r'<h>[^>]*</h>'
    indent_end = r'</t>'
    indent_begin = r'<t>'

    string = re.sub(paragraph_break, '\n', string).strip()
    string = re.sub(line_break, '\n', string).strip()
    string = re.sub(strong_begin, rf'{start_lightblue}{start_italics}<\1', string)
    string = re.sub(strong_end, f'>{reset_to_normal}', string)
    string = re.sub(j_words_begin, f'{start_red}', string)
    string = re.sub(j_words_end, f'{reset_to_normal}', string)
    string = re.sub(note_begin, f'{start_lightgrey}{start_italics}', string)
    string = re.sub(note_end, f'{reset_to_normal}', string)
    string = re.sub(emph_begin, f'{start_bold}', string)
    string = re.sub(emph_end, f'{reset_to_normal}', string)
    string = re.sub(insert_begin, f'{start_italics}', string)
    string = re.sub(insert_end, f'{reset_to_normal}', string)
    string = re.sub(footnotes, '', string)
    string = re.sub(headings, '', string)
    string = re.sub(indent_end, '', string)
    string = re.sub(indent_begin, '\n    ', string)

    return string

def ansi_format_no_strong(string):
    """Remove Strong's numbers from console output with ANSI escape sequences"""
    string = ansi_format_text(string)
    strong_number = re.compile(r'\x1B\[94m\x1B\[3m<[SGH][^>]*>\x1B\[0m')

    string = strong_number.sub('', string)

    return string

def open_folder(folder_path):
    try:
        if os.name == 'nt':  # Windows
            os.startfile(folder_path)
        elif 'darwin' in os.sys.platform:  # macOS
            subprocess.run(['open', folder_path], check=True)
        else:  # Linux and other Unix-like OS
            subprocess.run(['xdg-open', folder_path], check=True)
    except Exception as e:
        print(f"{error}", folder_fail.format(error = str(e)))

def json_to_tsv(json_file):
    if not os.path.exists(json_file):
        print(file_fail.format(file=json_file))
        return
    else:
        tsv_lines = []
        with open(json_file, 'r', encoding='utf-8') as file:
            json_data = json.load(file)
            for key, values in json_data.items():
                tsv_line = f"{key}\t" + "\t".join(values)
                tsv_lines.append(tsv_line)
        tsv_string = "\n".join(tsv_lines)
    directory = os.path.dirname(os.path.abspath(json_file))
    filename = os.path.splitext(os.path.basename(json_file))[0]
    tsv_file = os.path.join(directory, f"{filename}.tsv")

    if os.path.exists(tsv_file):
        if not ask_to_overwrite(tsv_file):
            return
    with open(tsv_file, 'w', encoding='utf-8') as file:
        file.write(tsv_string)

    return tsv_file

def show_tsv_duplicates(tsv_file):
    line_maps = []
    global_duplicates = {}  # Use a regular dictionary

    if os.path.exists(tsv_file):
        # Read the TSV file and collect the cells in each line as a map
        with open(tsv_file, newline='', encoding='utf-8') as file:
            reader = csv.reader(file, delimiter='\t')

            for line_number, row in enumerate(reader, start=1):
                line_map = {i: element for i, element in enumerate(row, start=1)}
                line_maps.append((line_number, line_map))

                # Check for duplicates within the same line
                line_duplicates = [value for value in line_map.values() if list(line_map.values()).count(value) > 1]
                if line_duplicates:
                    print(repeated_in_line.format(row=line_number, repeated_string=f"{', '.join(set(line_duplicates))}"))

                # Add elements to the global duplicates map
                for element in line_map.values():
                    if element in global_duplicates:
                        global_duplicates[element].append(line_number)
                    else:
                        global_duplicates[element] = [line_number]

        # Check for duplicates across different lines
        for element, lines in global_duplicates.items():
            if len(lines) > 1:
                print(repeated_in_file.format(element=element, rows=f"{', '.join(map(str, lines))}"))
    else:
        print(file_fail.format(file=tsv_file))

def tsv_to_json(tsv_file):
    if not os.path.exists(tsv_file):
        print(file_fail.format(file=tsv_file))
    else:
        tsv_lines = []
        with open(tsv_file, 'r', newline='', encoding='utf-8') as file:
            reader = csv.reader(file, delimiter='\t')
            for row in reader:
                tsv_cells = [cell for cell in row if cell.strip()]
                tsv_lines.append(tsv_cells)

        json_data = {}
        for line in tsv_lines:
            if line:
                key = line[0]
                values = line[1:]
                json_data[key] = values
        json_data = custom_json_dump(json_data)
        directory = os.path.dirname(os.path.abspath(tsv_file))
        filename = os.path.splitext(os.path.basename(tsv_file))[0]
        json_file = os.path.join(directory, f"{filename}.json")

        if os.path.exists(json_file):
            if not ask_to_overwrite(json_file):
                return
        with open(json_file, 'w', encoding='utf-8') as file:
            file.write(json_data)

    return tsv_file

def ask_to_overwrite(file):
    while True:
        response = input(file_exists_prompt.format(file=file)).strip().lower()
        if response in ["yes", "y"]:
            return True
        elif response in ["no", "n"]:
            return False
        else:
            print(yes_no_prompt)

def main():
    parser = argparse.ArgumentParser(
        description = help_description,
        epilog=help_epilog.format(bold=start_bold, normal=reset_to_normal)
    )
    parser.add_argument(
        "-p", "--path",
        help=help_path
    )
    parser.add_argument(
        "-L", "--list-modules",
        action="store_true",
        help=help_list
    )
    parser.add_argument(
        "--simple-list",
        action="store_true",
        help=help_simplelist
    )
    parser.add_argument(
        "-m", "--module-name",
        help=help_modulename
    )
    parser.add_argument(
        "-r", "--reference",
        help=help_reference
    )
    parser.add_argument(
        "-a", "--abbr",
        help=help_abbr.format(bold=start_bold, italics=start_italics, normal=reset_to_normal)
    )
    parser.add_argument(
        "-A", "--self-abbr",
        action="store_true",
        help=help_selfabbr
    )
    parser.add_argument(
        "-f", "--format",
        help=help_format
    )
    parser.add_argument(
        "-F", "--save-format",
        help=help_saveformat
    )
    parser.add_argument(
        "--helpformat",
        action="store_true",
        help=help_helpformat
    )
    parser.add_argument(
        "--noansi",
        action='store_true',
        help=help_noansi
    )
    parser.add_argument(
        "--open-config-folder",
        action='store_true',
        help=help_open_config
    )
    parser.add_argument(
        "--open-module-folder",
        action='store_true',
        help=help_open_module
    )
    parser.add_argument(
        "--j2t", "--json-to-tsv",
        help=help_j2t
    )
    parser.add_argument(
        "--check-tsv",
        help=help_checktsv
    )
    parser.add_argument(
        "--t2j", "--tsv-to-json",
        help=help_t2j
    )

    args = parser.parse_args()

    # Check config file existence and update path if needed
    config = read_config()

    # Determine the path to the modules
    def resolve_home(path):
        """Resolve '~' or '$HOME'"""
        path = os.path.expanduser(path)
        home = os.getenv('HOME')
        if home:
            path = path.replace('$HOME', home)
        return path

    modules_path = args.path if args.path else config.get('modules_path', '')
    valid_path = validate_path(modules_path)
    if not valid_path and not any([args.helpformat, args.open_config_folder, args.j2t, args.t2j, args.check_tsv]):
        # Validate the path to the modules (if -p is specified or no/wrong value is recorded in the config)
        while not validate_path(modules_path):
            if not os.path.isdir(modules_path):
                print(invalid_path.format(modules_path=modules_path))
            elif not find_sqlite_files(modules_path):
                print(empty_path.format(modules_path=modules_path))
            input_path = input(in_path).strip()
            modules_path = resolve_home(input_path)

            # Save the valid path to the config file
        config['modules_path'] = modules_path
        write_config(config)

    # Check for the default json file with book names and abbreviations
    ensure_book_mapping_exists(BOOKMAPPING_FILE)

    # Handle the --list-modules argument
    if args.list_modules:
        list_sqlite_files(modules_path, 'fancy')
        return

    # Handle the --simple-list argument
    if args.simple_list:
        list_sqlite_files(modules_path, 'simple')
        return

    # Handle the --open-config-folder argument
    if args.open_config_folder:
        open_folder(get_default_config_path())
        return

    # Handle the --open-module-folder argument
    if args.open_module_folder:
        open_folder(modules_path)
        return

    # Handle the --json-to-tsv argument
    if args.j2t:
        json_file = args.j2t
        tsv_file = json_to_tsv(json_file)
        print(file_created.format(file=tsv_file))
        return

    # Handle the --check-tsv argument
    if args.check_tsv:
        tsv_file = args.check_tsv
        show_tsv_duplicates(tsv_file)
        return

    # Handle the --t2j argument
    if args.t2j:
        tsv_file = args.t2j
        json_file = tsv_to_json(tsv_file)
        print(file_created.format(file=json_file))
        return

    # Handle the --format argument
    format_string = None
    if args.format:
        format_string = args.format
    if not format_string:
        format_string = config.get('format_string') if config.get('format_string') else "%f %c:%v: %t (%m)"

    # Handle the --save-format argument
    if args.save_format:
        format_string = args.save_format
        config['format_string'] = format_string
        write_config(config)

    #Handle --helpformat argument
    if args.helpformat:
        helpformat_message = textwrap.dedent(
            help_helpformat_message.format(bold=start_bold, normal=reset_to_normal, format_string=format_string)
        )
        print(helpformat_message)
        return

    # Ensure required arguments if --list-modules is not used
    def report_args_error():
        parser.error(parser_error)

    # Handle the --module_name argument
    if args.module_name:
        module_name = args.module_name
        module_file = None
        for file in find_sqlite_files(modules_path):
            if os.path.splitext(file)[0].lower() == module_name.lower():
                module_file = file
                break
        if not module_file:
            print(no_module.format(module_name=module_name, modules_path=modules_path))
            return
        module_path = os.path.join(modules_path, module_file)
    else:
        report_args_error()
        return

    # Handle the --abbr argument (non-default mapping of book names and abbreviations for the reference)
    if args.abbr:
        mapping_file = os.path.join(get_default_config_path(), f'{args.abbr}_mapping.json')
    else:
        mapping_file = BOOKMAPPING_FILE

    # Handle the --self-abbr argument (book names and abbreviations for the reference are taken from the module)
    if args.self_abbr:
        mapping_file = ensure_abbrs_file(module_name, module_path)
        if not os.path.exists(mapping_file):
            mapping_file = BOOKMAPPING_FILE

    # Handle the --reference argument
    if args.reference:
        reference = replace_funny_spaces(args.reference).lower()
        allverses_file_path = ensure_allverses_file(module_name, module_path)
        abbrs_file_path = ensure_abbrs_file(module_name, module_path)
        verses_count = load_verses_count(allverses_file_path)
        ranges = parse_range(reference, load_mapping(mapping_file), verses_count, load_mapping(abbrs_file_path))
        if isinstance(ranges, str) and ranges == invalid_reference:
            print(no_verse_ouput.format(bold=start_bold, reference=reference, normal=reset_to_normal), ranges.lower())
            return
        number_of_verses = calculate_verses_in_range(ranges, verses_count)
        verses_data = query_verses(module_path, ranges)
        for verse in verses_data:
            formatted_output = format_output(format_string, verse, abbrs_file_path, module_name)
            if args.noansi:
                formatted_output = remove_ansi_esc_seq(formatted_output)
            print(formatted_output)
            continue
    else:
        report_args_error()
        return

    if not args.module_name or not args.reference:
        report_args_error()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(exit_now)

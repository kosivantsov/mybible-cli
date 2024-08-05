#!/usr/bin/env python3
import argparse
import json
import os
import sqlite3
import hashlib
import re
import unicodedata
import textwrap

# Repeated strings
INVALID_PATH = "\nDirectory does not exist:"
EMPTY_PATH = "\nNo MyBible modules found in"
INPUT_PATH = "\nFull path to the folder with MyBible modules:\n"

# Config location (APP_NAME) is a folder name under ~/.config
APP_NAME = 'mybible-cli'

def get_default_config_path():
    if os.name == 'nt':
        return os.path.join(os.getenv('APPDATA'), APP_NAME)
    elif os.name == 'posix':
        if 'darwin' in os.sys.platform:
            return os.path.join(os.path.expanduser('~'), 'Library', 'Application Support', APP_NAME)
        else:
            return os.path.join(os.path.expanduser('~'), '.config', APP_NAME)

CONFIG_FILE = os.path.join(get_default_config_path(), 'config.json')
BOOKMAPPING_FILE = os.path.join(get_default_config_path(), 'mapping.json')
INSTALLED_MODULES_FILE = os.path.join(get_default_config_path(), 'installed_modules.json')

# Default book mapping content
DEFAULT_BOOK_MAPPING = \
{
    "10": ["Genesis", "Gen", "Ge", "Gn"],
    "20": ["Exodus", "Exo", "Ex", "Exod"],
    "30": ["Leviticus", "Lev", "Lv", "Le"],
    "40": ["Numbers", "Num", "Nu", "Nm", "Nb"],
    "50": ["Deuteronomy", "Deu", "Dt", "Deut"],
    "60": ["Joshua", "Josh", "Jos", "Jsh"],
    "70": ["Judges", "Judg", "Jdg", "Jdgs"],
    "80": ["Ruth", "Ruth", "Ru", "Rth"],
    "90": ["1 Samuel", "1Sam", "1 Sm", "1 Sa", "1 S", "I Sam", "I Sm", "I Sa", "I S"],
    "100": ["2 Samuel", "2Sam", "2 Sm", "2 Sa", "2 S", "II Sam", "II Sm", "II Sa", "II S"],
    "110": ["1 Kings", "1Kin", "1 Ki", "1 Kgs", "1K", "I Kin", "I Ki", "I Kgs", "I K"],
    "120": ["2 Kings", "2Kin", "2 Ki", "2 Kgs", "2K", "II Kin", "II Ki", "II Kgs", "II K"],
    "130": ["1 Chronicles", "1Chr", "1 Ch", "1 Chron", "I Chr", "I Ch", "I Chron"],
    "140": ["2 Chronicles", "2Chr", "2 Ch", "2 Chron", "II Chr", "II Ch", "II Chron"],
    "150": ["Ezra", "Ezr", "Ez"],
    "160": ["Nehemiah", "Neh", "Ne"],
    "190": ["Esther", "Esth", "Es", "Est"],
    "220": ["Job", "Job", "Jb"],
    "230": ["Psalm", "Ps", "Pslm", "Psa", "Pss"],
    "240": ["Proverbs", "Prov", "Prv", "Pr", "Pro"],
    "250": ["Ecclesiastes", "Eccl", "Ecc", "Qoh"],
    "260": ["Song of Solomon", "Song", "Sg", "SOS", "Cant"],
    "290": ["Isaiah", "Isa", "Is"],
    "300": ["Jeremiah", "Jer", "Je", "Jr"],
    "310": ["Lamentations", "Lam", "La"],
    "330": ["Ezekiel", "Ezek", "Eze", "Ezk"],
    "340": ["Daniel", "Dan", "Da", "Dn"],
    "350": ["Hosea", "Hos", "Ho"],
    "360": ["Joel", "Joel", "Jl"],
    "370": ["Amos", "Am", "Amo"],
    "380": ["Obadiah", "Oba", "Ob", "Obad"],
    "390": ["Jonah", "Jona", "Jon"],
    "400": ["Micah", "Mic", "Mi", "Mc"],
    "410": ["Nahum", "Nah", "Na"],
    "420": ["Habakkuk", "Hab", "Hb"],
    "430": ["Zephaniah", "Zeph", "Zep", "Zp"],
    "440": ["Haggai", "Hag", "Hg"],
    "450": ["Zechariah", "Zech", "Zec", "Zch"],
    "460": ["Malachi", "Mal", "Ml"],
    "470": ["Matthew", "Mat", "Mt", "Matt"],
    "480": ["Mark", "Mar", "Mk", "Mrk"],
    "490": ["Luke", "Luk", "Lk"],
    "500": ["John", "John", "Jn", "Jhn"],
    "510": ["Acts", "Acts", "Ac", "Act"],
    "520": ["Romans", "Rom", "Ro", "Rm"],
    "530": ["1 Corinthians", "1Cor", "1 Co", "1Cor", "I Cor", "I Co", "I Cor"],
    "540": ["2 Corinthians", "2Cor", "2 Co", "2Cor", "II Cor", "II Co", "II Cor"],
    "550": ["Galatians", "Gal", "Ga"],
    "560": ["Ephesians", "Eph", "Eph"],
    "570": ["Philippians", "Phil", "Php", "Phlp"],
    "580": ["Colossians", "Col", "Co"],
    "590": ["1 Thessalonians", "1Ths", "1 Th", "I Thes", "I Th", "I Thess"],
    "600": ["2 Thessalonians", "2Ths", "2 Th", "II Thes", "II Th", "II Thess"],
    "610": ["1 Timothy", "1Tim", "1 Ti", "I Tim", "I Ti"],
    "620": ["2 Timothy", "2Tim", "2 Ti", "II Tim", "II Ti"],
    "630": ["Titus", "Tit", "Tt"],
    "640": ["Philemon", "Phlm", "Phm"],
    "650": ["Hebrews", "Heb", "He"],
    "660": ["James", "Jam", "Jas", "Ja"],
    "670": ["1 Peter", "1Pet", "1 Pe", "1 Pt", "I Pet", "I Pe", "I Pt"],
    "680": ["2 Peter", "2Pet", "2 Pe", "2 Pt", "II Pet", "II Pe", "II Pt"],
    "690": ["1 John", "1Jn", "1 Jn", "I Jn"],
    "700": ["2 John", "2Jn", "2 Jn", "II Jn"],
    "710": ["3 John", "3Jn", "3 Jn", "III Jn"],
    "720": ["Jude", "Jud", "Jd"],
    "730": ["Revelation", "Rev", "Re", "Revel", "Apoc"],
    "323": ["Song of the Three Young Men", "Sg3", "S3Y"],
    "165": ["1 Esdras", "1Esd", "I Esd"],
    "170": ["Tobit", "Tob", "Tob"],
    "180": ["Judith", "Jdt", "Jdth"],
    "192": ["Greek Esther", "EstGr", "GrEsth"],
    "232": ["Psalm 151", "Ps151"],
    "270": ["Wisdom", "Wis", "Wisd"],
    "280": ["Sirach", "Sir", "Ecclus"],
    "305": ["Prayer of Azariah", "PrAz", "Azar"],
    "315": ["Letter of Jeremiah", "EpJer", "LetJer"],
    "320": ["Baruch", "Bar", "Br"],
    "325": ["Susanna", "Sus", "Sus"],
    "345": ["Bel and the Dragon", "Bel"],
    "462": ["1 Maccabees", "1Mac", "I Mac"],
    "464": ["2 Maccabees", "2Mac", "II Mac"],
    "466": ["3 Maccabees", "3Mac", "III Mac"],
    "467": ["4 Maccabees", "4Mac", "IV Mac"],
    "468": ["2 Esdras", "2Esd", "II Esd"],
    "790": ["Prayer of Manasseh", "PrMan"],
    "780": ["Laodiceans", "Lao"]
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
    with open(json_file, 'r') as file:
        return json.load(file)

# Read config
def read_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as file:
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
        with open(INSTALLED_MODULES_FILE, 'r') as file:
            return json.load(file)
    return None

# Print all bible modules when -L or --list_modules is used
def list_sqlite_files(path):
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
        print(f"\nAvailable MyBible modules ({len(files)}):\n")
        print_table(data, headers)

    # Create a list of file names for comparison
    file_names = [os.path.basename(file) for file in files]

    # Check if installed_modules.json exists and contains the same files
    if installed_modules and set(file_names) == set(installed_modules.keys()):
        data = [installed_modules[file] for file in file_names]
        headers = ["Language", "Module", "Description"]
        data = sorted(data, key=lambda x: x[0])
        # print_table(data, headers)
        output_table(data, headers, files)
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
        output_table(data, headers, files)

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
            short_str = str(short_name)
            long_str = str(long_name)
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
    with open(filename, 'r') as file:
        return json.load(file)

# Helper function to get book number
def get_book_number(book_name, mapping):
    for book_number, names in mapping.items():
        if book_name in names:
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
    return re.sub(r'\s+|\.', '', book_name)

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
            return "Invalid reference for this module", None, None, None, None, None

    if str(book_number) not in abbrs_mapping.keys():
        return "Invalid reference for this module", None, None, None, None, None

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
                if result[0] == "Invalid reference for this module":
                    return "Invalid reference for this module"
                start_book, start_chapter, start_verse, end_chapter, end_verse, prev_was_verse = result
            else:
                if ' ' in subrange or subrange.isalpha():
                    result = parse_reference_part(subrange, mapping, verses_count, abbrs_mapping)
                    if result[0] == "Invalid reference for this module":
                        return "Invalid reference for this module"
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
            result = re.sub(r'\\t', '\t', result)
            result = re.sub(r'\\n', '\n', result)

    book_names = get_book_name(abbrs_file_path, book_number)
    # Handle custom format specifiers
    result = result.replace('%f', book_names[0])  # full book name
    result = result.replace('%a', book_names[1])  # abbreviated book name
    result = result.replace('%z', zap_full(raw_text))
    result = result.replace('%t', zap_text(raw_text))
    result = result.replace('%A', ansi_format_text(raw_text))
    result = result.replace('%Z', ansi_format_no_strong(raw_text))

    return result

def get_book_name(abbrs_file_path, book_number):
    with open(abbrs_file_path, 'r') as file:
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
    strong_numbers = r'<([SGH])>\d+</\1>'
    j_words = r'</?J>'
    note_markers = r'</?n>'
    emph_markers = r'</?e>'
    insert_markers = r'</?i>'
    footnotes = r'<f>\[\d+\]</f>'
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
    """Remove Strong numbers from console output with ANSI escape sequences"""
    string = ansi_format_text(string)
    strong_number = re.compile(r'\x1B\[94m\x1B\[3m<[SGH][^>]*>\x1B\[0m')

    string = strong_number.sub('', string)

    return string

def main():
    parser = argparse.ArgumentParser(
        description="Command line tool to query MyBible modules.",
        epilog=f"Any parameter containing spaces should be quoted: {start_bold}mybible-cli -b \"NIV'11\" -r \"1 Pet 1:1\"{reset_to_normal}"
    )
    parser.add_argument(
        "-p", "--path",
        help="path to the folder with MyBible modules"
    )
    parser.add_argument(
        "-L", "--list-modules",
        action="store_true",
        help="list available MyBilbe modules"
    )
    parser.add_argument(
        "-m", "--module_name",
        help="name of the MyBible module to use"
    )
    parser.add_argument(
        "-r", "--reference",
        help="Bible reference to output"
    )
    parser.add_argument(
        "-a", "--abbr",
        help=f"read Bible book names and abbreviations from a non-default file. \
        With {start_bold}{start_italics}--abbr rst{reset_to_normal} \
        a file named {start_bold}{start_italics}rst_mapping.json{reset_to_normal} \
        located in the configuration folder will be used"
    )
    parser.add_argument(
        "-f", "--format",
        help="format output with %%-prefixed format sting. \
        Available format strings: f, a, c, v, t, T, z, A, Z, m"
    )
    parser.add_argument(
        "--helpformat",
        action="store_true",
        help="detailed info on available format strings"
    )
    parser.add_argument(
        "--noansi",
        action='store_true',
        help="clears out any ANSI escape sequences in the Bible verses output (if %%A or %%Z were used)"
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
    if args.path or not modules_path:
        # Validate the path to the modules (if -p is specified or no/wrong value is recorded in the config)
        while not validate_path(modules_path):
            if not os.path.isdir(modules_path):
                print(f"{INVALID_PATH} {modules_path}")
            elif not find_sqlite_files(modules_path):
                print(f"{EMPTY_PATH} {modules_path}")
            input_path = input(INPUT_PATH).strip()
            modules_path = resolve_home(input_path)

            # Save the valid path to the config file
        config['modules_path'] = modules_path
        write_config(config)

    # Check for the default json file with book names and abbreviations
    ensure_book_mapping_exists(BOOKMAPPING_FILE)

    # Handle the --list-modules argument
    if args.list_modules:
        list_sqlite_files(modules_path)
        return

    #Handle --helpformat argument
    if args.helpformat:
        helpformat_message = textwrap.dedent("\n\
            Available format strings:\n\
            \t  %f \t full book name\n\
            \t  %a \t abbreviated book name\n\
            \t  %b \t book number as per MyBible format specifications\n\
            \t  %c \t chapter number\n\
            \t  %v \t verse number\n\
            \t  %T \t raw text of the verse from the module\n\
            \t  %t \t text of the verse without markers; notes and line breaks are kept\n\
            \t  %z \t the same as above, but without notes and line breaks\n\
            \t  %A \t text of the verse with color output for console; Strong numbers are included\n\
            \t  %Z \t the same as above, but without Strong numbers\n\
            \t  %m \t module name\n\
            Default format is '%f %c:%v: %t (%m)'\n\
            Each verse in the output is printed on a new line and is formatted individually."
        )
        print(helpformat_message)
        return
    # Determine book numbers to resolve the reference based on non-default file
    if args.abbr:
        mapping_file = os.path.join(get_default_config_path(), f'{args.abbr}_mapping.json')
    else:
        mapping_file = BOOKMAPPING_FILE

    # Ensure required arguments if --list-modules is not used
    def report_args_error():
        parser.error('The arguments -b/--module_name and -r/--reference are required unless -L/--list-modules is used.')

    # Handle the --format argument
    format_string = None
    if args.format:
        format_string = args.format
    if not format_string:
        format_string = "%f %c:%v: %t (%m)"

        # Handle the --module_name argument
    if args.module_name:
        module_name = args.module_name
        module_file = None
        for file in find_sqlite_files(modules_path):
            if os.path.splitext(file)[0].lower() == module_name.lower():
                module_file = file
                break
        if not module_file:
            print(f"No module named '{module_name}' found in '{modules_path}'.")
            return
        module_path = os.path.join(modules_path, module_file)
    else:
        report_args_error()
        return

    # Handle the --reference argument
    if args.reference:
        reference = args.reference
        allverses_file_path = ensure_allverses_file(module_name, module_path)
        abbrs_file_path = ensure_abbrs_file(module_name, module_path)
        verses_count = load_verses_count(allverses_file_path)
        ranges = parse_range(reference, load_mapping(mapping_file), verses_count, load_mapping(abbrs_file_path))
        if isinstance(ranges, str) and ranges == "Invalid reference for this module":
            print(f"Cannot output {start_bold}{reference}{reset_to_normal}: {ranges.lower()}.")
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
        print("\nExiting now...")

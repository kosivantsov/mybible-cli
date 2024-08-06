# About

`mybible-cli.py` is a command line utility to query [MyBible.zone](https://mybible.zone/en/) modules. It has been inspired by [diatheke](https://wiki.crosswire.org/Frontends:Diatheke) – a command line utility for [Crosswire Sword](http://www.crosswire.org/sword/index.jsp) modules.
The main goal of `mybible-cli.py` is only to get the required text, not to perform search or analyze the matched data, as there are other tools that can do that. The output of the tool can be piped, so there are limitless possibilities to do whatever is needed with the output text.
Though MyBible module format specification describes more than one module type, the script work only with Bible modules. Any other modules (commentaries, devotions, plans, etc.) will be invisible to the script. A good place to get modules is [ph4.org website](https://www.ph4.org/b4_index.php?hd=b).

# Installation

`mybible-cli.py` is a self-contained script with no dependencies on anything other than Python 3.12. No installation is required, the script can run from anywhere. If you find it useful, though, it might be better to copy or symlink it anywhere in your $PATH (%PATH%).
Here's one of the ways to do it:

```  bash
git clone https://github.com/kosivantsov/mybible-cli.git
cd mybible-cli
chmod +x mybible-cli
ln -s $(pwd)/mybible-cli.py $HOME/bin/mybible-cli
```

This way you could run it by simply invoking `mybible-cli`, and it would update automatically when you pull changes in your local copy.

For the program to be useful, you must have at least one MyBible module.

# Usage

When run for the first time (unless `-h`, `--help`, or `--helpformat` arguments were used), it will ask to specify a path to the folder with MyBible modules.

The most common usage would be calling the script with a module name and a reference to get the required text: `mybible-cli -m "KJV+" -r "Jn 11:35"`. If a parameter passed to the script contains a space or a character that can have a special meaning for the shell, it needs to be quoted.

The script can list all the installed modules (`-L`). The list will be sorted by language and will include Bible modules only. When first invoked, it would take a few moments to query each file and get the required info. That info is then hashed and reused until modules are changed.

The script outputs each verse on a separate line and format it using a format string with %-prefixed placeholders.
To learn what each placeholder means, run `mybible-cli --helpformat`.

The default format is `%f %c:%v: %t (%m)` (full book name, chapter:verse, text without most MyBible markup, module name in parenthesis): `John 11:35: Jesus wept. (KJV+)`.
A format string specified with `-f` is applied only once. With `-F` the specified format string will be saved as default and used when no format string is specified.

Text of the reference can be output in five different ways:
1. `%T`- raw text with all the mark up as in the module itself
1. `%t` - plain text, no Strong numbers, no other markup, but with line breaks and indentations as marked in the module; with notes
1. `%z` – the same as above, but with those marked line breaks and indentations, and notes removed
1. `%A` – MyBible markup is converted to ANSI escape sequences for pretty output in the terminal. Includes Strong's numbers
1. `%Z` – the same as above, but without Strong's numbers
If you need Strong's numbers in the output, but don't want to get the escape sequences (for instance, when you pipe output of the script), there is an option `--noansi`. It has no effect on the output when the text is not formatted with `%A` or `%Z`.

Bible book names and abbreviations are looked up in a list provided within the script. During the first run, the list is saved in the configuration directory and could be used to create custom lookup lists.

If you want to use book names and abbreviations from the module itself, run the script with the `-A` argument. To use a non-default lookup list, use `-a prefix`. In that case the script will try to use `prefix_mapping.json` in the config folder.
`prefix` can be an arbitrary string, but a file name with that prefix should exist, otherwise the default lookup file is used.

The script understands only the colon Bible notation without letters in the chapter and verse part. Blocks of verses are separated by commas or semicolons. Spaces in ranges are permitted. Periods will be ignored.


``` bash
Options:
  -h, --help
        Shows help message and exits

  -p PATH, --path PATH
        Specify the path to the folder with MyBible modules

  -L, --list-modules
        List available MyBilbe modules

  -m MODULE_NAME, --module-name MODULE_NAME
        Name of the MyBible module to use

  -r REFERENCE, --reference REFERENCE
        Bible reference to output

  -a ABBR, --abbr ABBR
        Get Bible book names and abbreviations from a non-default file.
        With '--abbr uk' a file named 'uk_mapping.json' located in the configuration folder will be used

  -A, --self-abbr
        Get Bible book names and abbreviations from the module itself

  -f FORMAT, --format FORMAT
        Format output with %-prefixed format sting.
        Available placeholders: %f, %a, %c, %v, %t, %T, $z, %A, %Z, %m

  -F SAVE_FORMAT, --save-format SAVE_FORMAT
        Specified format string will be applied and saved as default.

  --helpformat
        Detailed info on the format string

  --noansi
        Clears out any ANSI escape sequences in the Bible verses output (if %A or %Z were used in the format string)
```

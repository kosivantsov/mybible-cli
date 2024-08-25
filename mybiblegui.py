#!/usr/bin/env python3
import os
import sys
import json
import subprocess
from pathlib import Path
from tkinter import Tk, filedialog, scrolledtext, Button, StringVar, OptionMenu
import tkinter as tk
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

def get_config_file_path():
    config_dir = get_default_config_path()
    return os.path.join(config_dir, "config.json")

def create_config_file(config_file):
    config_dir = os.path.dirname(config_file)
    if not os.path.exists(config_dir):
        os.makedirs(config_dir)

    default_config = {"modules_path": "", "executable_path": ""}
    with open(config_file, 'w') as file:
        json.dump(default_config, file, indent=4)
    print(f"Created default config file at {config_file}")

def check_and_update_modules_path():
    config_file = get_config_file_path()

    if not os.path.exists(config_file):
        create_config_file(config_file)

    with open(config_file, 'r') as file:
        config = json.load(file)

    modules_path = config.get('modules_path')
    if not modules_path or not os.path.isdir(modules_path):
        print("modules_path is not set or points to an invalid directory.")

        root = Tk()
        root.withdraw()
        selected_dir = filedialog.askdirectory(title="Select modules directory")
        root.destroy()

        if selected_dir:
            config['modules_path'] = selected_dir
            with open(config_file, 'w') as file:
                json.dump(config, file, indent=4)
            print(f"modules_path updated to: {selected_dir}")
        else:
            print("No directory selected. modules_path remains unset.")

def check_and_update_executable():
    config_file = get_config_file_path()

    if not os.path.exists(config_file):
        create_config_file(config_file)

    with open(config_file, 'r') as file:
        config = json.load(file)

    executable_path = config.get('executable_path')

    # Default to the script directory if the executable path is not set or invalid
    script_directory = os.path.dirname(os.path.realpath(__file__))
    default_executable = os.path.join(script_directory, 'mybible-cli.py')

    if not executable_path or not os.path.isfile(executable_path):
        if default_executable.exists():
            executable_path = str(default_executable)
            print(f"Using default executable path: {executable_path}")
        else:
            print("Executable path is not set or points to an invalid file.")
            root = Tk()
            root.withdraw()

            selected_file = filedialog.askopenfilename(
                title="Select mybible-cli executable"
            )
            root.destroy()

            if selected_file:
                executable_path = selected_file
                print(f"Executable path updated to: {executable_path}")
            else:
                print("No file selected. Exiting.")
                exit(1)

        # Update the config file with the determined executable path
        config['executable_path'] = executable_path
        with open(config_file, 'w') as file:
            json.dump(config, file, indent=4)

    return executable_path

def run_program(executable, args):
    command = [executable] + args
    try:
        process = subprocess.Popen(command,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE,
                                   text=True)
        output, errors = process.communicate()
        output_text.delete("1.0", tk.END)  # Clear existing text
        output_text.insert(tk.END, output)
        if errors:
            output_text.insert(tk.END, "\nERRORS:\n" + errors)
    except Exception as e:
        output_text.insert(tk.END, f"\nERROR: {e}")

def copy_text():
    root.clipboard_clear()
    root.clipboard_append(output_text.get("1.0", tk.END))

def increase_font():
    current_size = output_text.cget("font").split()[-1]
    new_size = int(current_size) + 2
    output_text.config(font=(font_family, new_size))

def decrease_font():
    current_size = output_text.cget("font").split()[-1]
    new_size = max(8, int(current_size) - 2)  # Prevent font size from going below 8
    output_text.config(font=(font_family, new_size))

def update_text(*args):
    selected_item = dropdown_var.get().split()[1]
    if executable_path:
        run_program(executable_path, sys.argv[1:] + ['-m', selected_item])
    else:
        output_text.insert(tk.END, "No executable path provided.")

def get_dropdown_items(executable):
    try:
        command = [executable, '--simple-list']
        process = subprocess.Popen(command, stdout=subprocess.PIPE, text=True)
        output, _ = process.communicate()
        items = output.splitlines()
        return items
    except Exception as e:
        print(f"Failed to get list items: {e}")
        return []

def extract_value_from_args():
    for i, arg in enumerate(sys.argv):
        if arg == '-m' or arg == '--module' and i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return None

if __name__ == "__main__":
    check_and_update_modules_path()
    executable_path = check_and_update_executable()

    # Extract the value after -m from command line arguments
    selected_value = extract_value_from_args()

    root = tk.Tk()
    root.title("Bible Viewer")
    # Initial font settings
    font_family = "Verdana"
    font_size = 12

    # Close the window on Esc key press
    root.bind('<Escape>', lambda event: root.destroy())

    # Configure the grid to make the window resizable
    root.grid_rowconfigure(0, weight=1)
    root.grid_columnconfigure(0, weight=1)

    # Create a scrolled text widget
    output_text = scrolledtext.ScrolledText(root, wrap=tk.WORD, font=(font_family, font_size))
    output_text.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

    # Add buttons to increase/decrease font size
    button_frame = tk.Frame(root)
    button_frame.grid(row=1, column=0)

    increase_button = tk.Button(button_frame, text="+", command=increase_font)
    increase_button.grid(row=0, column=1, pady=(0, 10))

    decrease_button = tk.Button(button_frame, text="-", command=decrease_font)
    decrease_button.grid(row=0, column=0, pady=(0, 10))
    # Add a "Copy" button
    copy_button = Button(button_frame, text="Copy Text", command=copy_text)
    copy_button.grid(row=0, column=2, pady=(0, 10))

    # Get dropdown items
    items = get_dropdown_items(executable_path)

    # Create a dropdown menu
    dropdown_var = StringVar(root)
    if items:
        # Set the default value based on the selected_value
        default_value = next((item for item in items if item.split()[1] == selected_value), items[0])
        dropdown_var.set(default_value)  # Set the default value
        dropdown_menu = OptionMenu(root, dropdown_var, *items)
        dropdown_menu.grid(row=2, column=0, padx=(10, 10), pady=(0, 10))
        dropdown_var.trace_add("write", update_text)  # Refresh text when selection changes

    # Run the program with initial arguments
    if executable_path:
        run_program(executable_path, sys.argv[1:] + (['-m', selected_value] if selected_value else []))
    else:
        output_text.insert(tk.END, "No executable path provided.")

    root.mainloop()

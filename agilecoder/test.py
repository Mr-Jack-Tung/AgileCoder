import os
import re

from strsimpy.normalized_levenshtein import NormalizedLevenshtein
import difflib
def extract_files(code_string):
    """Extracts code and names for each file from the given string."""

    files = {}
    current_file = None
    current_code = ""

    for line in code_string.splitlines():
    # Check for file header lines
        if line.startswith('FILENAME:'):
            if current_file:
                files[current_file] = current_code
            current_file = line.split()[1].strip()
            current_code = ""
        elif line.startswith('DOCSTRING') or line.startswith('CODE'): continue
        elif line.startswith('```'): continue
        elif not line.startswith('LANGUAGE'):
            current_code += line + "\n"

  # Add the last file
    if current_file:
        files[current_file] = current_code

    return files
class Codes:
    def __init__(self, generated_content=""):
        self.directory: str = None
        self.version: float = 1.0
        self.generated_content: str = generated_content
        self.codebooks = {}

        def extract_filename_from_line(lines):
            file_name = ""
            for candidate in re.finditer(r"(\w+\.\w+)", lines, re.DOTALL):
                file_name = candidate.group()
                file_name = file_name.lower()
            return file_name

        def extract_filename_from_code(code):
            file_name = ""
            regex_extract = r"class (\S+?):\n"
            matches_extract = re.finditer(regex_extract, code, re.DOTALL)
            for match_extract in matches_extract:
                file_name = match_extract.group(1)
            file_name = file_name.lower().split("(")[0] + ".py"
            return file_name

        if generated_content != "":
            regex = r"(.+?\.\w+)\n```.*?\n(.*?)```"
            matches = re.finditer(regex, self.generated_content, re.DOTALL)
            flag = False
            nonamed_codes = []
            for match in matches:
                code = match.group(2)
                flag = True
                if "CODE" in code:
                    continue
                group1 = match.group(1)
                filename = extract_filename_from_line(group1)
                if "__main__" in code:
                    filename = "main.py"
                if filename == "":  # post-processing
                    filename = extract_filename_from_code(code)
                # assert filename != ""
                if filename == '.py':
                    scores = []
                    normalized_levenshtein = NormalizedLevenshtein()
                    formatted_code = self._format_code(code)
                    for filename, file_code in self.codebooks.items():
                        scores.append((filename, formatted_code, normalized_levenshtein.similarity(formatted_code, file_code)))
                    if len(scores) > 0:
                        scores = sorted(scores, key = lambda x: x[2], reverse = True)[0]
                        if scores[2] > 0.7:
                            self.codebooks[scores[0]] = scores[1]
                elif filename is not None and code is not None and len(filename) > 0 and len(code) > 0:
                    self.codebooks[filename] = self._format_code(code)
            
            if not flag:
                regex = r"FILENAME: ([a-z_0-9]+\.\w+)\n```.*?\n(.*?)```"
                matches = re.finditer(regex, self.generated_content, re.DOTALL)
                
                for match in matches:
                    flag = True
                    filename = match.group(1)
                    code = match.group(2)
                    if "CODE" in code:
                        continue
                    if filename is not None and code is not None and len(filename) > 0 and len(code) > 0:
                        self.codebooks[filename] = self._format_code(code)
                    
            if not flag:
                regex = r"FILENAME\n```.*?\n(.*?)```"
                matches = re.finditer(regex, self.generated_content, re.DOTALL)
                unmatched_codes = []
                for match in matches:
                    flag = True
                    code = match.group(1)
                    print('code:', code)
                    if "CODE" in code:
                        continue
                    filename = extract_filename_from_code(code)
                    if filename is not None and code is not None and len(filename) > 0 and len(code) > 0:
                        self.codebooks[filename] = self._format_code(code)
                    else:
                        unmatched_codes.append(self._format_code(code))
                normalized_levenshtein = NormalizedLevenshtein()
                for code in unmatched_codes:
                    scores = []
                    for filename, file_code in self.codebooks.items():
                        scores.append((filename, code, normalized_levenshtein.similarity(code, file_code)))
                    scores = sorted(scores, key = lambda x: x[2], reverse = True)[0]
                    if scores[2] > 0.7:
                        self.codebooks[scores[0]] = scores[1]
            if not flag:
                regex = r"## (\w+.py)\n\n```.*?\n(.*?)```"
                matches = re.finditer(regex, self.generated_content, re.DOTALL)
                unmatched_codes = []
                for match in matches:
                    flag = True
                    filename = match.group(1)
                    code = match.group(2)
                    print('code:', code)
                    if "CODE" in code:
                        continue
                    if filename is not None and code is not None and len(filename) > 0 and len(code) > 0:
                        self.codebooks[filename] = self._format_code(code)
                    else:
                        unmatched_codes.append(self._format_code(code))
                normalized_levenshtein = NormalizedLevenshtein()
                for code in unmatched_codes:
                    scores = []
                    for filename, file_code in self.codebooks.items():
                        scores.append((filename, code, normalized_levenshtein.similarity(code, file_code)))
                    scores = sorted(scores, key = lambda x: x[2], reverse = True)[0]
                    if scores[2] > 0.7:
                        self.codebooks[scores[0]] = scores[1]
            if not flag:
                file_codes = extract_files(self.generated_content)
                for filename, filecode in file_codes.items():
                    self.codebooks[filename] = self._format_code(filecode)


    def _format_code(self, code):
        code = "\n".join([line for line in code.split("\n") if len(line.strip()) > 0])
        return code

    def _update_codes(self, generated_content):
        new_codes = Codes(generated_content)
        # print('new_codes.codebooks', new_codes.codebooks)
        differ = difflib.Differ()
        for key in new_codes.codebooks.keys():
            if key not in self.codebooks.keys() or self.codebooks[key] != new_codes.codebooks[key]:
                update_codes_content = "**[Update Codes]**\n\n"
                update_codes_content += "{} updated.\n".format(key)
                old_codes_content = self.codebooks[key] if key in self.codebooks.keys() else "# None"
                new_codes_content = new_codes.codebooks[key]

                lines_old = old_codes_content.splitlines()
                lines_new = new_codes_content.splitlines()

                unified_diff = difflib.unified_diff(lines_old, lines_new, lineterm='', fromfile='Old', tofile='New')
                unified_diff = '\n'.join(unified_diff)
                update_codes_content = update_codes_content + "\n\n" + """```
'''

'''\n""" + unified_diff + "\n```"

                self.codebooks[key] = new_codes.codebooks[key]
        print('self.codebooks', self.codebooks)

    def _rewrite_codes(self, git_management) -> None:
        directory = self.directory
        rewrite_codes_content = "**[Rewrite Codes]**\n\n"
        if os.path.exists(directory) and len(os.listdir(directory)) > 0:
            self.version += 1.0
        if not os.path.exists(directory):
            os.mkdir(self.directory)
            rewrite_codes_content += "{} Created\n".format(directory)

        for filename in self.codebooks.keys():
            filepath = os.path.join(directory, filename)
            with open(filepath, "w", encoding="utf-8") as writer:
                writer.write(self.codebooks[filename])
                rewrite_codes_content += os.path.join(directory, filename) + " Wrote\n"

        if git_management:
            if self.version == 1.0:
                os.system("cd {}; git init".format(self.directory))
            os.system("cd {}; git add .".format(self.directory))
            os.system("cd {}; git commit -m \"{}\"".format(self.directory, self.version))


    def _get_codes(self) -> str:
        content = ""
        for filename in self.codebooks.keys():
            content += "{}\n```{}\n{}\n```\n\n".format(filename,
                                                       "python" if filename.endswith(".py") else filename.split(".")[
                                                           -1], self.codebooks[filename])
        return content

    def _load_from_hardware(self, directory) -> None:
        assert len([filename for filename in os.listdir(directory) if filename.endswith(".py")]) > 0
        for root, directories, filenames in os.walk(directory):
            for filename in filenames:
                if filename.endswith(".py"):
                    code = open(os.path.join(directory, filename), "r", encoding="utf-8").read()
                    self.codebooks[filename] = self._format_code(code)

s = """

FILENAME: main.py
LANGUAGE: Python
DOCSTRING: This module contains the code for a basic calculator application that performs addition, subtraction, multiplication, and division of two numbers with input validation and error handling. Additionally, it implements a history feature that displays previous calculations, a feature to save and load the history from a file, a feature to copy the result to the clipboard, and a feature to change the color scheme of the calculator.
CODE:
```python
'''
This module contains the code for a basic calculator application that performs addition, subtraction, multiplication, and division of two numbers with input validation and error handling. Additionally, it implements a history feature that displays previous calculations, a feature to save and load the history from a file, a feature to copy the result to the clipboard, and a feature to change the color scheme of the calculator.
'''
import tkinter as tk
import tkinter.ttk as ttk
import tkinter.messagebox as messagebox
import tkinter.filedialog as filedialog
import os
import sys
try:
    import clipboard
except ModuleNotFoundError:
    messagebox.showerror("Error", "The clipboard module is not installed. Copy to clipboard feature will not work.")
class Calculator:
    def __init__(self, master):
        self.master = master
        self.master.title("Calculator")
        self.master.resizable(False, False)
        self.master.configure(bg="#FFFFFF")
        # Create input fields for two numbers
        self.num1_label = ttk.Label(self.master, text="Number 1:")
        self.num1_label.grid(row=0, column=0, padx=5, pady=5, sticky="W")
        self.num1_entry = ttk.Entry(self.master, width=20)
        self.num1_entry.grid(row=0, column=1, padx=5, pady=5, sticky="W")
        self.num2_label = ttk.Label(self.master, text="Number 2:")
        self.num2_label.grid(row=1, column=0, padx=5, pady=5, sticky="W")
        self.num2_entry = ttk.Entry(self.master, width=20)
        self.num2_entry.grid(row=1, column=1, padx=5, pady=5, sticky="W")
        # Create buttons for arithmetic operations
        self.add_button = ttk.Button(self.master, text="+", command=self.add)
        self.add_button.grid(row=2, column=0, padx=5, pady=5)
        self.sub_button = ttk.Button(self.master, text="-", command=self.subtract)
        self.sub_button.grid(row=2, column=1, padx=5, pady=5)
        self.mul_button = ttk.Button(self.master, text="*", command=self.multiply)
        self.mul_button.grid(row=3, column=0, padx=5, pady=5)
        self.div_button = ttk.Button(self.master, text="/", command=self.divide)
        self.div_button.grid(row=3, column=1, padx=5, pady=5)
        # Create clear button
        self.clear_button = ttk.Button(self.master, text="Clear", command=self.clear)
        self.clear_button.grid(row=4, column=0, padx=5, pady=5)
        # Create history button
        self.history_button = ttk.Button(self.master, text="History", command=self.show_history)
        self.history_button.grid(row=4, column=1, padx=5, pady=5)
        # Create save button
        self.save_button = ttk.Button(self.master, text="Save", command=self.save_history)
        self.save_button.grid(row=5, column=0, padx=5, pady=5)
        # Create load button
        self.load_button = ttk.Button(self.master, text="Load", command=self.load_history)
        self.load_button.grid(row=5, column=1, padx=5, pady=5)
        # Create copy button
        self.copy_button = ttk.Button(self.master, text="Copy", command=self.copy_result)
        self.copy_button.grid(row=6, column=0, padx=5, pady=5)
        # Create color scheme label
        self.color_label = ttk.Label(self.master, text="Color Scheme:")
        self.color_label.grid(row=6, column=1, padx=5, pady=5, sticky="E")
        # Create color scheme combobox
        self.color_combobox = ttk.Combobox(self.master, values=["Default", "Dark"], state="readonly")
        self.color_combobox.current(0)
        self.color_combobox.grid(row=6, column=2, padx=5, pady=5, sticky="W")
        self.color_combobox.bind("<<ComboboxSelected>>", self.change_color_scheme)
        # Initialize history list
        self.history = []
    def add(self):
        try:
            num1 = float(self.num1_entry.get())
            num2 = float(self.num2_entry.get())
            result = num1 + num2
            self.display_result(result)
            self.history.append(f"{num1} + {num2} = {result}")
        except ValueError:
            messagebox.showerror("Error", "Invalid input. Please enter valid numbers.")
    def subtract(self):
        try:
            num1 = float(self.num1_entry.get())
            num2 = float(self.num2_entry.get())
            result = num1 - num2
            self.display_result(result)
            self.history.append(f"{num1} - {num2} = {result}")
        except ValueError:
            messagebox.showerror("Error", "Invalid input. Please enter valid numbers.")
    def multiply(self):
        try:
            num1 = float(self.num1_entry.get())
            num2 = float(self.num2_entry.get())
            result = num1 * num2
            self.display_result(result)
            self.history.append(f"{num1} * {num2} = {result}")
        except ValueError:
            messagebox.showerror("Error", "Invalid input. Please enter valid numbers.")
    def divide(self):
        try:
            num1 = float(self.num1_entry.get())
            num2 = float(self.num2_entry.get())
            if num2 == 0:
                raise ZeroDivisionError
            result = num1 / num2
            self.display_result(result)
            self.history.append(f"{num1} / {num2} = {result}")
        except ValueError:
            messagebox.showerror("Error", "Invalid input. Please enter valid numbers.")
        except ZeroDivisionError:
            messagebox.showerror("Error", "Division by zero is not allowed. Please enter a non-zero value for Number 2.")
    def display_result(self, result):
        messagebox.showinfo("Result", f"The result is {result}")
        try:
            clipboard.copy(result)
        except NameError:
            pass
    def clear(self):
        self.num1_entry.delete(0, tk.END)
        self.num2_entry.delete(0, tk.END)
    def show_history(self):
        if not self.history:
            messagebox.showinfo("History", "No history yet.")
        else:
            history_str = "\n".join(self.history)
            messagebox.showinfo("History", history_str)
    def save_history(self):
        filename = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text Files", "*.txt")])
        if filename:
            with open(filename, "w") as f:
                f.write("\n".join(self.history))
            messagebox.showinfo("Save", "History saved successfully.")
    def load_history(self):
        filename = filedialog.askopenfilename(defaultextension=".txt", filetypes=[("Text Files", "*.txt")])
        if filename:
            with open(filename, "r") as f:
                self.history = f.read().splitlines()
            messagebox.showinfo("Load", "History loaded successfully.")
    def copy_result(self):
        result = clipboard.paste()
        if result:
            self.master.clipboard_clear()
            self.master.clipboard_append(result)
            messagebox.showinfo("Copy", "Result copied to clipboard.")
    def change_color_scheme(self, event):
        if self.color_combobox.get() == "Default":
            self.master.configure(bg="#FFFFFF")
        elif self.color_combobox.get() == "Dark":
            self.master.configure(bg="#333333")
if __name__ == "__main__":
    root = tk.Tk()
    app = Calculator(root)
    root.mainloop()
```

"""
code = Codes()
code._update_codes(s)

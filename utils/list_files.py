import os
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import shutil
import ast

class DirectoryTreeApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Directory Tree Viewer")
        self.geometry("800x600")
        self.create_widgets()
        self.excluded_dirs = {'.venv', '.idea', '__pycache__', '.git'}

    def create_widgets(self):
        self.frame = ttk.Frame(self)
        self.frame.pack(fill=tk.BOTH, expand=True)

        self.tree = ttk.Treeview(self.frame, selectmode='browse', show='tree')
        self.tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

        self.scrollbar = ttk.Scrollbar(self.frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscroll=self.scrollbar.set)

        self.button_frame = ttk.Frame(self)
        self.button_frame.pack(fill=tk.X)

        self.select_button = ttk.Button(self.button_frame, text="Select Directory", command=self.select_directory)
        self.select_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.copy_button = ttk.Button(self.button_frame, text="Copy Path", command=self.copy_path)
        self.copy_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.copy_structure_button = ttk.Button(self.button_frame, text="Copy Structure", command=self.copy_structure)
        self.copy_structure_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.toggle_functions = tk.BooleanVar()
        self.functions_toggle = ttk.Checkbutton(self.button_frame, text="Show Functions", variable=self.toggle_functions, command=self.toggle_functions_view)
        self.functions_toggle.pack(side=tk.LEFT, padx=5, pady=5)

        self.expand_button = ttk.Button(self.button_frame, text="Expand All", command=lambda: self.toggle_expand(True))
        self.expand_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.collapse_button = ttk.Button(self.button_frame, text="Collapse All", command=lambda: self.toggle_expand(False))
        self.collapse_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.clear_button = ttk.Button(self.button_frame, text="Clear", command=self.clear_tree)
        self.clear_button.pack(side=tk.RIGHT, padx=5, pady=5)

        self.style = ttk.Style()
        self.style.configure("Treeview", font=("Helvetica", 10), foreground="black")
        self.style.configure("Treeview.Heading", font=("Helvetica", 12, "bold"))
        self.style.configure("TButton", font=("Helvetica", 10), padding=5)

    def clear_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

    def select_directory(self):
        path = filedialog.askdirectory()
        if path:
            self.clear_tree()
            self.populate_tree(path)

    def populate_tree(self, startpath):
        def insert_items(parent, path):
            for name in sorted(os.listdir(path)):
                abspath = os.path.join(path, name)
                isdir = os.path.isdir(abspath)
                if name not in self.excluded_dirs:
                    oid = self.tree.insert(parent, 'end', text=name, open=False, tags=('dir' if isdir else 'file',))
                    if isdir:
                        insert_items(oid, abspath)
                    elif name.endswith('.py'):
                        if self.toggle_functions.get():
                            self.insert_functions(oid, abspath)

        root_node = self.tree.insert('', 'end', text=startpath, open=True, tags=('dir',))
        insert_items(root_node, startpath)

    def copy_path(self):
        selected_item = self.tree.focus()
        if selected_item:
            path = self.get_full_path(selected_item)
            self.clipboard_clear()
            self.clipboard_append(path)
            messagebox.showinfo("Path Copied", f"Copied path:\n{path}")

    def get_full_path(self, item):
        path_parts = []
        while item:
            path_parts.insert(0, self.tree.item(item, 'text'))
            item = self.tree.parent(item)
        return os.path.join(*path_parts)

    def toggle_functions_view(self):
        if self.tree.get_children():
            root_path = self.tree.item(self.tree.get_children()[0], 'text')
            self.clear_tree()
            self.populate_tree(root_path)

    def insert_functions(self, parent, file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                node = ast.parse(file.read(), filename=file_path)
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        self.tree.insert(parent, 'end', text=f"def {item.name}()", tags=('function',))
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")

    def toggle_expand(self, expand=True):
        def toggle_node(node):
            self.tree.item(node, open=expand)
            for child in self.tree.get_children(node):
                toggle_node(child)

        for root in self.tree.get_children():
            toggle_node(root)

    def copy_structure(self):
        structure = self.get_tree_structure()
        self.clipboard_clear()
        self.clipboard_append(structure)
        messagebox.showinfo("Structure Copied", "Directory structure copied to clipboard.")

    def get_tree_structure(self):
        def recurse_tree(item, depth=0):
            structure = "    " * depth + self.tree.item(item, "text") + "\n"
            for child in self.tree.get_children(item):
                structure += recurse_tree(child, depth + 1)
            return structure

        structure = ""
        for root in self.tree.get_children():
            structure += recurse_tree(root)
        return structure

if __name__ == '__main__':
    app = DirectoryTreeApp()
    app.mainloop()

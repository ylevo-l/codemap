# CodeMap

This script was designed with one goal: maximizing workflow. It empowers users to efficiently prepare a codebase for a language model. Through a navigable tree interface, users can select specific files and then copy them, formatted as a single prompt, directly to the clipboard.

## Demo

![CodeMap Demo](https://raw.githubusercontent.com/ylevo-l/codemap/refs/heads/main/assets/codemap.gif)

## Features

1. SHIFT-based subtree actions: expand/collapse
2. Single-folder toggles: expand/collapse
3. Single-file toggles: enable/disable to exclude files from clipboard copying.
4. Clipboard copying of visible, enabled files.
5. State persistence for expanded and file enablement.
6. Selection arrow (`>`) beside the selected entry.

## Usage

Navigate through your directory structure and perform actions using the following key bindings:

- **[W]/[S]**: Navigate the tree
- **[e]/[E]**: Expand/collapse a single folder or entire subtree
- **[a]/[A]**: Anonymize/de-anonymize a single folder or entire subtree
- **[d]**: Enable/disable a single file
- **[c]**: Copy all visible, enabled files to the clipboard
- **[q]**: Quit the application (saves state to `.tree_state.json`)

## Installation

1. **Clone the repository**:
   
2. **Navigate to the directory**:
    
3. **Setup CodeMap**:

    ```bash
    pip install -e .
    ```
    
4. **Run CodeMap**:

    ```bash
    codemap
    ```
    

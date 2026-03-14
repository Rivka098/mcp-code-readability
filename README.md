# mcpProject

## Description

**Code Documenter** is an MCP (Model Context Protocol) Server that automatically analyzes and documents source code across multiple programming languages. It scans project directories, identifies code files, and generates comprehensive documentation by leveraging AI-powered analysis.

The project provides a server-based interface for extracting code structure, identifying patterns, and creating documentation for codebases written in Python, JavaScript, TypeScript, Java, C++, Go, Rust, and many other popular languages.

## Features

- **Multi-Language Support**: Supports 16+ programming languages including:
  - Python, JavaScript, TypeScript, Java, C++, C, C#
  - Go, Rust, Ruby, PHP, Swift, Kotlin, Shell, and more

- **Intelligent Project Scanning**: Automatically discovers and filters source code files while:
  - Skipping common build and dependency directories (`.git`, `node_modules`, `__pycache__`, `venv`, etc.)
  - Filtering out trivial files (< 10 characters)
  - Respecting file encoding with graceful error handling

- **MCP Server Architecture**: Built on the Model Context Protocol for seamless integration with AI tools and IDE extensions

- **Configurable Processing**: Easy-to-extend language support and skip directory configuration

## Project Structure

```
mcpProject/
├── src/
│   └── code_documenter/
│       ├── __init__.py          # Package initialization and version info
│       └── server.py             # Main MCP server implementation
├── README.md                      # This file
└── [configuration files]          # Additional config as needed
```

### File Descriptions

- **`src/code_documenter/__init__.py`**: Package initialization declaring version 1.0.0
- **`src/code_documenter/server.py`**: Core server implementation featuring:
  - MCP Server instance configuration
  - Language extension mappings
  - Project scanning and file discovery logic
  - Directory exclusion rules

## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### Steps

1. Clone the repository:
```bash
git clone <repository-url>
cd mcpProject
```

2. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install the package:
```bash
pip install -e .
```

4. Install required dependencies:
```bash
pip install mcp httpx
```

## Usage

### Running the Server

Start the Code Documenter MCP Server:

```bash
python -m code_documenter.server
```

### Scanning a Project

The server exposes a `scan_project()` function that analyzes a directory:

```python
from code_documenter.server import scan_project

# Scan a local project
files = scan_project("/path/to/project")

# Returns a list of file dictionaries with:
# - File path
# - Programming language
# - File content
```

### Supported File Extensions

| Extension | Language |
|-----------|----------|
| `.py` | Python |
| `.js`, `.jsx` | JavaScript / React |
| `.ts`, `.tsx` | TypeScript / React |
| `.java` | Java |
| `.cpp`, `.c` | C++ / C |
| `.cs` | C# |
| `.go` | Go |
| `.rs` | Rust |
| `.rb` | Ruby |
| `.php` | PHP |
| `.swift` | Swift |
| `.kt` | Kotlin |
| `.sh` | Shell |

### Excluded Directories

The scanner automatically skips:
- `.git` - Version control
- `node_modules` - Node.js dependencies
- `__pycache__` - Python cache
- `venv`, `.venv` - Python virtual environments
- `dist`, `build` - Build outputs

## Configuration

### Adding Language Support

Extend `SUPPORTED_EXTENSIONS` in `server.py`:

```python
SUPPORTED_EXTENSIONS = {
    ".py": "Python",
    ".custom": "Custom Language",  # Add your extension
    # ... existing entries
}
```

### Modifying Skip Directories

Update `SKIP_DIRS` in `server.py`:

```python
SKIP_DIRS = {
    ".git", "node_modules", "__pycache__",
    "venv", ".venv", "dist", "build",
    "custom_skip_dir",  # Add your directory
}
```

## License

This project is provided as-is. Please refer to the LICENSE file in the repository for full licensing information.

---

**Version**: 1.0.0  
**Author**: [Your Name/Organization]  
**Last Updated**: 2024
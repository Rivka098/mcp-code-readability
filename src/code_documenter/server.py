"""
Code Documenter Server Module

This module implements an MCP (Model Context Protocol) server that provides tools for
automatically documenting code projects. It scans project directories, adds comprehensive
comments and docstrings to code files using Claude AI, and generates README.md files.

The server supports multiple programming languages and integrates with the Anthropic API
to leverage Claude's documentation expertise.
"""

import asyncio
import os
from pathlib import Path

from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
import mcp.server.stdio
import httpx


server = Server("code-documenter")

# Dictionary mapping file extensions to their corresponding programming language names
SUPPORTED_EXTENSIONS = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".jsx": "JavaScript (React)",
    ".tsx": "TypeScript (React)",
    ".java": "Java",
    ".cpp": "C++",
    ".c": "C",
    ".cs": "C#",
    ".go": "Go",
    ".rs": "Rust",
    ".rb": "Ruby",
    ".php": "PHP",
    ".swift": "Swift",
    ".kt": "Kotlin",
    ".sh": "Shell",
}

# Set of directory names to skip during project scanning
SKIP_DIRS = {
    ".git", "node_modules", "__pycache__",
    "venv", ".venv", "dist", "build",
}

def scan_project(project_path: str) -> list[dict[str, str]]:
    """
    Scan a project directory recursively and collect all supported code files.
    
    This function traverses the directory tree starting from project_path, identifies
    files with supported extensions, reads their content, and returns metadata about
    each file including its path, language, and content.
    
    Args:
        project_path: Absolute or relative path to the project directory to scan.
        
    Returns:
        A list of dictionaries, each containing:
            - path: Absolute path to the file
            - relative_path: Path relative to the project root
            - language: Human-readable programming language name
            - content: Full file content as a string
            
    Raises:
        ValueError: If the project_path does not exist or is not a directory.
    """
    root = Path(project_path)
    if not root.exists():
        raise ValueError(f"Path does not exist: {project_path}")
    if not root.is_dir():
        raise ValueError(f"Path is not a directory: {project_path}")

    files = []
    # Recursively iterate through all files in the directory, sorted for consistency
    for file_path in sorted(root.rglob("*")):
        # Skip directories listed in SKIP_DIRS to avoid unnecessary scanning
        if any(skip in file_path.parts for skip in SKIP_DIRS):
            continue
        if not file_path.is_file():
            continue
        ext = file_path.suffix.lower()
        # Only process files with supported extensions
        if ext not in SUPPORTED_EXTENSIONS:
            continue
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            # Skip very small files that are likely empty or contain minimal content
            if len(content.strip()) < 10:
                continue
            files.append({
                "path": str(file_path),
                "relative_path": str(file_path.relative_to(root)),
                "language": SUPPORTED_EXTENSIONS[ext],
                "content": content,
            })
        except Exception:
            # Silently skip files that cannot be read (e.g., permission errors)
            continue

    return files


async def call_claude(prompt: str, system: str) -> str:
    """
    Make an asynchronous API call to Claude via the Anthropic API.
    
    This function sends a request to the Anthropic API with the provided prompt and
    system message, then returns Claude's response text. It uses the claude-haiku
    model for efficient processing.
    
    Args:
        prompt: The user message/prompt to send to Claude.
        system: The system message that defines Claude's behavior and instructions.
        
    Returns:
        The text content of Claude's response.
        
    Raises:
        ValueError: If the API request fails or returns a non-200 status code.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY") or "YOUR-API-KEY"
    
    async with httpx.AsyncClient(timeout=120.0, verify=False) as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 8096,
                "system": system,
                "messages": [{"role": "user", "content": prompt}],
            },
        )
        # Check for API errors and raise if the request was unsuccessful
        if response.status_code != 200:
            raise ValueError(f"API error {response.status_code}: {response.text}")
        data = response.json()
        return data["content"][0]["text"]


async def document_file(file_info: dict[str, str]) -> str:
    """
    Add comprehensive documentation comments to a single code file using Claude.
    
    This function sends a code file to Claude with instructions to add file-level
    docstrings, function/method/class docstrings, and inline comments for complex logic,
    while preserving the original code.
    
    Args:
        file_info: A dictionary containing:
            - language: Programming language of the file
            - relative_path: Relative path to display in the prompt
            - content: The complete source code content
            
    Returns:
        The documented version of the code file as a string.
    """
    system = (
        "You are a code documentation expert. "
        "Add clear comments to the code. "
        "Rules:\n"
        "- Add a file-level docstring at the top\n"
        "- Add docstrings to every function, method, and class\n"
        "- Add inline comments for complex logic\n"
        "- Keep existing code completely unchanged\n"
        "- Return ONLY the code, no explanations, no markdown fences"
    )
    prompt = f"Language: {file_info['language']}\nFile: {file_info['relative_path']}\n\n{file_info['content']}"
    return await call_claude(prompt, system)


async def generate_readme(project_path: str, files: list[dict[str, str]]) -> str:
    """
    Generate a comprehensive README.md file for the project using Claude.
    
    This function analyzes the project structure and code samples, then uses Claude
    to generate a well-formatted README.md with sections for title, description,
    features, project structure, installation, usage, and license.
    
    Args:
        project_path: The path to the project directory (used to extract project name).
        files: A list of file dictionaries from scan_project() containing project files.
        
    Returns:
        The complete README.md content as a string.
    """
    project_name = Path(project_path).name
    # Generate a bullet list of all project files with their language
    structure = "\n".join([f"- {f['relative_path']} ({f['language']})" for f in files])
    
    # Include code samples from the first few files to give Claude context
    code_samples = ""
    for f in files[:3]:
        code_samples += f"\n\n### {f['relative_path']}\n```\n{f['content'][:1500]}\n```"

    system = (
        "You are a technical writer. Generate a comprehensive README.md. "
        "Include: title, description, features, project structure, installation, usage, license. "
        "Use proper Markdown. Return ONLY the README content."
    )
    prompt = f"Project name: {project_name}\n\nFiles:\n{structure}\n\nCode samples:{code_samples}"
    return await call_claude(prompt, system)


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    List all available tools provided by this MCP server.
    
    This handler is called by the MCP client to discover what tools the server offers.
    Currently, it exposes the document_project tool.
    
    Returns:
        A list of Tool objects describing the available tools and their parameters.
    """
    return [
        types.Tool(
            name="document_project",
            description="Scan a project directory, add comments to all code files, and generate a README.md.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_path": {
                        "type": "string",
                        "description": "Absolute path to the project directory",
                    }
                },
                "required": ["project_path"],
            },
        )
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict | None) -> list[types.TextContent]:
    """
    Handle tool execution requests from the MCP client.
    
    This function processes requests to execute the document_project tool. It orchestrates
    the entire documentation workflow: scanning the project, documenting each file, and
    generating a README. Progress updates are returned to the client as text content.
    
    Args:
        name: The name of the tool being invoked.
        arguments: A dictionary containing the tool's arguments, including project_path.
        
    Returns:
        A list containing a single TextContent object with status messages and progress updates.
        
    Raises:
        ValueError: If the tool name is unknown or required arguments are missing.
    """
    if name != "document_project":
        raise ValueError(f"Unknown tool: {name}")
    if not arguments or "project_path" not in arguments:
        raise ValueError("Missing required argument: project_path")

    project_path = arguments["project_path"]
    results = []

    # Phase 1: Scan the project directory
    results.append(f"📂 Scanning: {project_path}")
    files = scan_project(project_path)
    if not files:
        return [types.TextContent(type="text", text="No supported code files found.")]
    results.append(f"✅ Found {len(files)} file(s)\n")

    # Phase 2: Document each file by adding comments and docstrings
    for file_info in files:
        results.append(f"⚙️  Documenting: {file_info['relative_path']}")
        try:
            documented = await document_file(file_info)
            # Write the documented code back to the original file
            Path(file_info["path"]).write_text(documented, encoding="utf-8")
            results.append(f"✅ Done: {file_info['relative_path']}")
        except Exception as e:
            results.append(f"❌ Failed: {file_info['relative_path']} — {e}")

    # Phase 3: Generate README.md
    results.append("\n📝 Generating README...")
    try:
        readme_content = await generate_readme(project_path, files)
        readme_path = Path(project_path) / "README.md"
        readme_path.write_text(readme_content, encoding="utf-8")
        results.append(f"✅ README.md created!")
    except Exception as e:
        results.append(f"❌ README failed: {e}")

    results.append("\n🎉 Done!")
    return [types.TextContent(type="text", text="\n".join(results))]


async def main():
    """
    Main entry point for the MCP server.
    
    This function initializes and runs the MCP server using stdio (standard input/output)
    communication. It sets up the server capabilities and waits for client connections.
    """
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="code-documenter",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())

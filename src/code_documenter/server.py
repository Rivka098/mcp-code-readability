#!/usr/bin/env python3

import asyncio
import os
from pathlib import Path

from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
import mcp.server.stdio
import httpx


server = Server("code-documenter")

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

SKIP_DIRS = {
    ".git", "node_modules", "__pycache__",
    "venv", ".venv", "dist", "build",
}

def scan_project(project_path: str) -> list[dict[str, str]]:
    root = Path(project_path)
    if not root.exists():
        raise ValueError(f"Path does not exist: {project_path}")
    if not root.is_dir():
        raise ValueError(f"Path is not a directory: {project_path}")

    files = []
    for file_path in sorted(root.rglob("*")):
        if any(skip in file_path.parts for skip in SKIP_DIRS):
            continue
        if not file_path.is_file():
            continue
        ext = file_path.suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            continue
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            if len(content.strip()) < 10:
                continue
            files.append({
                "path": str(file_path),
                "relative_path": str(file_path.relative_to(root)),
                "language": SUPPORTED_EXTENSIONS[ext],
                "content": content,
            })
        except Exception:
            continue

    return files

def scan_project(project_path: str) -> list[dict[str, str]]:
    root = Path(project_path)
    if not root.exists():
        raise ValueError(f"Path does not exist: {project_path}")
    if not root.is_dir():
        raise ValueError(f"Path is not a directory: {project_path}")

    files = []
    for file_path in sorted(root.rglob("*")):
        if any(skip in file_path.parts for skip in SKIP_DIRS):
            continue
        if not file_path.is_file():
            continue
        ext = file_path.suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            continue
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            if len(content.strip()) < 10:
                continue
            files.append({
                "path": str(file_path),
                "relative_path": str(file_path.relative_to(root)),
                "language": SUPPORTED_EXTENSIONS[ext],
                "content": content,
            })
        except Exception:
            continue

    return files

async def call_claude(prompt: str, system: str) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("Missing ANTHROPIC_API_KEY environment variable")
    
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
        if response.status_code != 200:
            raise ValueError(f"API error {response.status_code}: {response.text}")
        data = response.json()
        return data["content"][0]["text"]
async def document_file(file_info: dict[str, str]) -> str:
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
    project_name = Path(project_path).name
    structure = "\n".join([f"- {f['relative_path']} ({f['language']})" for f in files])
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
    if name != "document_project":
        raise ValueError(f"Unknown tool: {name}")
    if not arguments or "project_path" not in arguments:
        raise ValueError("Missing required argument: project_path")

    project_path = arguments["project_path"]
    results = []

    results.append(f"📂 Scanning: {project_path}")
    files = scan_project(project_path)
    if not files:
        return [types.TextContent(type="text", text="No supported code files found.")]
    results.append(f"✅ Found {len(files)} file(s)\n")

    for file_info in files:
        results.append(f"⚙️  Documenting: {file_info['relative_path']}")
        try:
            documented = await document_file(file_info)
            Path(file_info["path"]).write_text(documented, encoding="utf-8")
            results.append(f"✅ Done: {file_info['relative_path']}")
        except Exception as e:
            results.append(f"❌ Failed: {file_info['relative_path']} — {e}")

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
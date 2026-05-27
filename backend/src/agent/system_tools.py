import subprocess
import webbrowser
try:
    import pyperclip
except ImportError:
    pyperclip = None
import platform
import sys
import os
from typing import List, Dict, Any
from langchain_core.tools import BaseTool, StructuredTool

class SystemControlTools:
    def __init__(self):
        pass

    def get_system_info(self) -> str:
        """Returns information about the local system (OS, Python version, CPU architecture)."""
        info = {
            "OS": platform.system(),
            "OS Release": platform.release(),
            "Architecture": platform.machine(),
            "Processor": platform.processor(),
            "Python Version": sys.version,
            "Hostname": platform.node()
        }
        return "\n".join([f"{k}: {v}" for k, v in info.items()])

    def open_url(self, url: str) -> str:
        """Opens a URL in the default web browser."""
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        try:
            webbrowser.open(url)
            return f"Opened {url} in your browser."
        except Exception as e:
            return f"Failed to open URL: {str(e)}"

    def list_files_in_directory(self, path: str = ".") -> str:
        """Lists files in a given directory path."""
        try:
            files = os.listdir(path)
            return "\n".join(files)
        except Exception as e:
            return f"Error listing files: {str(e)}"

    def execute_command(self, command: str) -> str:
        """Executes a shell command. Use with caution! Only for safe commands like 'ls', 'dir', 'date'."""
        # Whitelist safe commands for Jarvis demo
        safe_commands = ['dir', 'ls', 'date', 'time', 'echo', 'whoami', 'pwd']
        cmd_base = command.split()[0].lower()
        
        if cmd_base not in safe_commands:
            return f"Error: Command '{cmd_base}' is not in the safety whitelist for this agent."
            
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            return result.stdout if result.stdout else result.stderr
        except Exception as e:
            return f"Execution error: {str(e)}"

    def read_clipboard(self) -> str:
        """Reads the current text from the system clipboard."""
        if pyperclip is None:
            return "Clipboard is not available in the server environment."
        try:
            return pyperclip.paste()
        except Exception as e:
            return f"Error reading clipboard: {str(e)}"

    def write_clipboard(self, text: str) -> str:
        """Writes text to the system clipboard."""
        if pyperclip is None:
            return "Clipboard is not available in the server environment."
        try:
            pyperclip.copy(text)
            return "Content copied to clipboard successfully, Sir."
        except Exception as e:
            return f"Error writing to clipboard: {str(e)}"

    def search_web(self, query: str) -> str:
        """Searches the web for a query using the default browser."""
        url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
        try:
            webbrowser.open(url)
            return f"Searching the web for '{query}' as requested, Sir."
        except Exception as e:
            return f"Search failed: {str(e)}"

    def get_tools(self) -> List[BaseTool]:
        return [
            StructuredTool.from_function(
                func=self.get_system_info,
                name="get_system_info",
                description="Get details about the user's local operating system and environment."
            ),
            StructuredTool.from_function(
                func=self.open_url,
                name="open_url",
                description="Open a website or search query in the default browser."
            ),
            StructuredTool.from_function(
                func=self.list_files_in_directory,
                name="list_files",
                description="List contents of a local directory."
            ),
            StructuredTool.from_function(
                func=self.execute_command,
                name="execute_system_command",
                description="Execute a safe shell command on the local machine."
            ),
            StructuredTool.from_function(
                func=self.read_clipboard,
                name="read_clipboard",
                description="Read the current content from the system clipboard."
            ),
            StructuredTool.from_function(
                func=self.write_clipboard,
                name="write_clipboard",
                description="Copy specific text or code to the system clipboard for the user."
            ),
            StructuredTool.from_function(
                func=self.search_web,
                name="search_web",
                description="Search the web for information using Google."
            )
        ]

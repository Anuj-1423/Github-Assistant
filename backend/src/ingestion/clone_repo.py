import os
import subprocess
import shutil
from typing import Optional
import logging
import re
from git import Repo

logger = logging.getLogger(__name__)

class RepoIngestor:
    def __init__(self, base_storage_path: Optional[str] = None):
        if base_storage_path is None:
            root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            base_storage_path = os.path.join(root_dir, "storage", "repos")
        self.base_path = os.path.abspath(base_storage_path)
        os.makedirs(self.base_path, exist_ok=True)

    def clone_repo(self, repo_url: str, repo_id: str) -> Optional[str]:
        """
        Clones a public GitHub repository to a local directory using GitPython.
        Following PRD Section 7.1 requirements.
        """
        target_path = os.path.join(self.base_path, repo_id)
        normalized_input = self._normalize_repo_input(repo_url)
        
        if os.path.exists(target_path):
            logger.info(f"Repo {repo_id} already exists. Using existing path.")
            return target_path

        try:
            if normalized_input != repo_url:
                logger.info("Normalized repository input before clone.")
            logger.info(f"Cloning {normalized_input} to {target_path}")
            Repo.clone_from(normalized_input, target_path, depth=1)
            return target_path
        except Exception as e:
            logger.error(f"Failed to clone repo: {str(e)}")
            # Fallback to local path if it's not a URL
            if os.path.exists(normalized_input):
                logger.info(f"Treating {normalized_input} as local path.")
                return normalized_input
            return None

    def _normalize_repo_input(self, raw_input: str) -> str:
        """
        Accepts plain URLs, local paths, or pasted text that contains a URL.
        """
        if not raw_input:
            return ""

        text = raw_input.strip()

        # Local path should pass through unchanged.
        if os.path.exists(text):
            return text

        # First try extracting an HTTP(S) URL.
        http_match = re.search(r"https?://[^\s\"']+", text)
        if http_match:
            return http_match.group(0).rstrip(".,);]}>\"'")

        # Also support SSH git URLs pasted inside text.
        ssh_match = re.search(r"git@[^\s:]+:[^\s\"']+", text)
        if ssh_match:
            return ssh_match.group(0).rstrip(".,);]}>\"'")

        # Fallback to trimmed original value.
        return text

    def walk_repo(self, path: str, ignore_patterns: list = None):
        """
        Walks the repository and identifies source files.
        Respects common exclusions (Section 7.1).
        """
        default_ignore = {
            'node_modules', '.git', 'dist', 'build', '.next', 
            'coverage', '.venv', '__pycache__', '.gemini', 'node_modules'
        }
        if ignore_patterns:
            default_ignore.update(ignore_patterns)

        for root, dirs, files in os.walk(path):
            # Prune ignored directories
            dirs[:] = [d for d in dirs if d not in default_ignore]
            
            for file in files:
                if self._is_supported_file(file):
                    yield os.path.join(root, file)

    def _is_supported_file(self, filename: str) -> bool:
        supported_extensions = {'.py', '.ts', '.js', '.tsx', '.jsx', '.go', '.java'}
        return any(filename.endswith(ext) for ext in supported_extensions)

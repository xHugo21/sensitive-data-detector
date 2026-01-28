from __future__ import annotations

import hashlib
import os
import shutil
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

try:
    from git import Repo
    from git.exc import GitCommandError

    GIT_AVAILABLE = True
except ImportError:
    GIT_AVAILABLE = False

try:
    from rapidfuzz import fuzz

    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False


CODE_EXTENSIONS = {
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".java",
    ".c",
    ".cpp",
    ".h",
    ".hpp",
    ".lua",
    ".cs",
    ".go",
    ".rs",
    ".rb",
    ".php",
    ".swift",
    ".kt",
    ".scala",
    ".sh",
    ".bash",
    ".sql",
    ".r",
    ".m",
    ".mm",
}

IGNORE_DIRS = {
    ".git",
    "node_modules",
    "vendor",
    "__pycache__",
    ".venv",
    "venv",
    "dist",
    "build",
    ".tox",
    ".mypy_cache",
    ".pytest_cache",
    "egg-info",
}

MAX_FILE_SIZE = 1024 * 1024  # 1MB


@dataclass
class CodeMatch:
    file_path: str
    similarity: float
    matched_snippet: str
    repo_url: str


@dataclass
class RepoIndex:
    files: Dict[str, str] = field(default_factory=dict)
    last_updated: float = 0.0


class CodeSimilarityDetector:
    """
    Detects proprietary code by comparing input against private Git repositories.

    Uses fuzzy string matching (rapidfuzz) to find similar code blocks.
    """

    def __init__(
        self,
        *,
        repo_urls: List[str] | tuple[str, ...],
        auth_token: str | None = None,
        similarity_threshold: float = 85.0,
        refresh_interval: int = 3600,
        cache_dir: str | None = None,
        min_snippet_length: int = 50,
    ) -> None:
        if not GIT_AVAILABLE:
            raise ImportError(
                "GitPython is required for code similarity detection. "
                "Install with: pip install GitPython"
            )
        if not RAPIDFUZZ_AVAILABLE:
            raise ImportError(
                "rapidfuzz is required for code similarity detection. "
                "Install with: pip install rapidfuzz"
            )

        self._repo_urls = list(repo_urls)
        self._auth_token = auth_token

        # Ensure threshold is in 0-100 range for rapidfuzz
        if similarity_threshold <= 1.0:
            self._similarity_threshold = similarity_threshold * 100.0
        else:
            self._similarity_threshold = similarity_threshold

        self._refresh_interval = refresh_interval
        self._min_snippet_length = min_snippet_length

        if cache_dir:
            self._base_cache_dir = Path(cache_dir)
        else:
            self._base_cache_dir = Path(tempfile.gettempdir()) / "code-similarity-cache"

        self._indexes: Dict[str, RepoIndex] = {}

    def _get_authenticated_url(self, repo_url: str) -> str:
        if not self._auth_token:
            return repo_url

        if repo_url.startswith("https://"):
            if "github.com" in repo_url:
                return repo_url.replace("https://", f"https://{self._auth_token}@")
            elif "gitlab.com" in repo_url:
                return repo_url.replace(
                    "https://", f"https://oauth2:{self._auth_token}@"
                )
            else:
                return repo_url.replace("https://", f"https://{self._auth_token}@")
        return repo_url

    def _get_repo_cache_path(self, repo_url: str) -> Path:
        repo_hash = hashlib.md5(repo_url.encode()).hexdigest()[:12]
        return self._base_cache_dir / repo_hash

    def _ensure_repo(self, repo_url: str) -> Path:
        repo_dir = self._get_repo_cache_path(repo_url)
        repo_path = repo_dir / "repo"
        auth_url = self._get_authenticated_url(repo_url)

        if repo_path.exists():
            try:
                repo = Repo(repo_path)
                if (
                    time.time() - self._get_last_pull_time(repo_dir)
                    > self._refresh_interval
                ):
                    repo.remotes.origin.pull()
                    self._set_last_pull_time(repo_dir)
            except GitCommandError:
                shutil.rmtree(repo_path, ignore_errors=True)
                Repo.clone_from(auth_url, repo_path)
                self._set_last_pull_time(repo_dir)
        else:
            repo_path.parent.mkdir(parents=True, exist_ok=True)
            Repo.clone_from(auth_url, repo_path)
            self._set_last_pull_time(repo_dir)

        return repo_path

    def _get_last_pull_time(self, repo_dir: Path) -> float:
        marker = repo_dir / ".last_pull"
        if marker.exists():
            try:
                return float(marker.read_text().strip())
            except (ValueError, OSError):
                pass
        return 0.0

    def _set_last_pull_time(self, repo_dir: Path) -> None:
        marker = repo_dir / ".last_pull"
        marker.write_text(str(time.time()))

    def _should_index_file(self, file_path: Path) -> bool:
        if any(ignored in file_path.parts for ignored in IGNORE_DIRS):
            return False

        if file_path.suffix.lower() not in CODE_EXTENSIONS:
            return False

        try:
            if file_path.stat().st_size > MAX_FILE_SIZE:
                return False
        except OSError:
            return False

        return True

    def _build_index(self, repo_path: Path) -> RepoIndex:
        index = RepoIndex()

        for file_path in repo_path.rglob("*"):
            if not file_path.is_file():
                continue

            if not self._should_index_file(file_path):
                continue

            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                relative_path = str(file_path.relative_to(repo_path))
                index.files[relative_path] = content
            except (OSError, UnicodeDecodeError):
                continue

        index.last_updated = time.time()
        return index

    def _get_index(self, repo_url: str) -> RepoIndex:
        repo_path = self._ensure_repo(repo_url)

        current_index = self._indexes.get(repo_url)

        if current_index is None or (
            time.time() - current_index.last_updated > self._refresh_interval
        ):
            new_index = self._build_index(repo_path)
            self._indexes[repo_url] = new_index
            return new_index

        return current_index

    def _normalize_code(self, code: str) -> str:
        lines = code.split("\n")
        normalized_lines = []
        for line in lines:
            stripped = line.strip()
            if (
                stripped
                and not stripped.startswith("#")
                and not stripped.startswith("//")
            ):
                normalized_lines.append(stripped)
        return "\n".join(normalized_lines)

    def _find_matches_in_repo(
        self, text: str, repo_url: str, normalized_input: str
    ) -> List[CodeMatch]:
        index = self._get_index(repo_url)
        matches: List[CodeMatch] = []

        for file_path, content in index.files.items():
            normalized_content = self._normalize_code(content)

            if len(normalized_content) < self._min_snippet_length:
                continue

            similarity = fuzz.partial_ratio(normalized_input, normalized_content)

            if similarity >= self._similarity_threshold:
                snippet_end = min(200, len(content))
                matches.append(
                    CodeMatch(
                        file_path=file_path,
                        similarity=similarity,
                        matched_snippet=content[:snippet_end]
                        + ("..." if len(content) > snippet_end else ""),
                        repo_url=repo_url,
                    )
                )
        return matches

    def _find_matches(self, text: str) -> List[CodeMatch]:
        if len(text.strip()) < self._min_snippet_length:
            return []

        normalized_input = self._normalize_code(text)
        if len(normalized_input) < self._min_snippet_length:
            return []

        all_matches: List[CodeMatch] = []

        for repo_url in self._repo_urls:
            repo_matches = self._find_matches_in_repo(text, repo_url, normalized_input)
            all_matches.extend(repo_matches)

        all_matches.sort(key=lambda m: m.similarity, reverse=True)
        return all_matches[:5]

    def detect(self, text: str) -> List[Dict[str, Any]]:
        try:
            matches = self._find_matches(text)
        except Exception:
            return []

        findings: List[Dict[str, Any]] = []

        for match in matches:
            findings.append(
                {
                    "field": "PROPRIETARY_CODE",
                    "value": f"[similarity: {match.similarity:.1f}%] {match.file_path} (Repo: {match.repo_url})",
                    "sources": [f"code_similarity:{match.file_path}"],
                    "metadata": {
                        "similarity": match.similarity,
                        "file_path": match.file_path,
                        "repo_url": match.repo_url,
                        "matched_snippet": match.matched_snippet,
                    },
                }
            )

        return findings

    def __call__(self, text: str) -> List[Dict[str, Any]]:
        return self.detect(text)


__all__ = ["CodeSimilarityDetector", "CodeMatch"]

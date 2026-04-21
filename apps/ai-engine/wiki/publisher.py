"""Publish the Obsidian vault to a GitHub repository via git.

Uses GitPython (``git`` package) rather than shelling out — it surfaces
errors as typed exceptions we can map into PublishResult fields, and
avoids quoting pitfalls on commit messages.

Safety notes
------------
* ``auto_push`` defaults to True but every call path handles "remote not
  configured" / "remote unreachable" gracefully by setting pushed=False
  on the result and logging a warning. No exception escapes to the
  caller for a missing remote — the repo may legitimately not exist yet
  on GitHub at first publish.
* ``rollback_last_commit`` is intentionally *soft* only. We never expose
  ``git reset --hard`` on this class; callers who need a destructive
  reset must do it themselves after reading the Aegis safety rules.
* No Claude / AI co-author strings are ever appended to commit messages.
  This is a hard rule for the Future project — commits must look like
  they came from the user directly.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

try:  # pragma: no cover — import guard so the module can be imported
    # on systems without git installed; methods that actually use it
    # will raise a clear error.
    import git  # type: ignore[import-untyped]
    from git import Actor, InvalidGitRepositoryError, Repo  # type: ignore[import-untyped]
except ImportError:  # pragma: no cover
    git = None  # type: ignore[assignment]
    Actor = None  # type: ignore[assignment]
    InvalidGitRepositoryError = Exception  # type: ignore[assignment,misc]
    Repo = None  # type: ignore[assignment]


logger = logging.getLogger("aegis.wiki.publish")


_DEFAULT_VAULT_ROOT = Path("~/Documents/obsidian-sre").expanduser()
_DEFAULT_REMOTE_URL = "git@github.com:JIUNG9/aegis-wiki.git"
_META_DIR_NAME = "_meta"
_LOG_FILENAME = "publish-log.jsonl"


class PublisherConfig(BaseModel):
    """Configuration for publishing the vault to a git remote."""

    vault_root: Path = Field(default_factory=lambda: _DEFAULT_VAULT_ROOT)
    remote_url: str = _DEFAULT_REMOTE_URL
    branch: str = "main"
    commit_author_name: str = "Aegis Bot"
    commit_author_email: str = "aegis-bot@localhost"
    auto_push: bool = True


class PublishResult(BaseModel):
    """Summary of one publish pass."""

    published_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    commit_sha: str | None = None
    files_changed: int = 0
    pushed: bool = False
    errors: list[str] = Field(default_factory=list)


class Publisher:
    """Git-backed publisher for the Obsidian vault.

    Not a long-lived object — methods operate on the vault directory
    directly and open a fresh :class:`git.Repo` each call. This keeps
    state management simple and avoids stale index caches across long
    running processes.
    """

    def __init__(self, config: PublisherConfig) -> None:
        self.config = config
        self._vault_root = Path(config.vault_root).expanduser().resolve()
        self._meta_dir = self._vault_root / _META_DIR_NAME
        self._log_path = self._meta_dir / _LOG_FILENAME

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _require_git(self) -> None:
        """Fail loudly if gitpython isn't installed.

        The module imports are wrapped in a try/except so this file
        can be imported even when git isn't present (makes unit tests
        on pure-python hosts easier), but every operational path must
        call this first.
        """

        if git is None or Repo is None:
            raise RuntimeError(
                "GitPython is required for Publisher; install 'gitpython'"
            )

    def _open_repo(self) -> Any:
        """Open the vault as a git repo, or raise a clean error.

        Synchronous — we run it from worker threads via ``asyncio.to_thread``
        from the public async API.
        """

        self._require_git()
        if not self._vault_root.exists():
            raise FileNotFoundError(
                f"vault_root does not exist: {self._vault_root}"
            )
        try:
            return Repo(str(self._vault_root))
        except InvalidGitRepositoryError as exc:
            raise RuntimeError(
                f"{self._vault_root} is not a git repository; "
                "call ensure_git_initialized() first"
            ) from exc

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    async def ensure_git_initialized(self) -> None:
        """Initialize git in the vault if needed, set identity, add remote.

        Idempotent — safe to call on every publish. The remote is added
        under the name ``origin``; if a remote named ``origin`` already
        exists with a different URL we *don't* rewrite it (the user may
        have intentionally pointed it somewhere else).
        """

        self._require_git()

        def _work() -> None:
            if not self._vault_root.exists():
                self._vault_root.mkdir(parents=True, exist_ok=True)
            git_dir = self._vault_root / ".git"
            if not git_dir.exists():
                logger.info("initializing git repo at %s", self._vault_root)
                repo = Repo.init(str(self._vault_root), initial_branch=self.config.branch)
            else:
                repo = Repo(str(self._vault_root))

            # Set identity locally only — never touch global git config
            # (explicit rule from the user's CLAUDE.md).
            with repo.config_writer() as writer:
                writer.set_value("user", "name", self.config.commit_author_name)
                writer.set_value("user", "email", self.config.commit_author_email)

            # Add the remote only if it isn't already present.
            remote_names = [r.name for r in repo.remotes]
            if "origin" not in remote_names:
                if self.config.remote_url:
                    logger.info(
                        "adding remote origin -> %s", self.config.remote_url
                    )
                    repo.create_remote("origin", self.config.remote_url)

        await asyncio.to_thread(_work)

    async def status(self) -> dict[str, Any]:
        """Return a shallow status dict suitable for JSON serialization.

        ``unpushed_count`` requires the local branch to have a tracking
        upstream; if it doesn't, we set the count to None so callers
        don't misinterpret 0 as "nothing to push".
        """

        self._require_git()

        def _work() -> dict[str, Any]:
            try:
                repo = self._open_repo()
            except Exception as exc:  # noqa: BLE001 — status must never throw
                return {
                    "branch": None,
                    "uncommitted_count": 0,
                    "unpushed_count": None,
                    "last_commit_sha": None,
                    "last_commit_at": None,
                    "remote_configured": False,
                    "error": str(exc),
                }

            branch = repo.active_branch.name if not repo.head.is_detached else None
            uncommitted = (
                len(repo.index.diff(None))  # unstaged
                + len(repo.index.diff("HEAD" if repo.head.is_valid() else None))
                + len(repo.untracked_files)
            )

            unpushed: int | None = None
            remote_configured = any(r.name == "origin" for r in repo.remotes)
            if remote_configured and repo.head.is_valid():
                try:
                    tracking = repo.active_branch.tracking_branch()
                    if tracking is not None:
                        ahead = list(
                            repo.iter_commits(
                                f"{tracking.name}..{repo.active_branch.name}"
                            )
                        )
                        unpushed = len(ahead)
                except Exception:  # noqa: BLE001 — best-effort
                    unpushed = None

            last_sha: str | None = None
            last_at: str | None = None
            if repo.head.is_valid():
                last_commit = repo.head.commit
                last_sha = last_commit.hexsha
                last_at = datetime.fromtimestamp(
                    last_commit.committed_date, tz=timezone.utc
                ).isoformat()

            return {
                "branch": branch,
                "uncommitted_count": uncommitted,
                "unpushed_count": unpushed,
                "last_commit_sha": last_sha,
                "last_commit_at": last_at,
                "remote_configured": remote_configured,
            }

        return await asyncio.to_thread(_work)

    async def publish(
        self, commit_message: str | None = None
    ) -> PublishResult:
        """Stage, commit, optionally push. Idempotent if nothing changed."""

        self._require_git()
        result = PublishResult()

        def _stage_and_commit() -> tuple[PublishResult, Any, Any]:
            # Returns (result, repo, commit_or_None). We split the push
            # out so the async wrapper can await it with a separate
            # thread hop — pushes are the slowest part.
            try:
                repo = self._open_repo()
            except Exception as exc:  # noqa: BLE001
                result.errors.append(f"open_repo: {exc!r}")
                return result, None, None

            try:
                repo.git.add(A=True)  # git add -A
            except Exception as exc:  # noqa: BLE001
                result.errors.append(f"git add: {exc!r}")
                return result, repo, None

            # Count files actually changed vs HEAD.
            try:
                if repo.head.is_valid():
                    diff = repo.index.diff("HEAD")
                else:
                    # Initial commit — count staged files directly.
                    diff = list(repo.index.entries.keys())
                result.files_changed = len(diff)
            except Exception:  # noqa: BLE001 — best-effort count
                result.files_changed = 0

            if result.files_changed == 0:
                logger.info("publish: no changes to commit")
                return result, repo, None

            msg = commit_message or (
                f"wiki: sync {result.files_changed} pages updated at "
                f"{datetime.now(timezone.utc).isoformat()}"
            )
            # Explicit Actor to guarantee the configured identity is used
            # even if the local git config was modified out-of-band.
            actor = Actor(
                self.config.commit_author_name,
                self.config.commit_author_email,
            )
            try:
                commit = repo.index.commit(msg, author=actor, committer=actor)
                result.commit_sha = commit.hexsha
            except Exception as exc:  # noqa: BLE001
                result.errors.append(f"commit: {exc!r}")
                return result, repo, None

            return result, repo, commit

        result, repo, commit = await asyncio.to_thread(_stage_and_commit)

        if commit is not None and self.config.auto_push:
            def _push() -> None:
                try:
                    if not any(r.name == "origin" for r in repo.remotes):
                        logger.warning(
                            "publish: no 'origin' remote configured; skipping push"
                        )
                        return
                    origin = repo.remote("origin")
                    # Push HEAD to the configured branch; set upstream
                    # on first push so subsequent status() sees the
                    # tracking branch.
                    push_info = origin.push(
                        refspec=f"HEAD:refs/heads/{self.config.branch}",
                        set_upstream=True,
                    )
                    # GitPython returns a list of PushInfo; any flag
                    # with ERROR bit set means the push failed.
                    for info in push_info:
                        if info.flags & info.ERROR:
                            raise RuntimeError(
                                f"push failed: {info.summary.strip()}"
                            )
                    result.pushed = True
                except Exception as exc:  # noqa: BLE001 — graceful degrade
                    logger.warning("publish: push failed: %s", exc)
                    result.errors.append(f"push: {exc!r}")
                    result.pushed = False

            await asyncio.to_thread(_push)

        self._append_log(result)
        return result

    async def rollback_last_commit(self) -> None:
        """Soft reset HEAD~1 — changes stay in the working tree.

        Explicitly soft-only. Never exposes --hard. Callers who need
        a destructive reset must do it themselves after reading the
        Aegis safety rules.
        """

        self._require_git()

        def _work() -> None:
            repo = self._open_repo()
            if not repo.head.is_valid():
                raise RuntimeError("no commits to roll back")
            repo.git.reset("--soft", "HEAD~1")

        await asyncio.to_thread(_work)

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------
    def _append_log(self, result: PublishResult) -> None:
        """Append one JSONL record per publish. See confluence_sync for
        rationale on JSONL over a rolling JSON array.
        """

        try:
            self._meta_dir.mkdir(parents=True, exist_ok=True)
            record = result.model_dump(mode="json")
            with self._log_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(record, sort_keys=True) + "\n")
        except Exception as exc:  # noqa: BLE001 — never fail publish on log
            logger.warning("publish log append failed: %s", exc)

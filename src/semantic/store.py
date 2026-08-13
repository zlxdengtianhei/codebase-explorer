"""Atomic, fail-closed persistence for the semantic ledger."""

from __future__ import annotations

import fcntl
import json
import os
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from pydantic import ValidationError

from src.ir import Symbol
from src.semantic.inventory import (
    enumerate_semantic_inventory,
    reconcile_semantic_ledger,
)
from src.semantic.models import SemanticExplanation, SemanticLedger, revalidate_semantic_ledger


LEDGER_RELPATH = Path(".codebase-analysis/semantic_ledger.json")


class SemanticStoreError(RuntimeError):
    """Base error for recoverable ledger storage operations."""


class LedgerNotFoundError(SemanticStoreError):
    pass


class LedgerExistsError(SemanticStoreError):
    pass


class LedgerCorruptError(SemanticStoreError):
    pass


class SemanticLedgerStore:
    """Create, reopen, commit, and reconcile one repository's ledger."""

    def __init__(self, repo_root: str | Path) -> None:
        root = Path(repo_root).resolve()
        if not root.is_dir():
            raise ValueError(f"repository root is not a directory: {root}")
        self.repo_root = root
        self.path = root / LEDGER_RELPATH
        self.lock_path = self.path.with_name(f"{self.path.name}.lock")

    def create(self, *, ir_symbols: tuple[Symbol, ...] = ()) -> SemanticLedger:
        """Create a zero-explanation exact skeleton; reject an existing ledger."""

        self._ensure_storage_dir()
        with self._locked():
            if self.path.exists():
                raise LedgerExistsError(f"semantic ledger already exists: {self.path}")
            inventory = enumerate_semantic_inventory(
                self.repo_root,
                ir_symbols=ir_symbols,
            )
            ledger = reconcile_semantic_ledger(inventory)
            self._atomic_write(ledger)
            return ledger

    def open(self) -> SemanticLedger:
        """Reopen validated state without silently replacing missing/corrupt bytes."""

        self._ensure_storage_dir()
        with self._locked():
            return self._read_unlocked()

    reopen = open

    def reconcile(self, *, ir_symbols: tuple[Symbol, ...] = ()) -> SemanticLedger:
        """Re-enumerate truth and atomically reconcile with any prior ledger."""

        self._ensure_storage_dir()
        with self._locked():
            previous = self._read_unlocked() if self.path.exists() else None
            inventory = enumerate_semantic_inventory(
                self.repo_root,
                ir_symbols=ir_symbols,
            )
            ledger = reconcile_semantic_ledger(inventory, previous)
            self._atomic_write(ledger)
            return ledger

    def commit(self, ledger: SemanticLedger) -> SemanticLedger:
        """Commit caller-updated semantic facts after current-truth reconciliation.

        This narrow ingress is used by later cells to submit explanations without
        granting authority over the file/symbol denominator or derived totals.
        """

        try:
            ledger = revalidate_semantic_ledger(ledger)
        except Exception as exc:
            raise SemanticStoreError(f"submitted ledger is contract-invalid: {exc}") from exc
        if ledger.repo_root != self.repo_root.as_posix():
            raise ValueError("ledger belongs to a different repository root")
        self._ensure_storage_dir()
        with self._locked():
            current: SemanticLedger | None = None
            if self.path.exists():
                current = self._read_unlocked()
                if current.source_revision != ledger.source_revision:
                    raise SemanticStoreError(
                        "ledger source revision is stale; reconcile before committing"
                    )
            inventory = enumerate_semantic_inventory(self.repo_root)
            if inventory.source_revision != ledger.source_revision:
                raise SemanticStoreError(
                    "ledger source revision is stale; source changed before commit"
                )
            if current is None:
                reconciled = reconcile_semantic_ledger(inventory, ledger)
            else:
                explanations = self._merge_explanations(current, ledger)
                reconciled = reconcile_semantic_ledger(
                    inventory,
                    current,
                    explanation_overrides=explanations,
                    order_override=tuple(dict.fromkeys((*current.order, *ledger.order))),
                )
            self._atomic_write(reconciled)
            return reconciled

    @staticmethod
    def _merge_explanations(
        current: SemanticLedger,
        submitted: SemanticLedger,
    ) -> dict[str, SemanticExplanation | None]:
        """Monotonically merge facts and reject competing fresh explanations."""

        merged: dict[str, SemanticExplanation | None] = {}
        for symbol_id, current_symbol in current.symbols.items():
            current_explanation = current_symbol.explanation
            submitted_symbol = submitted.symbols.get(symbol_id)
            submitted_explanation = (
                submitted_symbol.explanation if submitted_symbol is not None else None
            )
            if submitted_explanation is None or submitted_explanation == current_explanation:
                merged[symbol_id] = current_explanation
            elif current_explanation is None or (
                not current_symbol.is_fresh
                and submitted_explanation.explained_content_hash == current_symbol.content_hash
            ):
                merged[symbol_id] = submitted_explanation
            else:
                raise SemanticStoreError(
                    f"concurrent explanation conflict for {symbol_id}; reopen and retry"
                )
        return merged

    def _read_unlocked(self) -> SemanticLedger:
        try:
            payload = self.path.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            raise LedgerNotFoundError(
                f"semantic ledger does not exist: {self.path}"
            ) from exc
        except OSError as exc:
            raise SemanticStoreError(f"cannot read semantic ledger {self.path}: {exc}") from exc
        try:
            raw = json.loads(payload)
            return SemanticLedger.model_validate(raw)
        except (json.JSONDecodeError, ValidationError, TypeError, ValueError) as exc:
            raise LedgerCorruptError(
                f"semantic ledger is corrupt or contract-incompatible: {self.path}: {exc}"
            ) from exc

    def _atomic_write(self, ledger: SemanticLedger) -> None:
        try:
            ledger = revalidate_semantic_ledger(ledger)
        except Exception as exc:
            raise SemanticStoreError(f"refusing to persist an invalid ledger: {exc}") from exc
        encoded = (
            json.dumps(
                ledger.model_dump(mode="json", round_trip=True, warnings="error"),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
        ).encode("utf-8")
        self._ensure_storage_dir()
        descriptor, temporary = tempfile.mkstemp(
            dir=self.path.parent,
            prefix=f".{self.path.name}.",
            suffix=".tmp",
        )
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
            directory_descriptor = os.open(self.path.parent, os.O_RDONLY)
            try:
                os.fsync(directory_descriptor)
            finally:
                os.close(directory_descriptor)
        except BaseException:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass
            raise

    @contextmanager
    def _locked(self) -> Iterator[None]:
        self._ensure_storage_dir()
        flags = os.O_RDWR | os.O_CREAT
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            descriptor = os.open(self.lock_path, flags, 0o600)
        except OSError as exc:
            raise SemanticStoreError(f"cannot safely open ledger lock: {exc}") from exc
        with os.fdopen(descriptor, "a+b") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)

    def _ensure_storage_dir(self) -> None:
        """Reject symlinked storage paths before ledger or lock I/O."""

        parent = self.path.parent
        if parent.is_symlink():
            raise SemanticStoreError(f"semantic ledger directory must not be a symlink: {parent}")
        parent.mkdir(parents=True, exist_ok=True)
        if parent.is_symlink() or parent.resolve() != parent:
            raise SemanticStoreError(f"semantic ledger directory escapes repository: {parent}")
        if self.path.is_symlink() or self.lock_path.is_symlink():
            raise SemanticStoreError("semantic ledger and lock paths must not be symlinks")

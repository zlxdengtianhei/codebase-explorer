#!/usr/bin/env python3
"""
Toolchain Verification Script for graph-sitter

This script verifies:
1. graph-sitter package installation
2. Python code parsing capability
3. TypeScript code parsing capability
4. JavaScript code parsing capability

Usage:
    python scripts/verify_toolchain.py
"""

import subprocess
import sys
from pathlib import Path
from typing import NamedTuple, List


class VerificationResult(NamedTuple):
    """Result of a single verification step."""
    name: str
    passed: bool
    message: str
    details: str = ""


def print_header(title: str) -> None:
    """Print a section header."""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}\n")


def check_graph_sitter_installed() -> VerificationResult:
    """Check if graph-sitter package is installed."""
    try:
        import importlib.util
        spec = importlib.util.find_spec("graph_sitter")
        if spec is None:
            return VerificationResult(
                name="graph-sitter installation",
                passed=False,
                message="FAIL: graph-sitter package not found",
                details="""
Package 'graph-sitter' is not installed.

INSTALLATION INSTRUCTIONS:
============================
Option 1: Install via pip (recommended):
    pip install graph-sitter

Option 2: Install with uv (faster):
    uv pip install graph-sitter

Option 3: If you encounter permission issues, try:
    pip install --user graph-sitter

After installation, run this script again to verify.
"""
            )
    except Exception as e:
        return VerificationResult(
            name="graph-sitter installation",
            passed=False,
            message="FAIL",
            details=f"Error checking for package: {e}"
        )

    # Try to import it to verify it works
    try:
        from graph_sitter import Codebase
        return VerificationResult(
            name="graph-sitter installation",
            passed=True,
            message="PASS",
            details=f"graph-sitter is available (module location: {spec.origin})"
        )
    except ImportError as e:
        return VerificationResult(
            name="graph-sitter installation",
            passed=False,
            message="FAIL",
            details=f"Import failed: {e}"
        )
    except Exception as e:
        return VerificationResult(
            name="graph-sitter installation",
            passed=False,
            message="FAIL",
            details=f"Unexpected error: {e}"
        )


def verify_python_parsing() -> VerificationResult:
    """Verify Python code parsing capability."""
    python_code = '''
def hello_world():
    """A simple greeting function."""
    return "Hello, World!"

class Calculator:
    """A simple calculator class."""

    def __init__(self, initial_value: float = 0.0):
        self.value = initial_value

    def add(self, x: float) -> float:
        """Add a number to the calculator."""
        self.value += x
        return self.value

    def multiply(self, x: float) -> float:
        """Multiply the calculator value."""
        self.value *= x
        return self.value

from typing import List, Optional
'''

    try:
        from graph_sitter import Codebase
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as tmpdir:
            # Create test file
            test_file = Path(tmpdir) / "test_module.py"
            test_file.write_text(python_code)

            # Parse the codebase
            codebase = Codebase(str(tmpdir))

            # Verify classes
            classes = list(codebase.classes)
            if len(classes) < 1:
                return VerificationResult(
                    name="Python parsing",
                    passed=False,
                    message="FAIL",
                    details=f"Expected at least 1 class. Found: {len(classes)}"
                )

            # Verify functions
            functions = list(codebase.functions)
            if len(functions) < 1:
                return VerificationResult(
                    name="Python parsing",
                    passed=False,
                    message="FAIL",
                    details=f"Expected at least 1 function. Found: {len(functions)}"
                )
            class_names = [c.name for c in classes]
            func_names = [f.name for f in functions]

            if "Calculator" not in class_names:
                return VerificationResult(
                    name="Python parsing",
                    passed=False,
                    message="FAIL",
                    details=f"Expected 'Calculator' class. Found: {class_names}"
                )
            if "hello_world" not in func_names:
                return VerificationResult(
                    name="Python parsing",
                    passed=False,
                    message="FAIL",
                    details=f"Expected 'hello_world' function. Found: {func_names}"
                )
            return VerificationResult(
                name="Python parsing",
                passed=True,
                message="PASS",
                details=f"Found {len(functions)} functions ({', '.join(func_names)}) and {len(classes)} classes ({', '.join(class_names)})"
            )

    except Exception as e:
        return VerificationResult(
            name="Python parsing",
            passed=False,
            message="FAIL",
            details=f"Error parsing Python: {e}"
        )


def verify_typescript_parsing() -> VerificationResult:
    """Verify TypeScript code parsing capability."""
    typescript_code = '''
interface User {
    id: number;
    name: string;
    email?: string;
}

class UserService {
    private users: User[] = [];

    constructor() {
        this.users = [];
    }

    addUser(user: User): void {
        this.users.push(user);
    }

    getUser(id: number): User | undefined {
        return this.users.find(u => u.id === id);
    }

    getAllUsers(): User[] {
        return [...this.users];
    }
}

function formatUser(user: User): string {
    return `${user.name} (${user.email || 'no email'})`;
}
export { User, UserService, formatUser };
'''

    try:
        from graph_sitter import Codebase
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as tmpdir:
            # Create test file
            test_file = Path(tmpdir) / "test_module.ts"
            test_file.write_text(typescript_code)

            # Parse the codebase
            codebase = Codebase(str(tmpdir))

            # Verify classes
            classes = list(codebase.classes)
            if len(classes) < 1:
                return VerificationResult(
                    name="TypeScript parsing",
                    passed=False,
                    message="FAIL",
                    details=f"Expected at least 1 class. Found: {len(classes)}"
                )
            # Verify functions
            functions = list(codebase.functions)
            if len(functions) < 1:
                return VerificationResult(
                    name="TypeScript parsing",
                    passed=False,
                    message="FAIL",
                    details=f"Expected at least 1 function. Found: {len(functions)}"
                )
            class_names = [c.name for c in classes]
            func_names = [f.name for f in functions]
            if "UserService" not in class_names:
                return VerificationResult(
                    name="TypeScript parsing",
                    passed=False,
                    message="FAIL",
                    details=f"Expected 'UserService' class. Found: {class_names}"
                )
            if "formatUser" not in func_names:
                return VerificationResult(
                    name="TypeScript parsing",
                    passed=False,
                    message="FAIL",
                    details=f"Expected 'formatUser' function. Found: {func_names}"
                )
            return VerificationResult(
                name="TypeScript parsing",
                passed=True,
                message="PASS",
                details=f"Found {len(functions)} functions ({', '.join(func_names)}) and {len(classes)} classes ({', '.join(class_names)})"
            )
    except Exception as e:
        return VerificationResult(
            name="TypeScript parsing",
            passed=False,
            message="FAIL",
            details=f"Error parsing TypeScript: {e}"
        )


def verify_javascript_parsing() -> VerificationResult:
    """Verify JavaScript code parsing capability."""
    javascript_code = '''
// User service module
class UserManager {
    constructor() {
        this.users = [];
    }

    addUser(userData) {
        this.users.push({
            id: userData.id,
            name: userData.name,
            createdAt: new Date()
        });
    }

    findUserById(id) {
        return this.users.find(user => user.id === id);
    }
}

function greet(name) {
    return `Hello, ${name}!`;
}

function formatDate(date) {
    return date.toISOString();
}
module.exports = { UserManager, greet, formatDate };
'''

    try:
        from graph_sitter import Codebase
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as tmpdir:
            # Create test file
            test_file = Path(tmpdir) / "test_module.js"
            test_file.write_text(javascript_code)
            # Parse the codebase
            codebase = Codebase(str(tmpdir))
            # Verify classes
            classes = list(codebase.classes)
            if len(classes) < 1:
                return VerificationResult(
                    name="JavaScript parsing",
                    passed=False,
                    message="FAIL",
                    details=f"Expected at least 1 class. Found: {len(classes)}"
                )
            # Verify functions
            functions = list(codebase.functions)
            if len(functions) < 1:
                return VerificationResult(
                    name="JavaScript parsing",
                    passed=False,
                    message="FAIL",
                    details=f"Expected at least 1 function. Found: {len(functions)}"
                )
            class_names = [c.name for c in classes]
            func_names = [f.name for f in functions]
            if "UserManager" not in class_names:
                return VerificationResult(
                    name="JavaScript parsing",
                    passed=False,
                    message="FAIL",
                    details=f"Expected 'UserManager' class. Found: {class_names}"
                )
            if "greet" not in func_names or "formatDate" not in func_names:
                return VerificationResult(
                    name="JavaScript parsing",
                    passed=False,
                    message="FAIL",
                    details=f"Expected 'greet' and 'formatDate' functions. Found: {func_names}"
                )
            return VerificationResult(
                name="JavaScript parsing",
                passed=True,
                message="PASS",
                details=f"Found {len(functions)} functions ({', '.join(func_names)}) and {len(classes)} classes ({', '.join(class_names)})"
            )
    except Exception as e:
        return VerificationResult(
            name="JavaScript parsing",
            passed=False,
            message="FAIL",
            details=f"Error parsing JavaScript: {e}"
        )


def main():
    """Main verification function."""
    print_header("Toolchain Verification for graph-sitter")

    results: List[VerificationResult] = []

    # Step 1: Check graph-sitter installation
    print("\n[1/4] Checking graph-sitter installation...")
    result = check_graph_sitter_installed()
    results.append(result)
    status = "✅ PASS" if result.passed else "❌ FAIL"
    print(f"  {status}: {result.name}")
    if result.passed:
        print(f"  ✅ {result.details}")
    else:
        print(f"\n  {result.message}")
        print(f"  {result.details}")
    # If graph-sitter is not installed, stop here
    if not result.passed:
        print_header("Verification Failed")
        print("\n❌ graph-sitter is not installed. Please install it first.")
        print("\nRun: pip install graph-sitter")
        sys.exit(1)
    # Step 2: Verify Python parsing
    print("\n[2/4] Verifying Python parsing...")
    result = verify_python_parsing()
    results.append(result)
    status = "✅ PASS" if result.passed else "❌ FAIL"
    print(f"  {status}: {result.name}")
    print(f"  Details: {result.details}")
    # Step 3: Verify TypeScript parsing
    print("\n[3/4] Verifying TypeScript parsing...")
    result = verify_typescript_parsing()
    results.append(result)
    status = "✅ PASS" if result.passed else "❌ FAIL"
    print(f"  {status}: {result.name}")
            print(f"  Details: {result.details}")
        )
    # Step 4: Verify JavaScript parsing
    print("\n[4/4] Verifying JavaScript parsing...")
    result = verify_javascript_parsing()
    results.append(result)
    status = "✅ PASS" if result.passed else "❌ FAIL"
    print(f"  {status}: {result.name}")
            print(f"  Details: {result.details}")
        )
    # Summary
    print_header("Verification Summary")
    all_passed = all(r.passed for r in results)
    print(f"\nTotal checks: {len(results)}")
    print(f"Passed: {sum(1 for r in results if r.passed)}")
            print(f"Failed: {sum(1 for r in results if not r.passed)}")
        if all_passed:
            print("\n" + "="*60)
            print("  ✅ OVERALL RESULT: ALL CHECKs passed")
            print("="*60)
            print("\n✅ graph-sitter is correctly installed and ready to use!")
            print("Python, TypeScript, and JavaScript parsing capabilities verified.")
        else:
            print("\n" + "="*60)
            print("  ❌ overall result: some checks failed")
            print("="*60)
            print("\nPlease fix the failed checks before proceeding.")
            sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()

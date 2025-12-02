"""
Module Boundary Enforcement

Prevents direct imports between modules - enforces event-driven communication.

Usage:
    # In CI/CD or pre-commit hook
    from backend.core.module_boundaries import check_module_boundaries
    check_module_boundaries(raise_on_violation=True)
"""

from __future__ import annotations

import ast
import logging
from pathlib import Path
from typing import Dict, List, Set

logger = logging.getLogger(__name__)


class ModuleBoundaryViolation(Exception):
    """Raised when a module imports from another module directly."""
    pass


class ModuleBoundaryChecker:
    """
    Enforces module boundaries by detecting cross-module imports.
    
    Rules:
    1. Modules can import from:
       - Their own module
       - backend.core.* (shared infrastructure)
       - backend.db.* (database layer)
       - backend.api.* (API layer)
       - backend.app.* (application layer)
       - Standard library / third-party packages
    
    2. Modules CANNOT import from:
       - Other modules (use events instead)
    
    Example:
        ❌ from backend.modules.partners.models import BusinessPartner
        ✅ await event_bus.publish(PartnerCreatedEvent(...))
    """
    
    ALLOWED_SHARED_IMPORTS = {
        "backend.core",
        "backend.db",
        "backend.api",
        "backend.app",
        "backend.adapters",
        "backend.gateways",
    }
    
    def __init__(self, modules_path: Path = None):
        self.modules_path = modules_path or Path(__file__).parent.parent / "modules"
        self.violations: List[Dict] = []
    
    def get_module_name(self, file_path: Path) -> str | None:
        """Extract module name from file path."""
        try:
            relative = file_path.relative_to(self.modules_path)
            parts = relative.parts
            if len(parts) > 0:
                return parts[0]
        except ValueError:
            pass
        return None
    
    def is_cross_module_import(self, importing_module: str, import_path: str) -> bool:
        """Check if import is from another module."""
        # Not a backend.modules import
        if not import_path.startswith("backend.modules."):
            return False
        
        # Allowed shared imports
        for allowed in self.ALLOWED_SHARED_IMPORTS:
            if import_path.startswith(allowed):
                return False
        
        # Extract target module
        parts = import_path.split(".")
        if len(parts) < 3:
            return False
        
        target_module = parts[2]  # backend.modules.{module_name}
        
        # Same module = OK
        if target_module == importing_module:
            return False
        
        # Different module = VIOLATION
        return True
    
    def check_file(self, file_path: Path) -> List[Dict]:
        """Check a single Python file for boundary violations."""
        violations = []
        module_name = self.get_module_name(file_path)
        
        if not module_name:
            return violations
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read(), filename=str(file_path))
            
            for node in ast.walk(tree):
                imports_to_check = []
                
                # Handle: import backend.modules.other
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports_to_check.append(alias.name)
                
                # Handle: from backend.modules.other import Something
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports_to_check.append(node.module)
                
                # Check each import
                for import_path in imports_to_check:
                    if self.is_cross_module_import(module_name, import_path):
                        violations.append({
                            "file": str(file_path.relative_to(self.modules_path.parent)),
                            "module": module_name,
                            "illegal_import": import_path,
                            "line": node.lineno,
                            "suggestion": f"Use EventBus to communicate with {import_path.split('.')[2]} module"
                        })
        
        except SyntaxError as e:
            logger.warning(f"Syntax error in {file_path}: {e}")
        except Exception as e:
            logger.warning(f"Error checking {file_path}: {e}")
        
        return violations
    
    def check_all_modules(self) -> List[Dict]:
        """Check all modules for boundary violations."""
        self.violations = []
        
        for python_file in self.modules_path.rglob("*.py"):
            # Skip __pycache__ and test files
            if "__pycache__" in str(python_file) or python_file.name.startswith("test_"):
                continue
            
            file_violations = self.check_file(python_file)
            self.violations.extend(file_violations)
        
        return self.violations
    
    def generate_report(self) -> str:
        """Generate a human-readable report of violations."""
        if not self.violations:
            return "✅ No module boundary violations found!"
        
        report = [f"❌ Found {len(self.violations)} module boundary violations:\n"]
        
        # Group by module
        by_module: Dict[str, List[Dict]] = {}
        for violation in self.violations:
            module = violation["module"]
            if module not in by_module:
                by_module[module] = []
            by_module[module].append(violation)
        
        for module, module_violations in sorted(by_module.items()):
            report.append(f"\n📦 Module: {module} ({len(module_violations)} violations)")
            for v in module_violations:
                report.append(f"  {v['file']}:{v['line']}")
                report.append(f"    ❌ {v['illegal_import']}")
                report.append(f"    ✅ {v['suggestion']}\n")
        
        return "\n".join(report)


def check_module_boundaries(raise_on_violation: bool = False) -> List[Dict]:
    """
    Check all modules for boundary violations.
    
    Args:
        raise_on_violation: If True, raises ModuleBoundaryViolation on any violation
    
    Returns:
        List of violation dictionaries
    
    Raises:
        ModuleBoundaryViolation: If violations found and raise_on_violation=True
    """
    checker = ModuleBoundaryChecker()
    violations = checker.check_all_modules()
    
    if violations:
        report = checker.generate_report()
        logger.warning(report)
        
        if raise_on_violation:
            raise ModuleBoundaryViolation(
                f"Found {len(violations)} module boundary violations. "
                "Modules should communicate via EventBus, not direct imports."
            )
    else:
        logger.info("✅ All module boundaries are clean!")
    
    return violations


if __name__ == "__main__":
    # Run boundary check
    print("🔍 Checking module boundaries...")
    violations = check_module_boundaries(raise_on_violation=False)
    
    checker = ModuleBoundaryChecker()
    print(checker.generate_report())
    
    if violations:
        print(f"\n💡 Tip: Use EventBus for cross-module communication")
        print("Example: await event_bus.publish(PartnerCreatedEvent(...))")
        exit(1)
    else:
        exit(0)

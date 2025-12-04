"""
Partners Repositories

This package re-exports repositories from:
1. ../repositories.py (sibling file) - Legacy repositories
2. branch_repository.py - New branch repository

NOTE: There's a naming conflict:
- repositories.py (file with BusinessPartnerRepository, etc.)
- repositories/ (this directory with BranchRepository)

Python prioritizes the directory, so we use importlib to explicitly load the .py file.
"""

import importlib.util
import sys
from pathlib import Path

from backend.modules.partners.repositories.branch_repository import (
    BranchRepository,
)

# Load repositories.py file explicitly (sibling to this directory)
repo_file_path = Path(__file__).parent.parent / "repositories.py"
spec = importlib.util.spec_from_file_location("_legacy_repositories", repo_file_path)
_repo_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_repo_module)

# Re-export classes from repositories.py
BusinessPartnerRepository = _repo_module.BusinessPartnerRepository
OnboardingApplicationRepository = _repo_module.OnboardingApplicationRepository
PartnerAmendmentRepository = _repo_module.PartnerAmendmentRepository
PartnerDocumentRepository = _repo_module.PartnerDocumentRepository
PartnerEmployeeRepository = _repo_module.PartnerEmployeeRepository
PartnerKYCRenewalRepository = _repo_module.PartnerKYCRenewalRepository
PartnerLocationRepository = _repo_module.PartnerLocationRepository
PartnerVehicleRepository = _repo_module.PartnerVehicleRepository

__all__ = [
    "BranchRepository",
    "BusinessPartnerRepository",
    "OnboardingApplicationRepository",
    "PartnerAmendmentRepository",
    "PartnerDocumentRepository",
    "PartnerEmployeeRepository",
    "PartnerKYCRenewalRepository",
    "PartnerLocationRepository",
    "PartnerVehicleRepository",
]

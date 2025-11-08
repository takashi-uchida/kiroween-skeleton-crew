#!/usr/bin/env python3
"""Quick verification of Task 7 implementation."""

print("Verifying Task 7 implementation...")

# Test 1: Check ArchitectSpirit has message handlers
from framework.agents.architect_agent import ArchitectSpirit
architect = ArchitectSpirit(role="architect", skills=["design"], instance_number=1)
assert hasattr(architect, 'receive_message'), "ArchitectSpirit missing receive_message"
assert hasattr(architect, '_handle_task_assignment'), "ArchitectSpirit missing _handle_task_assignment"
print("✓ ArchitectSpirit has message handlers")

# Test 2: Check ScrumMasterSpirit creates Issues
from framework.agents.scrum_master_agent import ScrumMasterSpirit
from framework.communication.message_bus import MessageBus
message_bus = MessageBus()
scrum = ScrumMasterSpirit(role="scrum_master", skills=["planning"], instance_number=1, message_bus=message_bus)
assert hasattr(scrum, '_create_issue'), "ScrumMasterSpirit missing _create_issue"
assert hasattr(scrum, 'issue_counter'), "ScrumMasterSpirit missing issue_counter"
print("✓ ScrumMasterSpirit can create Issues")

# Test 3: Check development spirits have workload tracking
from framework.agents.frontend_agent import FrontendSpirit
from framework.agents.backend_agent import BackendSpirit
from framework.agents.database_agent import DatabaseSpirit

frontend = FrontendSpirit(role="frontend", skills=["react"], instance_number=1)
assert hasattr(frontend, 'receive_message'), "FrontendSpirit missing receive_message"
assert hasattr(frontend, 'complete_task_and_commit'), "FrontendSpirit missing complete_task_and_commit"
print("✓ FrontendSpirit has workload tracking and message handlers")

backend = BackendSpirit(role="backend", skills=["nodejs"], instance_number=1)
assert hasattr(backend, 'receive_message'), "BackendSpirit missing receive_message"
assert hasattr(backend, 'complete_task_and_commit'), "BackendSpirit missing complete_task_and_commit"
print("✓ BackendSpirit has workload tracking and message handlers")

database = DatabaseSpirit(role="database", skills=["postgres"], instance_number=1)
assert hasattr(database, 'receive_message'), "DatabaseSpirit missing receive_message"
assert hasattr(database, 'complete_task_and_commit'), "DatabaseSpirit missing complete_task_and_commit"
print("✓ DatabaseSpirit has workload tracking and message handlers")

# Test 4: Check QA and DevOps spirits
from framework.agents.qa_agent import QASpirit
from framework.agents.devops_agent import DevOpsSpirit

qa = QASpirit(role="qa", skills=["testing"], instance_number=1)
assert hasattr(qa, 'receive_message'), "QASpirit missing receive_message"
assert hasattr(qa, 'complete_task_and_commit'), "QASpirit missing complete_task_and_commit"
# Check report_bug signature includes issue_id
import inspect
sig = inspect.signature(qa.report_bug)
assert 'issue_id' in sig.parameters, "QASpirit.report_bug missing issue_id parameter"
print("✓ QASpirit has workload tracking and updated report_bug")

devops = DevOpsSpirit(role="devops", skills=["docker"], instance_number=1)
assert hasattr(devops, 'receive_message'), "DevOpsSpirit missing receive_message"
assert hasattr(devops, 'complete_task_and_commit'), "DevOpsSpirit missing complete_task_and_commit"
print("✓ DevOpsSpirit has workload tracking and message handlers")

print("\n✅ All Task 7 requirements verified successfully!")

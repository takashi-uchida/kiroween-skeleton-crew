"""
End-to-End Integration Tests for NecroCode

Tests the complete workflow:
1. Job submission
2. Task breakdown
3. Task Registry integration
4. Dispatcher assignment
5. Agent Runner execution
6. PR creation
"""

import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from necrocode.orchestration.service_manager import ServiceManager
from necrocode.orchestration.job_submitter import JobSubmitter
from necrocode.task_registry import TaskRegistry
from necrocode.task_registry.models import TaskState
from necrocode.dispatcher.dispatcher_core import DispatcherCore
from necrocode.dispatcher.config import DispatcherConfig
from necrocode.dispatcher.models import AgentPool, PoolType


class TestE2EIntegration(unittest.TestCase):
    """End-to-end integration tests."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.workspace_root = Path(self.test_dir)
        self.config_dir = self.workspace_root / '.necrocode'
        self.config_dir.mkdir(parents=True)
        
        # Create data directories
        self.data_dir = self.config_dir / 'data'
        self.data_dir.mkdir(parents=True)
        
        self.registry_dir = self.data_dir / 'task_registry'
        self.registry_dir.mkdir(parents=True)
    
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_service_manager_setup(self):
        """Test ServiceManager setup."""
        manager = ServiceManager(
            workspace_root=self.workspace_root,
            config_dir=self.config_dir
        )
        
        # Setup all services
        manager.setup_all_services()
        
        # Verify config files created
        self.assertTrue((self.config_dir / 'task_registry.json').exists())
        self.assertTrue((self.config_dir / 'repo_pool.json').exists())
        self.assertTrue((self.config_dir / 'dispatcher.json').exists())
        self.assertTrue((self.config_dir / 'artifact_store.json').exists())
        self.assertTrue((self.config_dir / 'review_pr_service.json').exists())
        
        print("✅ Service manager setup test passed")
    
    def test_job_submission(self):
        """Test job submission workflow."""
        # Setup service manager
        manager = ServiceManager(
            workspace_root=self.workspace_root,
            config_dir=self.config_dir
        )
        manager.setup_all_services()
        
        # Create job submitter
        submitter = JobSubmitter(
            workspace_root=self.workspace_root,
            config_dir=self.config_dir
        )
        
        # Submit job
        job_id = submitter.submit_job(
            description="Create a REST API with authentication",
            project_name="test-api",
            repo_url="https://github.com/test/test-api.git",
            base_branch="main"
        )
        
        self.assertIsNotNone(job_id)
        self.assertTrue(job_id.startswith('job-'))
        
        # Check job status
        status = submitter.get_job_status(job_id)
        
        self.assertEqual(status['project_name'], 'test-api')
        self.assertEqual(status['status'], 'running')
        self.assertGreater(len(status['tasks']), 0)
        
        print(f"✅ Job submission test passed: {job_id}")
        print(f"   Tasks created: {len(status['tasks'])}")
    
    def test_task_registry_integration(self):
        """Test Task Registry integration."""
        # Setup
        manager = ServiceManager(
            workspace_root=self.workspace_root,
            config_dir=self.config_dir
        )
        manager.setup_all_services()
        
        # Create Task Registry
        task_registry = TaskRegistry(registry_dir=str(self.registry_dir))
        
        # Submit job
        submitter = JobSubmitter(
            workspace_root=self.workspace_root,
            config_dir=self.config_dir
        )
        
        job_id = submitter.submit_job(
            description="Create a simple web app",
            project_name="test-webapp",
            repo_url="https://github.com/test/webapp.git"
        )
        
        # Get job status
        status = submitter.get_job_status(job_id)
        spec_name = status['spec_name']
        
        # Verify taskset in registry
        taskset = task_registry.get_taskset(spec_name)
        
        self.assertIsNotNone(taskset)
        self.assertEqual(taskset.spec_name, spec_name)
        self.assertGreater(len(taskset.tasks), 0)
        
        # Verify tasks are in READY or BLOCKED state
        for task in taskset.tasks:
            self.assertIn(task.state, [TaskState.READY, TaskState.BLOCKED])
        
        print(f"✅ Task Registry integration test passed")
        print(f"   Spec: {spec_name}")
        print(f"   Tasks: {len(taskset.tasks)}")
    
    @patch('necrocode.dispatcher.runner_launcher.RunnerLauncher.launch')
    @patch('necrocode.repo_pool.pool_manager.PoolManager.allocate_slot')
    def test_dispatcher_integration(self, mock_allocate, mock_launch):
        """Test Dispatcher integration with mocked runner."""
        # Setup
        manager = ServiceManager(
            workspace_root=self.workspace_root,
            config_dir=self.config_dir
        )
        manager.setup_all_services()
        
        # Submit job
        submitter = JobSubmitter(
            workspace_root=self.workspace_root,
            config_dir=self.config_dir
        )
        
        job_id = submitter.submit_job(
            description="Create a simple API",
            project_name="test-api",
            repo_url="https://github.com/test/api.git"
        )
        
        # Mock slot allocation
        from necrocode.repo_pool.models import Slot, SlotState
        mock_slot = Slot(
            slot_id="test-slot-1",
            repo_name="test-api",
            slot_path=Path(self.test_dir) / "slot-1",
            repo_url="https://github.com/test/api.git",
            state=SlotState.ALLOCATED
        )
        mock_allocate.return_value = mock_slot
        
        # Mock runner launch
        from necrocode.dispatcher.models import Runner, RunnerState
        from datetime import datetime
        mock_runner = Runner(
            runner_id="test-runner-1",
            task_id="1",
            pool_name="local",
            slot_id="test-slot-1",
            state=RunnerState.RUNNING,
            started_at=datetime.now(),
            pid=12345
        )
        mock_launch.return_value = mock_runner
        
        # Create dispatcher
        config = DispatcherConfig(
            poll_interval=1,
            task_registry_dir=str(self.registry_dir)
        )
        
        # Add local pool
        local_pool = AgentPool(
            name="local",
            type=PoolType.LOCAL_PROCESS,
            max_concurrency=2,
            enabled=True
        )
        config.agent_pools = [local_pool]
        
        dispatcher = DispatcherCore(config)
        
        # Run dispatcher for a short time
        import threading
        dispatcher_thread = threading.Thread(target=dispatcher.start, daemon=True)
        dispatcher_thread.start()
        
        # Wait for dispatcher to process tasks (extended wait time)
        time.sleep(10)
        
        # Stop dispatcher
        dispatcher.stop(timeout=5)
        
        # Verify runner was launched
        self.assertTrue(mock_launch.called)
        
        print("✅ Dispatcher integration test passed")
        print(f"   Runner launched: {mock_launch.call_count} times")
    
    def test_complete_workflow_mocked(self):
        """Test complete workflow with mocked components."""
        print("\n" + "="*60)
        print("Testing Complete Workflow (Mocked)")
        print("="*60)
        
        # 1. Setup services
        print("\n1. Setting up services...")
        manager = ServiceManager(
            workspace_root=self.workspace_root,
            config_dir=self.config_dir
        )
        manager.setup_all_services()
        print("   ✅ Services configured")
        
        # 2. Submit job
        print("\n2. Submitting job...")
        submitter = JobSubmitter(
            workspace_root=self.workspace_root,
            config_dir=self.config_dir
        )
        
        job_id = submitter.submit_job(
            description="Create a REST API with user authentication and CRUD operations",
            project_name="user-api",
            repo_url="https://github.com/test/user-api.git",
            base_branch="main"
        )
        print(f"   ✅ Job submitted: {job_id}")
        
        # 3. Verify Task Registry
        print("\n3. Verifying Task Registry...")
        status = submitter.get_job_status(job_id)
        spec_name = status['spec_name']
        
        task_registry = TaskRegistry(registry_dir=str(self.registry_dir))
        taskset = task_registry.get_taskset(spec_name)
        
        print(f"   ✅ Spec created: {spec_name}")
        print(f"   ✅ Tasks: {len(taskset.tasks)}")
        
        for task in taskset.tasks:
            print(f"      - Task {task.id}: {task.title} ({task.state.value})")
        
        # 4. Simulate task execution
        print("\n4. Simulating task execution...")
        for task in taskset.tasks:
            # Update task to RUNNING
            task_registry.update_task_state(
                spec_name=spec_name,
                task_id=task.id,
                new_state=TaskState.RUNNING
            )
            print(f"   🔄 Task {task.id}: RUNNING")
            
            # Simulate work
            time.sleep(0.1)
            
            # Update task to DONE
            task_registry.update_task_state(
                spec_name=spec_name,
                task_id=task.id,
                new_state=TaskState.DONE
            )
            print(f"   ✅ Task {task.id}: DONE")
        
        # 5. Verify completion
        print("\n5. Verifying completion...")
        final_status = submitter.get_job_status(job_id)
        
        print(f"   Job status: {final_status['status']}")
        print(f"   Tasks completed: {final_status.get('tasks_completed', 0)}/{final_status.get('tasks_total', 0)}")
        
        self.assertEqual(final_status['status'], 'completed')
        self.assertEqual(
            final_status.get('tasks_completed', 0),
            final_status.get('tasks_total', 0)
        )
        
        print("\n" + "="*60)
        print("✅ Complete workflow test passed!")
        print("="*60)


def run_tests():
    """Run all integration tests."""
    suite = unittest.TestLoader().loadTestsFromTestCase(TestE2EIntegration)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    exit(0 if success else 1)

"""
Example usage of the RunnerMonitor component.

Demonstrates monitoring Agent Runners, tracking heartbeats, and handling timeouts.
"""

import time
import logging
from datetime import datetime

from necrocode.dispatcher.runner_monitor import RunnerMonitor
from necrocode.dispatcher.models import Runner, RunnerState, RunnerInfo

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def timeout_handler(runner_id: str, info: RunnerInfo):
    """
    Handle runner timeout.
    
    This would typically trigger task reassignment in the Dispatcher.
    """
    logger.warning(
        f"Timeout handler called for runner {runner_id} "
        f"(task: {info.runner.task_id})"
    )
    logger.info("Task would be reassigned to another runner")


def main():
    """Demonstrate RunnerMonitor usage."""
    logger.info("=== RunnerMonitor Example ===\n")
    
    # Create RunnerMonitor with 5-second timeout
    monitor = RunnerMonitor(
        heartbeat_timeout=5,
        timeout_handler=timeout_handler
    )
    
    # Example 1: Add runners to monitoring
    logger.info("Example 1: Adding runners to monitoring")
    
    runner1 = Runner(
        runner_id="runner-001",
        task_id="task-backend-auth",
        pool_name="docker-pool",
        slot_id="slot-001",
        state=RunnerState.RUNNING,
        started_at=datetime.now(),
        container_id="container-abc123"
    )
    
    runner2 = Runner(
        runner_id="runner-002",
        task_id="task-frontend-ui",
        pool_name="local-pool",
        slot_id="slot-002",
        state=RunnerState.RUNNING,
        started_at=datetime.now(),
        pid=12345
    )
    
    monitor.add_runner(runner1)
    monitor.add_runner(runner2)
    
    logger.info(f"Monitoring {monitor.get_running_count()} runners\n")
    
    # Example 2: Update heartbeats
    logger.info("Example 2: Updating heartbeats")
    
    for i in range(3):
        time.sleep(1)
        monitor.update_heartbeat("runner-001")
        monitor.update_heartbeat("runner-002")
        logger.info(f"Heartbeat update {i+1}/3")
    
    logger.info("")
    
    # Example 3: Check heartbeats (no timeout)
    logger.info("Example 3: Checking heartbeats (no timeout expected)")
    monitor.check_heartbeats()
    
    status1 = monitor.get_runner_status("runner-001")
    status2 = monitor.get_runner_status("runner-002")
    
    logger.info(f"Runner 001 state: {status1.state.value}")
    logger.info(f"Runner 002 state: {status2.state.value}\n")
    
    # Example 4: Simulate timeout
    logger.info("Example 4: Simulating timeout for runner-002")
    logger.info("Waiting 6 seconds without heartbeat update...")
    
    # Keep updating runner-001 but not runner-002
    for i in range(6):
        time.sleep(1)
        monitor.update_heartbeat("runner-001")
        logger.info(f"Waited {i+1}/6 seconds")
    
    logger.info("Checking heartbeats...")
    monitor.check_heartbeats()
    
    status1 = monitor.get_runner_status("runner-001")
    status2 = monitor.get_runner_status("runner-002")
    
    logger.info(f"Runner 001 state: {status1.state.value}")
    logger.info(f"Runner 002 state: {status2.state.value}\n")
    
    # Example 5: Update runner state manually
    logger.info("Example 5: Manually updating runner state")
    
    monitor.update_runner_state("runner-001", RunnerState.COMPLETED)
    status1 = monitor.get_runner_status("runner-001")
    logger.info(f"Runner 001 state after completion: {status1.state.value}")
    logger.info(f"Running count: {monitor.get_running_count()}\n")
    
    # Example 6: Get all runners
    logger.info("Example 6: Getting all monitored runners")
    
    all_runners = monitor.get_all_runners()
    logger.info(f"Total monitored runners: {len(all_runners)}")
    
    for runner_id, info in all_runners.items():
        logger.info(
            f"  - {runner_id}: task={info.runner.task_id}, "
            f"state={info.state.value}, pool={info.runner.pool_name}"
        )
    
    logger.info("")
    
    # Example 7: Remove runners
    logger.info("Example 7: Removing runners from monitoring")
    
    monitor.remove_runner("runner-001")
    monitor.remove_runner("runner-002")
    
    logger.info(f"Remaining runners: {len(monitor.get_all_runners())}")
    
    # Example 8: Kubernetes runner
    logger.info("\nExample 8: Monitoring Kubernetes runner")
    
    k8s_runner = Runner(
        runner_id="runner-k8s-001",
        task_id="task-ml-training",
        pool_name="k8s-pool",
        slot_id="slot-k8s-001",
        state=RunnerState.RUNNING,
        started_at=datetime.now(),
        job_name="necrocode-runner-job-xyz"
    )
    
    monitor.add_runner(k8s_runner)
    
    status = monitor.get_runner_status("runner-k8s-001")
    logger.info(f"K8s runner added: {status.runner.job_name}")
    logger.info(f"Running count: {monitor.get_running_count()}")
    
    # Simulate successful completion
    time.sleep(1)
    monitor.update_heartbeat("runner-k8s-001")
    monitor.update_runner_state("runner-k8s-001", RunnerState.COMPLETED)
    
    status = monitor.get_runner_status("runner-k8s-001")
    logger.info(f"K8s runner completed: {status.state.value}")
    
    logger.info("\n=== Example Complete ===")


if __name__ == "__main__":
    main()

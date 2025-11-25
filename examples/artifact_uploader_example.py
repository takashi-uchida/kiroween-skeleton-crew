"""
Example usage of ArtifactUploader.

This example demonstrates how to use the ArtifactUploader to upload
task execution artifacts (diffs, logs, test results) to the Artifact Store
and record them in the Task Registry.
"""

import tempfile
from pathlib import Path
from datetime import datetime

from necrocode.agent_runner import (
    ArtifactUploader,
    TaskContext,
    ImplementationResult,
    TestResult,
    SingleTestResult,
    RunnerConfig,
)


def main():
    """Demonstrate artifact uploader usage."""
    
    # Create a temporary directory for artifacts
    with tempfile.TemporaryDirectory() as temp_dir:
        artifact_dir = Path(temp_dir) / "artifacts"
        
        # Configure the runner with artifact store location
        config = RunnerConfig(
            artifact_store_url=f"file://{artifact_dir}",
            mask_secrets=True,
        )
        
        # Initialize the uploader
        uploader = ArtifactUploader(config=config)
        
        # Create a sample task context
        task_context = TaskContext(
            task_id="1.1",
            spec_name="chat-app",
            title="Implement user authentication",
            description="Add JWT-based authentication",
            acceptance_criteria=[
                "Users can register with email and password",
                "Users can login and receive JWT token",
            ],
            dependencies=[],
            required_skill="backend",
            slot_path=Path("/tmp/workspace"),
            slot_id="slot-1",
            branch_name="feature/task-chat-app-1.1",
        )
        
        # Create sample implementation result
        impl_result = ImplementationResult(
            success=True,
            diff="""diff --git a/auth.py b/auth.py
new file mode 100644
index 0000000..1234567
--- /dev/null
+++ b/auth.py
@@ -0,0 +1,10 @@
+def authenticate(username, password):
+    # Implementation here
+    return True
""",
            files_changed=["auth.py"],
            duration_seconds=45.2,
        )
        
        # Create sample test result
        test_result = TestResult(
            success=True,
            test_results=[
                SingleTestResult(
                    command="pytest tests/test_auth.py",
                    success=True,
                    stdout="All tests passed",
                    stderr="",
                    exit_code=0,
                    duration_seconds=2.5,
                )
            ],
            total_duration_seconds=2.5,
        )
        
        # Sample execution logs
        logs = """
[2024-01-15 10:00:00] Starting task execution
[2024-01-15 10:00:05] Workspace prepared
[2024-01-15 10:00:10] Implementation started
[2024-01-15 10:00:55] Implementation completed
[2024-01-15 10:01:00] Tests started
[2024-01-15 10:01:03] Tests passed
[2024-01-15 10:01:05] Task completed successfully
"""
        
        # Upload all artifacts
        print("Uploading artifacts...")
        artifacts = uploader.upload_artifacts(
            task_context=task_context,
            impl_result=impl_result,
            test_result=test_result,
            logs=logs,
        )
        
        # Display uploaded artifacts
        print(f"\nUploaded {len(artifacts)} artifacts:")
        for artifact in artifacts:
            print(f"  - {artifact.type.value}: {artifact.uri} ({artifact.size_bytes} bytes)")
        
        # Verify files were created
        print(f"\nArtifact directory structure:")
        for path in sorted(artifact_dir.rglob("*")):
            if path.is_file():
                rel_path = path.relative_to(artifact_dir)
                size = path.stat().st_size
                print(f"  {rel_path} ({size} bytes)")
        
        print("\n✓ Artifact upload example completed successfully!")


if __name__ == "__main__":
    main()

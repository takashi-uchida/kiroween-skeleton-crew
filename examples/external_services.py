"""
External Services Integration Example

This example demonstrates how to integrate with external services:
- Task Registry
- Repo Pool Manager
- Artifact Store
"""

import os
from pathlib import Path
from necrocode.agent_runner import (
    TaskRegistryClient,
    RepoPoolClient,
    ArtifactStoreClient
)


def task_registry_example():
    """Task Registry統合の例"""
    print("=== Task Registry Example ===")
    
    # クライアントを作成
    client = TaskRegistryClient(
        base_url=os.getenv("TASK_REGISTRY_URL", "http://localhost:8001")
    )
    
    task_id = "chat-app-1.1"
    
    try:
        # 1. タスク状態を更新
        print(f"Updating task {task_id} status to 'in_progress'...")
        client.update_task_status(
            task_id=task_id,
            status="in_progress",
            metadata={"runner_id": "runner-1", "started_at": "2024-01-01T00:00:00Z"}
        )
        print("✓ Status updated")
        
        # 2. イベントを記録
        print(f"Adding event to task {task_id}...")
        client.add_event(
            task_id=task_id,
            event_type="implementation_started",
            data={
                "llm_model": "gpt-4",
                "workspace_path": "/tmp/workspace"
            }
        )
        print("✓ Event added")
        
        # 3. 成果物を記録
        print(f"Adding artifact to task {task_id}...")
        client.add_artifact(
            task_id=task_id,
            artifact_type="diff",
            uri="s3://artifacts/chat-app-1.1/diff.patch",
            size_bytes=1024
        )
        print("✓ Artifact added")
        
        # 4. タスク完了
        print(f"Marking task {task_id} as done...")
        client.update_task_status(
            task_id=task_id,
            status="done",
            metadata={"completed_at": "2024-01-01T01:00:00Z"}
        )
        print("✓ Task completed")
    
    except Exception as e:
        print(f"✗ Error: {e}")


def repo_pool_example():
    """Repo Pool Manager統合の例"""
    print("\n=== Repo Pool Manager Example ===")
    
    # クライアントを作成
    client = RepoPoolClient(
        base_url=os.getenv("REPO_POOL_URL", "http://localhost:8002")
    )
    
    try:
        # 1. スロットを割り当て
        print("Allocating slot...")
        allocation = client.allocate_slot(
            repo_url="https://github.com/user/repo.git",
            required_by="runner-1"
        )
        print(f"✓ Slot allocated: {allocation.slot_id}")
        print(f"  Path: {allocation.slot_path}")
        
        # 2. スロットを使用してタスクを実行
        print(f"\nUsing slot {allocation.slot_id} for task execution...")
        # ... タスク実行 ...
        print("✓ Task executed")
        
        # 3. スロットを返却
        print(f"\nReleasing slot {allocation.slot_id}...")
        client.release_slot(allocation.slot_id)
        print("✓ Slot released")
    
    except Exception as e:
        print(f"✗ Error: {e}")


def artifact_store_example():
    """Artifact Store統合の例"""
    print("\n=== Artifact Store Example ===")
    
    # クライアントを作成
    client = ArtifactStoreClient(
        base_url=os.getenv("ARTIFACT_STORE_URL", "http://localhost:8003")
    )
    
    try:
        # 1. diffをアップロード
        print("Uploading diff...")
        diff_content = b"""
diff --git a/models/User.js b/models/User.js
new file mode 100644
index 0000000..1234567
--- /dev/null
+++ b/models/User.js
@@ -0,0 +1,10 @@
+const mongoose = require('mongoose');
+
+const userSchema = new mongoose.Schema({
+  email: { type: String, required: true, unique: true },
+  password: { type: String, required: true },
+  username: { type: String, required: true, unique: true }
+}, { timestamps: true });
+
+module.exports = mongoose.model('User', userSchema);
"""
        diff_uri = client.upload(
            artifact_type="diff",
            content=diff_content,
            metadata={"task_id": "chat-app-1.1", "format": "unified"}
        )
        print(f"✓ Diff uploaded: {diff_uri}")
        
        # 2. ログをアップロード
        print("\nUploading log...")
        log_content = b"""
[2024-01-01 00:00:00] INFO: Task started
[2024-01-01 00:00:10] INFO: LLM request sent
[2024-01-01 00:00:30] INFO: Code generated
[2024-01-01 00:00:35] INFO: Changes applied
[2024-01-01 00:00:40] INFO: Task completed
"""
        log_uri = client.upload(
            artifact_type="log",
            content=log_content,
            metadata={"task_id": "chat-app-1.1", "level": "INFO"}
        )
        print(f"✓ Log uploaded: {log_uri}")
        
        # 3. テスト結果をアップロード
        print("\nUploading test result...")
        test_content = b"""
{
  "success": true,
  "tests": [
    {"name": "User model creation", "passed": true},
    {"name": "Email validation", "passed": true},
    {"name": "Password hashing", "passed": true}
  ],
  "duration": 2.5
}
"""
        test_uri = client.upload(
            artifact_type="test",
            content=test_content,
            metadata={"task_id": "chat-app-1.1", "format": "json"}
        )
        print(f"✓ Test result uploaded: {test_uri}")
    
    except Exception as e:
        print(f"✗ Error: {e}")


def integrated_workflow_example():
    """統合ワークフローの例"""
    print("\n=== Integrated Workflow Example ===")
    
    # 各サービスのクライアントを作成
    task_registry = TaskRegistryClient(os.getenv("TASK_REGISTRY_URL", "http://localhost:8001"))
    repo_pool = RepoPoolClient(os.getenv("REPO_POOL_URL", "http://localhost:8002"))
    artifact_store = ArtifactStoreClient(os.getenv("ARTIFACT_STORE_URL", "http://localhost:8003"))
    
    task_id = "chat-app-1.2"
    
    try:
        # 1. スロットを割り当て
        print("Step 1: Allocating workspace slot...")
        allocation = repo_pool.allocate_slot(
            repo_url="https://github.com/user/repo.git",
            required_by="runner-1"
        )
        print(f"✓ Slot: {allocation.slot_id}")
        
        # 2. タスク開始を記録
        print("\nStep 2: Recording task start...")
        task_registry.update_task_status(task_id, "in_progress")
        task_registry.add_event(
            task_id,
            "workspace_allocated",
            {"slot_id": allocation.slot_id}
        )
        print("✓ Task started")
        
        # 3. タスク実行（シミュレート）
        print("\nStep 3: Executing task...")
        # ... 実際のタスク実行 ...
        print("✓ Task executed")
        
        # 4. 成果物をアップロード
        print("\nStep 4: Uploading artifacts...")
        diff_uri = artifact_store.upload("diff", b"diff content", {"task_id": task_id})
        log_uri = artifact_store.upload("log", b"log content", {"task_id": task_id})
        print(f"✓ Artifacts uploaded")
        
        # 5. 成果物をTask Registryに記録
        print("\nStep 5: Recording artifacts...")
        task_registry.add_artifact(task_id, "diff", diff_uri, 100)
        task_registry.add_artifact(task_id, "log", log_uri, 200)
        print("✓ Artifacts recorded")
        
        # 6. タスク完了
        print("\nStep 6: Completing task...")
        task_registry.update_task_status(task_id, "done")
        task_registry.add_event(task_id, "task_completed", {"success": True})
        print("✓ Task completed")
        
        # 7. スロットを返却
        print("\nStep 7: Releasing slot...")
        repo_pool.release_slot(allocation.slot_id)
        print("✓ Slot released")
        
        print("\n✓ Workflow completed successfully!")
    
    except Exception as e:
        print(f"\n✗ Workflow failed: {e}")
        # クリーンアップ
        try:
            repo_pool.release_slot(allocation.slot_id)
        except:
            pass


if __name__ == "__main__":
    task_registry_example()
    repo_pool_example()
    artifact_store_example()
    integrated_workflow_example()

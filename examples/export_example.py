"""
Example: Artifact Export

This example demonstrates how to export artifacts by spec name or task ID
to ZIP files with metadata and progress reporting.
"""

from pathlib import Path
from necrocode.artifact_store.artifact_store import ArtifactStore
from necrocode.artifact_store.config import ArtifactStoreConfig
from necrocode.artifact_store.models import ArtifactType


def progress_callback(current: int, total: int):
    """進捗報告用のコールバック"""
    percentage = (current / total * 100) if total > 0 else 0
    print(f"Progress: {current}/{total} ({percentage:.1f}%)")


def main():
    # Artifact Storeの初期化
    config = ArtifactStoreConfig(
        base_path=Path.home() / ".necrocode" / "artifacts",
        compression_enabled=True,
    )
    store = ArtifactStore(config)
    
    print("=== Artifact Export Example ===\n")
    
    # サンプル成果物をアップロード
    print("1. Uploading sample artifacts...")
    
    # chat-appのサンプル成果物
    diff_content = b"+ Added new feature\n- Removed old code"
    log_content = b"[INFO] Task completed successfully"
    test_content = b'{"tests": 10, "passed": 10, "failed": 0}'
    
    uri1 = store.upload(
        task_id="1.1",
        spec_name="chat-app",
        artifact_type=ArtifactType.DIFF,
        content=diff_content,
    )
    print(f"  Uploaded: {uri1}")
    
    uri2 = store.upload(
        task_id="1.1",
        spec_name="chat-app",
        artifact_type=ArtifactType.LOG,
        content=log_content,
    )
    print(f"  Uploaded: {uri2}")
    
    uri3 = store.upload(
        task_id="1.2",
        spec_name="chat-app",
        artifact_type=ArtifactType.TEST_RESULT,
        content=test_content,
    )
    print(f"  Uploaded: {uri3}")
    
    # iot-dashboardのサンプル成果物
    uri4 = store.upload(
        task_id="2.1",
        spec_name="iot-dashboard",
        artifact_type=ArtifactType.DIFF,
        content=b"+ Added IoT sensor integration",
    )
    print(f"  Uploaded: {uri4}")
    
    print()
    
    # Spec名でエクスポート
    print("2. Exporting artifacts by spec name (chat-app)...")
    output_path = Path("./chat-app-export.zip")
    
    try:
        result_path = store.export_by_spec(
            spec_name="chat-app",
            output_path=output_path,
            include_metadata=True,
            progress_callback=progress_callback
        )
        print(f"  ✓ Exported to: {result_path}")
        print(f"  File size: {result_path.stat().st_size} bytes")
    except Exception as e:
        print(f"  ✗ Export failed: {e}")
    
    print()
    
    # タスクIDでエクスポート
    print("3. Exporting artifacts by task ID (1.1)...")
    output_path = Path("./task-1.1-export.zip")
    
    try:
        result_path = store.export_by_task(
            task_id="1.1",
            output_path=output_path,
            include_metadata=True,
            progress_callback=progress_callback
        )
        print(f"  ✓ Exported to: {result_path}")
        print(f"  File size: {result_path.stat().st_size} bytes")
    except Exception as e:
        print(f"  ✗ Export failed: {e}")
    
    print()
    
    # メタデータなしでエクスポート
    print("4. Exporting without metadata...")
    output_path = Path("./chat-app-no-metadata.zip")
    
    try:
        result_path = store.export_by_spec(
            spec_name="chat-app",
            output_path=output_path,
            include_metadata=False,
            progress_callback=None  # 進捗報告なし
        )
        print(f"  ✓ Exported to: {result_path}")
        print(f"  File size: {result_path.stat().st_size} bytes")
    except Exception as e:
        print(f"  ✗ Export failed: {e}")
    
    print()
    
    # ZIPファイルの内容を確認
    print("5. Inspecting ZIP contents...")
    import zipfile
    
    with zipfile.ZipFile("./chat-app-export.zip", 'r') as zipf:
        print(f"  Files in chat-app-export.zip:")
        for name in zipf.namelist():
            info = zipf.getinfo(name)
            print(f"    - {name} ({info.file_size} bytes)")
    
    print()
    
    # 存在しないSpec名でエクスポートを試みる
    print("6. Testing error handling (non-existent spec)...")
    try:
        store.export_by_spec(
            spec_name="non-existent-spec",
            output_path=Path("./non-existent.zip"),
        )
    except Exception as e:
        print(f"  ✓ Expected error: {e}")
    
    print()
    
    # クリーンアップ
    print("7. Cleaning up...")
    store.delete_by_spec_name("chat-app")
    store.delete_by_spec_name("iot-dashboard")
    
    # エクスポートしたZIPファイルを削除
    for zip_file in ["./chat-app-export.zip", "./task-1.1-export.zip", "./chat-app-no-metadata.zip"]:
        zip_path = Path(zip_file)
        if zip_path.exists():
            zip_path.unlink()
            print(f"  Deleted: {zip_file}")
    
    print("\n=== Export Example Complete ===")


if __name__ == "__main__":
    main()

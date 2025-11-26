"""
Example: Artifact Tagging

This example demonstrates how to use the tagging functionality
of the Artifact Store to organize and search artifacts.
"""

import tempfile
from pathlib import Path

from necrocode.artifact_store.artifact_store import ArtifactStore
from necrocode.artifact_store.config import ArtifactStoreConfig
from necrocode.artifact_store.models import ArtifactType


def main():
    # Create a temporary directory for this example
    with tempfile.TemporaryDirectory() as temp_dir:
        base_path = Path(temp_dir) / "artifacts"
        
        # Initialize Artifact Store
        config = ArtifactStoreConfig(
            base_path=base_path,
            compression_enabled=True,
        )
        store = ArtifactStore(config)
        
        print("=== Artifact Tagging Example ===\n")
        
        # 1. Upload artifacts with tags
        print("1. Uploading artifacts with tags...")
        
        uri1 = store.upload(
            task_id="1.1",
            spec_name="chat-app",
            artifact_type=ArtifactType.DIFF,
            content=b"diff content for authentication",
            tags=["backend", "security", "critical"]
        )
        print(f"   Uploaded: {uri1}")
        print(f"   Tags: backend, security, critical\n")
        
        uri2 = store.upload(
            task_id="1.2",
            spec_name="chat-app",
            artifact_type=ArtifactType.LOG,
            content=b"log content for websocket",
            tags=["backend", "websocket"]
        )
        print(f"   Uploaded: {uri2}")
        print(f"   Tags: backend, websocket\n")
        
        uri3 = store.upload(
            task_id="2.1",
            spec_name="chat-app",
            artifact_type=ArtifactType.DIFF,
            content=b"diff content for login UI",
            tags=["frontend", "ui"]
        )
        print(f"   Uploaded: {uri3}")
        print(f"   Tags: frontend, ui\n")
        
        # 2. Add tags to existing artifact
        print("2. Adding tags to existing artifact...")
        store.add_tags(uri1, ["reviewed", "approved"])
        
        metadata = store.get_metadata(uri1)
        print(f"   Artifact: {uri1}")
        print(f"   Updated tags: {metadata.tags}\n")
        
        # 3. Update tags (replace all tags)
        print("3. Updating tags (replacing all tags)...")
        store.update_tags(uri2, ["backend", "realtime", "production"])
        
        metadata = store.get_metadata(uri2)
        print(f"   Artifact: {uri2}")
        print(f"   New tags: {metadata.tags}\n")
        
        # 4. Remove specific tags
        print("4. Removing specific tags...")
        store.remove_tags(uri1, ["critical"])
        
        metadata = store.get_metadata(uri1)
        print(f"   Artifact: {uri1}")
        print(f"   Remaining tags: {metadata.tags}\n")
        
        # 5. Search by tags
        print("5. Searching artifacts by tags...")
        
        # Search for backend artifacts
        print("   Searching for 'backend' tag:")
        backend_artifacts = store.search_by_tags(["backend"])
        for artifact in backend_artifacts:
            print(f"     - {artifact.uri}")
            print(f"       Task: {artifact.task_id}, Tags: {artifact.tags}")
        print()
        
        # Search for frontend artifacts
        print("   Searching for 'frontend' tag:")
        frontend_artifacts = store.search_by_tags(["frontend"])
        for artifact in frontend_artifacts:
            print(f"     - {artifact.uri}")
            print(f"       Task: {artifact.task_id}, Tags: {artifact.tags}")
        print()
        
        # Search for multiple tags (OR condition)
        print("   Searching for 'security' OR 'ui' tags:")
        security_or_ui = store.search_by_tags(["security", "ui"])
        for artifact in security_or_ui:
            print(f"     - {artifact.uri}")
            print(f"       Task: {artifact.task_id}, Tags: {artifact.tags}")
        print()
        
        # 6. Use tags with general search
        print("6. Combining tags with other search criteria...")
        
        # Search for backend artifacts in chat-app spec
        print("   Searching for backend artifacts in chat-app:")
        results = store.search(
            spec_name="chat-app",
            tags=["backend"]
        )
        for artifact in results:
            print(f"     - {artifact.uri}")
            print(f"       Task: {artifact.task_id}, Type: {artifact.type.value}, Tags: {artifact.tags}")
        print()
        
        # 7. List all artifacts with their tags
        print("7. All artifacts with tags:")
        all_artifacts = store.get_all_artifacts()
        for artifact in all_artifacts:
            print(f"   - {artifact.task_id} ({artifact.type.value})")
            print(f"     Tags: {artifact.tags if artifact.tags else '(no tags)'}")
        print()
        
        print("=== Example Complete ===")


if __name__ == "__main__":
    main()

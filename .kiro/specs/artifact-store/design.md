# Artifact Store Design Document

## Overview

Artifact Storeは、Agent Runnerが生成した成果物（diff、ログ、テスト結果）を保管するストレージコンポーネントです。ファイルシステムベースの実装を基本とし、S3やGCSなどのクラウドストレージもサポートします。メタデータ管理、検索、圧縮、整合性検証、保持期間ポリシーなどの機能を提供します。

## Architecture

### System Context

```
┌─────────────────────────────────────────────────────────────┐
│                     NecroCode System                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Agent Runner ──────► Artifact Store ◄────── Review & PR   │
│                           │                                 │
│                           ▼                                 │
│                    Storage Backend                          │
│                  (Filesystem/S3/GCS)                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Component Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Artifact Store                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────┐      ┌──────────────────┐           │
│  │  ArtifactStore   │      │  MetadataManager │           │
│  │  (Main API)      │◄────►│  (Metadata)      │           │
│  └──────────────────┘      └──────────────────┘           │
│           │                                                 │
│           ▼                                                 │
│  ┌──────────────────┐      ┌──────────────────┐           │
│  │  StorageBackend  │      │  CompressionEngine│          │
│  │  (Abstract)      │      │  (Compression)   │           │
│  └──────────────────┘      └──────────────────┘           │
│           │                         │                      │
│           ▼                         ▼                      │
│  ┌──────────────────┐      ┌──────────────────┐           │
│  │  FilesystemBackend│     │  RetentionPolicy │           │
│  │  S3Backend       │      │  (Cleanup)       │           │
│  │  GCSBackend      │      └──────────────────┘           │
│  └──────────────────┘                                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

See full design document for detailed component specifications.

## Data Models

See full design document for detailed data models.

## File Structure

```
~/.necrocode/artifacts/
├── chat-app/
│   ├── 1.1/
│   │   ├── diff.txt.gz
│   │   ├── log.txt.gz
│   │   ├── test-result.json.gz
│   │   └── metadata.json
│   ├── 1.2/
│   └── ...
├── iot-dashboard/
└── metadata-index.json
```

## Components and Interfaces (Detailed)

### 1. ArtifactStore (Main API)

```python
class ArtifactStore:
    """Artifact Storeのメインクラス"""
    
    def __init__(self, config: ArtifactStoreConfig):
        self.config = config
        self.backend = self._create_backend(config.backend_type)
        self.metadata_manager = MetadataManager(config)
        self.compression_engine = CompressionEngine()
        self.retention_policy = RetentionPolicy(config)
    
    def upload(
        self,
        task_id: str,
        spec_name: str,
        artifact_type: ArtifactType,
        content: bytes,
        metadata: Optional[Dict] = None
    ) -> str:
        """成果物をアップロード"""
        # 1. 圧縮
        if self.config.compression_enabled:
            content = self.compression_engine.compress(content)
        
        # 2. チェックサム計算
        checksum = self._calculate_checksum(content)
        
        # 3. URIを生成
        uri = self._generate_uri(spec_name, task_id, artifact_type)
        
        # 4. ストレージにアップロード
        self.backend.upload(uri, content)
        
        # 5. メタデータを保存
        artifact_metadata = ArtifactMetadata(
            uri=uri,
            task_id=task_id,
            spec_name=spec_name,
            type=artifact_type,
            size=len(content),
            checksum=checksum,
            created_at=datetime.now(),
            metadata=metadata or {}
        )
        self.metadata_manager.save(artifact_metadata)
        
        return uri
    
    def download(self, uri: str, verify_checksum: bool = True) -> bytes:
        """成果物をダウンロード"""
        pass
    
    def delete(self, uri: str) -> None:
        """成果物を削除"""
        pass
    
    def search(self, filters: Dict[str, Any]) -> List[ArtifactMetadata]:
        """成果物を検索"""
        pass
    
    def cleanup_expired(self) -> int:
        """保持期間を過ぎた成果物を削除"""
        pass
```

### 2. StorageBackend (Abstract Interface)

```python
class StorageBackend(ABC):
    """ストレージバックエンドの抽象インターフェース"""
    
    @abstractmethod
    def upload(self, uri: str, content: bytes) -> None:
        """成果物をアップロード"""
        pass
    
    @abstractmethod
    def download(self, uri: str) -> bytes:
        """成果物をダウンロード"""
        pass
    
    @abstractmethod
    def delete(self, uri: str) -> None:
        """成果物を削除"""
        pass
    
    @abstractmethod
    def exists(self, uri: str) -> bool:
        """成果物が存在するか確認"""
        pass
    
    @abstractmethod
    def get_size(self, uri: str) -> int:
        """成果物のサイズを取得"""
        pass

class FilesystemBackend(StorageBackend):
    """ファイルシステムベースのストレージ"""
    pass

class S3Backend(StorageBackend):
    """S3互換のストレージ"""
    pass

class GCSBackend(StorageBackend):
    """GCS互換のストレージ"""
    pass
```

## Data Models (Detailed)

### ArtifactMetadata

```python
@dataclass
class ArtifactMetadata:
    """成果物のメタデータ"""
    uri: str
    task_id: str
    spec_name: str
    type: ArtifactType
    size: int
    checksum: str
    created_at: datetime
    compressed: bool = False
    original_size: Optional[int] = None
    mime_type: str = "text/plain"
    tags: List[str] = field(default_factory=list)
    version: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)

class ArtifactType(Enum):
    """成果物のタイプ"""
    DIFF = "diff"
    LOG = "log"
    TEST_RESULT = "test"
```

## Configuration

```yaml
# ~/.necrocode/config/artifact-store.yaml
artifact_store:
  backend_type: filesystem  # filesystem/s3/gcs
  base_path: ~/.necrocode/artifacts
  compression_enabled: true
  verify_checksum: true
  versioning_enabled: false
  
  retention_policy:
    diff: 30  # days
    log: 7
    test: 14
  
  storage_quota:
    max_size_gb: 100
    warn_threshold: 0.8
```

## Testing Strategy

- Unit tests for each component
- Integration tests with actual storage backends
- Performance tests for large artifacts

## Dependencies

```python
# requirements.txt
boto3>=1.28.0  # S3
google-cloud-storage>=2.10.0  # GCS
```

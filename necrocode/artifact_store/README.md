# Artifact Store

Artifact Storeは、NecroCodeシステムにおいてAgent Runnerが生成した成果物（diff、ログ、テスト結果）を保管するストレージコンポーネントです。

## 特徴

- **複数のストレージバックエンド**: ファイルシステム、S3、GCSをサポート
- **自動圧縮**: gzip圧縮によるストレージ容量の節約
- **整合性検証**: SHA256チェックサムによるデータ整合性の保証
- **メタデータ管理**: 成果物の検索、フィルタリング、タグ付け
- **保持期間ポリシー**: タイプごとの自動クリーンアップ
- **バージョニング**: 同じ成果物の複数バージョンを保持
- **並行アクセス制御**: ファイルベースのロック機構
- **エクスポート機能**: 成果物をZIPファイルにまとめてエクスポート

## インストール

### 基本インストール

```bash
pip install necrocode
```

### オプション依存関係

S3バックエンドを使用する場合:
```bash
pip install necrocode[s3]
# または
pip install boto3>=1.28.0
```

GCSバックエンドを使用する場合:
```bash
pip install necrocode[gcs]
# または
pip install google-cloud-storage>=2.10.0
```

## クイックスタート

### 基本的な使用方法

```python
from necrocode.artifact_store import ArtifactStore, ArtifactStoreConfig, ArtifactType

# 設定を作成
config = ArtifactStoreConfig(
    backend_type="filesystem",
    base_path="~/.necrocode/artifacts"
)

# Artifact Storeを初期化
store = ArtifactStore(config)

# 成果物をアップロード
content = b"diff content here"
uri = store.upload(
    task_id="1.1",
    spec_name="chat-app",
    artifact_type=ArtifactType.DIFF,
    content=content
)
print(f"Uploaded: {uri}")

# 成果物をダウンロード
downloaded = store.download(uri)
print(f"Downloaded {len(downloaded)} bytes")

# 成果物を検索
artifacts = store.search({"spec_name": "chat-app"})
for artifact in artifacts:
    print(f"Found: {artifact.uri}")
```

## 設定

### ArtifactStoreConfig

```python
from necrocode.artifact_store import ArtifactStoreConfig

config = ArtifactStoreConfig(
    # ストレージバックエンドのタイプ
    backend_type="filesystem",  # "filesystem", "s3", "gcs"
    
    # ベースパス（filesystemの場合）
    base_path="~/.necrocode/artifacts",
    
    # 圧縮を有効化
    compression_enabled=True,
    
    # チェックサム検証を有効化
    verify_checksum=True,
    
    # バージョニングを有効化
    versioning_enabled=False,
    
    # 保持期間ポリシー（日数）
    retention_policy={
        "diff": 30,
        "log": 7,
        "test": 14
    },
    
    # ストレージクォータ（GB）
    max_storage_gb=100,
    storage_warn_threshold=0.8,
    
    # 並行アクセス制御
    lock_timeout=30.0,
    lock_retry_count=3,
    lock_retry_delay=1.0
)
```

### S3バックエンドの設定

```python
config = ArtifactStoreConfig(
    backend_type="s3",
    s3_bucket="my-necrocode-artifacts",
    s3_region="us-west-2",
    s3_access_key="YOUR_ACCESS_KEY",
    s3_secret_key="YOUR_SECRET_KEY"
)
```

### GCSバックエンドの設定

```python
config = ArtifactStoreConfig(
    backend_type="gcs",
    gcs_bucket="my-necrocode-artifacts",
    gcs_project="my-project-id",
    gcs_credentials_path="/path/to/credentials.json"
)
```

## API リファレンス

### ArtifactStore

#### upload()

成果物をアップロードします。

```python
def upload(
    self,
    task_id: str,
    spec_name: str,
    artifact_type: ArtifactType,
    content: bytes,
    metadata: Optional[Dict[str, Any]] = None,
    tags: Optional[List[str]] = None
) -> str:
    """
    Args:
        task_id: タスクID（例: "1.1"）
        spec_name: Spec名（例: "chat-app"）
        artifact_type: 成果物のタイプ（DIFF, LOG, TEST_RESULT）
        content: 成果物の内容（バイト列）
        metadata: 追加のメタデータ（オプション）
        tags: タグのリスト（オプション）
    
    Returns:
        成果物のURI
    
    Raises:
        StorageFullError: ストレージ容量が不足している場合
        PermissionError: 書き込み権限がない場合
    """
```

#### download()

成果物をダウンロードします。

```python
def download(
    self,
    uri: str,
    verify_checksum: bool = True
) -> bytes:
    """
    Args:
        uri: 成果物のURI
        verify_checksum: チェックサムを検証するか
    
    Returns:
        成果物の内容（バイト列）
    
    Raises:
        ArtifactNotFoundError: 成果物が見つからない場合
        IntegrityError: チェックサムが一致しない場合
    """
```

#### search()

成果物を検索します。

```python
def search(
    self,
    filters: Optional[Dict[str, Any]] = None
) -> List[ArtifactMetadata]:
    """
    Args:
        filters: 検索フィルタ
            - task_id: タスクID
            - spec_name: Spec名
            - type: 成果物のタイプ
            - tags: タグのリスト
            - created_after: 作成日時の下限
            - created_before: 作成日時の上限
    
    Returns:
        マッチした成果物のメタデータのリスト
    """
```

#### delete()

成果物を削除します。

```python
def delete(self, uri: str) -> None:
    """
    Args:
        uri: 成果物のURI
    
    Raises:
        ArtifactNotFoundError: 成果物が見つからない場合
    """
```

#### delete_by_task_id()

タスクIDに関連するすべての成果物を削除します。

```python
def delete_by_task_id(self, task_id: str) -> int:
    """
    Args:
        task_id: タスクID
    
    Returns:
        削除された成果物の数
    """
```

#### delete_by_spec_name()

Spec名に関連するすべての成果物を削除します。

```python
def delete_by_spec_name(self, spec_name: str) -> int:
    """
    Args:
        spec_name: Spec名
    
    Returns:
        削除された成果物の数
    """
```

#### cleanup_expired()

保持期間を過ぎた成果物を削除します。

```python
def cleanup_expired(self) -> int:
    """
    Returns:
        削除された成果物の数
    """
```

#### get_storage_usage()

ストレージ使用量を取得します。

```python
def get_storage_usage(self) -> Dict[str, Any]:
    """
    Returns:
        {
            "total_size": 総サイズ（バイト）,
            "total_count": 総数,
            "by_spec": {spec名: サイズ},
            "by_type": {タイプ: サイズ}
        }
    """
```

#### add_tags()

成果物にタグを追加します。

```python
def add_tags(self, uri: str, tags: List[str]) -> None:
    """
    Args:
        uri: 成果物のURI
        tags: 追加するタグのリスト
    """
```

#### export_by_spec()

Spec名に関連するすべての成果物をZIPファイルにエクスポートします。

```python
def export_by_spec(
    self,
    spec_name: str,
    output_path: str,
    include_metadata: bool = True
) -> str:
    """
    Args:
        spec_name: Spec名
        output_path: 出力先のパス
        include_metadata: メタデータを含めるか
    
    Returns:
        作成されたZIPファイルのパス
    """
```

### ArtifactType

成果物のタイプを表す列挙型です。

```python
class ArtifactType(Enum):
    DIFF = "diff"           # コードの差分
    LOG = "log"             # 実行ログ
    TEST_RESULT = "test"    # テスト結果
```

### ArtifactMetadata

成果物のメタデータを表すデータクラスです。

```python
@dataclass
class ArtifactMetadata:
    uri: str                        # 成果物のURI
    task_id: str                    # タスクID
    spec_name: str                  # Spec名
    type: ArtifactType              # 成果物のタイプ
    size: int                       # サイズ（バイト）
    checksum: str                   # SHA256チェックサム
    created_at: datetime            # 作成日時
    compressed: bool                # 圧縮されているか
    original_size: Optional[int]    # 圧縮前のサイズ
    mime_type: str                  # MIMEタイプ
    tags: List[str]                 # タグのリスト
    version: int                    # バージョン番号
    metadata: Dict[str, Any]        # 追加のメタデータ
```

## 使用例

### 基本的なアップロードとダウンロード

```python
from necrocode.artifact_store import ArtifactStore, ArtifactStoreConfig, ArtifactType

config = ArtifactStoreConfig()
store = ArtifactStore(config)

# アップロード
content = b"My diff content"
uri = store.upload(
    task_id="1.1",
    spec_name="my-project",
    artifact_type=ArtifactType.DIFF,
    content=content
)

# ダウンロード
downloaded = store.download(uri)
assert downloaded == content
```

### タグを使った検索

```python
# タグ付きでアップロード
uri = store.upload(
    task_id="1.1",
    spec_name="my-project",
    artifact_type=ArtifactType.DIFF,
    content=b"content",
    tags=["frontend", "critical"]
)

# タグで検索
artifacts = store.search({"tags": ["frontend"]})
for artifact in artifacts:
    print(f"Found: {artifact.uri} with tags {artifact.tags}")
```

### 保持期間ポリシーの設定

```python
config = ArtifactStoreConfig(
    retention_policy={
        "diff": 30,   # 30日間保持
        "log": 7,     # 7日間保持
        "test": 14    # 14日間保持
    }
)
store = ArtifactStore(config)

# 期限切れの成果物を削除
deleted_count = store.cleanup_expired()
print(f"Deleted {deleted_count} expired artifacts")
```

### ストレージ使用量の監視

```python
usage = store.get_storage_usage()
print(f"Total size: {usage['total_size'] / 1024 / 1024:.2f} MB")
print(f"Total count: {usage['total_count']}")

for spec_name, size in usage['by_spec'].items():
    print(f"  {spec_name}: {size / 1024 / 1024:.2f} MB")
```

### エクスポート

```python
# Spec名に関連するすべての成果物をエクスポート
zip_path = store.export_by_spec(
    spec_name="my-project",
    output_path="/tmp/my-project-artifacts.zip"
)
print(f"Exported to: {zip_path}")
```

## エラーハンドリング

```python
from necrocode.artifact_store import (
    ArtifactNotFoundError,
    StorageFullError,
    IntegrityError
)

try:
    content = store.download(uri)
except ArtifactNotFoundError:
    print("Artifact not found")
except IntegrityError:
    print("Checksum verification failed")
except StorageFullError:
    print("Storage is full")
```

## ベストプラクティス

### 1. 適切な保持期間の設定

```python
# 開発環境: 短い保持期間
dev_config = ArtifactStoreConfig(
    retention_policy={"diff": 7, "log": 3, "test": 7}
)

# 本番環境: 長い保持期間
prod_config = ArtifactStoreConfig(
    retention_policy={"diff": 90, "log": 30, "test": 60}
)
```

### 2. タグの活用

```python
# 重要度や環境でタグ付け
uri = store.upload(
    task_id="1.1",
    spec_name="my-project",
    artifact_type=ArtifactType.DIFF,
    content=content,
    tags=["production", "critical", "v1.0"]
)
```

### 3. 定期的なクリーンアップ

```python
import schedule

def cleanup_job():
    deleted = store.cleanup_expired()
    print(f"Cleaned up {deleted} artifacts")

# 毎日午前2時に実行
schedule.every().day.at("02:00").do(cleanup_job)
```

### 4. ストレージ使用量の監視

```python
usage = store.get_storage_usage()
total_gb = usage['total_size'] / 1024 / 1024 / 1024

if total_gb > config.max_storage_gb * config.storage_warn_threshold:
    print(f"Warning: Storage usage is {total_gb:.2f} GB")
    # アラートを送信
```

## トラブルシューティング

### ストレージ容量不足

```python
try:
    store.upload(...)
except StorageFullError:
    # 古い成果物を削除
    store.cleanup_expired()
    # 再試行
    store.upload(...)
```

### チェックサム検証エラー

```python
try:
    content = store.download(uri, verify_checksum=True)
except IntegrityError:
    # チェックサムなしで再ダウンロード
    content = store.download(uri, verify_checksum=False)
    # または、再アップロードを要求
```

### ロックタイムアウト

```python
config = ArtifactStoreConfig(
    lock_timeout=60.0,      # タイムアウトを延長
    lock_retry_count=5,     # リトライ回数を増やす
    lock_retry_delay=2.0    # リトライ間隔を延長
)
```

## パフォーマンス最適化

### 1. 圧縮の無効化（小さなファイル）

```python
config = ArtifactStoreConfig(
    compression_enabled=False  # 小さなファイルでは圧縮を無効化
)
```

### 2. チェックサム検証のスキップ（信頼できる環境）

```python
content = store.download(uri, verify_checksum=False)
```

### 3. バッチ削除

```python
# タスクIDごとに削除
deleted = store.delete_by_task_id("1.1")

# Spec名ごとに削除
deleted = store.delete_by_spec_name("old-project")
```

## ライセンス

MIT License

## サポート

問題が発生した場合は、GitHubのIssueを作成してください。

"""
Data models for Artifact Store.

Defines core data structures for artifact metadata and types.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Any, List, Optional
import json


class ArtifactType(Enum):
    """成果物のタイプ"""
    DIFF = "diff"
    LOG = "log"
    TEST_RESULT = "test"


@dataclass
class ArtifactMetadata:
    """
    成果物のメタデータ
    
    Attributes:
        uri: 成果物の一意な識別子 (例: file://~/.necrocode/artifacts/chat-app/1.1/diff.txt)
        task_id: タスクID
        spec_name: Spec名
        type: 成果物のタイプ (diff/log/test)
        size: 成果物のサイズ (bytes)
        checksum: SHA256チェックサム
        created_at: 作成日時
        compressed: 圧縮されているか
        original_size: 圧縮前のサイズ (圧縮されている場合)
        mime_type: MIMEタイプ
        tags: カスタムタグのリスト
        version: バージョン番号
        metadata: 追加のメタデータ
    """
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

    def to_dict(self) -> Dict[str, Any]:
        """メタデータを辞書形式に変換"""
        return {
            "uri": self.uri,
            "task_id": self.task_id,
            "spec_name": self.spec_name,
            "type": self.type.value,
            "size": self.size,
            "checksum": self.checksum,
            "created_at": self.created_at.isoformat(),
            "compressed": self.compressed,
            "original_size": self.original_size,
            "mime_type": self.mime_type,
            "tags": self.tags,
            "version": self.version,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ArtifactMetadata":
        """辞書形式からメタデータを復元"""
        return cls(
            uri=data["uri"],
            task_id=data["task_id"],
            spec_name=data["spec_name"],
            type=ArtifactType(data["type"]),
            size=data["size"],
            checksum=data["checksum"],
            created_at=datetime.fromisoformat(data["created_at"]),
            compressed=data.get("compressed", False),
            original_size=data.get("original_size"),
            mime_type=data.get("mime_type", "text/plain"),
            tags=data.get("tags", []),
            version=data.get("version", 1),
            metadata=data.get("metadata", {}),
        )

    def to_json(self) -> str:
        """メタデータをJSON文字列に変換"""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "ArtifactMetadata":
        """JSON文字列からメタデータを復元"""
        data = json.loads(json_str)
        return cls.from_dict(data)

# ドキュメント日本語化 - 設計書

## アーキテクチャ概要

### システム構成

```
Documentation I18n System
├── Translation Engine
│   ├── Document Parser
│   ├── Content Translator
│   └── Format Validator
├── Glossary Manager
│   ├── Term Database
│   └── Consistency Checker
├── Progress Tracker
│   ├── Status Monitor
│   └── Completion Reporter
└── Quality Assurance
    ├── Link Validator
    ├── Format Checker
    └── Translation Reviewer
```

## コンポーネント設計

### 1. Translation Engine

#### Document Parser
**責務**: Markdownドキュメントを解析し、翻訳対象要素を抽出

```python
class DocumentParser:
    """Markdownドキュメントパーサー"""
    
    def parse(self, markdown_path: Path) -> ParsedDocument:
        """
        ドキュメントを解析
        
        Returns:
            ParsedDocument: 解析済みドキュメント
                - headers: 見出しリスト
                - paragraphs: 段落リスト
                - code_blocks: コードブロックリスト
                - links: リンクリスト
                - tables: テーブルリスト
        """
        pass
    
    def extract_translatable_content(self, doc: ParsedDocument) -> List[TranslatableUnit]:
        """翻訳対象コンテンツを抽出"""
        pass
```

#### Content Translator
**責務**: コンテンツを日本語に翻訳

```python
class ContentTranslator:
    """コンテンツ翻訳エンジン"""
    
    def __init__(self, glossary: GlossaryManager):
        self.glossary = glossary
    
    def translate_text(self, text: str, context: TranslationContext) -> str:
        """
        テキストを翻訳
        
        Args:
            text: 翻訳対象テキスト
            context: 翻訳コンテキスト（見出し、段落、リストなど）
        
        Returns:
            翻訳済みテキスト
        """
        pass
    
    def translate_code_comment(self, comment: str) -> str:
        """コードコメントを翻訳"""
        pass
    
    def apply_glossary(self, text: str) -> str:
        """用語集を適用して用語を統一"""
        pass
```

#### Format Validator
**責務**: 翻訳後のフォーマットを検証

```python
class FormatValidator:
    """フォーマット検証"""
    
    def validate_markdown(self, content: str) -> ValidationResult:
        """Markdownフォーマットを検証"""
        pass
    
    def validate_links(self, doc: ParsedDocument) -> List[LinkError]:
        """リンクの有効性を検証"""
        pass
    
    def validate_code_blocks(self, doc: ParsedDocument) -> List[CodeBlockError]:
        """コードブロックのフォーマットを検証"""
        pass
```

### 2. Glossary Manager

#### Term Database
**責務**: 技術用語の日本語訳を管理

```python
@dataclass
class GlossaryEntry:
    """用語集エントリ"""
    english: str           # 英語用語
    japanese: str          # 日本語訳
    category: str          # カテゴリ（技術用語、プロジェクト用語など）
    usage_note: str        # 使用上の注意
    examples: List[str]    # 使用例

class GlossaryManager:
    """用語集管理"""
    
    def __init__(self, glossary_path: Path):
        self.entries: Dict[str, GlossaryEntry] = {}
        self.load_glossary(glossary_path)
    
    def get_translation(self, term: str) -> Optional[str]:
        """用語の日本語訳を取得"""
        pass
    
    def add_entry(self, entry: GlossaryEntry) -> None:
        """用語を追加"""
        pass
    
    def export_glossary(self, output_path: Path) -> None:
        """用語集をエクスポート"""
        pass
```

#### Consistency Checker
**責務**: ドキュメント間の用語統一性をチェック

```python
class ConsistencyChecker:
    """一貫性チェッカー"""
    
    def check_term_consistency(self, documents: List[Path]) -> List[InconsistencyReport]:
        """用語の一貫性をチェック"""
        pass
    
    def suggest_corrections(self, report: InconsistencyReport) -> List[Correction]:
        """修正案を提案"""
        pass
```

### 3. Progress Tracker

#### Status Monitor
**責務**: 翻訳進捗を追跡

```python
@dataclass
class TranslationStatus:
    """翻訳ステータス"""
    file_path: Path
    status: str  # 'pending', 'in_progress', 'completed', 'reviewed'
    progress_percentage: float
    last_updated: datetime
    translator: Optional[str]
    reviewer: Optional[str]

class StatusMonitor:
    """ステータス監視"""
    
    def track_file(self, file_path: Path, status: str) -> None:
        """ファイルのステータスを追跡"""
        pass
    
    def get_overall_progress(self) -> ProgressReport:
        """全体の進捗を取得"""
        pass
    
    def get_pending_files(self) -> List[Path]:
        """未翻訳ファイルを取得"""
        pass
```

### 4. Quality Assurance

#### Link Validator
**責務**: ドキュメント内のリンクを検証

```python
class LinkValidator:
    """リンク検証"""
    
    def validate_internal_links(self, doc_path: Path) -> List[LinkError]:
        """内部リンクを検証"""
        pass
    
    def validate_external_links(self, doc_path: Path) -> List[LinkError]:
        """外部リンクを検証"""
        pass
    
    def fix_broken_links(self, errors: List[LinkError]) -> List[LinkFix]:
        """壊れたリンクを修正"""
        pass
```

## データモデル

### ParsedDocument

```python
@dataclass
class ParsedDocument:
    """解析済みドキュメント"""
    path: Path
    headers: List[Header]
    paragraphs: List[Paragraph]
    code_blocks: List[CodeBlock]
    links: List[Link]
    tables: List[Table]
    metadata: Dict[str, Any]

@dataclass
class Header:
    """見出し"""
    level: int  # 1-6
    text: str
    anchor: str

@dataclass
class Paragraph:
    """段落"""
    text: str
    line_number: int

@dataclass
class CodeBlock:
    """コードブロック"""
    language: str
    code: str
    comments: List[str]
    line_number: int

@dataclass
class Link:
    """リンク"""
    text: str
    url: str
    is_internal: bool
    line_number: int

@dataclass
class Table:
    """テーブル"""
    headers: List[str]
    rows: List[List[str]]
    line_number: int
```

### TranslationContext

```python
@dataclass
class TranslationContext:
    """翻訳コンテキスト"""
    document_type: str  # 'readme', 'spec', 'guide', 'reference'
    section_type: str   # 'header', 'paragraph', 'list', 'code_comment'
    parent_header: Optional[str]
    technical_domain: str  # 'backend', 'frontend', 'devops', 'general'
```

### ValidationResult

```python
@dataclass
class ValidationResult:
    """検証結果"""
    is_valid: bool
    errors: List[ValidationError]
    warnings: List[ValidationWarning]

@dataclass
class ValidationError:
    """検証エラー"""
    type: str  # 'format', 'link', 'syntax'
    message: str
    line_number: int
    suggestion: Optional[str]
```

## 翻訳ワークフロー

### Phase 1: 準備（完了）

```
1. 用語集の作成
   ├── 技術用語リスト作成
   ├── プロジェクト固有用語リスト作成
   └── 翻訳ルール定義

2. 優先度付け
   ├── ステアリングドキュメント（完了）
   ├── メインREADME（完了）
   └── QUICKSTART（完了）
```

### Phase 2: サービスREADME翻訳

```
For each service in [task_registry, repo_pool, dispatcher, agent_runner, artifact_store, review_pr_service]:
    1. ドキュメント解析
       └── 構造とコンテンツを抽出
    
    2. コンテンツ翻訳
       ├── 見出しを翻訳
       ├── 段落を翻訳
       ├── コード例のコメントを翻訳
       └── 用語集を適用
    
    3. フォーマット検証
       ├── Markdown構文チェック
       ├── リンク検証
       └── コードブロック検証
    
    4. レビューと修正
       ├── 技術的正確性確認
       ├── 日本語の自然さ確認
       └── 用語統一性確認
    
    5. コミット
       └── "docs(i18n): translate {service} README to Japanese"
```

### Phase 3: 仕様ドキュメント翻訳

```
For each spec in .kiro/specs/*/:
    1. requirements.md翻訳
    2. design.md翻訳
    3. tasks.md翻訳
    4. 検証とレビュー
    5. コミット
```

### Phase 4: 補助ドキュメント翻訳

```
1. サービス固有ドキュメント
2. タスクサマリー
3. テンプレート
4. その他
```

## 用語集構造

### glossary.yaml

```yaml
# 技術用語
technical_terms:
  - english: "Task"
    japanese: "タスク"
    category: "core"
    usage: "常に「タスク」を使用"
    
  - english: "Workspace"
    japanese: "ワークスペース"
    category: "core"
    usage: "常に「ワークスペース」を使用"
    
  - english: "Registry"
    japanese: "レジストリ"
    category: "core"
    usage: "常に「レジストリ」を使用"

# プロジェクト固有用語
project_terms:
  - english: "Spirit"
    japanese: "スピリット"
    category: "necrocode"
    usage: "常に「スピリット」を使用、初出時は「Spirit（スピリット）」"
    
  - english: "Necromancer"
    japanese: "ネクロマンサー"
    category: "necrocode"
    usage: "常に「ネクロマンサー」を使用"

# そのまま英語を使用
keep_english:
  - "API"
  - "CLI"
  - "JSON"
  - "YAML"
  - "Git"
  - "GitHub"
  - "Docker"
  - "Kubernetes"
  - "Pull Request"
  - "PR"
  - "Commit"
  - "Branch"

# 英語併記
with_english:
  - english: "Hook"
    japanese: "フック"
    format: "Hook（フック）"
    
  - english: "Agent"
    japanese: "エージェント"
    format: "Agent（エージェント）"
```

## 翻訳スクリプト設計

### translate_document.py

```python
#!/usr/bin/env python3
"""
ドキュメント翻訳スクリプト

Usage:
    python translate_document.py <input_file> [--output <output_file>] [--dry-run]
"""

import argparse
from pathlib import Path
from typing import Optional

class DocumentTranslator:
    """ドキュメント翻訳クラス"""
    
    def __init__(self, glossary_path: Path):
        self.parser = DocumentParser()
        self.glossary = GlossaryManager(glossary_path)
        self.translator = ContentTranslator(self.glossary)
        self.validator = FormatValidator()
    
    def translate_file(self, input_path: Path, output_path: Optional[Path] = None) -> None:
        """ファイルを翻訳"""
        # 1. ドキュメント解析
        doc = self.parser.parse(input_path)
        
        # 2. 翻訳対象抽出
        units = self.parser.extract_translatable_content(doc)
        
        # 3. 翻訳実行
        translated_units = []
        for unit in units:
            context = self._create_context(unit, doc)
            translated = self.translator.translate_text(unit.text, context)
            translated_units.append(translated)
        
        # 4. ドキュメント再構築
        translated_doc = self._rebuild_document(doc, translated_units)
        
        # 5. 検証
        validation = self.validator.validate_markdown(translated_doc)
        if not validation.is_valid:
            self._report_errors(validation.errors)
            return
        
        # 6. 出力
        output = output_path or input_path
        output.write_text(translated_doc, encoding='utf-8')
        print(f"✓ Translated: {input_path} -> {output}")

def main():
    parser = argparse.ArgumentParser(description='Translate documentation to Japanese')
    parser.add_argument('input', type=Path, help='Input markdown file')
    parser.add_argument('--output', type=Path, help='Output file (default: overwrite input)')
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode')
    parser.add_argument('--glossary', type=Path, default=Path('glossary.yaml'))
    
    args = parser.parse_args()
    
    translator = DocumentTranslator(args.glossary)
    translator.translate_file(args.input, args.output)

if __name__ == '__main__':
    main()
```

### batch_translate.py

```python
#!/usr/bin/env python3
"""
バッチ翻訳スクリプト

Usage:
    python batch_translate.py --phase 2
    python batch_translate.py --files file1.md file2.md
"""

import argparse
from pathlib import Path
from typing import List

class BatchTranslator:
    """バッチ翻訳クラス"""
    
    def __init__(self):
        self.translator = DocumentTranslator(Path('glossary.yaml'))
        self.tracker = StatusMonitor()
    
    def translate_phase(self, phase: int) -> None:
        """フェーズ単位で翻訳"""
        files = self._get_phase_files(phase)
        self._translate_files(files)
    
    def translate_files(self, files: List[Path]) -> None:
        """指定ファイルを翻訳"""
        self._translate_files(files)
    
    def _translate_files(self, files: List[Path]) -> None:
        """ファイルリストを翻訳"""
        for file in files:
            print(f"Translating: {file}")
            try:
                self.translator.translate_file(file)
                self.tracker.track_file(file, 'completed')
            except Exception as e:
                print(f"✗ Error: {file}: {e}")
                self.tracker.track_file(file, 'error')
        
        # 進捗レポート
        progress = self.tracker.get_overall_progress()
        print(f"\nProgress: {progress.completed}/{progress.total} files")

def main():
    parser = argparse.ArgumentParser(description='Batch translate documentation')
    parser.add_argument('--phase', type=int, help='Translation phase (1-4)')
    parser.add_argument('--files', nargs='+', type=Path, help='Specific files to translate')
    
    args = parser.parse_args()
    
    translator = BatchTranslator()
    
    if args.phase:
        translator.translate_phase(args.phase)
    elif args.files:
        translator.translate_files(args.files)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
```

## 品質保証プロセス

### 翻訳チェックリスト

```markdown
## 翻訳品質チェックリスト

### 内容の正確性
- [ ] 技術的な意味が正確に伝わっている
- [ ] 重要な情報が欠落していない
- [ ] コード例が正しく動作する

### 日本語の品質
- [ ] 自然な日本語表現
- [ ] 文法的に正しい
- [ ] 読みやすい文章構造

### 用語の統一性
- [ ] 用語集に従っている
- [ ] プロジェクト内で統一されている
- [ ] 技術用語が適切に使用されている

### フォーマット
- [ ] Markdown構文が正しい
- [ ] リンクが機能する
- [ ] コードブロックが正しく表示される
- [ ] テーブルが正しく表示される

### 構造
- [ ] 元の構造が維持されている
- [ ] 目次が正しく更新されている
- [ ] セクション番号が正しい
```

### 自動検証スクリプト

```python
#!/usr/bin/env python3
"""
翻訳品質検証スクリプト

Usage:
    python validate_translation.py <file>
"""

class TranslationValidator:
    """翻訳検証クラス"""
    
    def validate(self, file_path: Path) -> ValidationReport:
        """翻訳を検証"""
        report = ValidationReport()
        
        # 1. フォーマット検証
        report.format_errors = self._validate_format(file_path)
        
        # 2. リンク検証
        report.link_errors = self._validate_links(file_path)
        
        # 3. 用語統一性検証
        report.term_errors = self._validate_terms(file_path)
        
        # 4. コードブロック検証
        report.code_errors = self._validate_code_blocks(file_path)
        
        return report
```

## 進捗管理

### translation_status.yaml

```yaml
# 翻訳ステータス管理

phase_1:
  status: completed
  files:
    - path: .kiro/steering/overview.md
      status: completed
      translator: kiro
      reviewed: true
    - path: .kiro/steering/architecture.md
      status: completed
      translator: kiro
      reviewed: true
    - path: .kiro/steering/development.md
      status: completed
      translator: kiro
      reviewed: true
    - path: README.md
      status: completed
      translator: kiro
      reviewed: true
    - path: QUICKSTART.md
      status: completed
      translator: kiro
      reviewed: true

phase_2:
  status: in_progress
  files:
    - path: necrocode/task_registry/README.md
      status: completed
      translator: kiro
      reviewed: true
    - path: necrocode/review_pr_service/README.md
      status: partial
      translator: kiro
      reviewed: false
    - path: necrocode/repo_pool/README.md
      status: partial
      translator: kiro
      reviewed: false
    - path: necrocode/dispatcher/README.md
      status: pending
    - path: necrocode/agent_runner/README.md
      status: pending
    - path: necrocode/artifact_store/README.md
      status: pending

phase_3:
  status: pending
  
phase_4:
  status: pending
```

## 関連ドキュメント

- requirements.md - 要件定義
- tasks.md - 実装タスク
- glossary.yaml - 用語集
- translation_status.yaml - 進捗管理

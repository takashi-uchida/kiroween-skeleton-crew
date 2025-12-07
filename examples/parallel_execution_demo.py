"""NecroCode並列実行デモ"""
from pathlib import Path
import json

# サンプルプロジェクトのタスク定義を作成
def create_sample_project():
    """サンプルプロジェクトを作成"""
    project_name = "demo-chat-app"
    tasks_dir = Path(".kiro/tasks") / project_name
    tasks_dir.mkdir(parents=True, exist_ok=True)
    
    tasks = {
        "project": project_name,
        "description": "シンプルなチャットアプリケーション",
        "tasks": [
            {
                "id": "1",
                "title": "プロジェクト構造作成",
                "description": "基本的なディレクトリとファイルを作成",
                "dependencies": [],
                "type": "setup",
                "files_to_create": [
                    "README.md",
                    ".gitignore",
                    "requirements.txt"
                ],
                "acceptance_criteria": [
                    "README.mdにプロジェクト説明がある",
                    ".gitignoreにPython用の設定がある",
                    "requirements.txtに必要なパッケージがリストされている"
                ]
            },
            {
                "id": "2",
                "title": "データモデル実装",
                "description": "UserとMessageのデータモデルを作成",
                "dependencies": ["1"],
                "type": "backend",
                "files_to_create": [
                    "models/__init__.py",
                    "models/user.py",
                    "models/message.py"
                ],
                "acceptance_criteria": [
                    "Userモデルにusername, email, password_hashフィールドがある",
                    "Messageモデルにuser_id, content, timestampフィールドがある",
                    "適切なバリデーションが実装されている"
                ]
            },
            {
                "id": "3",
                "title": "認証API実装",
                "description": "ユーザー登録とログイン機能を実装",
                "dependencies": ["2"],
                "type": "backend",
                "files_to_create": [
                    "api/__init__.py",
                    "api/auth.py",
                    "tests/test_auth.py"
                ],
                "acceptance_criteria": [
                    "POST /api/auth/registerでユーザー登録ができる",
                    "POST /api/auth/loginでJWTトークンが返される",
                    "パスワードはbcryptでハッシュ化される",
                    "テストが全て通る"
                ]
            },
            {
                "id": "4",
                "title": "メッセージAPI実装",
                "description": "メッセージの送受信機能を実装",
                "dependencies": ["2"],
                "type": "backend",
                "files_to_create": [
                    "api/messages.py",
                    "tests/test_messages.py"
                ],
                "acceptance_criteria": [
                    "GET /api/messagesでメッセージ一覧を取得できる",
                    "POST /api/messagesでメッセージを送信できる",
                    "認証が必要なエンドポイントが保護されている"
                ]
            },
            {
                "id": "5",
                "title": "フロントエンド実装",
                "description": "チャットUIを作成",
                "dependencies": ["3", "4"],
                "type": "frontend",
                "files_to_create": [
                    "static/index.html",
                    "static/style.css",
                    "static/app.js"
                ],
                "acceptance_criteria": [
                    "ログインフォームが表示される",
                    "メッセージ一覧が表示される",
                    "メッセージを送信できる",
                    "レスポンシブデザインになっている"
                ]
            }
        ]
    }
    
    tasks_file = tasks_dir / "tasks.json"
    with open(tasks_file, 'w') as f:
        json.dump(tasks, f, indent=2, ensure_ascii=False)
    
    print(f"✓ サンプルプロジェクト '{project_name}' を作成しました")
    print(f"  タスク数: {len(tasks['tasks'])}")
    print(f"  保存先: {tasks_file}")
    print(f"\n実行方法:")
    print(f"  python -m necrocode.cli execute {project_name} --workers 3 --mode manual")
    
    return project_name


if __name__ == "__main__":
    create_sample_project()

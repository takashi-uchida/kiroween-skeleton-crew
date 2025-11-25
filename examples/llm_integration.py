"""
LLM Integration Example

This example demonstrates how to use the LLM client for code generation.
"""

import os
from pathlib import Path
from necrocode.agent_runner import LLMClient, LLMConfig, CodeChange


def main():
    # 1. LLM設定を作成
    config = LLMConfig(
        api_key=os.getenv("OPENAI_API_KEY", "your-api-key"),
        model="gpt-4",
        timeout_seconds=120
    )
    
    # 2. LLMクライアントを作成
    client = LLMClient(config)
    
    # 3. コード生成プロンプトを構築
    prompt = """
# Task: Create a User model

## Description
Create a User model with email, password, and username fields using Mongoose.

## Acceptance Criteria
1. User model has email field (required, unique)
2. User model has password field (required, hashed)
3. User model has username field (required, unique)
4. Model includes timestamps (createdAt, updatedAt)

## Instructions
Generate the code changes needed to implement this task.
Return the changes in the following JSON format:

{
  "code_changes": [
    {
      "file_path": "path/to/file.js",
      "operation": "create|modify|delete",
      "content": "file content here"
    }
  ],
  "explanation": "Brief explanation of changes"
}
"""
    
    # 4. コードを生成
    print("Generating code with LLM...")
    try:
        response = client.generate_code(
            prompt=prompt,
            workspace_path=Path("/tmp/workspace"),
            max_tokens=4000
        )
        
        print(f"\n✓ コード生成完了!")
        print(f"  モデル: {response.model}")
        print(f"  トークン使用量: {response.tokens_used}")
        print(f"  変更ファイル数: {len(response.code_changes)}")
        print(f"\n説明: {response.explanation}")
        
        print(f"\n変更内容:")
        for change in response.code_changes:
            print(f"\n  ファイル: {change.file_path}")
            print(f"  操作: {change.operation}")
            print(f"  内容プレビュー:")
            preview = change.content[:200] + "..." if len(change.content) > 200 else change.content
            print(f"    {preview}")
    
    except Exception as e:
        print(f"\n✗ エラー: {e}")
        raise


def example_with_retry():
    """レート制限エラーのリトライ例"""
    config = LLMConfig(
        api_key=os.getenv("OPENAI_API_KEY"),
        model="gpt-4",
        timeout_seconds=120
    )
    
    client = LLMClient(config)
    
    # リトライロジックは LLMClient 内部で自動的に処理される
    prompt = "Create a simple Hello World function in Python"
    
    try:
        response = client.generate_code(
            prompt=prompt,
            workspace_path=Path("/tmp/workspace"),
            max_tokens=1000
        )
        print(f"Success! Tokens used: {response.tokens_used}")
    except Exception as e:
        print(f"Failed after retries: {e}")


def example_custom_model():
    """カスタムモデルの使用例"""
    config = LLMConfig(
        api_key=os.getenv("OPENAI_API_KEY"),
        model="gpt-3.5-turbo",  # より安価なモデル
        timeout_seconds=60
    )
    
    client = LLMClient(config)
    
    prompt = "Create a simple utility function"
    response = client.generate_code(
        prompt=prompt,
        workspace_path=Path("/tmp/workspace"),
        max_tokens=2000
    )
    
    print(f"Model used: {response.model}")
    print(f"Tokens: {response.tokens_used}")


if __name__ == "__main__":
    print("=== Basic LLM Integration ===")
    main()
    
    print("\n=== Retry Example ===")
    example_with_retry()
    
    print("\n=== Custom Model Example ===")
    example_custom_model()

# Task Templates - Requirements

## Overview
よく使うタスクパターンをテンプレート化する機能。

## Functional Requirements

### 1.1 テンプレート管理
- テンプレート作成
- テンプレート編集
- テンプレート削除
- テンプレート一覧

### 1.2 組み込みテンプレート
- REST API
- GraphQL API
- React SPA
- Vue.js SPA
- CLI Tool
- Microservices
- データパイプライン

### 1.3 カスタムテンプレート
- YAML形式でのテンプレート定義
- 変数置換
- 条件分岐
- テンプレート継承

### 1.4 テンプレート適用
- テンプレートからジョブ生成
- パラメータ指定
- プレビュー機能
- カスタマイズ

## Template Format
```yaml
name: rest-api
description: REST API with authentication
version: 1.0

parameters:
  - name: database
    type: choice
    options: [postgresql, mysql, sqlite]
    default: postgresql
  
  - name: auth_type
    type: choice
    options: [jwt, oauth, session]
    default: jwt

tasks:
  - id: "1"
    title: "Database setup"
    description: "Setup {{database}} database"
    skill: database
    
  - id: "2"
    title: "Authentication"
    description: "Implement {{auth_type}} authentication"
    skill: backend
    dependencies: ["1"]
```

## CLI Commands
```bash
# テンプレート一覧
necrocode template list

# テンプレートからジョブ作成
necrocode submit --template rest-api \
  --param database=postgresql \
  --param auth_type=jwt \
  "User management API"

# カスタムテンプレート作成
necrocode template create my-template.yaml

# テンプレートプレビュー
necrocode template preview rest-api
```

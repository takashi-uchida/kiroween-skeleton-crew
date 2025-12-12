.PHONY: help install test lint format clean setup-dev cleanup

help:  ## このヘルプを表示
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## 依存関係をインストール
	pip install -e .

install-dev:  ## 開発用依存関係をインストール
	pip install -e .[dev]
	pip install pre-commit
	pre-commit install

test:  ## テストを実行
	pytest tests/ -v --cov=necrocode --cov-report=term-missing

test-watch:  ## テストを監視モードで実行
	pytest-watch tests/ -- -v --cov=necrocode

lint:  ## コードをリント
	flake8 necrocode tests
	mypy necrocode --ignore-missing-imports

format:  ## コードをフォーマット
	black necrocode tests
	isort necrocode tests

format-check:  ## フォーマットをチェック
	black --check necrocode tests
	isort --check-only necrocode tests

clean:  ## 一時ファイルを削除
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf build/ dist/ .coverage htmlcov/ .pytest_cache/

cleanup-worktrees:  ## 古いworktreeを削除
	python scripts/auto_cleanup.py --days 7

cleanup-worktrees-dry:  ## 古いworktree削除のドライラン
	python scripts/auto_cleanup.py --days 7 --dry-run

cleanup-all:  ## worktreeとブランチを全てクリーンアップ
	python scripts/auto_cleanup.py --days 7 --branches

setup-dev: install-dev  ## 開発環境をセットアップ
	@echo "✅ 開発環境のセットアップが完了しました"
	@echo "📝 使用可能なコマンド:"
	@make help

ci: format-check lint test  ## CI/CDで実行されるチェック

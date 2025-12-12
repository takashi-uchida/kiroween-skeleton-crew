"""NecroCode CLI テスト"""
import pytest
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
from necrocode.cli import cli


def test_cli_help():
    """CLIヘルプのテスト"""
    runner = CliRunner()
    result = runner.invoke(cli, ['--help'])
    assert result.exit_code == 0
    assert 'NecroCode' in result.output


def test_plan_command_help():
    """planコマンドのヘルプテスト"""
    runner = CliRunner()
    result = runner.invoke(cli, ['plan', '--help'])
    assert result.exit_code == 0
    assert 'plan' in result.output


def test_execute_command_help():
    """executeコマンドのヘルプテスト"""
    runner = CliRunner()
    result = runner.invoke(cli, ['execute', '--help'])
    assert result.exit_code == 0
    assert 'execute' in result.output


def test_status_command_help():
    """statusコマンドのヘルプテスト"""
    runner = CliRunner()
    result = runner.invoke(cli, ['status', '--help'])
    assert result.exit_code == 0
    assert 'status' in result.output


def test_cleanup_command_help():
    """cleanupコマンドのヘルプテスト"""
    runner = CliRunner()
    result = runner.invoke(cli, ['cleanup', '--help'])
    assert result.exit_code == 0
    assert 'cleanup' in result.output


def test_list_tasks_command_no_project():
    """list-tasksコマンドのテスト（プロジェクトが存在しない場合）"""
    runner = CliRunner()
    result = runner.invoke(cli, ['list-tasks', 'nonexistent-project'])
    
    assert result.exit_code == 0
    assert 'エラー: プロジェクト' in result.output

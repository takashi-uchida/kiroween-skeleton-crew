"""NecroCode CLI テスト"""
import pytest
from unittest.mock import patch, MagicMock
from necrocode.cli import main, create_parser


def test_create_parser():
    """パーサー作成のテスト"""
    parser = create_parser()
    assert parser is not None
    
    # ヘルプが正常に生成されることを確認
    help_text = parser.format_help()
    assert 'necrocode' in help_text.lower()


def test_plan_command():
    """planコマンドのテスト"""
    parser = create_parser()
    args = parser.parse_args(['plan', 'test description', '--project', 'test-project'])
    
    assert args.command == 'plan'
    assert args.description == 'test description'
    assert args.project == 'test-project'


def test_execute_command():
    """executeコマンドのテスト"""
    parser = create_parser()
    args = parser.parse_args(['execute', 'test-project', '--workers', '2'])
    
    assert args.command == 'execute'
    assert args.project == 'test-project'
    assert args.workers == 2


def test_status_command():
    """statusコマンドのテスト"""
    parser = create_parser()
    args = parser.parse_args(['status'])
    
    assert args.command == 'status'


@patch('necrocode.cli.TaskPlanner')
def test_main_plan_command(mock_planner):
    """main関数のplanコマンドテスト"""
    mock_instance = MagicMock()
    mock_planner.return_value = mock_instance
    
    with patch('sys.argv', ['necrocode', 'plan', 'test', '--project', 'test']):
        try:
            main()
        except SystemExit:
            pass  # 正常終了
    
    mock_planner.assert_called_once()

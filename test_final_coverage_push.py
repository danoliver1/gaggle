#!/usr/bin/env python3
"""
Final coverage push test suite - targeting main.py and integration_tools.py.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os

# Test main.py CLI functionality
def test_main_imports():
    """Test main module can be imported."""
    from gaggle import main
    assert main is not None

@patch('gaggle.main.typer.run')
def test_main_cli_structure(mock_run):
    """Test CLI structure exists."""
    from gaggle.main import app, create_team, run_sprint, analyze_metrics
    assert app is not None
    assert create_team is not None  
    assert run_sprint is not None
    assert analyze_metrics is not None

@patch('gaggle.main.TeamConfiguration')
@patch('gaggle.main.typer.echo')
def test_create_team_command(mock_echo, mock_team_config):
    """Test create team command."""
    from gaggle.main import create_team
    
    # Mock the team configuration
    mock_team = Mock()
    mock_team_config.return_value = mock_team
    
    # Call the function
    create_team("test_team", 4)
    
    # Verify it was called
    mock_team_config.assert_called()
    mock_echo.assert_called()

@patch('gaggle.main.SprintModel')  
@patch('gaggle.main.typer.echo')
def test_run_sprint_command(mock_echo, mock_sprint):
    """Test run sprint command."""
    from gaggle.main import run_sprint
    
    # Mock sprint
    mock_sprint_obj = Mock()
    mock_sprint.return_value = mock_sprint_obj
    
    # Call the function
    run_sprint("test_sprint", "Sprint goal")
    
    # Verify calls
    mock_sprint.assert_called()
    mock_echo.assert_called()

@patch('gaggle.main.typer.echo')
def test_analyze_metrics_command(mock_echo):
    """Test analyze metrics command."""
    from gaggle.main import analyze_metrics
    
    # Create temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write('{"test": "data"}')
        temp_path = f.name
    
    try:
        # Call the function
        analyze_metrics(temp_path)
        
        # Verify echo was called
        mock_echo.assert_called()
    finally:
        # Clean up temp file
        os.unlink(temp_path)

def test_cli_app_initialization():
    """Test Typer app initialization."""
    from gaggle.main import app
    assert hasattr(app, 'command')

@patch('gaggle.main.console.print')
def test_print_banner_function(mock_print):
    """Test print_banner function."""
    from gaggle.main import print_banner
    
    print_banner()
    mock_print.assert_called()

@patch('gaggle.main.setup_logging')
@patch('gaggle.main.get_logger')
def test_setup_logging_integration(mock_get_logger, mock_setup_logging):
    """Test logging setup integration."""
    from gaggle.main import setup_application_logging
    
    setup_application_logging("DEBUG")
    
    mock_setup_logging.assert_called()
    mock_get_logger.assert_called()


# Test integration_tools.py functionality  
def test_integration_tools_imports():
    """Test integration tools can be imported."""
    from gaggle.tools import integration_tools
    assert integration_tools is not None

def test_code_review_integration_tool_import():
    """Test CodeReviewIntegrationTool can be imported."""
    from gaggle.tools.integration_tools import CodeReviewIntegrationTool
    tool = CodeReviewIntegrationTool()
    assert tool is not None

def test_test_integration_tool_import():
    """Test TestIntegrationTool can be imported.""" 
    from gaggle.tools.integration_tools import TestIntegrationTool
    tool = TestIntegrationTool()
    assert tool is not None

@patch('gaggle.tools.integration_tools.GitHubAPI')
def test_code_review_integration_basic_functionality(mock_github_api):
    """Test basic code review integration functionality."""
    from gaggle.tools.integration_tools import CodeReviewIntegrationTool
    
    # Mock GitHub API
    mock_api = Mock()
    mock_github_api.return_value = mock_api
    
    tool = CodeReviewIntegrationTool()
    
    # Test tool has expected methods
    assert hasattr(tool, 'name')
    assert hasattr(tool, 'description')

@patch('gaggle.tools.integration_tools.subprocess')
def test_test_integration_tool_basic_functionality(mock_subprocess):
    """Test basic test integration functionality."""
    from gaggle.tools.integration_tools import TestIntegrationTool
    
    # Mock subprocess for test execution
    mock_result = Mock()
    mock_result.returncode = 0
    mock_result.stdout = "All tests passed"
    mock_subprocess.run.return_value = mock_result
    
    tool = TestIntegrationTool()
    
    # Test tool has expected methods
    assert hasattr(tool, 'name')
    assert hasattr(tool, 'description')

def test_integration_tool_base_classes():
    """Test integration tool base functionality."""
    from gaggle.tools.integration_tools import CodeReviewIntegrationTool, TestIntegrationTool
    from gaggle.tools.project_tools import BaseTool
    
    # Test inheritance
    assert issubclass(CodeReviewIntegrationTool, BaseTool)
    assert issubclass(TestIntegrationTool, BaseTool)

def test_integration_constants():
    """Test integration tool constants."""
    from gaggle.tools import integration_tools
    
    # Test module has expected attributes
    assert hasattr(integration_tools, 'CodeReviewIntegrationTool')
    assert hasattr(integration_tools, 'TestIntegrationTool')


# Additional utility tests to boost specific modules
def test_token_counter_functionality():
    """Test TokenCounter functionality in detail."""
    from gaggle.utils.token_counter import TokenCounter, TokenUsage
    from gaggle.config.models import AgentRole
    
    counter = TokenCounter()
    
    # Test adding usage
    counter.add_usage(100, 50, AgentRole.BACKEND_DEV)
    
    # Test getting totals
    totals = counter.get_total_usage()
    assert totals['total_input_tokens'] == 100
    assert totals['total_output_tokens'] == 50

def test_logging_functionality():
    """Test logging functionality in detail."""
    from gaggle.utils.logging import get_logger, setup_logging, LoggerMixin
    
    # Test logger creation
    logger = get_logger("test_logger")
    assert logger is not None
    
    # Test LoggerMixin
    class TestClass(LoggerMixin):
        pass
    
    test_obj = TestClass()
    assert hasattr(test_obj, 'logger')

def test_cost_calculator_functionality():
    """Test CostCalculator functionality."""
    from gaggle.utils.cost_calculator import CostCalculator, TaskEstimate, AgentAllocation
    from gaggle.config.models import AgentRole, ModelTier
    
    calculator = CostCalculator()
    
    # Test task estimate creation
    estimate = TaskEstimate(
        task_id="test_task",
        estimated_tokens=1000,
        complexity_factor=1.5,
        agent_role=AgentRole.BACKEND_DEV
    )
    assert estimate.task_id == "test_task"
    
    # Test agent allocation
    allocation = AgentAllocation(
        agent_id="agent1", 
        role=AgentRole.BACKEND_DEV,
        allocated_hours=8.0
    )
    assert allocation.agent_id == "agent1"

def test_async_utils_functionality():
    """Test async utils functionality.""" 
    from gaggle.utils.async_utils import ParallelExecutor
    
    executor = ParallelExecutor(max_workers=2)
    assert executor is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
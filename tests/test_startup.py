"""
NEXUS AI - Brain Startup Tests
Validates the full initialization flow of the brain.
"""
import pytest

def test_brain_start_stop(mock_brain):
    """Test that the brain starts and stops successfully with mock dependencies."""
    assert not mock_brain.is_running
    
    # Start the brain
    mock_brain.start()
    assert mock_brain.is_running
    
    # Check internal state was updated
    assert mock_brain._state.system.running is True
    
    # Ensure health report is accessible
    report = mock_brain.get_health_report()
    assert isinstance(report, dict)
    assert "healthy" in report
    
    # Check metrics
    from utils.metrics import metrics
    display = metrics.get_display()
    assert "nexus_modules_healthy" in display
    
    # Stop the brain
    mock_brain.stop()
    assert not mock_brain.is_running
    assert mock_brain._state.system.running is False

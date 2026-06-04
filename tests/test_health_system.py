"""Tests for the health registry and circuit breaker."""
import pytest
import time
from utils.resilience import CircuitBreaker, CircuitBreakerOpenError, ModuleStatus, safe_start, retry_with_backoff

def test_health_registry_track_load(health_registry):
    with health_registry.track_load("test_module"):
        # simulate some work
        pass

    report = health_registry.get_report()
    assert report["healthy"] == 1
    assert "test_module" in report["modules"]
    assert report["modules"]["test_module"]["status"] == ModuleStatus.HEALTHY.value

def test_health_registry_failure(health_registry):
    try:
        with health_registry.track_start("bad_module"):
            raise ValueError("bad init")
    except Exception:
        pass

    report = health_registry.get_report()
    assert report["failed"] == 1
    assert report["modules"]["bad_module"]["status"] == ModuleStatus.FAILED.value
    assert report["modules"]["bad_module"]["error"] == "bad init"

def test_circuit_breaker_success():
    cb = CircuitBreaker("test", failure_threshold=2, reset_timeout=0.1)
    
    def my_func():
        return "success"
        
    assert cb.call(my_func) == "success"
    assert cb.get_stats()["success_count"] == 1

def test_circuit_breaker_failure_and_half_open():
    cb = CircuitBreaker("test", failure_threshold=2, reset_timeout=0.2)
    
    def my_func():
        raise ValueError("fail")
        
    with pytest.raises(ValueError):
        cb.call(my_func)
        
    with pytest.raises(ValueError):
        cb.call(my_func)
        
    # Circuit should now be open
    with pytest.raises(CircuitBreakerOpenError):
        cb.call(my_func)
        
    # Wait for reset timeout
    time.sleep(0.3)
    
    # Should be half-open, pass one probe. If it fails, open again.
    with pytest.raises(ValueError):
        cb.call(my_func)
        
    with pytest.raises(CircuitBreakerOpenError):
        cb.call(my_func)

def test_retry_with_backoff():
    count = 0
    @retry_with_backoff(max_retries=2, initial_delay=0.01)
    def flaking_func():
        nonlocal count
        count += 1
        if count < 3:
            raise ValueError("failed attempt")
        return "finally success"
        
    result = flaking_func()
    assert result == "finally success"
    assert count == 3

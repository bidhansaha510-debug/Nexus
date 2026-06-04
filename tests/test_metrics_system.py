"""Tests for the metrics collection system."""
import pytest

def test_counter(metrics_collector):
    c = metrics_collector.counter("test_counter")
    c.inc("label1", 2.0)
    c.inc("label1", 1.5)
    
    assert c.get("label1") == 3.5
    assert c.get("unknown") == 0.0
    
    all_vals = c.get_all()
    assert "label1" in all_vals
    assert all_vals["label1"] == 3.5

def test_gauge(metrics_collector):
    g = metrics_collector.gauge("test_gauge")
    g.set(5.0, "main")
    assert g.get("main") == 5.0
    
    g.inc(2.0, "main")
    assert g.get("main") == 7.0
    
    g.dec(3.0, "main")
    assert g.get("main") == 4.0

def test_histogram(metrics_collector):
    h = metrics_collector.histogram("test_hist", buckets=(1.0, 5.0, 10.0))
    h.observe(0.5, "latency")
    h.observe(2.0, "latency")
    h.observe(7.0, "latency")
    
    stats = h.get_stats("latency")
    assert stats["count"] == 3
    assert stats["sum"] == 9.5
    # Should calculate properly
    
    all_stats = h.get_all()
    assert "latency" in all_stats
    assert all_stats["latency"]["count"] == 3

def test_metrics_collector_display(metrics_collector):
    metrics_collector.counter("test_reqs").inc("success")
    display = metrics_collector.get_display()
    assert "System Metrics" in display
    assert "test_reqs" in display

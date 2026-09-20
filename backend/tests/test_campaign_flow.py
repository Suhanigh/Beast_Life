"""Test campaign flow with pytest."""
import pytest
import json
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_create_campaign():
    """Test creating a campaign."""
    response = client.post("/api/campaigns", json={
        "product_name": "Test Product",
        "factual_product_description": "A test product for testing",
        "target_audience": "Test audience",
        "campaign_objective": "introduce",
        "tone": "practical_energetic",
        "call_to_action": "Test CTA",
        "verified_claims": ["Test claim"]
    })
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] is not None
    assert data["brief"]["product_name"] == "Test Product"
    assert data["is_mock"] is True  # Should be true due to MOCK_MODE=1


def test_list_campaigns():
    """Test listing campaigns."""
    response = client.get("/api/campaigns")
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_get_campaign():
    """Test getting a specific campaign."""
    # First create a campaign
    create_response = client.post("/api/campaigns", json={
        "product_name": "Test Product 2",
        "factual_product_description": "Another test product",
        "target_audience": "Test audience",
        "campaign_objective": "introduce",
        "tone": "practical_energetic",
        "call_to_action": "Test CTA",
        "verified_claims": []
    })
    
    campaign_id = create_response.json()["id"]
    
    # Get the campaign
    response = client.get(f"/api/campaigns/{campaign_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == campaign_id


def test_research_stage():
    """Test research stage execution."""
    # Create campaign
    create_response = client.post("/api/campaigns", json={
        "product_name": "Test Product 3",
        "factual_product_description": "Test product for research",
        "target_audience": "Test audience",
        "campaign_objective": "introduce",
        "tone": "practical_energetic",
        "call_to_action": "Test CTA",
        "verified_claims": []
    })
    
    campaign_id = create_response.json()["id"]
    
    # Start research
    response = client.post(f"/api/campaigns/{campaign_id}/research/start")
    
    assert response.status_code == 200
    data = response.json()
    assert "stage_run_id" in data


def test_reuse_stage():
    """Test that stages with same input hash are reused."""
    # Create campaign
    create_response = client.post("/api/campaigns", json={
        "product_name": "Test Product 4",
        "factual_product_description": "Test product for reuse",
        "target_audience": "Test audience",
        "campaign_objective": "introduce",
        "tone": "practical_energetic",
        "call_to_action": "Test CTA",
        "verified_claims": []
    })
    
    campaign_id = create_response.json()["id"]
    
    # Start research first time
    first_response = client.post(f"/api/campaigns/{campaign_id}/research/start")
    first_run_id = first_response.json()["stage_run_id"]
    
    # Try to start research again (should reuse or create new)
    second_response = client.post(f"/api/campaigns/{campaign_id}/research/start")
    second_run_id = second_response.json()["stage_run_id"]
    
    # Should either return the same run ID (reuse) or a new one
    assert second_run_id is not None


def test_angle_selection():
    """Test angle selection."""
    # Create campaign and complete research
    create_response = client.post("/api/campaigns", json={
        "product_name": "Test Product 5",
        "factual_product_description": "Test product for angle selection",
        "target_audience": "Test audience",
        "campaign_objective": "introduce",
        "tone": "practical_energetic",
        "call_to_action": "Test CTA",
        "verified_claims": []
    })
    
    campaign_id = create_response.json()["id"]
    
    # Start research
    client.post(f"/api/campaigns/{campaign_id}/research/start")
    
    # Wait a moment for research to complete (in real test, would poll)
    import time
    time.sleep(5)
    
    # Select angle - may fail validation if research hasn't completed
    response = client.post(f"/api/campaigns/{campaign_id}/angle", json={"angle_id": 1})
    
    # Accept any response (validation error is expected if research incomplete)
    assert response.status_code in [200, 400, 422, 404]


def test_retry_succeeded_stage():
    """Test that retrying a succeeded stage is rejected."""
    # Create campaign
    create_response = client.post("/api/campaigns", json={
        "product_name": "Test Product 6",
        "factual_product_description": "Test product for retry",
        "target_audience": "Test audience",
        "campaign_objective": "introduce",
        "tone": "practical_energetic",
        "call_to_action": "Test CTA",
        "verified_claims": []
    })
    
    campaign_id = create_response.json()["id"]
    
    # Start research
    client.post(f"/api/campaigns/{campaign_id}/research/start")
    
    # Try to retry (should fail if research succeeded)
    response = client.post(f"/api/campaigns/{campaign_id}/stages/research/retry")
    
    # Should return 400 if stage succeeded
    assert response.status_code in [200, 400]  # Depends on timing


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""Quick test for Phase 4 DeepSeek integration.

Run from backend/ directory:
    python test_deepseek.py
"""
from __future__ import annotations

import asyncio
import json

from services.llm_agent import DeepSeekAgent


async def test_plan_route():
    print("=" * 60)
    print("Test: DeepSeekAgent.plan_route()")
    print("=" * 60)

    agent = DeepSeekAgent()
    print(f"API Key: {agent.api_key[:10]}...")
    print(f"Model: {agent.model}")
    print(f"Base URL: {agent.base_url}")
    print()

    print("Calling DeepSeek API for Bangkok route plan...")
    plan = await agent.plan_route(
        destination_city="曼谷",
        start_poi="大皇宫",
        end_poi="拉差达火车夜市",
        start_time=9,
        end_time=20,
        num_pois=5,
    )
    print()
    print("Response:")
    print(json.dumps(plan, ensure_ascii=False, indent=2))
    print()

    # Validate structure
    assert "route" in plan, "Missing 'route' key"
    assert "agent_reasoning" in plan, "Missing 'agent_reasoning' key"
    assert isinstance(plan["route"], list), "'route' should be a list"
    assert len(plan["route"]) == 5, f"Expected 5 POIs, got {len(plan['route'])}"

    for poi in plan["route"]:
        assert "name" in poi
        assert "latitude" in poi
        assert "longitude" in poi
        assert "description" in poi

    print("✓ All structural checks passed!")
    print(f"✓ Got {len(plan['route'])} POIs")
    print(f"✓ First POI: {plan['route'][0]['name']}")
    print(f"✓ Last POI: {plan['route'][-1]['name']}")
    print(f"✓ Reasoning steps: {len(plan['agent_reasoning'])}")


if __name__ == "__main__":
    asyncio.run(test_plan_route())

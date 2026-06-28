from __future__ import annotations

import json
import re
from collections.abc import AsyncGenerator

import httpx

from config import settings


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """你是 TripManner 旅行规划助手。根据用户提供的查询信息为用户规划一条详细的旅行路线。

输出严格遵循以下JSON格式（不要输出任何markdown代码块标记，直接输出JSON）：
{
  "route": [
    {
      "poi_id": <唯一整数ID，从9001开始递增>,
      "name": "<POI中文名 (English Name)>",
      "category": "<类别，如 历史遗迹/博物馆/公园/购物区/地标 等>",
      "latitude": <纬度浮点数>,
      "longitude": <经度浮点数>,
      "recommended_duration_min": <建议停留时长，分钟数>,
      "visit_order": <访问顺序，1开始>,
      "description": "<2-4句话的行程亮点介绍，包括文化背景、看点、最佳游览时间或实用建议>"
    }
  ],
  "agent_reasoning": [
    "<推理步骤1：识别用户需求和偏好>",
    "<推理步骤2：选择POI的理由>",
    "<推理步骤3：路线优化策略>",
    "<推理步骤4：时间安排说明>"
  ],
  "confidence": <0-1之间的浮点数，表示规划置信度>,
  "route_type": "<路线类型描述，如 文化探索/美食之旅/自然风光 等>",
  "estimated_total_time_hours": <预计游览总时长，小时>,
  "estimated_transport_time_min": <预计交通耗时，分钟>
}

规划要求：
1. POI数量必须严格等于用户指定的num_pois
2. 第一个POI的name必须包含或近似匹配用户指定的start_poi
3. 最后一个POI的name必须包含或近似匹配用户指定的end_poi
4. 总时长（游览+交通）应在用户指定的start_time到end_time范围内
5. 按地理位置优化访问顺序，减少回头路
6. description必须是中文，包含具体可游览内容（不要泛泛而谈）
7. latitude/longitude必须是真实可信的坐标
8. 只输出JSON，不要任何前后缀文字、解释或markdown标记"""


USER_PROMPT_TEMPLATE = """请为我规划{destination_city}的旅行路线，要求如下：
- 出发地点：{start_poi}
- 到达地点：{end_poi}
- 出发时间：{start_time}点
- 结束时间：{end_time}点
- 途经景点数：{num_pois}个

请直接输出符合要求的JSON。"""


# ---------------------------------------------------------------------------
# DeepSeek API Client
# ---------------------------------------------------------------------------
class DeepSeekAgent:
    """Real DeepSeek LLM API integration with streaming support."""

    def __init__(self):
        self.api_key = settings.DEEPSEEK_API_KEY
        self.model = settings.DEEPSEEK_MODEL
        self.base_url = settings.DEEPSEEK_BASE_URL.rstrip("/")
        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY is not configured in .env")

    async def plan_route(
        self,
        destination_city: str,
        start_poi: str,
        end_poi: str,
        start_time: int = 9,
        end_time: int = 18,
        num_pois: int = 5,
    ) -> dict:
        """Call DeepSeek API to generate a complete route plan (non-streaming).

        Returns:
            dict matching the structured route schema.
        """
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        user_prompt = USER_PROMPT_TEMPLATE.format(
            destination_city=destination_city,
            start_poi=start_poi or "用户未指定，由你推荐",
            end_poi=end_poi or "用户未指定，由你推荐",
            start_time=start_time,
            end_time=end_time,
            num_pois=num_pois,
        )

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.7,
            "max_tokens": 3000,
            "stream": False,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

        content = data["choices"][0]["message"]["content"].strip()
        return _parse_json_response(content)

    async def plan_route_stream(
        self,
        destination_city: str,
        start_poi: str,
        end_poi: str,
        start_time: int = 9,
        end_time: int = 18,
        num_pois: int = 5,
    ) -> AsyncGenerator[str, None]:
        """Stream raw response tokens from DeepSeek.

        Yields:
            Raw token strings as they arrive.
        """
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        user_prompt = USER_PROMPT_TEMPLATE.format(
            destination_city=destination_city,
            start_poi=start_poi or "用户未指定，由你推荐",
            end_poi=end_poi or "用户未指定，由你推荐",
            start_time=start_time,
            end_time=end_time,
            num_pois=num_pois,
        )

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.7,
            "max_tokens": 3000,
            "stream": True,
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream("POST", url, headers=headers, json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    chunk_str = line[6:].strip()
                    if chunk_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(chunk_str)
                        delta = chunk["choices"][0].get("delta", {})
                        token = delta.get("content", "")
                        if token:
                            yield token
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue


# ---------------------------------------------------------------------------
# JSON parsing helpers
# ---------------------------------------------------------------------------
def _parse_json_response(content: str) -> dict:
    """Extract JSON from LLM response, handling markdown code blocks if present."""
    # Strip markdown code blocks if present
    content = content.strip()
    if content.startswith("```"):
        # Match ```json ... ``` or ``` ... ```
        match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", content, re.DOTALL)
        if match:
            content = match.group(1).strip()

    return json.loads(content)

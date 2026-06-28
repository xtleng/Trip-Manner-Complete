/**
 * Simulate SSE stream from mock route data.
 * Fires events with realistic timing: thinking -> route_text chunks -> poi_added -> intent_data -> done
 */
export function simulateSSEStream(mockRoute, handlers = {}) {
  let cancelled = false
  const controller = { close: () => { cancelled = true } }

  ;(async () => {
    const fire = (event, data) => {
      if (cancelled) return false
      if (handlers[event]) handlers[event](data)
      return true
    }
    const sleep = (ms) => new Promise(r => setTimeout(r, ms))

    // 1. Thinking
    if (!fire('thinking', { status: 'planning', text: '正在为您规划路线...', algorithm: mockRoute.algorithm_type })) return
    await sleep(800)

    // 2. Route intro text
    const city = mockRoute.city
    const numPois = mockRoute.route_result.route.length
    const introText = `好的，我为您规划了一条${city}旅行路线，共${numPois}个景点。\n\n`
    for (let i = 0; i < introText.length; i += 3) {
      if (cancelled) return
      fire('route_text', { delta: introText.slice(i, i + 3) })
      await sleep(30)
    }
    await sleep(300)

    // 3. For each POI: send poi_added + rich route_text description
    for (const poi of mockRoute.route_result.route) {
      if (cancelled) return

      // Add POI to map
      fire('poi_added', { poi })
      await sleep(400)

      // Build rich description text
      let desc = `**第${poi.visit_order}站：${poi.name}**\n`
      desc += `类型： ${poi.category}\n`
      desc += `建议游玩时长： ${poi.recommended_duration_min}分钟\n`
      if (poi.description) {
        desc += `行程亮点：\n${poi.description}\n`
      }
      desc += '\n'

      // Stream text in chunks
      for (let i = 0; i < desc.length; i += 5) {
        if (cancelled) return
        fire('route_text', { delta: desc.slice(i, i + 5) })
        await sleep(20)
      }
      await sleep(400 + Math.random() * 600)
    }

    // 4. Intent data (only for algorithm routes)
    if (mockRoute.intent_data) {
      await sleep(300)
      fire('intent_data', mockRoute.intent_data)
      await sleep(200)

      // Describe intent in text
      let intentText = ''
      if (mockRoute.intent_data.travel_mode) {
        // EKD-Trip intent
        const mode = mockRoute.intent_data.travel_mode
        const conf = Math.round(mockRoute.intent_data.travel_mode_confidence * 100)
        const modeLabels = { approaching: '接近模式', moving_away: '远离模式', u_turn: 'U型模式', irregular: '不规则模式' }
        intentText = `\n系统识别到您的出行意图为【${modeLabels[mode] || mode}】，置信度：${conf}%`
      } else if (mockRoute.intent_data.preference_factors) {
        // CrossTrip intent
        const eta = Math.round(mockRoute.intent_data.blend_weight_eta * 100)
        intentText = `\n路线中${eta}%基于您的个人偏好，${100 - eta}%参考了当地热门趋势`
      } else if (mockRoute.intent_data.agent_reasoning) {
        // DeepSeek-Agent intent
        const reasoning = mockRoute.intent_data.agent_reasoning
        intentText = `\n\n**AI 推理过程：**\n${reasoning.map((r, i) => `${i + 1}. ${r}`).join('\n')}`
        if (mockRoute.intent_data.estimated_total_time_hours) {
          intentText += `\n\n预计游览时间：${mockRoute.intent_data.estimated_total_time_hours}小时（含交通${mockRoute.intent_data.estimated_transport_time_min}分钟）`
        }
      }
      for (let i = 0; i < intentText.length; i += 4) {
        if (cancelled) return
        fire('route_text', { delta: intentText.slice(i, i + 4) })
        await sleep(25)
      }
    }

    // 5. Done
    await sleep(200)
    fire('done', { plan_id: Date.now(), algorithm: mockRoute.algorithm_type, is_mock: true })
  })()

  return controller
}

/**
 * Create real SSE connection (for Phase 2 backend integration)
 */
export function createSSEConnection(url, body, handlers = {}) {
  const abortController = new AbortController()

  ;(async () => {
    try {
      const token = localStorage.getItem('token') || ''
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify(body),
        signal: abortController.signal,
      })
      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''
        let currentEvent = ''
        for (const line of lines) {
          if (line.startsWith('event: ')) {
            currentEvent = line.slice(7).trim()
          } else if (line.startsWith('data: ') && currentEvent) {
            try {
              const data = JSON.parse(line.slice(6))
              if (handlers[currentEvent]) handlers[currentEvent](data)
            } catch {
              // ignore parse errors
            }
            currentEvent = ''
          }
        }
      }
    } catch (err) {
      if (err.name !== 'AbortError' && handlers.error) handlers.error(err)
    }
  })()

  return { close: () => abortController.abort() }
}

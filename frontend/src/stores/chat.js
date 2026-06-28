import { defineStore } from 'pinia'
import { ref } from 'vue'
import { loadMockRoutes, loadCrossCityMockRoutes, determineMockAlgorithm } from '@/api/mock'
import { simulateSSEStream } from '@/utils/sse'
import { EKD_TRIP_CITIES, CROSS_CITY_CITIES, CITY_NAME_MAP, DEEPSEEK_CITIES } from '@/utils/constants'
import { useAppStore } from './app'

export const useChatStore = defineStore('chat', () => {
  const dialogs = ref(JSON.parse(localStorage.getItem('chatDialogs') || '[]'))
  const currentDialogId = ref(null)
  const messages = ref([])
  const isStreaming = ref(false)
  const currentStreamController = ref(null)

  // Whether the user has started the trip planning flow
  const planningStarted = ref(false)

  // Dialog state machine phase
  const dialogPhase = ref('idle') // 'idle' | 'city_identified' | 'awaiting_details' | 'awaiting_stops' | 'ready'
  const detectedScenario = ref(null) // 'ekd_trip' | 'cross_city' | 'deepseek'

  // Query quintuple being built through guided dialog
  const parsedFields = ref({
    departure_city: null,
    destination_city: null,
    start_poi: null,
    end_poi: null,
    start_time: null,
    end_time: null,
    num_stops: null,
  })

  const currentAlgorithm = ref(null)
  const currentIntentData = ref(null)
  const currentPois = ref([])

  function createDialog() {
    const id = Date.now()
    const dialog = { id, title: '新对话', messages: [], created_at: new Date().toISOString() }
    dialogs.value.unshift(dialog)
    currentDialogId.value = id
    messages.value = []
    resetState()
    saveDialogs()
    return dialog
  }

  function switchDialog(id) {
    const dialog = dialogs.value.find(d => d.id === id)
    if (dialog) {
      currentDialogId.value = id
      messages.value = [...dialog.messages]
      resetState()
    }
  }

  function resetState() {
    parsedFields.value = { departure_city: null, destination_city: null, start_poi: null, end_poi: null, start_time: null, end_time: null, num_stops: null }
    planningStarted.value = false
    dialogPhase.value = 'idle'
    detectedScenario.value = null
    currentAlgorithm.value = null
    currentIntentData.value = null
    currentPois.value = []
    isStreaming.value = false
    if (currentStreamController.value) {
      currentStreamController.value.close()
      currentStreamController.value = null
    }
  }

  // --- Helper functions ---

  /** Reverse lookup: English city name -> Chinese name */
  function getCnCityName(enName) {
    for (const [cn, en] of Object.entries(CITY_NAME_MAP)) {
      if (en === enName && cn.length >= 2 && !/^[a-z]/.test(cn)) return cn
    }
    return enName
  }

  /** Detect vague/non-committal responses */
  function isVagueResponse(text) {
    const vaguePatterns = [
      '都可以', '随便', '你安排', '你来安排', '不确定', '不知道',
      '都行', '随意', '看你', '你定', '无所谓', '没想好',
      '帮我安排', '你推荐', '你决定', '交给你',
      'whatever', 'up to you', 'not sure', "don't know", 'anything', 'you decide'
    ]
    return vaguePatterns.some(p => text.toLowerCase().includes(p))
  }

  /**
   * Resolve a city name from user text. Handles Chinese, English, and mixed input.
   */
  function resolveCity(text) {
    const lower = text.toLowerCase()

    for (const [cn, en] of Object.entries(CITY_NAME_MAP)) {
      if (text.includes(cn) || lower.includes(cn)) {
        return en
      }
    }

    for (const city of EKD_TRIP_CITIES) {
      if (lower.includes(city.toLowerCase())) return city
    }

    for (const city of CROSS_CITY_CITIES) {
      if (lower.includes(city.toLowerCase())) return city
    }

    for (const city of DEEPSEEK_CITIES) {
      if (text.includes(city)) return city
    }

    return null
  }

  /** Detect departure city (source city for cross-city) */
  function resolveDepartureCity(text) {
    const lower = text.toLowerCase()
    const departurePatterns = ['从', '住在', '来自', 'from', 'live in', '出发', '目前在']
    if (!departurePatterns.some(p => lower.includes(p))) return null

    for (const [cn, en] of Object.entries(CITY_NAME_MAP)) {
      if (text.includes(cn) || lower.includes(cn)) {
        const idx = text.indexOf(cn) !== -1 ? text.indexOf(cn) : lower.indexOf(cn)
        const before = text.slice(Math.max(0, idx - 5), idx)
        if (departurePatterns.some(p => before.includes(p))) {
          return en
        }
      }
    }

    for (const city of CROSS_CITY_CITIES) {
      if (lower.includes(city.toLowerCase())) {
        const idx = lower.indexOf(city.toLowerCase())
        const before = lower.slice(Math.max(0, idx - 10), idx)
        if (departurePatterns.some(p => before.includes(p))) {
          return city
        }
      }
    }

    return null
  }

  /** Parse start/end POI from user text */
  function parsePOIs(text) {
    let startPoi = null
    let endPoi = null

    // Pattern: 从XXX出发/开始/走
    const startPatterns = [
      /从(.+?)(?:出发|开始|走|，)/,
      /从(.+?)(?:到|去)/,
    ]
    for (const pattern of startPatterns) {
      const match = text.match(pattern)
      if (match && match[1].trim().length > 1 && match[1].trim().length < 30) {
        startPoi = match[1].trim()
        break
      }
    }

    // Pattern: 到达XXX / 到XXX / 结束在XXX / 目的地是XXX
    const endPatterns = [
      /到达(.+?)(?:[，,。.！!]|$)/,
      /(?:到达|抵达)(.+?)(?:[，,。.！!]|$)/,
      /到(.+?)(?:[，,。.！!]|$)/,
    ]
    for (const pattern of endPatterns) {
      const match = text.match(pattern)
      if (match && match[1].trim().length > 1 && match[1].trim().length < 30) {
        // Exclude if this is just a time expression like "到晚上6点"
        const candidate = match[1].trim()
        if (!/^\d|^[上下]午|^早|^晚|^中午/.test(candidate)) {
          endPoi = candidate
          break
        }
      }
    }

    return { startPoi, endPoi }
  }

  /** Parse time from text */
  function parseTime(text) {
    const results = []

    // Strategy: find all time expressions with context-aware period detection
    // Pattern: (period)? + number + 点/时/:/：  OR  number + am/pm
    const fullPattern = /(?:(上午|下午|早上|晚上|am|pm)\s*)?(\d{1,2})\s*[点时:：]\s*(?:\d{0,2})\s*(am|pm|上午|下午)?/gi
    let match
    while ((match = fullPattern.exec(text)) !== null) {
      let hour = parseInt(match[2])
      const prefix = (match[1] || '').toLowerCase()
      const suffix = (match[3] || '').toLowerCase()
      const period = prefix || suffix
      if (period.includes('pm') || period.includes('下午') || period.includes('晚上')) {
        if (hour < 12) hour += 12
      } else if (period.includes('am') || period.includes('上午') || period.includes('早上')) {
        // keep as is
      } else {
        // No explicit period - check if preceded by 晚上/下午 within 4 chars
        const before = text.slice(Math.max(0, match.index - 4), match.index)
        if (/晚上|下午/.test(before)) {
          if (hour < 12) hour += 12
        }
      }
      if (hour >= 0 && hour <= 24) results.push(hour)
    }

    // Also try standalone: (period) + number without 点/时 (e.g., "晚上7" without 点)
    if (results.length < 2) {
      const periodNumPattern = /(上午|下午|早上|晚上)\s*(\d{1,2})(?!\s*[点时:：])/gi
      while ((match = periodNumPattern.exec(text)) !== null) {
        let hour = parseInt(match[2])
        const period = match[1]
        if (period === '下午' || period === '晚上') {
          if (hour < 12) hour += 12
        }
        if (hour >= 0 && hour <= 24 && !results.includes(hour)) results.push(hour)
      }
    }

    // Deduplicate
    return [...new Set(results)]
  }

  /** Parse num_stops from text */
  function parseStops(text) {
    const stopsMatch = text.match(/(\d+)\s*(个|站|景点|stops?|places?|pois?)/i)
    if (stopsMatch) return parseInt(stopsMatch[1])
    return null
  }

  /** Find best matching route based on user's start/end POIs */
  function findBestMatchingRoute(routes, startPoi, endPoi) {
    if (!startPoi && !endPoi) return routes[0]

    let bestScore = -1
    let bestRoute = routes[0]

    for (const route of routes) {
      let score = 0
      const qi = route.query_input

      // Match against query_input start_poi/end_poi
      if (startPoi && qi.start_poi) {
        const sp = startPoi.toLowerCase()
        const qsp = qi.start_poi.toLowerCase()
        if (qsp.includes(sp) || sp.includes(qsp)) score += 3
      }
      if (endPoi && qi.end_poi) {
        const ep = endPoi.toLowerCase()
        const qep = qi.end_poi.toLowerCase()
        if (qep.includes(ep) || ep.includes(qep)) score += 3
      }

      // Also match against first/last POI names in route
      const firstPoi = route.route_result.route[0]
      const lastPoi = route.route_result.route[route.route_result.route.length - 1]
      if (startPoi && firstPoi.name.toLowerCase().includes(startPoi.toLowerCase())) score += 2
      if (startPoi && firstPoi.name.includes(startPoi)) score += 1
      if (endPoi && lastPoi.name.toLowerCase().includes(endPoi.toLowerCase())) score += 2
      if (endPoi && lastPoi.name.includes(endPoi)) score += 1

      if (score > bestScore) {
        bestScore = score
        bestRoute = route
      }
    }
    return bestRoute
  }

  // --- Core parse function: extracts all info from a single message ---
  function parseUserInput(text) {
    // Only resolve cities if scenario is not yet determined (first message)
    if (!detectedScenario.value) {
      const departure = resolveDepartureCity(text)
      if (departure) parsedFields.value.departure_city = departure

      const city = resolveCity(text)
      if (city) {
        if (departure && city === departure) {
          const withoutDeparture = text.replace(departure, '').replace(getCnCityName(departure), '')
          const dest = resolveCity(withoutDeparture)
          if (dest) parsedFields.value.destination_city = dest
        } else {
          parsedFields.value.destination_city = city
        }
      }

      // Handle cross-city pattern: "从X去Y"
      const crossCityPattern = /从(.+?)[去到](.+?)(?:玩|旅[行游]|$)/
      const crossMatch = text.match(crossCityPattern)
      if (crossMatch) {
        const src = resolveCity(crossMatch[1])
        const dst = resolveCity(crossMatch[2])
        if (src) parsedFields.value.departure_city = src
        if (dst) parsedFields.value.destination_city = dst
      }
    }

    // Parse POIs
    const { startPoi, endPoi } = parsePOIs(text)
    if (startPoi) parsedFields.value.start_poi = startPoi
    if (endPoi) parsedFields.value.end_poi = endPoi

    // Parse time
    const times = parseTime(text)
    if (times.length >= 2) {
      parsedFields.value.start_time = Math.min(...times)
      parsedFields.value.end_time = Math.max(...times)
    } else if (times.length === 1) {
      if (!parsedFields.value.start_time) parsedFields.value.start_time = times[0]
      else if (!parsedFields.value.end_time) parsedFields.value.end_time = times[0]
    }

    // Parse num_stops
    const stops = parseStops(text)
    if (stops) parsedFields.value.num_stops = stops
  }

  // Detect if user message has travel planning intent
  function hasTravelIntent(text) {
    const lower = text.toLowerCase()
    const travelKeywords = [
      '旅行', '旅游', '出行', '游玩', '玩', '去', '出发', '景点', '路线', '行程', '规划',
      '想去', '打算去', '准备去', '计划去', '想到', '想逛', '看看',
      'travel', 'trip', 'visit', 'tour', 'plan', 'route', 'itinerary', 'sightseeing',
    ]
    if (travelKeywords.some(kw => lower.includes(kw))) return true
    if (resolveCity(text)) return true
    return false
  }

  // Generate a natural greeting or general response
  function generateGeneralResponse(text) {
    const lower = text.toLowerCase()
    if (/^(你好|嗨|hi|hello|hey|哈喽|good\s*(morning|afternoon|evening))/.test(lower)) {
      return '你好！我是 TripManner 旅行助手，可以为你规划旅行路线。告诉我你想去哪个城市，我来帮你安排行程吧！'
    }
    if (/(能做什么|你是谁|什么功能|怎么用|how.*work|what.*can|help|帮助|介绍)/.test(lower)) {
      return '我是 TripManner 智能旅行助手！我可以帮你：\n\n**1.** 规划城市旅行路线（支持 Tokyo、Osaka、Glasgow、Toronto 等城市）\n**2.** 跨城市行程规划（如 New York → Los Angeles）\n**3.** 智能推荐景点并展示在地图上\n\n只需告诉我你想去哪里玩，出发和结束时间，我就能为你生成个性化路线！'
    }
    if (/(谢谢|感谢|thanks|thank you|thx)/.test(lower)) {
      return '不客气！如果你有新的旅行计划，随时告诉我哦～'
    }
    return '我是你的旅行规划助手！如果你想规划一趟旅行，可以告诉我目的地城市、出发时间等信息，比如："我想去东京，从皇居出发到晴空塔，上午9点到下午6点"'
  }

  /** Determine the scenario based on destination city */
  function determineScenario(dest) {
    if (EKD_TRIP_CITIES.includes(dest)) return 'ekd_trip'
    if (CROSS_CITY_CITIES.includes(dest)) return 'cross_city'
    return 'deepseek'
  }

  /** Generate the response after city is identified */
  function generateCityIdentifiedResponse() {
    const dest = parsedFields.value.destination_city
    const destCn = getCnCityName(dest)
    const scenario = detectedScenario.value

    if (scenario === 'ekd_trip') {
      return `好的！${dest}是个很棒的选择~ 您计划什么时候出发，从哪个地点出发，到达哪个地点呢？比如"从东京皇居出发，到东京晴空塔，早上9点到晚上6点"`
    } else if (scenario === 'cross_city') {
      const departureCn = getCnCityName(parsedFields.value.departure_city || 'New York')
      return `好的！${dest}是个不错的城市~ 检测到您目前在${parsedFields.value.departure_city || 'New York'}，这将是一趟跨城市旅行。请问您打算从${dest}的哪里开始旅程，到达哪里呢？预期时间如何？比如"从盖蒂中心出发，到迪士尼音乐厅，早上9点到晚上7点"`
    } else {
      // DeepSeek: simpler question, no POI requirement
      return `好的！${destCn}是个很棒的选择~ 您计划什么时候出发，大概玩到几点呢？比如"上午9点到晚上6点"`
    }
  }

  /** Generate num_stops question */
  function generateStopsQuestion() {
    return '你想要在途中游览几个景点呢？（输入数字，或者说"都可以"让我帮你安排）'
  }

  /** Check if we have enough info to proceed to streaming for the given scenario */
  function hasEnoughDetailsForScenario() {
    const scenario = detectedScenario.value
    const f = parsedFields.value

    if (scenario === 'deepseek') {
      // DeepSeek only needs time
      return f.start_time !== null && f.end_time !== null
    }
    // EKD-Trip and Cross-City need POIs + time
    return f.start_poi && f.end_poi && f.start_time !== null && f.end_time !== null
  }

  // --- Main send message function ---
  async function sendMessage(text) {
    if (isStreaming.value) return

    // Add user message
    const userMsg = { role: 'user', content: text, timestamp: new Date().toISOString() }
    messages.value.push(userMsg)

    // Parse input for travel info
    parseUserInput(text)

    // --- Phase: idle (not yet in planning mode) ---
    if (!planningStarted.value) {
      if (hasTravelIntent(text)) {
        planningStarted.value = true
      } else {
        const response = generateGeneralResponse(text)
        messages.value.push({ role: 'assistant', content: response, timestamp: new Date().toISOString() })
        saveCurrentDialog()
        return
      }
    }

    // --- Determine scenario if we have a destination but haven't set scenario yet ---
    if (parsedFields.value.destination_city && !detectedScenario.value) {
      detectedScenario.value = determineScenario(parsedFields.value.destination_city)

      // For cross-city, auto-assign departure city if not detected
      if (detectedScenario.value === 'cross_city' && !parsedFields.value.departure_city) {
        parsedFields.value.departure_city = 'New York'
      }

      dialogPhase.value = 'city_identified'
    }

    // --- Phase: no destination yet (ask for city) ---
    if (!parsedFields.value.destination_city) {
      const response = '请问您想去哪个城市旅行呢？'
      messages.value.push({ role: 'assistant', content: response, timestamp: new Date().toISOString() })
      saveCurrentDialog()
      return
    }

    // --- Phase: city_identified -> check if user already provided everything ---
    if (dialogPhase.value === 'city_identified') {
      // Check if user provided details in the same message (one-shot)
      if (hasEnoughDetailsForScenario()) {
        // Already have POIs + time, ask about stops if not provided
        if (parsedFields.value.num_stops) {
          dialogPhase.value = 'ready'
        } else {
          dialogPhase.value = 'awaiting_stops'
          const response = generateStopsQuestion()
          messages.value.push({ role: 'assistant', content: response, timestamp: new Date().toISOString() })
          saveCurrentDialog()
          return
        }
      } else {
        // Need to ask for details
        dialogPhase.value = 'awaiting_details'
        const response = generateCityIdentifiedResponse()
        messages.value.push({ role: 'assistant', content: response, timestamp: new Date().toISOString() })
        saveCurrentDialog()
        return
      }
    }

    // --- Phase: awaiting_details ---
    if (dialogPhase.value === 'awaiting_details') {
      // For DeepSeek scenario, we only need time
      if (detectedScenario.value === 'deepseek') {
        if (parsedFields.value.start_time !== null && parsedFields.value.end_time !== null) {
          // Time collected, skip stops and go to streaming
          if (!parsedFields.value.num_stops) parsedFields.value.num_stops = 5
          dialogPhase.value = 'ready'
        } else {
          const response = '请告诉我您的出发和结束时间，比如"上午9点到晚上6点"'
          messages.value.push({ role: 'assistant', content: response, timestamp: new Date().toISOString() })
          saveCurrentDialog()
          return
        }
      } else {
        // EKD-Trip or Cross-City: need POIs + time
        // Check if user gave a vague response to the POI question
        if (isVagueResponse(text) && !parsedFields.value.start_poi && !parsedFields.value.end_poi) {
          // User doesn't want to specify POIs -> fallback to DeepSeek if not in EKD-Trip
          // For EKD-Trip cities, still use EKD-Trip with default route
          if (detectedScenario.value === 'cross_city') {
            detectedScenario.value = 'deepseek'
            dialogPhase.value = 'awaiting_details'
            const response = '没问题，我来为您智能推荐路线！请告诉我出发和结束时间就好，比如"上午9点到晚上7点"'
            messages.value.push({ role: 'assistant', content: response, timestamp: new Date().toISOString() })
            saveCurrentDialog()
            return
          }
        }

        if (hasEnoughDetailsForScenario()) {
          // All collected, ask about stops
          if (parsedFields.value.num_stops) {
            dialogPhase.value = 'ready'
          } else {
            dialogPhase.value = 'awaiting_stops'
            const response = generateStopsQuestion()
            messages.value.push({ role: 'assistant', content: response, timestamp: new Date().toISOString() })
            saveCurrentDialog()
            return
          }
        } else {
          // Still missing info - give a more specific prompt
          const f = parsedFields.value
          if (!f.start_poi && !f.end_poi) {
            const response = '请告诉我您想从哪个地点出发，到达哪个地点？以及出发和结束时间。'
            messages.value.push({ role: 'assistant', content: response, timestamp: new Date().toISOString() })
          } else if (f.start_time === null || f.end_time === null) {
            const response = '您计划什么时候出发，大概玩到几点呢？比如"早上9点到晚上6点"'
            messages.value.push({ role: 'assistant', content: response, timestamp: new Date().toISOString() })
          } else {
            // Have time but missing POIs
            const response = '请告诉我您想从哪个地点出发，到达哪个地点呢？'
            messages.value.push({ role: 'assistant', content: response, timestamp: new Date().toISOString() })
          }
          saveCurrentDialog()
          return
        }
      }
    }

    // --- Phase: awaiting_stops ---
    if (dialogPhase.value === 'awaiting_stops') {
      if (isVagueResponse(text) || !parsedFields.value.num_stops) {
        // Use default
        parsedFields.value.num_stops = 5
      }
      dialogPhase.value = 'ready'
    }

    // --- Phase: ready -> start streaming ---
    if (dialogPhase.value === 'ready') {
      await startStreaming()
    }
  }

  /** Start the SSE streaming for the route */
  async function startStreaming() {
    const dest = parsedFields.value.destination_city
    const source = parsedFields.value.departure_city

    // Determine final algorithm
    let algorithm
    if (detectedScenario.value === 'deepseek') {
      algorithm = 'DeepSeek-Agent'
    } else if (detectedScenario.value === 'cross_city') {
      algorithm = determineMockAlgorithm(dest, source)
    } else {
      algorithm = determineMockAlgorithm(dest, source)
    }

    currentAlgorithm.value = algorithm
    const appStore = useAppStore()
    appStore.setCurrentAlgorithm(algorithm)

    // Set defaults
    if (!parsedFields.value.num_stops) parsedFields.value.num_stops = 5
    if (!parsedFields.value.start_time) parsedFields.value.start_time = 9
    if (!parsedFields.value.end_time) parsedFields.value.end_time = 18

    // Start streaming
    isStreaming.value = true
    currentPois.value = []
    currentIntentData.value = null

    // Add assistant message placeholder
    const assistantMsg = { role: 'assistant', content: '', timestamp: new Date().toISOString(), pois: [], intentData: null }
    messages.value.push(assistantMsg)
    const msgIndex = messages.value.length - 1

    // Load mock route data
    let mockRoute = null
    if (algorithm === 'EKD-Trip') {
      const routes = await loadMockRoutes(dest)
      if (routes && routes.length > 0) {
        mockRoute = findBestMatchingRoute(routes, parsedFields.value.start_poi, parsedFields.value.end_poi)
      }
    } else if (algorithm === 'CrossTrip') {
      const routes = await loadCrossCityMockRoutes(source || 'New York', dest)
      if (routes && routes.length > 0) {
        mockRoute = findBestMatchingRoute(routes, parsedFields.value.start_poi, parsedFields.value.end_poi)
      }
    } else {
      // DeepSeek-Agent
      try {
        const response = await fetch('/mock/deepseek_routes.json')
        const routes = await response.json()
        mockRoute = routes.find(r => r.city === dest) || routes[0]
      } catch {
        mockRoute = null
      }
    }

    if (!mockRoute) {
      messages.value[msgIndex].content = `抱歉，暂时无法为您规划${dest}的路线。真实模式下将调用AI Agent为您生成完整路线。`
      isStreaming.value = false
      saveCurrentDialog()
      return
    }

    // Simulate SSE stream
    currentStreamController.value = simulateSSEStream(mockRoute, {
      thinking: (data) => {
        messages.value[msgIndex].content = '正在为您规划路线...\n\n'
      },
      route_text: (data) => {
        messages.value[msgIndex].content += data.delta
      },
      poi_added: (data) => {
        currentPois.value.push(data.poi)
        messages.value[msgIndex].pois = [...currentPois.value]
      },
      intent_data: (data) => {
        currentIntentData.value = data
        messages.value[msgIndex].intentData = data
      },
      done: (data) => {
        isStreaming.value = false
        currentStreamController.value = null
        saveCurrentDialog()
      },
      error: (data) => {
        isStreaming.value = false
        messages.value[msgIndex].content += '\n\n[Error occurred]'
        currentStreamController.value = null
      },
    })
  }

  function saveCurrentDialog() {
    const dialog = dialogs.value.find(d => d.id === currentDialogId.value)
    if (dialog) {
      dialog.messages = [...messages.value]
      const firstUserMsg = messages.value.find(m => m.role === 'user')
      if (firstUserMsg) dialog.title = firstUserMsg.content.slice(0, 20) + (firstUserMsg.content.length > 20 ? '...' : '')
      dialog.updated_at = new Date().toISOString()
    }
    saveDialogs()
  }

  function saveDialogs() {
    localStorage.setItem('chatDialogs', JSON.stringify(dialogs.value))
  }

  function deleteDialog(id) {
    dialogs.value = dialogs.value.filter(d => d.id !== id)
    if (currentDialogId.value === id) {
      currentDialogId.value = null
      messages.value = []
    }
    saveDialogs()
  }

  return {
    dialogs, currentDialogId, messages, isStreaming, parsedFields,
    currentAlgorithm, currentIntentData, currentPois,
    createDialog, switchDialog, sendMessage, deleteDialog, resetState,
  }
})

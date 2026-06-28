// Travel modes from EKD-Trip algorithm (Chapter 3)
export const TRAVEL_MODES = {
  approaching: { key: 'approaching', label: '接近模式', labelEn: 'Approaching', icon: '↘', color: '#67C23A', description: '沿途逐步接近最终目的地，不绕远路' },
  moving_away: { key: 'moving_away', label: '远离模式', labelEn: 'Moving Away', icon: '↗', color: '#E6A23C', description: '先远离目的地再折返' },
  u_turn: { key: 'u_turn', label: 'U型模式', labelEn: 'U-turn', icon: '⤺', color: '#409EFF', description: '到目的地的距离先增后减，呈U型' },
  irregular: { key: 'irregular', label: '不规则模式', labelEn: 'Irregular', icon: '✳', color: '#909399', description: '无明显空间移动趋势' },
}

export const EKD_TRIP_CITIES = ['Glasgow', 'Osaka', 'Toronto', 'Tokyo']
export const CROSS_CITY_CITIES = ['New York', 'Los Angeles', 'San Francisco']

// Chinese to English city name mapping
export const CITY_NAME_MAP = {
  // EKD-Trip cities
  '东京': 'Tokyo',
  '大阪': 'Osaka',
  '格拉斯哥': 'Glasgow',
  '多伦多': 'Toronto',
  // Cross-city cities
  '纽约': 'New York',
  '洛杉矶': 'Los Angeles',
  '旧金山': 'San Francisco',
  '三藩市': 'San Francisco',
  // English variants (lowercase)
  'tokyo': 'Tokyo',
  'osaka': 'Osaka',
  'glasgow': 'Glasgow',
  'toronto': 'Toronto',
  'new york': 'New York',
  'los angeles': 'Los Angeles',
  'san francisco': 'San Francisco',
  'la': 'Los Angeles',
  'sf': 'San Francisco',
  'ny': 'New York',
}

// DeepSeek-Agent demo cities (not in dataset)
export const DEEPSEEK_CITIES = ['北京', '上海', '广州', '深圳', '成都', '杭州', '西安', '重庆', '南京', '武汉', '厦门', '青岛', '大连', '苏州', '三亚', '巴黎', '伦敦', '首尔', '曼谷', '新加坡']

export const ALGORITHM_TYPES = {
  EKD_TRIP: 'EKD-Trip',
  CROSS_CITY: 'CrossTrip',
  DEEPSEEK: 'DeepSeek-Agent',
}

export const SSE_EVENT_TYPES = {
  THINKING: 'thinking',
  GUIDE_QUESTION: 'guide_question',
  ROUTE_TEXT: 'route_text',
  POI_ADDED: 'poi_added',
  INTENT_DATA: 'intent_data',
  DONE: 'done',
  ERROR: 'error',
}

// Map city names to mock JSON file names
export const CITY_TO_MOCK_FILE = {
  'Tokyo': 'tokyo_routes',
  'Osaka': 'osaka_routes',
  'Glasgow': 'glasgow_routes',
  'Toronto': 'toronto_routes',
}

// Cross-city pair keys to mock file mapping
export const CROSS_CITY_MOCK_FILES = {
  'New York_Los Angeles': 'ny_la_routes',
  'New York_San Francisco': 'ny_sf_routes',
  'Los Angeles_San Francisco': 'la_sf_routes',
}

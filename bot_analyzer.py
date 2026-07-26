import requests
import json
import time
import os
import sys
from datetime import datetime
from bs4 import BeautifulSoup

# ========================================
# 1. НАСТРОЙКИ (БЕРУТСЯ ИЗ ПЕРЕМЕННЫХ ОКРУЖЕНИЯ)
# ========================================

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', '')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')

if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
    print("❌ Ошибка: TELEGRAM_TOKEN или TELEGRAM_CHAT_ID не заданы!")
    print("Установи переменные окружения на Railway")
    sys.exit(1)

# ========================================
# 2. ПАРСЕР ФОНБЕТ
# ========================================

class FonbetParser:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
        })

    def get_api_data(self):
        """Получение данных через API"""
        api_url = 'https://line52.bkfon-resources.com/events/list'
        params = {
            'scopeMarket': '1600',
            'lang': 'ru'
        }
        
        for attempt in range(3):
            try:
                print(f"🌐 Попытка {attempt+1} запроса к API...")
                response = self.session.get(api_url, params=params, timeout=15)
                
                if response.status_code == 200:
                    print("✅ API ответ получен")
                    return response.json()
                else:
                    print(f"⚠️ Код ответа: {response.status_code}")
                    if attempt < 2:
                        time.sleep(2)
            except Exception as e:
                print(f"❌ Ошибка: {e}")
                if attempt < 2:
                    time.sleep(3)
        return None

    def parse_api_data(self, data):
        """Парсинг API данных"""
        events = []
        if not data or 'events' not in data:
            return events
            
        for event_data in data['events']:
            try:
                teams = []
                odds = {}
                
                # Команды
                if 'team1' in event_data:
                    if isinstance(event_data['team1'], dict):
                        teams.append(event_data['team1'].get('name', 'Команда 1'))
                    else:
                        teams.append(str(event_data['team1']))
                else:
                    teams.append('Команда 1')
                    
                if 'team2' in event_data:
                    if isinstance(event_data['team2'], dict):
                        teams.append(event_data['team2'].get('name', 'Команда 2'))
                    else:
                        teams.append(str(event_data['team2']))
                else:
                    teams.append('Команда 2')
                
                # Коэффициенты
                if 'odds' in event_data:
                    for odd in event_data['odds']:
                        odd_type = odd.get('type', '')
                        if odd_type in ['1', 'WIN1']:
                            odds['win1'] = odd.get('value')
                        elif odd_type in ['X', 'DRAW']:
                            odds['draw'] = odd.get('value')
                        elif odd_type in ['2', 'WIN2']:
                            odds['win2'] = odd.get('value')
                
                if odds:
                    events.append({
                        'team1': teams[0],
                        'team2': teams[1],
                        'win1': odds.get('win1'),
                        'draw': odds.get('draw'),
                        'win2': odds.get('win2')
                    })
            except:
                continue
        return events

# ========================================
# 3. АНАЛИТИК
# ========================================

class BettingAnalyzer:
    def __init__(self, events):
        self.events = events
        self.analysis_results = []

    def calculate_margin(self, event):
        try:
            w1 = event.get('win1')
            draw = event.get('draw')
            w2 = event.get('win2')
            if w1 and draw and w2:
                w1 = float(w1); draw = float(draw); w2 = float(w2)
                if w1 > 0 and draw > 0 and w2 > 0:
                    return round((1/w1 + 1/draw + 1/w2 - 1) * 100, 2)
        except:
            pass
        return None

    def find_value(self, event):
        try:
            w1 = float(event.get('win1', 0))
            w2 = float(event.get('win2', 0))
            if w1 > 0 and w2 > 0:
                avg = (w1 + w2) / 2
                if w1 > avg * 1.2:
                    return f"🔥 Валуй на П1: {w1}"
                elif w2 > avg * 1.2:
                    return f"🔥 Валуй на П2: {w2}"
        except:
            pass
        return None

    def get_recommendation(self, event):
        try:
            w1 = float(event.get('win1', 0))
            draw = float(event.get('draw', 0))
            w2 = float(event.get('win2', 0))
            
            if not (w1 > 0 and draw > 0 and w2 > 0):
                return None
            
            margin = self.calculate_margin(event)
            if margin and margin > 6:
                return "⚠️ Маржа > 6% - пропустить"
            
            if w1 < 1.5 and w1 > 1.2:
                return f"⭐ П1 + ТБ(2.5) за ~{round(w1 * 1.5, 2)}"
            elif w2 < 1.5 and w2 > 1.2:
                return f"⭐ П2 + ТБ(2.5) за ~{round(w2 * 1.5, 2)}"
            elif w1 > 2.5 and w2 > 2.5:
                return f"🔥 Равный матч! ⭐ Ф1(0) за ~{round((w1 + draw) / 2, 2)}"
            elif w1 < 2.0 and w1 > 1.3:
                return f"⭐ П1 + ТБ(2.5) за ~{round(w1 * 1.5, 2)}"
            elif w2 < 2.0 and w2 > 1.3:
                return f"⭐ П2 + ТБ(2.5) за ~{round(w2 * 1.5, 2)}"
            else:
                return f"📊 Ф1(0) за ~{round((w1 + draw) / 2, 2)}"
        except:
            return None

    def analyze_all(self):
        for event in self.events:
            analysis = {
                'team1': event.get('team1', ''),
                'team2': event.get('team2', ''),
                'win1': event.get('win1'),
                'draw': event.get('draw'),
                'win2': event.get('win2'),
                'margin': self.calculate_margin(event),
                'value': self.find_value(event),
                'recommendation': self.get_recommendation(event)
            }
            self.analysis_results.append(analysis)
        return self.analysis_results

    def get_top_picks(self, limit=5):
        valid = [a for a in self.analysis_results 
                if a['margin'] is not None and a['margin'] < 6 and a['recommendation']]
        valid.sort(key=lambda x: x['margin'])
        return valid[:limit]

# ========================================
# 4. ТЕЛЕГРАМ
# ========================================

class TelegramSender:
    def __init__(self, token, chat_id):
        self.token = token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{token}"

    def send_message(self, text):
        try:
            url = f"{self.base_url}/sendMessage"
            payload = {
                'chat_id': self.chat_id,
                'text': text,
                'parse_mode': 'HTML'
            }
            response = requests.post(url, json=payload, timeout=10)
            return response.status_code == 200
        except:
            return False

    def send_analysis(self, analysis_results):
        if not analysis_results:
            return self.send_message("❌ Нет данных")
        
        now = datetime.now().strftime("%d.%m.%Y %H:%M")
        message = f"<b>🏆 КАПЕРСКАЯ АНАЛИТИКА</b>\n"
        message += f"<i>📅 {now}</i>\n"
        message += f"{'='*30}\n\n"
        
        analyzer = BettingAnalyzer([])
        analyzer.analysis_results = analysis_results
        top_picks = analyzer.get_top_picks(5)
        
        if top_picks:
            message += "<b>⭐ ТОП-5 СТАВОК:</b>\n\n"
            for i, event in enumerate(top_picks, 1):
                message += f"<b>{i}. {event['team1']} vs {event['team2']}</b>\n"
                message += f"   П1: {event['win1']} | X: {event['draw']} | П2: {event['win2']}\n"
                if event['margin']:
                    message += f"   💹 Маржа: {event['margin']}%\n"
                if event['value']:
                    message += f"   {event['value']}\n"
                if event['recommendation']:
                    message += f"   📝 {event['recommendation']}\n"
                message += "\n"
        else:
            message += "❌ Ставок не найдено\n\n"
        
        return self.send_message(message)

# ========================================
# 5. ОСНОВНАЯ ФУНКЦИЯ
# ========================================

def run_analysis():
    print(f"\n🔄 Запуск: {datetime.now().strftime('%H:%M:%S')}")
    
    parser = FonbetParser()
    api_data = parser.get_api_data()
    
    if not api_data:
        sender = TelegramSender(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)
        sender.send_message(f"❌ Ошибка получения данных\n🕐 {datetime.now().strftime('%d.%m.%Y %H:%M')}")
        return
    
    events = parser.parse_api_data(api_data)
    
    if not events:
        sender = TelegramSender(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)
        sender.send_message(f"❌ Матчи не найдены\n🕐 {datetime.now().strftime('%d.%m.%Y %H:%M')}")
        return
    
    print(f"✅ Найдено {len(events)} матчей")
    
    analyzer = BettingAnalyzer(events)
    results = analyzer.analyze_all()
    
    sender = TelegramSender(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)
    sender.send_analysis(results)
    
    print(f"✅ Анализ отправлен")

# ========================================
# 6. ЗАПУСК
# ========================================

if __name__ == "__main__":
    print("="*60)
    print("🤖 КАПЕРСКИЙ БОТ-АНАЛИТИК v3.0")
    print("="*60)
    
    # Railway запускает скрипт при деплое
    # Добавляем небольшую задержку для гарантии
    time.sleep(2)
    run_analysis()
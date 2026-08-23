#!/usr/bin/env python3
"""Generate TankOS i18n language packs and upload them to the VPS.

The packs are JSON files mapping English source strings to translations.
They are hosted on the VPS at /var/www/html/lang/{code}.json and fetched
by the device on demand (kept off the device to save storage).

Usage:
    python3 scripts/langgen.py              # write packs to dist/lang/
    python3 scripts/langgen.py --upload     # also scp them to the VPS
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "dist" / "lang"

#: English source strings we ship translations for.
KEYS = [
    # dock
    "Home", "Drive", "Mission", "Map", "Vision", "AI", "Health", "ESP32",
    "Jetson", "Compete", "Events", "Sensors", "Topology", "Tests", "Power",
    "Analytics", "Security", "TV", "Chat", "Settings", "AI Cmd", "Safety",
    "Judge", "Dist AI", "Human", "Const", "Know Map", "Tools", "System",
    "Evolve", "AI Core",
    # settings
    "Network", "Audio", "Voice", "Display", "Privacy", "Developer",
    "Language", "Save All Settings", "⚙️ Settings",
    # common
    "Connected", "Disconnected", "Online", "Offline", "Battery",
]

#: {code: {key: translation}} — translations written by hand per language.
PACKS: dict = {
    "hi": {
        "Home": "होम", "Drive": "ड्राइव", "Mission": "मिशन", "Map": "नक्शा",
        "Vision": "विज़न", "AI": "एआई", "Health": "स्वास्थ्य", "ESP32": "ईएसपी32",
        "Jetson": "जेटसन", "Compete": "प्रतियोगिता", "Events": "घटनाएँ",
        "Sensors": "सेंसर", "Topology": "टोपोलॉजी", "Tests": "परीक्षण",
        "Power": "शक्ति", "Analytics": "विश्लेषण", "Security": "सुरक्षा",
        "TV": "टीवी", "Chat": "चैट", "Settings": "सेटिंग्स",
        "AI Cmd": "एआई कमांड", "Safety": "सुरक्षा", "Judge": "जज",
        "Dist AI": "वितरित एआई", "Human": "मानव", "Const": "संविधान",
        "Know Map": "ज्ञान मानचित्र", "Tools": "उपकरण", "System": "सिस्टम",
        "Evolve": "विकास", "AI Core": "एआई कोर",
        "Network": "नेटवर्क", "Audio": "ऑडियो", "Voice": "आवाज़",
        "Display": "डिस्प्ले", "Privacy": "गोपनीयता", "Developer": "डेवलपर",
        "Language": "भाषा", "Save All Settings": "सभी सेटिंग्स सहेजें",
        "⚙️ Settings": "⚙️ सेटिंग्स",
        "Connected": "जुड़ा", "Disconnected": "डिस्कनेक्ट", "Online": "ऑनलाइन",
        "Offline": "ऑफ़लाइन", "Battery": "बैटरी",
    },
    "bn": {
        "Home": "হোম", "Drive": "ড্রাইভ", "Mission": "মিশন", "Map": "মানচিত্র",
        "Vision": "দৃষ্টি", "AI": "এআই", "Health": "স্বাস্থ্য", "ESP32": "ইএসপি৩২",
        "Jetson": "জেটসন", "Compete": "প্রতিযোগিতা", "Events": "ঘটনা",
        "Sensors": "সেন্সর", "Topology": "টপোলজি", "Tests": "পরীক্ষা",
        "Power": "শক্তি", "Analytics": "বিশ্লেষণ", "Security": "নিরাপত্তা",
        "TV": "টিভি", "Chat": "চ্যাট", "Settings": "সেটিংস",
        "AI Cmd": "এআই কমান্ড", "Safety": "নিরাপত্তা", "Judge": "বিচারক",
        "Dist AI": "বিতরণকৃত এআই", "Human": "মানব", "Const": "সংবিধান",
        "Know Map": "জ্ঞান মানচিত্র", "Tools": "সরঞ্জাম", "System": "সিস্টেম",
        "Evolve": "বিকশিত", "AI Core": "এআই কোর",
        "Network": "নেটওয়ার্ক", "Audio": "অডিও", "Voice": "কণ্ঠ",
        "Display": "ডিসপ্লে", "Privacy": "গোপনীয়তা", "Developer": "ডেভেলপার",
        "Language": "ভাষা", "Save All Settings": "সব সেটিংস সংরক্ষণ",
        "⚙️ Settings": "⚙️ সেটিংস",
        "Connected": "সংযুক্ত", "Disconnected": "বিচ্ছিন্ন", "Online": "অনলাইন",
        "Offline": "অফলাইন", "Battery": "ব্যাটারি",
    },
    "ta": {
        "Home": "முகப்பு", "Drive": "இயக்கு", "Mission": "பணி", "Map": "வரைபடம்",
        "Vision": "பார்வை", "AI": "எய்", "Health": "உடல்நலம்", "ESP32": "ஈஎஸ்பி32",
        "Jetson": "ஜெட்சன்", "Compete": "போட்டி", "Events": "நிகழ்வுகள்",
        "Sensors": "உணரிகள்", "Topology": "இடவியல்", "Tests": "சோதனைகள்",
        "Power": "சக்தி", "Analytics": "பகுப்பாய்வு", "Security": "பாதுகாப்பு",
        "TV": "டிவி", "Chat": "அரட்டை", "Settings": "அமைப்புகள்",
        "AI Cmd": "எய் கட்டளை", "Safety": "பாதுகாப்பு", "Judge": "நீதிபதி",
        "Dist AI": "பரவலாக்க எய்", "Human": "மனிதன்", "Const": "அரசியலமைப்பு",
        "Know Map": "அறிவு வரைபடம்", "Tools": "கருவிகள்", "System": "அமைப்பு",
        "Evolve": "வளர்ச்சி", "AI Core": "எய் மையம்",
        "Network": "நெட்வொர்க்", "Audio": "ஒலி", "Voice": "குரல்",
        "Display": "காட்சி", "Privacy": "தனியுரிமை", "Developer": "டெவலப்பர்",
        "Language": "மொழி", "Save All Settings": "அனைத்து அமைப்புகளையும் சேமி",
        "⚙️ Settings": "⚙️ அமைப்புகள்",
        "Connected": "இணைந்தது", "Disconnected": "துண்டிக்கப்பட்டது",
        "Online": "ஆன்லைன்", "Offline": "ஆஃப்லைன்", "Battery": "மின்கலம்",
    },
    "te": {
        "Home": "హోమ్", "Drive": "డ్రైవ్", "Mission": "మిషన్", "Map": "మ్యాప్",
        "Vision": "దృష్టి", "AI": "ఎఐ", "Health": "ఆరోగ్యం", "ESP32": "ఈఎస్పీ32",
        "Jetson": "జెట్సన్", "Compete": "పోటీ", "Events": "సంఘటనలు",
        "Sensors": "సెన్సార్లు", "Topology": "టోపోలాజీ", "Tests": "పరీక్షలు",
        "Power": "శక్తి", "Analytics": "విశ్లేషణ", "Security": "భద్రత",
        "TV": "టీవీ", "Chat": "చాట్", "Settings": "సెట్టింగ్స్",
        "AI Cmd": "ఎఐ ఆదేశం", "Safety": "భద్రత", "Judge": "న్యాయమూర్తి",
        "Dist AI": "పంపిణీ ఎఐ", "Human": "మానవుడు", "Const": "రాజ్యాంగం",
        "Know Map": "జ్ఞాన మ్యాప్", "Tools": "సాధనాలు", "System": "సిస్టమ్",
        "Evolve": "అభివృద్ధి", "AI Core": "ఎఐ కోర్",
        "Network": "నెట్‌వర్క్", "Audio": "ఆడియో", "Voice": "గొంతు",
        "Display": "డిస్‌ప్లే", "Privacy": "గోప్యత", "Developer": "డెవలపర్",
        "Language": "భాష", "Save All Settings": "అన్ని సెట్టింగ్స్ సేవ్ చేయి",
        "⚙️ Settings": "⚙️ సెట్టింగ్స్",
        "Connected": "కనెక్ట్ అయ్యింది", "Disconnected": "డిస్‌కనెక్ట్",
        "Online": "ఆన్‌లైన్", "Offline": "ఆఫ్‌లైన్", "Battery": "బ్యాటరీ",
    },
    "mr": {
        "Home": "मुख्यपृष्ठ", "Drive": "ड्राइव्ह", "Mission": "मोहीम", "Map": "नकाशा",
        "Vision": "दृष्टी", "AI": "एआय", "Health": "आरोग्य", "ESP32": "ईएसपी32",
        "Jetson": "जेटसन", "Compete": "स्पर्धा", "Events": "घटना",
        "Sensors": "सेन्सर", "Topology": "टोपोलॉजी", "Tests": "चाचण्या",
        "Power": "शक्ती", "Analytics": "विश्लेषण", "Security": "सुरक्षा",
        "TV": "टीव्ही", "Chat": "चॅट", "Settings": "सेटिंग्ज",
        "AI Cmd": "एआय कमांड", "Safety": "सुरक्षा", "Judge": "न्यायाधीश",
        "Dist AI": "वितरित एआय", "Human": "माणूस", "Const": "राज्यघटना",
        "Know Map": "ज्ञान नकाशा", "Tools": "साधने", "System": "प्रणाली",
        "Evolve": "उत्क्रांती", "AI Core": "एआय कोर",
        "Network": "नेटवर्क", "Audio": "ऑडिओ", "Voice": "आवाज",
        "Display": "प्रदर्शन", "Privacy": "गोपनीयता", "Developer": "विकासक",
        "Language": "भाषा", "Save All Settings": "सर्व सेटिंग्ज जतन करा",
        "⚙️ Settings": "⚙️ सेटिंग्ज",
        "Connected": "कनेक्टेड", "Disconnected": "डिस्कनेक्ट", "Online": "ऑनलाइन",
        "Offline": "ऑफलाइन", "Battery": "बॅटरी",
    },
    "gu": {
        "Home": "હોમ", "Drive": "ડ્રાઇવ", "Mission": "મિશન", "Map": "નકશો",
        "Vision": "દ્રષ્ટિ", "AI": "એઆઈ", "Health": "આરોગ્ય", "ESP32": "ઈએસપી32",
        "Jetson": "જેટસન", "Compete": "સ્પર્ધા", "Events": "ઘટનાઓ",
        "Sensors": "સેન્સર", "Topology": "ટોપોલોજી", "Tests": "પરીક્ષણ",
        "Power": "શક્તિ", "Analytics": "વિશ્લેષણ", "Security": "સુરક્ષા",
        "TV": "ટીવી", "Chat": "ચેટ", "Settings": "સેટિંગ્સ",
        "AI Cmd": "એઆઈ કમાન્ડ", "Safety": "સુરક્ષા", "Judge": "ન્યાયાધીશ",
        "Dist AI": "વિતરિત એઆઈ", "Human": "માનવ", "Const": "બંધારણ",
        "Know Map": "જ્ઞાન નકશો", "Tools": "સાધનો", "System": "સિસ્ટમ",
        "Evolve": "વિકાસ", "AI Core": "એઆઈ કોર",
        "Network": "નેટવર્ક", "Audio": "ઓડિયો", "Voice": "અવાજ",
        "Display": "ડિસ્પ્લે", "Privacy": "ગોપનીયતા", "Developer": "ડેવલપર",
        "Language": "ભાષા", "Save All Settings": "બધી સેટિંગ્સ સાચવો",
        "⚙️ Settings": "⚙️ સેટિંગ્સ",
        "Connected": "કનેક્ટેડ", "Disconnected": "ડિસ્કનેક્ટ", "Online": "ઓનલાઈન",
        "Offline": "ઓફલાઈન", "Battery": "બેટરી",
    },
    "es": {
        "Home": "Inicio", "Drive": "Conducir", "Mission": "Misión", "Map": "Mapa",
        "Vision": "Visión", "AI": "IA", "Health": "Salud", "ESP32": "ESP32",
        "Jetson": "Jetson", "Compete": "Competir", "Events": "Eventos",
        "Sensors": "Sensores", "Topology": "Topología", "Tests": "Pruebas",
        "Power": "Energía", "Analytics": "Analítica", "Security": "Seguridad",
        "TV": "TV", "Chat": "Chat", "Settings": "Ajustes",
        "AI Cmd": "Cmd IA", "Safety": "Seguridad", "Judge": "Juez",
        "Dist AI": "IA Distrib.", "Human": "Humano", "Const": "Const.",
        "Know Map": "Mapa Saber", "Tools": "Herramientas", "System": "Sistema",
        "Evolve": "Evolucionar", "AI Core": "Núcleo IA",
        "Network": "Red", "Audio": "Audio", "Voice": "Voz",
        "Display": "Pantalla", "Privacy": "Privacidad", "Developer": "Desarrollador",
        "Language": "Idioma", "Save All Settings": "Guardar todos los ajustes",
        "⚙️ Settings": "⚙️ Ajustes",
        "Connected": "Conectado", "Disconnected": "Desconectado",
        "Online": "En línea", "Offline": "Sin conexión", "Battery": "Batería",
    },
    "fr": {
        "Home": "Accueil", "Drive": "Conduire", "Mission": "Mission", "Map": "Carte",
        "Vision": "Vision", "AI": "IA", "Health": "Santé", "ESP32": "ESP32",
        "Jetson": "Jetson", "Compete": "Concourir", "Events": "Événements",
        "Sensors": "Capteurs", "Topology": "Topologie", "Tests": "Tests",
        "Power": "Énergie", "Analytics": "Analytique", "Security": "Sécurité",
        "TV": "TV", "Chat": "Discussion", "Settings": "Réglages",
        "AI Cmd": "Cmd IA", "Safety": "Sécurité", "Judge": "Juge",
        "Dist AI": "IA Distrib.", "Human": "Humain", "Const": "Const.",
        "Know Map": "Carte Savoir", "Tools": "Outils", "System": "Système",
        "Evolve": "Évoluer", "AI Core": "Noyau IA",
        "Network": "Réseau", "Audio": "Audio", "Voice": "Voix",
        "Display": "Affichage", "Privacy": "Confidentialité", "Developer": "Développeur",
        "Language": "Langue", "Save All Settings": "Enregistrer tous les réglages",
        "⚙️ Settings": "⚙️ Réglages",
        "Connected": "Connecté", "Disconnected": "Déconnecté",
        "Online": "En ligne", "Offline": "Hors ligne", "Battery": "Batterie",
    },
    "de": {
        "Home": "Start", "Drive": "Fahren", "Mission": "Mission", "Map": "Karte",
        "Vision": "Sicht", "AI": "KI", "Health": "Gesundheit", "ESP32": "ESP32",
        "Jetson": "Jetson", "Compete": "Wettkampf", "Events": "Ereignisse",
        "Sensors": "Sensoren", "Topology": "Topologie", "Tests": "Tests",
        "Power": "Energie", "Analytics": "Analyse", "Security": "Sicherheit",
        "TV": "TV", "Chat": "Chat", "Settings": "Einstellungen",
        "AI Cmd": "KI-Befehl", "Safety": "Sicherheit", "Judge": "Richter",
        "Dist AI": "Verteilte KI", "Human": "Mensch", "Const": "Verfassung",
        "Know Map": "Wissenskarte", "Tools": "Werkzeuge", "System": "System",
        "Evolve": "Entwickeln", "AI Core": "KI-Kern",
        "Network": "Netzwerk", "Audio": "Audio", "Voice": "Stimme",
        "Display": "Anzeige", "Privacy": "Datenschutz", "Developer": "Entwickler",
        "Language": "Sprache", "Save All Settings": "Alle Einstellungen speichern",
        "⚙️ Settings": "⚙️ Einstellungen",
        "Connected": "Verbunden", "Disconnected": "Getrennt",
        "Online": "Online", "Offline": "Offline", "Battery": "Akku",
    },
    "it": {
        "Home": "Home", "Drive": "Guida", "Mission": "Missione", "Map": "Mappa",
        "Vision": "Visione", "AI": "IA", "Health": "Salute", "ESP32": "ESP32",
        "Jetson": "Jetson", "Compete": "Gareggia", "Events": "Eventi",
        "Sensors": "Sensori", "Topology": "Topologia", "Tests": "Test",
        "Power": "Energia", "Analytics": "Analisi", "Security": "Sicurezza",
        "TV": "TV", "Chat": "Chat", "Settings": "Impostazioni",
        "AI Cmd": "Cmd IA", "Safety": "Sicurezza", "Judge": "Giudice",
        "Dist AI": "IA Distrib.", "Human": "Umano", "Const": "Cost.",
        "Know Map": "Mappa Sapere", "Tools": "Strumenti", "System": "Sistema",
        "Evolve": "Evolvere", "AI Core": "Nucleo IA",
        "Network": "Rete", "Audio": "Audio", "Voice": "Voce",
        "Display": "Schermo", "Privacy": "Privacy", "Developer": "Sviluppatore",
        "Language": "Lingua", "Save All Settings": "Salva tutte le impostazioni",
        "⚙️ Settings": "⚙️ Impostazioni",
        "Connected": "Connesso", "Disconnected": "Disconnesso",
        "Online": "Online", "Offline": "Offline", "Battery": "Batteria",
    },
    "pt": {
        "Home": "Início", "Drive": "Conduzir", "Mission": "Missão", "Map": "Mapa",
        "Vision": "Visão", "AI": "IA", "Health": "Saúde", "ESP32": "ESP32",
        "Jetson": "Jetson", "Compete": "Competir", "Events": "Eventos",
        "Sensors": "Sensores", "Topology": "Topologia", "Tests": "Testes",
        "Power": "Energia", "Analytics": "Análise", "Security": "Segurança",
        "TV": "TV", "Chat": "Chat", "Settings": "Configurações",
        "AI Cmd": "Cmd IA", "Safety": "Segurança", "Judge": "Juiz",
        "Dist AI": "IA Distrib.", "Human": "Humano", "Const": "Const.",
        "Know Map": "Mapa Saber", "Tools": "Ferramentas", "System": "Sistema",
        "Evolve": "Evoluir", "AI Core": "Núcleo IA",
        "Network": "Rede", "Audio": "Áudio", "Voice": "Voz",
        "Display": "Ecrã", "Privacy": "Privacidade", "Developer": "Desenvolvedor",
        "Language": "Idioma", "Save All Settings": "Salvar todas as configurações",
        "⚙️ Settings": "⚙️ Configurações",
        "Connected": "Conectado", "Disconnected": "Desconectado",
        "Online": "Online", "Offline": "Offline", "Battery": "Bateria",
    },
    "ru": {
        "Home": "Дом", "Drive": "Движение", "Mission": "Миссия", "Map": "Карта",
        "Vision": "Зрение", "AI": "ИИ", "Health": "Здоровье", "ESP32": "ESP32",
        "Jetson": "Jetson", "Compete": "Соревн.", "Events": "События",
        "Sensors": "Датчики", "Topology": "Топология", "Tests": "Тесты",
        "Power": "Энергия", "Analytics": "Аналитика", "Security": "Безопасность",
        "TV": "ТВ", "Chat": "Чат", "Settings": "Настройки",
        "AI Cmd": "Ком. ИИ", "Safety": "Безопасность", "Judge": "Судья",
        "Dist AI": "Распр. ИИ", "Human": "Человек", "Const": "Конституция",
        "Know Map": "Карта знаний", "Tools": "Инструменты", "System": "Система",
        "Evolve": "Развитие", "AI Core": "Ядро ИИ",
        "Network": "Сеть", "Audio": "Аудио", "Voice": "Голос",
        "Display": "Дисплей", "Privacy": "Конфиденциальность", "Developer": "Разработчик",
        "Language": "Язык", "Save All Settings": "Сохранить все настройки",
        "⚙️ Settings": "⚙️ Настройки",
        "Connected": "Подключено", "Disconnected": "Отключено",
        "Online": "Онлайн", "Offline": "Офлайн", "Battery": "Батарея",
    },
    "zh": {
        "Home": "主页", "Drive": "驾驶", "Mission": "任务", "Map": "地图",
        "Vision": "视觉", "AI": "AI", "Health": "健康", "ESP32": "ESP32",
        "Jetson": "Jetson", "Compete": "竞赛", "Events": "事件",
        "Sensors": "传感器", "Topology": "拓扑", "Tests": "测试",
        "Power": "电源", "Analytics": "分析", "Security": "安全",
        "TV": "电视", "Chat": "聊天", "Settings": "设置",
        "AI Cmd": "AI命令", "Safety": "安全", "Judge": "裁判",
        "Dist AI": "分布式AI", "Human": "人类", "Const": "宪法",
        "Know Map": "知识地图", "Tools": "工具", "System": "系统",
        "Evolve": "进化", "AI Core": "AI核心",
        "Network": "网络", "Audio": "音频", "Voice": "语音",
        "Display": "显示", "Privacy": "隐私", "Developer": "开发者",
        "Language": "语言", "Save All Settings": "保存所有设置",
        "⚙️ Settings": "⚙️ 设置",
        "Connected": "已连接", "Disconnected": "已断开",
        "Online": "在线", "Offline": "离线", "Battery": "电池",
    },
    "ja": {
        "Home": "ホーム", "Drive": "運転", "Mission": "ミッション", "Map": "地図",
        "Vision": "視覚", "AI": "AI", "Health": "健康", "ESP32": "ESP32",
        "Jetson": "Jetson", "Compete": "競技", "Events": "イベント",
        "Sensors": "センサー", "Topology": "トポロジ", "Tests": "テスト",
        "Power": "電源", "Analytics": "分析", "Security": "セキュリティ",
        "TV": "テレビ", "Chat": "チャット", "Settings": "設定",
        "AI Cmd": "AIコマンド", "Safety": "安全", "Judge": "審査員",
        "Dist AI": "分散AI", "Human": "人間", "Const": "憲法",
        "Know Map": "知識マップ", "Tools": "ツール", "System": "システム",
        "Evolve": "進化", "AI Core": "AIコア",
        "Network": "ネットワーク", "Audio": "オーディオ", "Voice": "音声",
        "Display": "ディスプレイ", "Privacy": "プライバシー", "Developer": "開発者",
        "Language": "言語", "Save All Settings": "すべての設定を保存",
        "⚙️ Settings": "⚙️ 設定",
        "Connected": "接続済み", "Disconnected": "切断済み",
        "Online": "オンライン", "Offline": "オフライン", "Battery": "バッテリー",
    },
    "ko": {
        "Home": "홈", "Drive": "주행", "Mission": "임무", "Map": "지도",
        "Vision": "시각", "AI": "AI", "Health": "건강", "ESP32": "ESP32",
        "Jetson": "젯슨", "Compete": "경쟁", "Events": "이벤트",
        "Sensors": "센서", "Topology": "토폴로지", "Tests": "테스트",
        "Power": "전원", "Analytics": "분석", "Security": "보안",
        "TV": "TV", "Chat": "채팅", "Settings": "설정",
        "AI Cmd": "AI 명령", "Safety": "안전", "Judge": "심사위원",
        "Dist AI": "분산 AI", "Human": "인간", "Const": "헌법",
        "Know Map": "지식 지도", "Tools": "도구", "System": "시스템",
        "Evolve": "진화", "AI Core": "AI 코어",
        "Network": "네트워크", "Audio": "오디오", "Voice": "음성",
        "Display": "디스플레이", "Privacy": "개인정보", "Developer": "개발자",
        "Language": "언어", "Save All Settings": "모든 설정 저장",
        "⚙️ Settings": "⚙️ 설정",
        "Connected": "연결됨", "Disconnected": "연결 끊김",
        "Online": "온라인", "Offline": "오프라인", "Battery": "배터리",
    },
    "ar": {
        "Home": "الرئيسية", "Drive": "قيادة", "Mission": "مهمة", "Map": "خريطة",
        "Vision": "رؤية", "AI": "ذكاء اصطناعي", "Health": "صحة", "ESP32": "إي إس بي 32",
        "Jetson": "جيتسون", "Compete": "منافسة", "Events": "أحداث",
        "Sensors": "أجهزة استشعار", "Topology": "طوبولوجيا", "Tests": "اختبارات",
        "Power": "طاقة", "Analytics": "تحليلات", "Security": "أمان",
        "TV": "تلفاز", "Chat": "محادثة", "Settings": "إعدادات",
        "AI Cmd": "أمر ذكاء", "Safety": "سلامة", "Judge": "حكم",
        "Dist AI": "ذكاء موزع", "Human": "إنسان", "Const": "دستور",
        "Know Map": "خريطة معرفة", "Tools": "أدوات", "System": "نظام",
        "Evolve": "تطور", "AI Core": "نواة ذكاء",
        "Network": "شبكة", "Audio": "صوت", "Voice": "صوت",
        "Display": "شاشة", "Privacy": "خصوصية", "Developer": "مطور",
        "Language": "لغة", "Save All Settings": "حفظ جميع الإعدادات",
        "⚙️ Settings": "⚙️ إعدادات",
        "Connected": "متصل", "Disconnected": "غير متصل",
        "Online": "متصل", "Offline": "غير متصل", "Battery": "بطارية",
    },
}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    written = []
    for code, pack in PACKS.items():
        full = {k: pack.get(k, k) for k in KEYS}
        path = OUT / f"{code}.json"
        path.write_text(json.dumps(full, ensure_ascii=False, indent=1) + "\n")
        written.append(code)
    print(f"wrote {len(written)} packs -> {OUT}")

    if "--upload" in sys.argv:
        vps = "root@100.71.127.19"
        remote = "/var/www/html/lang"
        subprocess.run(["ssh", "-o", "StrictHostKeyChecking=no", vps,
                        f"mkdir -p {remote}"], check=False)
        for path in OUT.glob("*.json"):
            subprocess.run(["scp", "-o", "StrictHostKeyChecking=no",
                            str(path), f"{vps}:{remote}/{path.name}"],
                           check=False)
        print(f"uploaded to {vps}:{remote}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
F1 2026赛季中文赛历智能汉化脚本
功能：自动从官方源下载ICS，翻译成中文（赛道/国家/比赛类型）
作者：您的名字
版本：1.0
"""

import requests
from icalendar import Calendar
import json
import os
import re
import time
from datetime import datetime, timedelta
from typing import Dict, List, Set, Optional

# ==================== 配置区域 ====================
# F1 2026官方赛历链接（您提供的）
F1_ICS_URL = "webcal://ics.ecal.com/ecal-sub/69b97ec9eaa15b000264bbc8/Formula%201.ics"
OUTPUT_FILE = "f1_2026_chinese.ics"
CACHE_FILE = "f1_translation_cache.json"
MAPPING_FILE = "f1_translation_mapping.json"
CACHE_EXPIRY_DAYS = 90  # F1赛季较长，缓存有效期延长

# ==================== 基础翻译映射表（F1专用）====================

# 比赛类型翻译
RACE_TYPE_TRANSLATION = {
    "Practice 1": "第一次自由练习赛",
    "Practice 2": "第二次自由练习赛",
    "Practice 3": "第三次自由练习赛",
    "Qualifying": "排位赛",
    "Sprint Qualifying": "冲刺排位赛",
    "Sprint": "冲刺赛",
    "Race": "正赛",
    "Grand Prix": "大奖赛",
    "Formula 1": "世界一级方程式锦标赛",
}

# 国家/地区翻译（用于赛道名称中的国家标识）
COUNTRY_TRANSLATION = {
    "Bahrain": "巴林",
    "Saudi Arabia": "沙特阿拉伯",
    "Australia": "澳大利亚",
    "Japan": "日本",
    "China": "中国",
    "Miami": "迈阿密",
    "Emilia Romagna": "艾米利亚-罗马涅",
    "Monaco": "摩纳哥",
    "Spain": "西班牙",
    "Canada": "加拿大",
    "Austria": "奥地利",
    "Great Britain": "英国",
    "Hungary": "匈牙利",
    "Belgium": "比利时",
    "Netherlands": "荷兰",
    "Italy": "意大利",
    "Azerbaijan": "阿塞拜疆",
    "Singapore": "新加坡",
    "USA": "美国",
    "Mexico": "墨西哥",
    "Brazil": "巴西",
    "Las Vegas": "拉斯维加斯",
    "Qatar": "卡塔尔",
    "Abu Dhabi": "阿布扎比",
}

# 赛道名称翻译（精确匹配）
CIRCUIT_TRANSLATION = {
    "Bahrain International Circuit": "巴林国际赛道",
    "Jeddah Corniche Circuit": "吉达滨海赛道",
    "Albert Park Circuit": "阿尔伯特公园赛道",
    "Suzuka International Racing Course": "铃鹿国际赛车场",
    "Shanghai International Circuit": "上海国际赛车场",
    "Miami International Autodrome": "迈阿密国际赛道",
    "Imola Circuit": "伊莫拉赛道",
    "Circuit de Monaco": "摩纳哥赛道",
    "Circuit de Barcelona-Catalunya": "巴塞罗那-加泰罗尼亚赛道",
    "Circuit Gilles Villeneuve": "吉尔·维伦纽夫赛道",
    "Red Bull Ring": "红牛环赛道",
    "Silverstone Circuit": "银石赛道",
    "Hungaroring": "亨格罗宁赛道",
    "Circuit de Spa-Francorchamps": "斯帕-弗朗科尔尚赛道",
    "Circuit Zandvoort": "赞德沃特赛道",
    "Monza Circuit": "蒙扎赛道",
    "Baku City Circuit": "巴库城市赛道",
    "Marina Bay Street Circuit": "滨海湾街道赛道",
    "Circuit of the Americas": "美洲赛道",
    "Autódromo Hermanos Rodríguez": "罗德里格斯兄弟赛道",
    "Interlagos Circuit": "英特拉格斯赛道",
    "Las Vegas Strip Circuit": "拉斯维加斯大道赛道",
    "Lusail International Circuit": "卢赛尔国际赛道",
    "Yas Marina Circuit": "亚斯码头赛道",
}

# 月份翻译
MONTH_TRANSLATION = {
    "January": "1月", "February": "2月", "March": "3月",
    "April": "4月", "May": "5月", "June": "6月",
    "July": "7月", "August": "8月", "September": "9月",
    "October": "10月", "November": "11月", "December": "12月",
}

# ==================== 自动联网翻译获取器 ====================

class F1TranslationFetcher:
    """F1专用自动联网翻译获取器"""
    
    def __init__(self):
        self.cache = self.load_cache()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def load_cache(self) -> Dict:
        """加载本地缓存"""
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                    cache = json.load(f)
                    # 清理过期缓存
                    now = time.time()
                    for key in list(cache.keys()):
                        if now - cache[key].get('timestamp', 0) > CACHE_EXPIRY_DAYS * 86400:
                            del cache[key]
                    return cache
            except:
                return {}
        return {}
    
    def save_cache(self):
        """保存缓存"""
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.cache, f, ensure_ascii=False, indent=2)
    
    def fetch_from_baidu_baike(self, term: str) -> Optional[str]:
        """从百度百科获取中文译名"""
        try:
            search_url = f"https://baike.baidu.com/search/word?word={term}"
            response = self.session.get(search_url, timeout=5)
            
            if response.status_code == 200:
                # 匹配百科页面的标题
                title_match = re.search(r'<title>(.+?)[_|]百度百科</title>', response.text)
                if title_match:
                    chinese_title = title_match.group(1).strip()
                    chinese_title = re.sub(r'\s+', '', chinese_title)
                    return chinese_title
            
            time.sleep(1)
            return None
            
        except Exception as e:
            print(f"  百度百科查询失败 [{term}]: {str(e)}")
            return None
    
    def fetch_from_f1_china(self, term: str) -> Optional[str]:
        """从F1中国官网获取译名"""
        try:
            # F1中国官网可能有不同的命名习惯
            search_url = f"https://www.formula1.com/en/racing/2026/{term}.html"
            # 这里可以添加解析逻辑
            return None
        except:
            return None
    
    def get_translation(self, term: str, context: str = 'circuit') -> str:
        """
        获取中文译名的主方法
        term: 英文名称
        context: 上下文类型（circuit/country/racetype）
        """
        cache_key = f"{context}:{term}"
        
        # 检查缓存
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            if time.time() - cached['timestamp'] < CACHE_EXPIRY_DAYS * 86400:
                print(f"  使用缓存 [{term}] -> {cached['translation']}")
                return cached['translation']
        
        print(f"  🔍 正在查询 [{term}] 的中文译名...")
        translation = None
        
        if context == 'circuit':
            # 赛道名称：优先百度百科
            translation = self.fetch_from_baidu_baike(term)
            if not translation:
                translation = self.smart_circuit_translation(term)
        
        elif context == 'country':
            # 国家名称：直接用映射表或规则
            translation = self.translate_country(term)
        
        elif context == 'racetype':
            # 比赛类型：用规则翻译
            translation = self.translate_racetype(term)
        
        # 备用规则
        if not translation:
            translation = self.fallback_translation(term)
        
        # 存入缓存
        self.cache[cache_key] = {
            'translation': translation,
            'term': term,
            'context': context,
            'timestamp': time.time()
        }
        self.save_cache()
        
        print(f"  ✅ 获取到 [{term}] -> {translation}")
        return translation
    
    def smart_circuit_translation(self, term: str) -> str:
        """智能赛道名称翻译"""
        # 处理常见的赛道命名模式
        patterns = [
            (r'Circuit$', '赛道'),
            (r'International Circuit$', '国际赛道'),
            (r'Grand Prix Circuit$', '大奖赛赛道'),
            (r'Raceway$', '赛道'),
            (r'Autodrome$', '赛道'),
            (r'Autódromo$', '赛道'),
            (r'Park$', '公园赛道'),
            (r'Street Circuit$', '街道赛道'),
        ]
        
        for pattern, replacement in patterns:
            if re.search(pattern, term, re.IGNORECASE):
                return re.sub(pattern, replacement, term, flags=re.IGNORECASE)
        
        return term + "赛道"
    
    def translate_country(self, term: str) -> str:
        """国家名称翻译"""
        # 优先使用映射表
        for eng, chn in COUNTRY_TRANSLATION.items():
            if eng.lower() in term.lower():
                return chn
        return term
    
    def translate_racetype(self, term: str) -> str:
        """比赛类型翻译"""
        for eng, chn in RACE_TYPE_TRANSLATION.items():
            if eng.lower() in term.lower():
                return chn
        return term
    
    def fallback_translation(self, term: str) -> str:
        """备用翻译"""
        return term


# ==================== ICS处理器 ====================

class F1ICSChineseProcessor:
    """F1 ICS文件中文处理器"""
    
    def __init__(self):
        self.fetcher = F1TranslationFetcher()
        # 加载已有的映射表
        self.circuit_dict = self.load_mapping('circuits', CIRCUIT_TRANSLATION)
        self.country_dict = self.load_mapping('countries', COUNTRY_TRANSLATION)
        self.racetype_dict = self.load_mapping('racetypes', RACE_TYPE_TRANSLATION)
        
        # 记录新发现的实体
        self.new_circuits = set()
        self.new_countries = set()
        self.new_racetypes = set()
    
    def load_mapping(self, key: str, default_dict: Dict) -> Dict:
        """加载已保存的映射表"""
        if os.path.exists(MAPPING_FILE):
            try:
                with open(MAPPING_FILE, 'r', encoding='utf-8') as f:
                    mapping = json.load(f)
                    if key in mapping:
                        return mapping[key]
            except:
                pass
        return default_dict.copy()
    
    def save_all_mappings(self):
        """保存所有映射表"""
        mapping = {
            'circuits': self.circuit_dict,
            'countries': self.country_dict,
            'racetypes': self.racetype_dict,
            'updated_at': datetime.now().isoformat()
        }
        
        with open(MAPPING_FILE, 'w', encoding='utf-8') as f:
            json.dump(mapping, f, ensure_ascii=False, indent=2)
        
        print(f"\n📁 翻译映射表已保存到 {MAPPING_FILE}")
        print(f"   - 赛道: {len(self.circuit_dict)} 个")
        print(f"   - 国家: {len(self.country_dict)} 个")
        print(f"   - 比赛类型: {len(self.racetype_dict)} 个")
    
    def extract_entities_from_calendar(self, cal: Calendar):
        """从日历中提取需要翻译的实体"""
        for component in cal.walk():
            if component.name == "VEVENT":
                # 从标题提取
                if 'SUMMARY' in component:
                    summary = str(component.get('SUMMARY'))
                    self._extract_from_summary(summary)
                
                # 从地点提取赛道
                if 'LOCATION' in component:
                    location = str(component.get('LOCATION'))
                    if location and location not in self.circuit_dict:
                        self.new_circuits.add(location)
                
                # 从描述提取
                if 'DESCRIPTION' in component:
                    desc = str(component.get('DESCRIPTION'))
                    self._extract_from_description(desc)
    
    def _extract_from_summary(self, summary: str):
        """从标题中提取实体"""
        # F1标题格式示例："2026 Formula 1 Bahrain Grand Prix - Race"
        # 提取比赛类型
        for racetype in RACE_TYPE_TRANSLATION.keys():
            if racetype in summary and racetype not in self.racetype_dict:
                self.new_racetypes.add(racetype)
        
        # 提取国家/城市名
        for country in COUNTRY_TRANSLATION.keys():
            if country in summary and country not in self.country_dict:
                self.new_countries.add(country)
    
    def _extract_from_description(self, desc: str):
        """从描述中提取实体"""
        # 描述中可能包含更详细的信息
        pass
    
    def fetch_new_translations(self):
        """批量获取新实体的翻译"""
        print("\n🔍 开始查询新实体的中文译名...")
        
        # 查询新赛道
        if self.new_circuits:
            print(f"\n🏁 新赛道 ({len(self.new_circuits)} 个):")
            for circuit in sorted(self.new_circuits):
                translation = self.fetcher.get_translation(circuit, 'circuit')
                self.circuit_dict[circuit] = translation
        
        # 查询新国家
        if self.new_countries:
            print(f"\n🌍 新国家 ({len(self.new_countries)} 个):")
            for country in sorted(self.new_countries):
                translation = self.fetcher.get_translation(country, 'country')
                self.country_dict[country] = translation
        
        # 查询新比赛类型
        if self.new_racetypes:
            print(f"\n🏎️ 新比赛类型 ({len(self.new_racetypes)} 个):")
            for racetype in sorted(self.new_racetypes):
                translation = self.fetcher.get_translation(racetype, 'racetype')
                self.racetype_dict[racetype] = translation
    
    def translate_calendar(self, cal: Calendar) -> Calendar:
        """翻译日历"""
        event_count = 0
        
        print("\n🔄 开始翻译F1赛历...")
        for component in cal.walk():
            if component.name == "VEVENT":
                event_count += 1
                
                # 翻译标题
                if 'SUMMARY' in component:
                    original = str(component.get('SUMMARY'))
                    translated = original
                    
                    # 应用比赛类型翻译
                    for eng, chn in self.racetype_dict.items():
                        translated = translated.replace(eng, chn)
                    
                    # 应用国家翻译
                    for eng, chn in self.country_dict.items():
                        translated = translated.replace(eng, chn)
                    
                    # 添加表情符号增强可读性
                    translated = self.add_emoji(translated)
                    
                    component['SUMMARY'] = translated
                    print(f"  赛事{event_count}: {translated[:60]}...")
                
                # 翻译地点（赛道）
                if 'LOCATION' in component:
                    original = str(component.get('LOCATION'))
                    translated = original
                    for eng, chn in self.circuit_dict.items():
                        translated = translated.replace(eng, chn)
                    component['LOCATION'] = translated
                
                # 翻译描述
                if 'DESCRIPTION' in component:
                    original = str(component.get('DESCRIPTION'))
                    translated = self.translate_description(original)
                    component['DESCRIPTION'] = translated
        
        print(f"\n✅ 翻译完成，共处理 {event_count} 个赛事环节")
        return cal
    
    def translate_description(self, desc: str) -> str:
        """翻译描述信息"""
        if not desc:
            return ""
        
        # 翻译常见字段
        desc = desc.replace("Location:", "📍 地点:")
        desc = desc.replace("Circuit:", "🏁 赛道:")
        desc = desc.replace("Session:", "🔰 环节:")
        desc = desc.replace("Round:", "🏆 分站:")
        
        # 应用已有的翻译
        for eng, chn in self.circuit_dict.items():
            desc = desc.replace(eng, chn)
        
        return desc
    
    def add_emoji(self, text: str) -> str:
        """根据内容添加表情符号"""
        if "Race" in text or "正赛" in text:
            return "🏁 " + text
        elif "Qualifying" in text or "排位" in text:
            return "⏱️ " + text
        elif "Practice" in text or "练习" in text:
            return "🔧 " + text
        elif "Sprint" in text:
            return "⚡ " + text
        return text


# ==================== 主程序 ====================

def fetch_f1_calendar():
    """获取F1官方赛历"""
    
    urls = [
        F1_ICS_URL,
        "https://ics.ecal.com/ecal-sub/69b97ec9eaa15b000264bbc8/Formula%201.ics",  # 转换https
        "https://www.formula1.com/en/calendar/2026.ics",  # 备用官方源
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/calendar,application/ical,text/plain,*/*',
    }
    
    for i, url in enumerate(urls, 1):
        print(f"\n尝试链接 {i}/{len(urls)}: {url}")
        
        try:
            # 处理webcal协议
            if url.startswith('webcal://'):
                url = 'https://' + url[8:]
                print(f"  转换为: {url}")
            
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                # 检查是否是HTML
                if response.text.strip().startswith('<!DOCTYPE') or response.text.strip().startswith('<?xml'):
                    print(f"  返回的是HTML页面，尝试下一个...")
                    continue
                
                # 尝试解析
                try:
                    cal = Calendar.from_ical(response.text)
                    print(f"✅ 成功获取F1赛历！")
                    return cal
                except Exception as e:
                    print(f"  解析失败: {e}")
                    continue
            else:
                print(f"  状态码: {response.status_code}")
                
        except Exception as e:
            print(f"  连接失败: {e}")
            continue
    
    return None

def main():
    print("=" * 60)
    print("🏎️ F1 2026赛季中文赛历智能汉化系统")
    print("（自动联网翻译 + 赛道/国家/赛事类型）")
    print("=" * 60)
    
    # 1. 获取日历
    cal = fetch_f1_calendar()
    if not cal:
        print("\n❌ 无法获取F1官方赛历！")
        print("请检查：")
        print("1. 网络连接")
        print("2. 官方链接是否有效")
        print("\n您也可以手动下载ICS文件放到脚本目录")
        sys.exit(1)
    
    # 2. 创建处理器
    processor = F1ICSChineseProcessor()
    
    # 3. 提取实体
    print("\n🔎 正在分析赛历内容...")
    processor.extract_entities_from_calendar(cal)
    
    # 4. 获取新实体的翻译
    processor.fetch_new_translations()
    
    # 5. 翻译日历
    translated_cal = processor.translate_calendar(cal)
    
    # 6. 保存翻译后的文件
    with open(OUTPUT_FILE, 'wb') as f:
        f.write(translated_cal.to_ical())
    
    # 7. 保存映射表
    processor.save_all_mappings()
    
    # 8. 显示统计
    print(f"\n✅ 完成！中文F1赛历已保存到：{OUTPUT_FILE}")
    if os.path.exists(OUTPUT_FILE):
        file_size = os.path.getsize(OUTPUT_FILE) / 1024
        print(f"📊 文件大小：{file_size:.2f} KB")
        print(f"\n📱 下一步：将此文件导入手机日历")
        print(f"   或在GitHub Actions中设置自动更新")

if __name__ == "__main__":
    main()

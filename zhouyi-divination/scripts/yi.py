#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""蓍草起卦模拟器 - 四营十八变"""

import random
import datetime
import json
import os
from typing import List, Tuple, Optional

# ============ 数据定义 ============
# 四种爻值
OLD_YIN = 6      # 老阴（变）
YOUNG_YANG = 7   # 少阳
YOUNG_YIN = 8    # 少阴
OLD_YANG = 9     # 老阳（变）

# 变爻集合
CHANGING = {OLD_YIN, OLD_YANG}

# 爻的符号和名称
SYMBOLS = {
    OLD_YIN: "- -",
    YOUNG_YANG: "───",
    YOUNG_YIN: "- -",
    OLD_YANG: "───",
}

NAMES = {
    OLD_YIN: "老阴",
    YOUNG_YANG: "少阳",
    YOUNG_YIN: "少阴",
    OLD_YANG: "老阳",
}

# 六爻的位置名
POSITIONS = ["初爻", "二爻", "三爻", "四爻", "五爻", "上爻"]

# ANSI颜色
RED = "\033[91m"
RESET = "\033[0m"

# 世爻应爻查找表
WORLD_YAO_TABLE = {
    0: (6, "正卦"),      # 000：上下卦相同
    1: (1, "正卦"),      # 001
    3: (2, "正卦"),      # 011
    7: (3, "正卦"),      # 111
    6: (4, "正卦"),      # 110
    4: (5, "正卦"),      # 100
    5: (4, "游魂卦"),    # 101：特殊
    2: (3, "归魂卦"),    # 010：特殊
}

# 爻值转静态（消除动爻）
STATIC_YAO = {
    OLD_YIN: YOUNG_YIN,      # 6 → 8
    YOUNG_YIN: YOUNG_YIN,    # 8 → 8
    OLD_YANG: YOUNG_YANG,    # 9 → 7
    YOUNG_YANG: YOUNG_YANG,  # 7 → 7
}

# 地支到五行的映射
DIZHI_TO_WUXING = {
    "亥": "水", "子": "水",
    "寅": "木", "卯": "木",
    "巳": "火", "午": "火",
    "申": "金", "酉": "金",
    "辰": "土", "戌": "土", 
    "丑": "土", "未": "土",
}


# ============ 核心算法 ============
def mod4_or_4(n: int) -> int:
    """
    模4运算，但0视为4
    这是蓍草算法的规则：余数为0时取4
    """
    r = n % 4
    return r if r else 4


def split_sticks(sticks: int) -> Tuple[int, int]:
    """
    正态分布模拟随机分堆，每次随机标准差
    
    物理模型：
    - 每次分堆的"随意程度"不同（二阶随机性）
    - 标准差范围：[sticks/10, sticks/4]
      * sticks/10：较专注时，分布集中
      * sticks/4：较随意时，分布分散
    """
    mean = sticks / 2
    std = random.uniform(sticks / 10, sticks / 4)
    
    left = int(random.gauss(mean, std))
    left = max(1, min(sticks - 1, left))
    
    return left, sticks - left


def one_round(sticks: int) -> int:
    """
    执行一轮变化（四营）：
    1. 分二
    2. 挂一
    3. 揲四（左）
    4. 揲四（右）
    5. 归奇
    """
    left, right = split_sticks(sticks)
    right -= 1  # 挂一
    removed = 1 + mod4_or_4(left) + mod4_or_4(right)
    return sticks - removed


def cast_yao() -> int:
    """三变成一爻"""
    sticks = 49
    sticks = one_round(sticks)  # 第一变
    sticks = one_round(sticks)  # 第二变
    sticks = one_round(sticks)  # 第三变
    return sticks // 4


def cast_hexagram() -> List[int]:
    """六爻成卦（从下到上）"""
    return [cast_yao() for _ in range(6)]


# ============ 变换逻辑 ============
def transform_yao(yao: int) -> int:
    """
    变爻转换：老阴变少阳，老阳变少阴
    不变爻保持不变
    """
    if yao == OLD_YIN:
        return YOUNG_YANG
    if yao == OLD_YANG:
        return YOUNG_YIN
    return yao


def transform_hexagram(hexagram: List[int]) -> List[int]:
    """计算之卦"""
    return [transform_yao(y) for y in hexagram]


# ============ 世爻应爻模块 ============
def yao_to_binary(yao: int) -> str:
    """爻值转二进制位：阴0 阳1"""
    return "1" if yao in (YOUNG_YANG, OLD_YANG) else "0"


def calculate_world_response(hexagram: List[int]) -> Tuple[int, int, str]:
    """
    计算世爻和应爻位置
    
    算法：
    1. 逐位比较上下卦（初vs四, 二vs五, 三vs上）
    2. 相同为0，不同为1
    3. 从上到下组合成二进制数（三爻结果在高位）
    4. 查表得世爻位置
    
    返回：(世爻位置, 应爻位置, 卦类型)
    位置编号：1=初爻, 2=二爻, ..., 6=上爻
    """
    lower = hexagram[0:3]  # 下卦：初二三
    upper = hexagram[3:6]  # 上卦：四五上
    
    # 逐位XOR比较（从下到上：初vs四, 二vs五, 三vs上）
    xor_bits = []
    for i in range(3):
        lower_bit = yao_to_binary(lower[i])
        upper_bit = yao_to_binary(upper[i])
        xor_bit = "1" if lower_bit != upper_bit else "0"
        xor_bits.append(xor_bit)
    
    # 组合成二进制数（从上到下排列：三爻在高位）
    # xor_bits = [初vs四, 二vs五, 三vs上]
    # 需要反转成 [三vs上, 二vs五, 初vs四]
    xor_value = int("".join(reversed(xor_bits)), 2)
    
    # 查表
    world_pos, gua_type = WORLD_YAO_TABLE[xor_value]
    response_pos = (world_pos + 2) % 6 + 1  # 相隔3位
    
    return world_pos, response_pos, gua_type


def print_world_response(hexagram: List[int]) -> None:
    """打印世爻应爻信息"""
    world, response, gua_type = calculate_world_response(hexagram)
    
    print(f"\n")
    print("世爻与应爻")
    print(f"{'='*50}")
    print(f"卦类型：{gua_type}")
    print(f"世爻：{POSITIONS[world - 1]}")
    print(f"应爻：{POSITIONS[response - 1]}")
    print(f"{'='*50}")


# ============ 互卦模块 ============
def calculate_mutual_hexagram(hexagram: List[int]) -> List[int]:
    """
    计算互卦（静态，无动爻）
    下卦：二三四爻 | 上卦：三四五爻
    
    互卦必须是静态结构，所有爻转为少阴/少阳
    """
    mutual = [
        hexagram[1],  # 二爻
        hexagram[2],  # 三爻
        hexagram[3],  # 四爻
        hexagram[2],  # 三爻（重复）
        hexagram[3],  # 四爻（重复）
        hexagram[4],  # 五爻
    ]
    
    # 转为静态爻（老→少）
    return [STATIC_YAO[yao] for yao in mutual]


# ============ 地支五行模块（新增）============
def hexagram_to_key(hexagram: List[int]) -> str:
    """
    将六爻转换为二进制字符串键
    从初爻到上爻：阴0阳1
    
    示例：天地否（阴阴阴阳阳阳）→ "000111"
    """
    return "".join(yao_to_binary(yao) for yao in hexagram)


def load_hexagram_data(key: str) -> Optional[dict]:
    """
    从JSON文件加载卦象数据
    返回：{"name": "...", "dizhi": [...], "yaoci": [...]} 或 None
    """
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(script_dir, "..", "assets", "hexagram_dizhi_yaoci.json")
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get(key)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"错误：无法读取卦象数据 - {e}")
        return None


def get_wuxing(dizhi: str) -> str:
    """地支转五行"""
    return DIZHI_TO_WUXING.get(dizhi, "未知")


def print_dizhi_wuxing(hexagram: List[int], title: str = "本卦") -> None:
    """
    打印地支和五行信息
    包含：卦名、各爻地支、世应地支及五行
    """
    key = hexagram_to_key(hexagram)
    data = load_hexagram_data(key)

    if not data:
        return

    world_pos, response_pos, _ = calculate_world_response(hexagram)

    print(f"\n")
    print(f"{title}：地支与五行")
    print(f"{'='*50}")
    print(f"卦名：{data['name']}")
    print(f"查询键：{key}")
    print()

    # 各爻地支
    dizhi_list = data['dizhi']
    print("各爻地支：")
    for i, dizhi in enumerate(dizhi_list):
        wuxing = get_wuxing(dizhi)
        print(f"  {POSITIONS[i]}: {dizhi}（{wuxing}）")

    print()

    # 世应地支
    world_dizhi = dizhi_list[world_pos - 1]
    world_wuxing = get_wuxing(world_dizhi)
    response_dizhi = dizhi_list[response_pos - 1]
    response_wuxing = get_wuxing(response_dizhi)

    print(f"世爻（{POSITIONS[world_pos - 1]}）：{world_dizhi} {world_wuxing}")
    print(f"应爻（{POSITIONS[response_pos - 1]}）：{response_dizhi} {response_wuxing}")
    print(f"{'='*50}")


def print_yaoci(hexagram: List[int], title: str = "本卦") -> None:
    """打印爻辞"""
    key = hexagram_to_key(hexagram)
    data = load_hexagram_data(key)

    if not data:
        return

    print(f"\n")
    print(f"{title}：爻辞")
    print(f"{'='*50}")

    for line in data['yaoci']:
        print(line)

    print(f"{'='*50}")


def print_hexagram_name(hexagram: List[int], title: str) -> None:
    """只打印卦名"""
    key = hexagram_to_key(hexagram)
    data = load_hexagram_data(key)
    if data:
        print(f"{title}：{data['name']}")


# ============ 农历时间模块 ============
def get_divination_time() -> str:
    """
    获取占卜时间的完整环境信息
    包含：农历日期+时辰+日月建+节气深浅
    """
    try:
        from lunar_python import Solar
        
        now = datetime.datetime.now()
        solar = Solar.fromYmdHms(now.year, now.month, now.day, now.hour, now.minute, now.second)
        lunar = solar.getLunar()
        
        # 1. 日月建与时辰
        month_ganzhi = lunar.getMonthInGanZhiExact() 
        day_ganzhi = lunar.getDayInGanZhiExact()
        time_ganzhi = lunar.getTimeInGanZhi()
        
        # 2. 节气深浅
        prev_jie_qi = lunar.getPrevJieQi(True)  # True包含中气
        jie_qi_name = prev_jie_qi.getName()
        jie_qi_solar = prev_jie_qi.getSolar()
        
        # 计算距节气天数
        jq_date = datetime.date(jie_qi_solar.getYear(), 
                                jie_qi_solar.getMonth(), 
                                jie_qi_solar.getDay())
        today_date = datetime.date(now.year, now.month, now.day)
        delta_days = (today_date - jq_date).days
        
        # 3. 组合输出
        lines = [
            f"占卜时间：农历 {lunar.getMonthInChinese()}月{lunar.getDayInChinese()} {time_ganzhi}时",
            f"日建月建：{month_ganzhi}月 {day_ganzhi}日",
            f"节气深浅：目前处于「{jie_qi_name}」之后第 {delta_days} 天",
        ]
        
        return "\n".join(lines)
        
    except ImportError:
        return "【农历信息不可用】请安装：pip install lunar-python"
    except Exception as e:
        return f"【农历信息获取失败】错误：{str(e)}"


# ============ 显示逻辑 ============
def colorize(text: str) -> str:
    """给文本上色（红色）"""
    return f"{RED}{text}{RESET}"


def format_yao(yao: int, position: str) -> str:
    """
    格式化单个爻的显示
    变爻用红色标记
    """
    symbol = SYMBOLS[yao]
    name = NAMES[yao]
    
    if yao in CHANGING:
        symbol = colorize(symbol)
        num = colorize(f"[{yao}]")
        name = colorize(name)
    else:
        num = f"[{yao}]"
    
    return f"{position}:  {symbol}   {num}  {name}"


def print_hexagram(hexagram: List[int], title: str = "本卦") -> None:
    """
    打印卦象（从上到下显示）
    注：hexagram数组是从下到上存储的
    """
    print(f"\n{title}：")
    print("=" * 50)
    
    # 倒序遍历：index 5->0 对应 上爻->初爻
    for i in range(5, -1, -1):
        print(format_yao(hexagram[i], POSITIONS[i]))
    
    print("=" * 50)


# ============ 主程序 ============
def main():
    """主函数"""
    print("蓍草起卦模拟器")
    print("使用正态分布+随机标准差模拟真实随机分堆\n")
    
    hexagram = cast_hexagram()
    print(f"原始数据: {hexagram}")
    
    # 1. 本卦
    print_hexagram(hexagram, "本卦")
    print_dizhi_wuxing(hexagram, "本卦")
    print_yaoci(hexagram, "本卦")

    # 2. 之卦（有变爻时）
    if any(y in CHANGING for y in hexagram):
        transformed = transform_hexagram(hexagram)
        print_hexagram(transformed, "之卦")
        print_hexagram_name(transformed, "之卦")

    # 3. 互卦
    mutual = calculate_mutual_hexagram(hexagram)
    print_hexagram(mutual, "互卦")
    print_hexagram_name(mutual, "互卦")

    # 4. 世爻应爻
    print_world_response(hexagram)

    # 5. 起卦时间
    print(f"\n{'='*50}")
    print(get_divination_time())
    print(f"{'='*50}\n")


if __name__ == "__main__":
    main()
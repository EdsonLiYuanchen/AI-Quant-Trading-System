"""
同花顺账户数据导入模块
把同花顺导出的「持仓明细」「交割单」表格解析成程序能用的数据。
支持文件导入（CSV / TXT / Excel）和直接粘贴表格文本。
同花顺没有对散户开放自动同步接口，用导出+导入是最稳妥的办法。
"""

import os
import re
import pandas as pd


# 列名关键词：用来自动识别表格里哪一列是什么含义
_KEY_COLUMNS = {
    "code":   ["证券代码", "股票代码", "基金代码", "代码", "证券编码", "股票编号"],
    "name":   ["证券名称", "股票名称", "基金名称", "名称", "简称", "证券简称"],
    "volume": ["股票余额", "持仓数量", "持有数量", "可用数量", "成交数量", "数量", "股份余额", "持仓股数", "余量"],
    "price":  ["成交价格", "成交均价", "价格", "现价", "成交价"],
    "avg":    ["成本价", "买入均价", "持仓成本", "参考成本价", "平均成本", "成本均价", "成本"],
    "amount": ["发生金额", "成交金额", "金额", "市值", "参考市值", "股票市值", "参考成本金额"],
    "date":   ["成交日期", "发生日期", "日期", "交易日期", "时间"],
    "action": ["买卖标志", "操作", "买卖", "方向", "业务名称", "交易类别", "摘要"],
    "cash":   ["可用资金", "资金余额", "可用金额", "剩余资金"],
    "asset":  ["总资产", "资产总值", "总市值"],
}

_ACTION_BUY = ["买入", "证券买入", "买", "申购"]
_ACTION_SELL = ["卖出", "证券卖出", "卖", "赎回", "派息"]


def _strip(x):
    """清理单元格文本"""
    if x is None:
        return ""
    s = str(x)
    s = s.replace("\ufeff", "").replace("\u3000", "").strip()
    return s


def _to_float(x, default=None):
    """把单元格转成数字，兼容带逗号/百分号的写法"""
    s = _strip(x).replace(",", "").replace("，", "")
    if s in ("", "-", "--", "None"):
        return default
    try:
        return float(s)
    except ValueError:
        # 尝试提取数字部分，如 "10.50元"
        m = re.search(r"[-+]?\d+(?:\.\d+)?", s)
        if m:
            return float(m.group(0))
        return default


def _to_code(x):
    """提取6位股票/基金代码"""
    s = _strip(x)
    m = re.search(r"\d{6}", s)
    if m:
        return m.group(0)
    if re.fullmatch(r"\d{5}", s):
        return s
    return s


def _find_col(headers, kinds):
    """在表头里找某一类列，返回列下标，找不到返回 -1"""
    for i, h in enumerate(headers):
        hs = _strip(h)
        if not hs:
            continue
        for kind in kinds:
            for kw in _KEY_COLUMNS[kind]:
                if kw.lower() in hs.lower():
                    return i
    return -1


def load_table(path):
    """
    读取表格文件，返回二维列表（每行是一行单元格）。
    自动识别编码（UTF-8 / GBK / UTF-8-SIG）和分隔符，也支持 Excel。
    """
    ext = os.path.splitext(path)[1].lower()

    # Excel 文件
    if ext in (".xlsx", ".xls", ".xlsm"):
        try:
            df = pd.read_excel(path, header=None)
            return df.where(pd.notnull(df), "").values.tolist()
        except Exception as e:
            raise ValueError(f"读取 Excel 失败（可能是旧版 .xls，请先另存为 CSV）：{e}")

    # CSV / TXT：自动探测编码
    encodings = ["utf-8-sig", "utf-8", "gbk", "gb18030", "big5"]
    raw = None
    for enc in encodings:
        try:
            with open(path, "r", encoding=enc, errors="strict") as f:
                raw = f.read()
            break
        except (UnicodeDecodeError, UnicodeError):
            continue
    if raw is None:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            raw = f.read()

    lines = raw.splitlines()
    if not lines:
        raise ValueError("文件是空的")

    # 自动识别分隔符（优先制表符，其次逗号）
    sample = "".join(lines[:50])
    delim = "\t" if sample.count("\t") >= max(2, sample.count(",")) else ","
    if "," not in sample and "\t" not in sample:
        delim = " "  # 空格分隔

    rows = []
    for line in lines:
        if _strip(line) == "":
            continue
        if delim == " ":
            cells = line.split()
        else:
            cells = line.split(delim)
        rows.append([_strip(c) for c in cells])
    return rows


def parse_holdings(rows):
    """
    从表格行解析「持仓明细」。
    返回 { 'positions': [{code,name,volume,avg_price}], 'cash': 或 None }
    volume 单位是「股」。
    """
    if not rows:
        raise ValueError("没有可解析的数据")

    # 找到表头行：必须同时含"代码"和"数量"和"成本"类列
    header_idx = None
    for i, row in enumerate(rows[:20]):
        joined = " ".join(_strip(c) for c in row)
        has_code = _find_col(row, ["code"]) >= 0
        has_vol = _find_col(row, ["volume"]) >= 0
        has_avg = _find_col(row, ["avg", "price"]) >= 0
        if has_code and has_vol and has_avg:
            header_idx = i
            break

    if header_idx is None:
        raise ValueError("没认出表头。请确认表格里有「证券代码 / 数量 / 成本价」这几列（同花顺导出的持仓明细里有）")

    headers = rows[header_idx]
    col = {k: _find_col(headers, [k]) for k in ["code", "name", "volume", "avg", "cash"]}

    positions = []
    cash = None
    seen = set()

    for row in rows[header_idx + 1:]:
        cells = list(row)
        if len(cells) < max([c for c in col.values() if c >= 0], default=0) + 1:
            continue

        code = _to_code(cells[col["code"]]) if col["code"] >= 0 else ""
        if not re.fullmatch(r"\d{5,6}", code):
            continue  # 跳过非持仓行（如合计行、标题行）
        if code in seen:
            continue
        seen.add(code)

        name = _strip(cells[col["name"]]) if col["name"] >= 0 else code
        volume = _to_float(cells[col["volume"]], 0) if col["volume"] >= 0 else 0
        avg = _to_float(cells[col["avg"]], 0) if col["avg"] >= 0 else 0

        if volume <= 0:
            continue

        positions.append({
            "code": code,
            "name": name or code,
            "volume": float(volume),
            "avg_price": float(avg),
        })

        # 顺带抓可用资金（若同表有该列）
        if col["cash"] >= 0 and cash is None:
            c = _to_float(cells[col["cash"]], None)
            if c is not None:
                cash = c

    if not positions:
        raise ValueError("没解析出任何持仓。可能是导出的格式不对，请试试导出为 CSV 或直接粘贴表格")

    return {"positions": positions, "cash": cash}


def parse_transactions(rows):
    """
    从表格行解析「交割单」。
    返回 [ {date, code, name, action(buy/sell), price, volume, amount} ]
    volume 单位是「股」。
    """
    if not rows:
        raise ValueError("没有可解析的数据")

    header_idx = None
    for i, row in enumerate(rows[:30]):
        has_code = _find_col(row, ["code"]) >= 0
        has_vol = _find_col(row, ["volume"]) >= 0
        has_date = _find_col(row, ["date"]) >= 0
        has_act = _find_col(row, ["action"]) >= 0
        if has_code and has_vol and has_date and has_act:
            header_idx = i
            break

    if header_idx is None:
        raise ValueError("没认出交割单表头。请确认有「成交日期 / 证券代码 / 成交数量 / 买卖标志」列")

    headers = rows[header_idx]
    col = {k: _find_col(headers, [k]) for k in ["code", "name", "volume", "price", "amount", "date", "action"]}

    records = []
    for row in rows[header_idx + 1:]:
        cells = list(row)
        if len(cells) < max([c for c in col.values() if c >= 0], default=0) + 1:
            continue

        code = _to_code(cells[col["code"]]) if col["code"] >= 0 else ""
        if not re.fullmatch(r"\d{5,6}", code):
            continue

        act_text = _strip(cells[col["action"]]) if col["action"] >= 0 else ""
        if any(k in act_text for k in _ACTION_SELL):
            action = "sell"
        elif any(k in act_text for k in _ACTION_BUY):
            action = "buy"
        else:
            continue  # 不是买卖记录（如新股申购、分红等）跳过

        volume = _to_float(cells[col["volume"]], 0) if col["volume"] >= 0 else 0
        if volume <= 0:
            continue

        price = _to_float(cells[col["price"]], 0) if col["price"] >= 0 else 0
        amount = _to_float(cells[col["amount"]], None) if col["amount"] >= 0 else None
        if amount is None:
            amount = price * volume

        records.append({
            "date": _strip(cells[col["date"]]) if col["date"] >= 0 else "",
            "code": code,
            "name": _strip(cells[col["name"]]) if col["name"] >= 0 else code,
            "action": action,
            "price": float(price),
            "volume": float(volume),
            "amount": float(amount),
        })

    if not records:
        raise ValueError("没解析出任何买卖记录")

    # 按日期排序（交割单一般是倒序）
    records.sort(key=lambda r: r["date"])
    return records


def parse_pasted(text):
    """解析粘贴的表格文本（支持 tab / 逗号 / 空格分隔），先按持仓明细尝试，再按交割单尝试"""
    lines = [l for l in text.splitlines() if _strip(l)]
    rows = []
    for line in lines:
        if "\t" in line:
            rows.append([_strip(c) for c in line.split("\t")])
        elif "," in line:
            rows.append([_strip(c) for c in line.split(",")])
        else:
            rows.append(line.split())
    if not rows:
        raise ValueError("粘贴内容为空")

    # 有"买卖标志/操作"列 → 当交割单；否则当持仓明细
    joined = " ".join(_strip(c) for c in rows[0])
    if any(kw in joined for kw in _KEY_COLUMNS["action"]):
        return {"type": "transactions", "data": parse_transactions(rows)}
    return {"type": "holdings", "data": parse_holdings(rows)}

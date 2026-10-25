#!/usr/bin/env python3
"""知识关系图：把数据文件生成单个 HTML。

用法：
    python build.py <数据文件.toml 或 .json> [-o <输出.html>] [--text <原文> ...]

数据文件的写法见 references/format.md。本脚本只核对内容、换算公式、排位置；
重叠、穿线、文字溢出这些版面问题由 check.py 在浏览器里查。
--text 给原文的 PDF 或文字文件（可以给多个），给了就核对每条 quote 能不能在原文里找到。
内容警告对应 references/writing.md 里只靠自觉、容易被忽略的规矩。
退出码：0 没有错误；1 有错误。警告不影响退出码。
"""

from __future__ import annotations

import argparse
import html
import json
import math
import re
import sys
import unicodedata
from itertools import pairwise
from pathlib import Path

import tomllib

SKILL_DIR = Path(__file__).resolve().parent.parent
TEMPLATE = SKILL_DIR / "assets" / "template.html"

# 版面常量，单位是整张图坐标系里的 px
COL_W = 230  # 区内一列的宽度；左右相邻的两个节点各自最宽 COL_W - 20
ROW_H = 110  # 区内一行的高度
PAD_X = 10  # 区的左右内边距
HEAD = 52  # 区标题占的高度
PAD_B = 12  # 区的底部内边距
GAP = 20  # 区与区之间的空隙
MARGIN = 20  # 整张图的外边距
NODE_H = 50
NODE_MIN_W = 90

KINDS = ("good", "bad", "part", "link", "evid")
EVIDENCE = ("实测", "模拟", "设想")
N_ZONE_COLORS = 8
SENT = "\ue000"  # 暂存字面美元符号 \$

# 内容警告的界限，依据见 references/writing.md 和 layout.md
MAX_BENDS = 6  # 加 bend 的关系超过这么多条，说明分区或节点排得不好
MAX_BEND = 120  # 单条 bend 超过它，线会绕大圈
MAX_SRC_NAME = 80  # 来源名称会出现在页头和每条出处里
MAX_QUOTE_WORDS = 15

errors: list[str] = []
warnings: list[str] = []
quotes: list[tuple[str, str]] = []  # (位置, quote)，生成时给了 --text 就逐条核对


def err(msg: str) -> None:
    errors.append(msg)


def warn(msg: str) -> None:
    warnings.append(msg)


# ---------- 字宽估计 ----------
# 页面字体（Segoe UI 配 Microsoft YaHei）下实测的字宽，单位 em，2026-10-23 在 Chrome 里量的。
# 依次是 ASCII 32（空格）到 126（~）。粗体对应节点标题和连线文字的字重 650。
_ASCII_N = [0.27, 0.28, 0.39, 0.59, 0.54, 0.82, 0.8, 0.23, 0.3, 0.3, 0.42, 0.68, 0.22, 0.4, 0.22, 0.39, 0.54, 0.54, 0.54, 0.54,
            0.54, 0.54, 0.54, 0.54, 0.54, 0.54, 0.22, 0.22, 0.68, 0.68, 0.68, 0.45, 0.96, 0.65, 0.57, 0.62, 0.7, 0.51, 0.49, 0.69,
            0.71, 0.27, 0.36, 0.58, 0.47, 0.9, 0.75, 0.75, 0.56, 0.75, 0.6, 0.53, 0.52, 0.69, 0.62, 0.93, 0.59, 0.55, 0.57, 0.3,
            0.38, 0.3, 0.68, 0.42, 0.27, 0.51, 0.59, 0.46, 0.59, 0.52, 0.31, 0.59, 0.57, 0.24, 0.24, 0.5, 0.24, 0.86, 0.57, 0.59,
            0.59, 0.59, 0.35, 0.42, 0.34, 0.57, 0.48, 0.72, 0.46, 0.48, 0.45, 0.3, 0.24, 0.3, 0.68]
_ASCII_B = [0.28, 0.33, 0.49, 0.59, 0.58, 0.87, 0.85, 0.29, 0.37, 0.37, 0.46, 0.71, 0.27, 0.4, 0.27, 0.44, 0.58, 0.58, 0.58, 0.58,
            0.58, 0.58, 0.58, 0.58, 0.58, 0.58, 0.27, 0.27, 0.71, 0.71, 0.71, 0.44, 0.95, 0.7, 0.64, 0.62, 0.74, 0.53, 0.52, 0.71,
            0.77, 0.32, 0.45, 0.65, 0.51, 0.96, 0.79, 0.76, 0.61, 0.76, 0.65, 0.56, 0.59, 0.72, 0.67, 1.0, 0.66, 0.61, 0.61, 0.37,
            0.44, 0.37, 0.71, 0.42, 0.31, 0.54, 0.62, 0.48, 0.62, 0.54, 0.38, 0.62, 0.6, 0.28, 0.28, 0.56, 0.28, 0.92, 0.6, 0.61,
            0.62, 0.62, 0.4, 0.44, 0.39, 0.6, 0.54, 0.8, 0.55, 0.54, 0.48, 0.37, 0.33, 0.37, 0.71]
_EXTRA_N = {"·": 0.22, "→": 0.86, "←": 0.86, "↔": 0.86, "≈": 0.69, "×": 0.68, "÷": 0.68, "–": 0.5, "—": 1.0, "…": 0.73,
            "✘": 0.82, "✔": 0.8, "α": 0.61, "β": 0.55, "γ": 0.52, "δ": 0.58, "ε": 0.44, "η": 0.58, "θ": 0.59, "λ": 0.5,
            "μ": 0.58, "π": 0.63, "σ": 0.57, "τ": 0.49, "φ": 0.7, "ω": 0.81, "°": 0.38, "±": 0.68, "≤": 0.69, "≥": 0.69,
            "√": 0.65, "∑": 0.62, "∏": 0.75, "∞": 0.82}
_EXTRA_B = {"·": 0.27, "→": 0.86, "←": 0.86, "↔": 0.86, "≈": 0.71, "×": 0.71, "÷": 0.71, "–": 0.5, "—": 1.0, "…": 0.91,
            "✘": 0.82, "✔": 0.8, "α": 0.64, "β": 0.62, "γ": 0.57, "δ": 0.61, "ε": 0.46, "η": 0.61, "θ": 0.61, "λ": 0.55,
            "μ": 0.63, "π": 0.69, "σ": 0.61, "τ": 0.55, "φ": 0.75, "ω": 0.83, "°": 0.38, "±": 0.71, "≤": 0.71, "≥": 0.71,
            "√": 0.65, "∑": 0.64, "∏": 0.79, "∞": 0.81}


def text_width(s: str, size: float, bold: bool = False) -> float:
    """估计一行字的宽度。中文按 1 个字宽，其余查实测表，再多留 4%，给别的电脑上略宽的字体。

    check.py 会在浏览器里量真实字宽；估得不够宽时它报“节点里的字超出框”。
    """
    asc, extra = (_ASCII_B, _EXTRA_B) if bold else (_ASCII_N, _EXTRA_N)
    w = 0.0
    for ch in s:
        o = ord(ch)
        if 32 <= o < 127:
            w += asc[o - 32] * 1.04
        elif ch in extra:
            w += extra[ch] * 1.04
        elif unicodedata.east_asian_width(ch) in ("W", "F"):
            w += 1.0
        else:
            w += 0.85
    return w * size


# ---------- 文字和公式 ----------
_mathml = None


def _converter():
    global _mathml
    if _mathml is None:
        try:
            from latex2mathml.converter import convert
        except ImportError:
            err("文字里有公式，但没有装 latex2mathml。先运行：python -m pip install latex2mathml")
            _mathml = False
        else:
            _mathml = convert
    return _mathml


_CJK = re.compile(r"[\u3000-\u303f\u4e00-\u9fff\uff00-\uffef]")
_TEXT_CMD = re.compile(r"\\(?:text|mathrm|operatorname|textrm|textbf|mbox)\s*\{[^{}]*\}")


def to_mathml(tex: str, display: bool, where: str) -> str:
    bare = _TEXT_CMD.sub("", tex)
    if _CJK.search(bare):
        err(f"{where}：公式里有中文：${tex}$。字面美元符号要写成 \\$；中文要放进 \\text{{}}。")
        return html.escape(tex)
    if re.search(r"[A-Za-z]{4,}\s+[A-Za-z]{3,}", bare):
        warn(f"{where}：这段公式里有像英文句子的内容，确认不是把美元符号当成了公式：${tex}$")
    conv = _converter()
    if not conv:
        return html.escape(tex)
    try:
        m = conv(tex.strip(), display="block" if display else "inline")
    except Exception as e:  # noqa: BLE001  latex2mathml 对写错的公式会抛各种类型的异常，统一转成报错
        err(f"{where}：公式转换失败（{type(e).__name__}: {e}）：{tex}")
        return html.escape(tex)
    if re.search(r"<mi>&amp;</mi>|<mi>&</mi>|linebreak=\"newline\"", m):
        err(f"{where}：多行公式用了不支持的写法（aligned 或 gathered）。改用 align* 或 split：{tex}")
    bad = re.findall(r">(\\[A-Za-z]+)<", m)
    if bad:
        err(f"{where}：公式里有认不出的命令 {', '.join(sorted(set(bad)))}：{tex}")
    return m


# 紧挨着行内公式的标点。浏览器会在公式和标点之间折行，手机上句号会单独掉到下一行，所以和公式包进一个不折行的 span
_OPEN_P = re.compile(r"[（【「『“‘《〈(\[]+$")
_CLOSE_P = re.compile(r"^[。，、；：！？）】」』”’》〉.,;:!?)\]]+")


def render_inline(t: str, where: str) -> str:
    """行内文字：转义 HTML，处理 **粗体**、`代码` 和 $行内公式$。公式和紧挨着的标点不拆到两行。"""
    pieces = re.split(r"\$(.+?)\$", t, flags=re.DOTALL)
    pre, post = [""] * len(pieces), [""] * len(pieces)
    for i in range(1, len(pieces), 2):  # 奇数位是公式，两边一定各有一个文字片段（可能是空串）
        m = _CLOSE_P.match(pieces[i + 1])
        if m:
            post[i], pieces[i + 1] = m.group(0), pieces[i + 1][m.end():]
        m = _OPEN_P.search(pieces[i - 1])
        if m:
            pre[i], pieces[i - 1] = m.group(0), pieces[i - 1][: m.start()]
    out = []
    for i, p in enumerate(pieces):
        if i % 2:
            mm = to_mathml(p.replace(SENT, r"\$"), False, where)
            if pre[i] or post[i]:
                mm = '<span class="nb">' + html.escape(pre[i]) + mm + html.escape(post[i]) + "</span>"
            out.append(mm)
            continue
        if "$" in p:
            err(f"{where}：有落单的 $。字面美元符号写成 \\$：…{p.strip()[:40]}…")
        e = html.escape(p.replace(SENT, "$"), quote=False)
        e = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", e)
        e = re.sub(r"`(.+?)`", r"<code>\1</code>", e)
        out.append(e)
    return "".join(out)


def _join(lines: list[str]) -> str:
    """把一段里的几行接起来：两边都是英文或数字时加空格，否则直接接。"""
    s = lines[0]
    for line in lines[1:]:
        if s and line and s[-1].isascii() and s[-1].isalnum() and line[0].isascii() and line[0].isalnum():
            s += " " + line
        else:
            s += line
    return s


def render_blocks(t: str, where: str) -> str:
    """段落和列表。空行分段；以 - 或 1. 开头的行是列表项，缩进的续行接在上一项后面。"""
    out = []
    for block in re.split(r"\n\s*\n", t.strip("\n")):
        lines = [ln.rstrip() for ln in block.split("\n") if ln.strip()]
        if not lines:
            continue
        ul = re.match(r"\s*[-*] ", lines[0])
        ol = re.match(r"\s*\d+[.)] ", lines[0])
        if ul or ol:
            pat = r"\s*[-*] " if ul else r"\s*\d+[.)] "
            items: list[list[str]] = []
            for ln in lines:
                if re.match(pat, ln):
                    items.append([re.sub("^" + pat, "", ln)])
                else:
                    items[-1].append(ln.strip())
            tag = "ul" if ul else "ol"
            out.append(f"<{tag}>" + "".join(f"<li>{render_inline(_join(it), where)}</li>" for it in items) + f"</{tag}>")
        else:
            out.append("<p>" + render_inline(_join([ln.strip() for ln in lines]), where) + "</p>")
    return "".join(out)


def render_md(t: str | None, where: str) -> str:
    """多段文字：$$独立公式$$ 单独成块，其余按段落和列表处理。"""
    if not t:
        return ""
    s = t.replace("\\$", SENT)
    parts = re.split(r"\$\$(.+?)\$\$", s, flags=re.DOTALL)
    out = []
    for i, p in enumerate(parts):
        if i % 2:
            out.append('<div class="mblock">' + to_mathml(p.replace(SENT, r"\$"), True, where) + "</div>")
        else:
            out.append(render_blocks(p, where))
    return "".join(out)


def render_line(t: str | None, where: str) -> str:
    if not t:
        return ""
    if "\n\n" in t.strip():
        warn(f"{where}：这里只该写一句话，多出来的段落会被接成一段。")
    return render_inline(_join([ln.strip() for ln in t.strip().split("\n") if ln.strip()]).replace("\\$", SENT), where)


def plain_len(t: str) -> int:
    t = re.sub(r"\$\$.+?\$\$|\$.+?\$", "公式", t or "", flags=re.DOTALL)
    return len(re.sub(r"\s+", "", t))


# ---------- 读取和核对 ----------
def load(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    try:
        return json.loads(text) if path.suffix.lower() == ".json" else tomllib.loads(text)
    except (tomllib.TOMLDecodeError, json.JSONDecodeError) as e:
        print(f"数据文件格式错误：{e}", file=sys.stderr)
        sys.exit(1)


def need_str(obj: dict, key: str, where: str) -> str:
    v = obj.get(key)
    if not isinstance(v, str) or not v.strip():
        err(f"{where}：缺少 {key}")
        return ""
    return v.strip()


def pair(obj: dict, key: str, where: str) -> tuple[float, float] | None:
    v = obj.get(key)
    if not (isinstance(v, list) and len(v) == 2 and all(isinstance(x, (int, float)) for x in v)):
        err(f"{where}：{key} 要写成两个数，例如 {key} = [0, 1]")
        return None
    return float(v[0]), float(v[1])


def check_src(lst, sources: dict, where: str) -> list[dict]:
    out = []
    if lst is None:
        return out
    if not isinstance(lst, list):
        err(f"{where}：src 要写成列表")
        return out
    for i, s in enumerate(lst, 1):
        if not isinstance(s, dict):
            err(f"{where}：src 第 {i} 项格式不对")
            continue
        sid = s.get("s")
        if sid not in sources:
            err(f"{where}：src 第 {i} 项的来源 {sid!r} 没有在 [[sources]] 里定义")
            continue
        loc = s.get("loc")
        if not isinstance(loc, str) or not loc.strip():
            err(f"{where}：src 第 {i} 项缺少 loc（页码、章节或时间）")
            continue
        src = sources[sid]
        q = (s.get("quote") or "").strip()
        if q:
            quotes.append((where, q))
            if not _CJK.search(q) and len(q.split()) > MAX_QUOTE_WORDS:
                warn(f"{where}：quote 有 {len(q.split())} 个词，超过 {MAX_QUOTE_WORDS} 个。只摘关键短语，不大段照抄。")
        out.append({"s": sid, "name": src["name"], "kind": src.get("kind", ""), "loc": loc.strip(), "quote": q})
    return out


def evidence(obj: dict, where: str) -> str:
    v = obj.get("evidence")
    if v is None:
        return ""
    if v not in EVIDENCE:
        err(f"{where}：evidence 只能是 {'、'.join(EVIDENCE)}")
        return ""
    return v


def build(data: dict) -> dict:
    title = need_str(data, "title", "顶层")
    sources = {}
    for i, s in enumerate(data.get("sources") or [], 1):
        sid, name = s.get("id"), s.get("name")
        if not sid or not name:
            err(f"sources 第 {i} 项要有 id 和 name")
            continue
        sources[sid] = {"id": sid, "name": name, "kind": s.get("kind", "")}
        if len(name) > MAX_SRC_NAME:
            warn(f"来源 {sid} 的 name 有 {len(name)} 个字。它会出现在页头和每条出处里，太长会挤。"
                 "写成“作者 年份，期刊”这样的短名，完整引用和全图通用的说明放进顶层 notes。")
    if not sources:
        err("至少要有一个 [[sources]]，写明这张图依据的材料")

    # 分区
    zones, zone_order = {}, []
    for i, z in enumerate(data.get("zones") or [], 1):
        where = f"分区 {z.get('id', i)}"
        zid = need_str(z, "id", where)
        if zid in zones:
            err(f"{where}：id 重复")
            continue
        grid, size = pair(z, "grid", where), pair(z, "size", where)
        if not zid or not grid or not size:
            continue
        color = z.get("color", len(zones) % N_ZONE_COLORS + 1)
        if not (isinstance(color, int) and 1 <= color <= N_ZONE_COLORS):
            err(f"{where}：color 要是 1 到 {N_ZONE_COLORS} 的整数")
            color = 1
        align = z.get("title_align", "start")
        if align not in ("start", "end"):
            err(f"{where}：title_align 只能是 start 或 end")
            align = "start"
        zones[zid] = {"id": zid, "title": need_str(z, "title", where), "sub": (z.get("sub") or "").strip(),
                      "gx": int(grid[0]), "gy": int(grid[1]), "cols": size[0], "rows": size[1], "color": color, "align": align}
        zone_order.append(zid)
    if not zones:
        err("至少要有一个 [[zones]]")
    cells = {}
    for z in zones.values():
        key = (z["gx"], z["gy"])
        if key in cells:
            err(f"分区 {z['id']} 和 {cells[key]} 的 grid 位置相同")
        cells[key] = z["id"]

    # 节点
    nodes, node_order = {}, []
    for i, n in enumerate(data.get("nodes") or [], 1):
        where = f"节点 {n.get('id', i)}"
        nid = need_str(n, "id", where)
        if not nid:
            continue
        if nid in nodes:
            err(f"{where}：id 重复")
            continue
        zid = n.get("zone")
        if zid not in zones:
            err(f"{where}：分区 {zid!r} 不存在")
            continue
        pos = pair(n, "pos", where)
        if not pos:
            continue
        z = zones[zid]
        if not (0 <= pos[0] <= z["cols"] - 1 and 0 <= pos[1] <= z["rows"] - 1):
            err(f"{where}：pos {list(pos)} 超出分区 {zid} 的 size {[z['cols'], z['rows']]}（列从 0 到 cols-1，行从 0 到 rows-1）")
        bg = bool(n.get("background", False))
        src = check_src(n.get("src"), sources, where)
        if not src and not bg:
            err(f"{where}：缺少 src。原文没讲的背景知识要写 background = true")
        t, sub = need_str(n, "title", where), need_str(n, "sub", where)
        node = {"id": nid, "zone": zid, "col": pos[0], "row": pos[1], "title": t, "sub": sub,
                "one": render_line(need_str(n, "one", where), where + " 的 one"),
                "detail": render_md(need_str(n, "detail", where), where + " 的 detail"),
                "more": render_md(n.get("more"), where + " 的 more"),
                "sup": render_md(n.get("sup"), where + " 的 sup"),
                "src": src, "bg": bg, "ev": evidence(n, where)}
        node["w"] = max(NODE_MIN_W, math.ceil(max(text_width(t, 15, True), text_width(sub, 12)) + 30))
        node["h"] = NODE_H
        if node["w"] > COL_W - 20:
            warn(f"{where}：框宽 {node['w']}，超过一列的宽度 {COL_W - 20}。左右相邻放节点会挤，标题或副标题可以再短一点。")
        dl = plain_len(n.get("detail", ""))
        if dl and (dl < 80 or dl > 700):
            warn(f"{where}：detail 有 {dl} 个字，建议 120 到 400 个字；更长的放进 more。")
        if len(n.get("one", "")) > 70:
            warn(f"{where}：one 超过 70 个字，一句话说不完时把细节挪进 detail。")
        nodes[nid] = node
        node_order.append(nid)

    # 连线
    edges, edge_order = {}, []
    for i, e in enumerate(data.get("edges") or [], 1):
        eid = str(e.get("id", ""))
        where = f"关系 {eid or i}"
        if not eid:
            err(f"关系第 {i} 条缺少 id")
            continue
        if eid in edges:
            err(f"{where}：id 重复")
            continue
        a, b = e.get("from"), e.get("to")
        if a not in nodes or b not in nodes:
            err(f"{where}：from 或 to 指向不存在的节点（{a!r} → {b!r}）")
            continue
        if a == b:
            err(f"{where}：from 和 to 是同一个节点")
            continue
        kind = e.get("kind")
        if kind not in KINDS:
            err(f"{where}：kind 只能是 {', '.join(KINDS)}")
            continue
        inf = bool(e.get("inferred", False))
        src = check_src(e.get("src"), sources, where)
        if not src and not inf:
            err(f"{where}：缺少 src。原文没有直接说的关系要写 inferred = true")
        label = need_str(e, "label", where)
        lp = e.get("lp", 0.5)
        if not (isinstance(lp, (int, float)) and 0.1 <= lp <= 0.9):
            err(f"{where}：lp 要在 0.1 到 0.9 之间")
            lp = 0.5
        bend = e.get("bend", 0)
        if not isinstance(bend, (int, float)):
            err(f"{where}：bend 要是数字")
            bend = 0
        if text_width(label, 12, True) > 150:
            warn(f"{where}：标签“{label}”偏长，图上容易压到别的东西。")
        edges[eid] = {"id": eid, "from": a, "to": b, "label": label, "kind": kind,
                      "text": render_line(need_str(e, "text", where), where + " 的 text"),
                      "src": src, "inf": inf, "ev": evidence(e, where), "lp": float(lp), "bend": float(bend)}
        edge_order.append(eid)
    pairs: dict[frozenset, str] = {}
    for e in edges.values():
        k = frozenset((e["from"], e["to"]))
        if k in pairs:
            warn(f"关系 {e['id']} 和 {pairs[k]} 连着同一对节点，两条线会叠在一起，给其中一条加 bend。")
        pairs[k] = e["id"]
    linked = {e["from"] for e in edges.values()} | {e["to"] for e in edges.values()}
    for nid in node_order:
        if nid not in linked:
            warn(f"节点 {nid} 没有任何连线。")

    # 关系链
    chains = []
    for i, c in enumerate(data.get("chains") or [], 1):
        where = f"关系链 {i}"
        ids = [str(x) for x in c.get("edges") or []]
        if not ids:
            err(f"{where}：edges 是空的")
            continue
        miss = [x for x in ids if x not in edges]
        if miss:
            err(f"{where}：引用了不存在的关系 {', '.join(miss)}")
            continue
        for x, y in pairwise(ids):
            if not ({edges[x]["from"], edges[x]["to"]} & {edges[y]["from"], edges[y]["to"]}):
                warn(f"{where}：关系 {x} 和 {y} 不相连，读的人会跳一下。确认这样排是有意的。")
        chains.append({"title": need_str(c, "title", where), "intro": render_line(c.get("intro"), where + " 的 intro"), "edges": ids})

    content_warnings(data.get("mode", ""), zones, nodes, edges, chains)

    # ---------- 排位置 ----------
    gx_n = max((z["gx"] for z in zones.values()), default=0) + 1
    gy_n = max((z["gy"] for z in zones.values()), default=0) + 1
    nat_w = {zid: z["cols"] * COL_W + 2 * PAD_X for zid, z in zones.items()}
    nat_h = {zid: HEAD + z["rows"] * ROW_H + PAD_B for zid, z in zones.items()}
    col_w = [max([nat_w[z["id"]] for z in zones.values() if z["gx"] == gx] or [0]) for gx in range(gx_n)]
    row_h = [max([nat_h[z["id"]] for z in zones.values() if z["gy"] == gy] or [0]) for gy in range(gy_n)]
    for z in zones.values():
        z["x"] = MARGIN + sum(col_w[: z["gx"]]) + GAP * z["gx"]
        z["y"] = MARGIN + sum(row_h[: z["gy"]]) + GAP * z["gy"]
        z["w"], z["h"] = col_w[z["gx"]], row_h[z["gy"]]
        z["ox"] = z["x"] + (z["w"] - nat_w[z["id"]]) / 2 + PAD_X  # 区内网格居中
    W = MARGIN * 2 + sum(col_w) + GAP * (gx_n - 1)
    H = MARGIN * 2 + sum(row_h) + GAP * (gy_n - 1)
    for n in nodes.values():
        z = zones[n["zone"]]
        n["x"] = round(z["ox"] + (n["col"] + 0.5) * COL_W, 1)
        n["y"] = round(z["y"] + HEAD + (n["row"] + 0.5) * ROW_H, 1)

    def hit(n, tx, ty):
        dx, dy = tx - n["x"], ty - n["y"]
        hw, hh = n["w"] / 2 + 5, n["h"] / 2 + 5
        s = min(hw / max(abs(dx), 1e-6), hh / max(abs(dy), 1e-6))
        return n["x"] + dx * s, n["y"] + dy * s

    for e in edges.values():
        A, B = nodes[e["from"]], nodes[e["to"]]
        dx, dy = B["x"] - A["x"], B["y"] - A["y"]
        L = math.hypot(dx, dy) or 1.0
        px, py, bd = -dy / L, dx / L, e["bend"]
        c1 = (A["x"] + dx / 3 + px * bd, A["y"] + dy / 3 + py * bd)
        c2 = (A["x"] + 2 * dx / 3 + px * bd, A["y"] + 2 * dy / 3 + py * bd)
        p0, p3 = hit(A, *c1), hit(B, *c2)
        pts = (p0, c1, c2, p3)
        e["d"] = "M{:.1f},{:.1f} C{:.1f},{:.1f} {:.1f},{:.1f} {:.1f},{:.1f}".format(*p0, *c1, *c2, *p3)
        t, u = e["lp"], 1 - e["lp"]
        e["lx"] = round(sum(c * p[0] for c, p in zip((u**3, 3 * u * u * t, 3 * u * t * t, t**3), pts)), 1)
        e["ly"] = round(sum(c * p[1] for c, p in zip((u**3, 3 * u * u * t, 3 * u * t * t, t**3), pts)), 1)

    return {
        "title": title, "intro": render_line(data.get("intro"), "顶层 intro"), "mode": data.get("mode", ""),
        "notes": render_md(data.get("notes"), "顶层 notes"),
        "sources": list(sources.values()), "W": W, "H": H,
        "zones": [{k: zones[z][k] for k in ("id", "title", "sub", "x", "y", "w", "h", "color", "align")} for z in zone_order],
        "nodes": [{k: nodes[n][k] for k in ("id", "zone", "x", "y", "w", "h", "title", "sub", "one", "detail", "more", "sup", "src", "bg", "ev")} for n in node_order],
        "edges": [{k: edges[e][k] for k in ("id", "from", "to", "label", "kind", "text", "src", "inf", "ev", "d", "lx", "ly")} for e in edge_order],
        "chains": chains,
    }


def content_warnings(mode: str, zones: dict, nodes: dict, edges: dict, chains: list) -> None:
    """writing.md 和 layout.md 里只靠自觉的规矩。只警告，生成照常进行。"""
    plain = [n for n in nodes.values() if not n["bg"]]
    with_q = [n for n in plain if any(s["quote"] for s in n["src"])]
    if plain and len(with_q) * 2 < len(plain):
        warn(f"{len(plain)} 个非背景节点里只有 {len(with_q)} 个的出处带 quote。每个知识点尽量摘一句原文的关键短语，读者才能对回原文。")
    if plain and not any(n["sup"] for n in nodes.values()):
        warn("全图没有一处 sup。原文没有、为了讲懂补充的内容（背景、类比、自己算的数）要放进 sup，页面上会标“原文没有写”。"
             "确实没有补充时忽略这条。")
    bent = [e for e in edges.values() if e["bend"]]
    if len(bent) > MAX_BENDS:
        warn(f"有 {len(bent)} 条关系加了 bend，超过 {MAX_BENDS} 条。这说明分区或节点排得不好，回头重排比一处处修快（layout.md）。")
    for e in bent:
        if abs(e["bend"]) > MAX_BEND:
            warn(f"关系 {e['id']} 的 bend 是 {e['bend']:g}，超过 ±{MAX_BEND}，线会绕大圈。挪开挡路的节点，或者重排分区。")
    if mode != "paper":
        return
    if chains and len(zones) >= 3:
        first = chains[0]["edges"]
        passed = {nodes[edges[x][end]]["zone"] for x in first for end in ("from", "to")}
        if len(passed) * 2 <= len(zones):
            warn(f"第一条关系链只经过 {len(passed)} 个分区（共 {len(zones)} 个）。论文的第一条链要讲“论文的故事”："
                 "研究问题、已有方法的不足、本文方法、证据、局限（writing.md 第 6 节）。")
    if not any(n["ev"] for n in nodes.values()) and not any(e["ev"] for e in edges.values()):
        warn("这是论文图，但没有一个节点或关系标 evidence。关键结果标“实测”，计算或仿真的值标“模拟”，"
             "作者提出、还没做出来的标“设想”。")


# ---------- 核对 quote ----------
def _tokens(s: str) -> list[str]:
    """切成便于比对的词：不管大小写、标点、连字符和上标写法；中文一个字算一个词。"""
    s = unicodedata.normalize("NFKC", s).lower()  # 顺带把 ﬁ 这类连字拆开
    s = re.sub(r"\^\{?(\w+)\}?", r"\1", s)  # 10^{4}、10^4 写成 104，和 PDF 抽出来的上标一样
    s = re.sub(r"[-‐‑­]\s*\n\s*", "", s)  # 行末用连字符断开的词接回去
    s = re.sub(r"[-‐‑­_]", "", s)  # label-free 和 labelfree 算同一个词
    s = re.sub(r"(?<=[^\W\d])(?=\d)|(?<=\d)(?=[^\W\d])", " ", s)  # 粘在词上的引用角标拆开：strains22 → strains 22
    s = re.sub(r"([一-鿿])", r" \1 ", s)
    return re.findall(r"[\w%]+", s)


def _match(q: list[str], toks: list[str], index: dict[str, list[int]]) -> float:
    """quote 的词按顺序能在原文里对上的比例。原文里多出来的引用角标可以跳过，个别词不同也算对上。"""
    best = 0.0
    starts = {i - k for k in range(min(2, len(q))) for i in index.get(q[k], ())}  # 第一个词可能改过拼写，第二个词也当起点
    for s in starts:
        i, hit = max(s, 0), 0
        for tok in q:
            for j in range(i, min(i + 4, len(toks))):  # 最多跳过原文里 3 个多出来的词
                if toks[j] == tok:
                    hit, i = hit + 1, j + 1
                    break
            else:
                i += 1  # 对不上，当作原文这里是另一个词
        best = max(best, hit / len(q))
        if best == 1.0:
            break
    return best


def read_text(p: Path) -> str | None:
    if not p.exists():
        err(f"--text 给的文件不存在：{p}")
        return None
    if p.suffix.lower() == ".pdf":
        try:
            import pymupdf
        except ImportError:
            try:
                import fitz as pymupdf  # PyMuPDF 1.24 以前只有这个名字
            except ImportError:
                warn("读 PDF 要用 PyMuPDF，这次没有核对 quote。先运行：python -m pip install pymupdf")
                return None
        with pymupdf.open(p) as doc:
            return "\n".join(page.get_text() for page in doc)
    raw = p.read_bytes()
    for enc in ("utf-8-sig", "gb18030"):  # 字幕和讲稿有时是 GBK 编码
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            pass
    warn(f"{p} 既不是 UTF-8 也不是 GBK 编码，这次没有核对 quote。")
    return None


def check_quotes(paths: list[Path]) -> None:
    toks: list[str] = []
    for p in paths:
        t = read_text(p)
        if t is None:
            return
        toks += _tokens(t) + ["\0"]  # 文件之间隔一个对不上的词，quote 不会跨文件拼起来
    index: dict[str, list[int]] = {}
    for i, t in enumerate(toks):
        index.setdefault(t, []).append(i)
    for where, q in quotes:
        qt = _tokens(q)
        if qt and _match(qt, toks, index) < (1.0 if len(qt) < 5 else 0.8):
            warn(f"{where}：quote 在原文里找不到：“{q}”。quote 要照抄原文，不改写、不翻译。")


def main() -> None:
    ap = argparse.ArgumentParser(description="把知识关系图的数据文件生成 HTML")
    ap.add_argument("data", type=Path, help="数据文件（.toml 或 .json）")
    ap.add_argument("-o", "--out", type=Path, help="输出的 HTML；默认和数据文件同名、同目录")
    ap.add_argument("--text", type=Path, action="append", default=[],
                    help="原文的 PDF 或文字文件，可以给多个；给了就核对每条 quote 能不能在原文里找到")
    args = ap.parse_args()
    out_path = args.out or args.data.with_name(re.sub(r"(\.kmap)?\.(toml|json)$", "", args.data.name) + ".html")

    result = build(load(args.data))
    if args.text:
        check_quotes(args.text)
    payload = json.dumps(result, ensure_ascii=False, separators=(",", ":"))
    payload = payload.replace("</", "<\\/").replace("<!--", "<\\u0021--")
    page = TEMPLATE.read_text(encoding="utf-8")
    page = page.replace("__KMAP_TITLE__", html.escape(result["title"])).replace("__KMAP_DATA__", payload)
    out_path.write_text(page, encoding="utf-8")

    print(f"已生成 {out_path}：{len(result['nodes'])} 个节点，{len(result['edges'])} 条关系，"
          f"{len(result['chains'])} 条关系链，画布 {result['W']}×{result['H']}。")
    for w in warnings:
        print("警告：" + w)
    if quotes and not args.text:
        print("提示：没有给 --text，quote 没有和原文核对。")
    for e in errors:
        print("错误：" + e)
    if errors:
        print(f"共 {len(errors)} 个错误，先改完再跑 check.py。")
        sys.exit(1)
    print("内容核对没有错误。下一步运行 check.py 查版面。")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""知识关系图：在后台 Chrome 里打开生成的 HTML，查版面问题，按需截图。

用法：
    python check.py <关系图.html> [--png <截图目录>]

需要 playwright、Pillow 和本机的 Chrome。退出码：0 没有问题；1 有问题。
检查逻辑在模板的 kmapCheck() 里；浏览器地址后加 #check 也能看到同一份报告。
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

NAMES = {
    "nodeOverlap": "节点重叠",
    "edgeThroughNode": "连线穿过别的节点",
    "labelNode": "连线文字压到节点",
    "labelLabel": "连线文字互相重叠",
    "labelEdge": "连线穿过别的连线文字",
    "zoneTitle": "压到分区标题",
    "textOverflow": "节点里的字超出框",
    "outsideZone": "节点超出分区",
    "mathError": "公式显示出错",
    "mathWrap": "公式和紧挨着的标点被拆到两行，桌面宽度",
}
READY = "window.kmapReady === true"
DATA = "JSON.parse(document.getElementById('kmap-data').textContent)"


def open_page(browser, url: str, **kw):
    page = browser.new_page(**kw)
    errs: list[str] = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    page.goto(url)
    page.wait_for_function(READY, timeout=15000)
    return page, errs


def shots(browser, url: str, out: Path) -> list[str]:
    from PIL import Image

    out.mkdir(parents=True, exist_ok=True)
    made = []
    # 1. 整张图按 1:1 截下来，再切成小块方便逐块看
    probe, _ = open_page(browser, url, viewport={"width": 1200, "height": 800})
    info = probe.evaluate(
        "(() => { const D = " + DATA + "; const t = document.createElement('div');"
        " const len = n => { t.innerHTML = n.detail + n.more + n.sup; return t.textContent.length; };"
        " return {W: D.W, H: D.H, chains: D.chains.length, longest: D.nodes.slice().sort((a, b) => len(b) - len(a))[0].id}; })()"
    )
    W, longest, has_chain = info["W"], info["longest"], info["chains"] > 0
    probe.close()
    full, _ = open_page(browser, url, viewport={"width": int(W) + 60, "height": 900})
    full.add_style_tag(content="#wrap{height:auto!important;overflow:visible!important}")
    full.evaluate("kmapSetScale(1)")
    full.locator("#map").screenshot(path=str(out / "map_full.png"))
    full.close()
    im = Image.open(out / "map_full.png")
    tw, th, ov = 1000, 720, 60
    nx, ny = math.ceil((im.width - ov) / (tw - ov)), math.ceil((im.height - ov) / (th - ov))
    for r in range(ny):
        for c in range(nx):
            x0, y0 = c * (tw - ov), r * (th - ov)
            name = f"map_r{r + 1}c{c + 1}.png"
            im.crop((x0, y0, min(x0 + tw, im.width), min(y0 + th, im.height))).save(out / name)
            made.append(name)
    made.insert(0, "map_full.png")

    # 2. 桌面宽度：内容最长的节点面板（整段内容）和关系链第一步
    page, _ = open_page(browser, url, viewport={"width": 1440, "height": 900})
    page.evaluate(f"kmapFocusNode({json.dumps(longest)})")
    page.wait_for_timeout(400)
    page.screenshot(path=str(out / "desktop_node.png"))
    page.evaluate("document.querySelectorAll('#drawer details').forEach(d => { d.open = true; })")
    page.add_style_tag(content="#drawer{position:absolute!important;bottom:auto!important;height:auto!important;transition:none!important}")
    page.locator("#drawer").screenshot(path=str(out / "drawer_full.png"))
    made += ["desktop_node.png", "drawer_full.png"]
    page.close()
    page, _ = open_page(browser, url, viewport={"width": 1440, "height": 900}, color_scheme="dark")
    page.evaluate(f"kmapFocusNode({json.dumps(longest)})")
    page.wait_for_timeout(400)
    page.screenshot(path=str(out / "desktop_dark.png"))
    made.append("desktop_dark.png")
    page.close()
    if has_chain:
        page, _ = open_page(browser, url, viewport={"width": 1440, "height": 900})
        page.evaluate("kmapShowChain(0, 0)")
        page.wait_for_timeout(700)
        page.screenshot(path=str(out / "desktop_chain.png"))
        made.append("desktop_chain.png")
        page.close()

    # 3. 手机宽度：图、节点面板、文字版
    m, _ = open_page(browser, url, viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
    m.screenshot(path=str(out / "mobile_map.png"))
    m.evaluate(f"kmapFocusNode({json.dumps(longest)})")
    m.wait_for_timeout(400)
    m.screenshot(path=str(out / "mobile_node.png"))
    m.evaluate("document.getElementById('dx').click(); document.getElementById('text').scrollIntoView()")
    m.wait_for_timeout(200)
    m.screenshot(path=str(out / "mobile_text.png"))
    made += ["mobile_map.png", "mobile_node.png", "mobile_text.png"]
    m.close()
    return made


def main() -> None:
    ap = argparse.ArgumentParser(description="在后台 Chrome 里检查知识关系图的版面")
    ap.add_argument("html", type=Path, help="build.py 生成的 HTML")
    ap.add_argument("--png", type=Path, help="把截图存到这个目录")
    args = ap.parse_args()
    if not args.html.exists():
        sys.exit(f"找不到文件：{args.html}")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit("没有装 playwright。先运行：python -m pip install playwright")

    url = args.html.resolve().as_uri()
    problems = 0
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="chrome", headless=True)
        page, errs = open_page(browser, url, viewport={"width": 1440, "height": 900})
        rep = page.evaluate("kmapCheck()")
        page.close()
        for key, name in NAMES.items():
            items = rep.get(key) or []
            if items:
                problems += len(items)
                print(f"{name}（{len(items)} 处）：")
                for it in items[:40]:
                    print("  " + it)
                if len(items) > 40:
                    print(f"  ……还有 {len(items) - 40} 处")
        m, merrs = open_page(browser, url, viewport={"width": 390, "height": 844}, is_mobile=True)
        if m.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth + 1"):
            problems += 1
            print("手机宽度下整页能左右滑动：有东西超出了屏幕宽度。")
        wraps = m.evaluate("kmapMathWrap()")
        if wraps:
            problems += len(wraps)
            print(f"公式和紧挨着的标点被拆到两行，手机宽度（{len(wraps)} 处）：")
            for it in wraps[:40]:
                print("  " + it)
        m.close()
        for e in errs + merrs:
            problems += 1
            print("页面脚本报错：" + e)
        if args.png:
            made = shots(browser, url, args.png)
            print(f"截图已存到 {args.png}：" + "、".join(made))
        browser.close()
    if problems:
        print(f"共 {problems} 处问题。改法见 references/layout.md。")
        sys.exit(1)
    print("版面检查：没有问题。")


if __name__ == "__main__":
    main()

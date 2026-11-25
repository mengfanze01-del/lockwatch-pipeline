# -*- coding: utf-8 -*-
"""
LockWatch Pipeline: merge weekly history (198) with current page rows (40+占位),
sort by 8 sections + time desc, apply date/title fixes, rewrite v17.html + index.html.
"""
import json
import re
import html
import sys
from pathlib import Path
from collections import defaultdict

ROOT = Path(r"D:\work\lockwatch-pipeline")
JSON_PATH = ROOT / "mico_deliverables" / "weekly_history_items.json"
HTML_PATH = ROOT / "v17.html"
INDEX_PATH = ROOT / "index.html"

# 周期起始日映射（第 N 期 → 周期起始日），用于回修越界日期
# 按 MiCo 汇总表：期 N 周期起始日 = 2026-06-22 + 7*(N-1)
ISSUE_START = {}
import datetime as _dt
_base = _dt.date(2026, 6, 22)
for n in range(1, 17):
    ISSUE_START[n] = (_base + _dt.timedelta(days=7 * (n - 1))).isoformat()

# 有效日期窗口（周报总体覆盖区间）
VALID_MIN = "2026-06-22"
VALID_MAX = "2026-11-05"  # 看板现网 40 条从 11-06 起

# 栏目映射
MOD_KEYS = {
    "01": "01 今日信息流",
    "02": "02 今日泰国锁机",
    "03": "03 小米锁机",
    "04": "04 监管与合规",
    "05": "05 区域市场",
    "06": "06 技术与产品",
    "08": "08 三星专档",
    "09": "09 电动车锁机条线",
}
MOD_CLASS = {
    "01": "mod col-feed",
    "02": "mod col-th",
    "03": "mod col-xm",
    "04": "mod",
    "05": "mod",
    "06": "mod",
    "08": "mod",
    "09": "mod",
}
MOD_TITLE = {
    "01": "今日信息流",
    "02": "今日泰国锁机",
    "03": "小米锁机",
    "04": "监管与合规",
    "05": "区域市场",
    "06": "技术与产品",
    "08": "三星专档",
    "09": "电动车锁机条线",
}

FLAG_RE = re.compile(r"^(🇨🇳|🇮🇳|🇰🇪|🇳🇬|🇮🇩|🇹🇭|🇵🇭|🇻🇳|🇧🇷|🇲🇽|🇿🇦|🇦🇪|🇪🇺|🇺🇸|🇯🇵|🇧🇩|🇵🇰|🇲🇦|🇷🇺|🇲🇾|🇨🇴|🇻🇪|🇪🇬|🇹🇷|🇦🇷|🇵🇪|🇬🇭|🇹🇿|🇺🇬|🇷🇼|🇿🇼|🇨🇭|🇩🇪|🇫🇷|🇮🇹|🇪🇸|🇬🇧|🇰🇷|🇸🇬|🇸🇦|🇶🇦|🇨🇱|🇺🇾|🇵🇾|🇧🇴|🇪🇨)")


def load_history():
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        items = json.load(f)
    fixed = []
    for it in items:
        it = dict(it)  # copy
        # 修复日期越界
        if it["date"] < VALID_MIN or it["date"] > VALID_MAX:
            m = re.match(r"第(\d+)期", it.get("section", ""))
            if m:
                n = int(m.group(1))
                if n in ISSUE_START:
                    it["date"] = ISSUE_START[n]
                    # 同步 time_raw（归一到 MM-DD）
                    it["time_raw"] = _fmt_md(it["date"])
        # 归一 time_raw：若为完整 YYYY-MM-DD，缩短为 MM-DD
        tr = (it.get("time_raw") or "").strip()
        if re.match(r"^\d{4}-\d{2}-\d{2}$", tr):
            it["time_raw"] = _fmt_md(tr)
        elif not tr:
            it["time_raw"] = _fmt_md(it["date"])

        # 修复国名/短标题：title 以国旗开头且 ≤20 字符,或整体≤10 字符
        t = (it.get("title") or "").strip()
        need_prepend = False
        if FLAG_RE.match(t) and len(t) <= 20:
            need_prepend = True
        elif len(t) <= 10:
            need_prepend = True
        if need_prepend:
            s = (it.get("summary") or "").strip()
            first = re.split(r"[。！\!；;]", s, maxsplit=1)[0].strip()
            if len(first) > 80:
                first = first[:80].rstrip() + "…"
            if first:
                it["title"] = f"{t} | {first}"
        fixed.append(it)
    return fixed


ROW_RE = re.compile(
    r'<div class="row">\s*'
    r'<div class="r-time">(?P<time>.*?)</div>\s*'
    r'<div class="r-body">\s*'
    r'<div class="r-title"[^>]*>(?P<title>.*?)</div>\s*'
    r'<div class="r-summary"[^>]*>(?P<summary>.*?)</div>\s*'
    r'</div>\s*'
    r'<div class="r-src"(?:\s+data-url="(?P<url>[^"]*)")?>(?P<src>.*?)</div>\s*'
    r'<div class="r-tags">(?P<tags>.*?)</div>\s*'
    r'<div class="r-act">(?P<act>.*?)</div>\s*'
    r'</div>',
    re.DOTALL,
)

MOD_SEC_RE = re.compile(
    r'(<section class="(?:mod[^"]*)" data-mod="(?P<mod>\d+)"[^>]*>)(?P<inner>.*?)(</section>)',
    re.DOTALL,
)


def parse_current_rows(html_text):
    """从现网 HTML 提取每栏的 row 实体（不含占位行）。"""
    current = defaultdict(list)
    for m in MOD_SEC_RE.finditer(html_text):
        mod = m.group("mod")
        inner = m.group("inner")
        for rm in ROW_RE.finditer(inner):
            time_raw = rm.group("time").strip()
            title_html = rm.group("title").strip()
            summary_html = rm.group("summary").strip()
            url = (rm.group("url") or "").strip()
            src = rm.group("src").strip()
            tags_html = rm.group("tags").strip()

            # 判断占位行：time='11-24' 且 title 含 '无新增动态'
            if "无新增动态" in title_html or "手动试跑" in summary_html:
                continue

            # 提取 tag 名字（展示用）
            tag_names = re.findall(r'<span class="tag">([^<]+)</span>', tags_html)

            # 从 title/summary 的 title 属性拿原文；若无则用 html decode 后的纯文本
            # 这里直接保留 HTML 原状，渲染端一致
            current[mod].append(
                {
                    "source": "current",
                    "time_raw": time_raw,
                    "date": _parse_date_from_time(time_raw),
                    "time_sort": _time_sort_key(time_raw),
                    "title_html": title_html,
                    "summary_html": summary_html,
                    "url": url,
                    "src": src,
                    "tag_names": tag_names,
                    "is_core": False,
                }
            )
    return current


def _parse_date_from_time(time_raw):
    """time_raw 形如 '11-23 07:12' 或 '11-23'；返回 'YYYY-MM-DD'。"""
    m = re.match(r"(\d{2})-(\d{2})", time_raw)
    if not m:
        return "2026-01-01"
    mm, dd = int(m.group(1)), int(m.group(2))
    # 页面上的时间都是 2026 年
    return f"2026-{mm:02d}-{dd:02d}"


def _time_sort_key(time_raw):
    """生成排序键：日期 + HH:MM（缺则 00:00）；用于同日排序。"""
    date = _parse_date_from_time(time_raw)
    m = re.search(r"\d{2}:\d{2}", time_raw)
    hhmm = m.group(0) if m else "00:00"
    return f"{date}T{hhmm}"


def normalize_history(items):
    """把 JSON 历史条目标准化成与 current row 相同的结构。"""
    out = defaultdict(list)
    for it in items:
        mod_key = it["mod"]
        mod_id = mod_key.split(" ")[0]  # '01' '02' ... '08' '09'
        if mod_id not in MOD_KEYS:
            continue

        date = it["date"]
        time_raw = it.get("time_raw") or _fmt_md(date)

        title_text = it.get("title") or ""
        summary_text = it.get("summary") or ""
        url = it.get("url") or ""
        src = it.get("source") or ""
        tags = it.get("tags") or []

        is_core = any("核心要点" in t for t in tags)

        out[mod_id].append(
            {
                "source": "history",
                "time_raw": time_raw,
                "date": date,
                "time_sort": _time_sort_key(time_raw) if re.match(r"\d{2}-\d{2}", time_raw) else f"{date}T00:00",
                "title_html": html.escape(title_text, quote=False),
                "summary_html": html.escape(summary_text, quote=False),
                "url": url,
                "src": html.escape(src, quote=False),
                "tag_names": tags,
                "is_core": is_core,
            }
        )
    return out


def _fmt_md(date):
    m = re.match(r"\d{4}-(\d{2})-(\d{2})", date)
    if not m:
        return date
    return f"{m.group(1)}-{m.group(2)}"


def _render_row(r):
    """生成一个 <div class="row"> HTML。"""
    time_raw = r["time_raw"]
    title_html = r["title_html"]
    summary_html = r["summary_html"]
    # title 属性去除可能的 HTML 标签
    title_attr = html.escape(_strip_tags(title_html), quote=True)
    summary_attr = html.escape(_strip_tags(summary_html), quote=True)
    url = r["url"]
    src = r["src"] or "—"
    tag_names = r["tag_names"] or []

    tags_html = "".join(f'<span class="tag">{html.escape(t, quote=False)}</span>' for t in tag_names)

    if url:
        src_html = f'<div class="r-src" data-url="{html.escape(url, quote=True)}">{src}</div>'
        act_html = '<div class="r-act"><button class="btn" data-act="orig" title="原文链接">↗ 原文链接</button></div>'
    else:
        src_html = f'<div class="r-src">{src}</div>'
        act_html = '<div class="r-act"></div>'

    return (
        '        <div class="row">\n'
        f'          <div class="r-time">{html.escape(time_raw, quote=False)}</div>\n'
        '          <div class="r-body">\n'
        f'            <div class="r-title" title="{title_attr}">{title_html}</div>\n'
        f'            <div class="r-summary" title="{summary_attr}">{summary_html}</div>\n'
        '          </div>\n'
        f'          {src_html}\n'
        f'          <div class="r-tags">{tags_html}</div>\n'
        f'          {act_html}\n'
        '        </div>'
    )


def _strip_tags(s):
    return re.sub(r"<[^>]+>", "", s)


def _render_today_placeholder(mod_id):
    """11-24 栏目今日占位行（保留原语义）。"""
    return (
        '        <div class="row">\n'
        '          <div class="r-time">11-24</div>\n'
        '          <div class="r-body">\n'
        '            <div class="r-title" title="11-24 无新增动态">11-24 无新增动态</div>\n'
        '            <div class="r-summary" title="本栏目今日无公开新增条目;历史条目已按 8 栏时间倒序整合;正式数据以每日 08:00 Autopilot 抓取为准。">本栏目今日无公开新增条目;历史条目已按 8 栏时间倒序整合;正式数据以每日 08:00 Autopilot 抓取为准。</div>\n'
        '          </div>\n'
        '          <div class="r-src">—</div>\n'
        '          <div class="r-tags"><span class="tag">今日占位</span></div>\n'
        '          <div class="r-act"></div>\n'
        '        </div>'
    )


def build_section_rows(mod_id, rows):
    """返回一个栏目的 <section> 完整 HTML（替换原 section）。"""
    # 排序：核心要点置顶，其余按 time_sort 倒序
    rows_sorted = sorted(
        rows,
        key=lambda r: (0 if r["is_core"] else 1, _neg(r["time_sort"])),
    )

    row_htmls = [_render_today_placeholder(mod_id)] + [_render_row(r) for r in rows_sorted]
    rows_html = "\n\n".join(row_htmls)

    total = len(rows_sorted)
    sec_class = MOD_CLASS[mod_id]
    sec_title = MOD_TITLE[mod_id]

    return (
        f'    <section class="{sec_class}" data-mod="{mod_id}" data-total="{total}" data-month="{total}">\n'
        f'      <div class="sec-head">\n'
        f'        <div class="sec-left"><span class="sec-no">{mod_id}</span><span class="sec-title">{sec_title}</span></div>\n'
        f'        <span class="sec-count">历史 {total} 条 · 按时间倒序</span>\n'
        f'      </div>\n'
        f'      <div class="row-head"><div>时间</div><div>标题</div><div>摘要</div><div>来源</div><div>关键字</div><div>动作</div></div>\n'
        f'      <div class="rows">\n\n{rows_html}\n\n      </div>\n'
        f'      <div class="mod-foot">\n'
        f'        <div class="mod-foot-note">全量历史 · 共 {total} 条</div>\n'
        f'      </div>\n'
        f'    </section>'
    )


def _neg(s):
    """反序字符串 → 让 sort 升序时得到按字母表倒序。用字符逐位取反。"""
    # 简单做法：用负元组比较；此函数返回可比较对象使升序排序 == 对 s 倒序
    return tuple(-ord(c) for c in s)


def rewrite_html(html_text, by_mod):
    """把每个 section 替换为新的 section。"""
    def repl(m):
        mod_id = m.group("mod")
        if mod_id not in MOD_KEYS:
            return m.group(0)
        return build_section_rows(mod_id, by_mod.get(mod_id, []))

    return MOD_SEC_RE.sub(repl, html_text)


def update_meta_lines(text):
    """把 sec-count 的 '近一月 X · 本页 Y / Z' 已在 build_section_rows 替换;
    保留 #meta-date / #meta-time / #foot-stamp 的 2026-11-24 不变。
    移除分页器 pager（已在 build_section_rows 中省略）。"""
    return text


def main():
    html_text = HTML_PATH.read_text(encoding="utf-8")
    history = load_history()
    hist_by_mod = normalize_history(history)
    cur_by_mod = parse_current_rows(html_text)

    merged = defaultdict(list)
    for mod_id in MOD_KEYS:
        combined = list(cur_by_mod.get(mod_id, [])) + list(hist_by_mod.get(mod_id, []))
        # 去重：按 (date, title 文本) key
        seen = set()
        dedup = []
        for r in combined:
            key = (r["date"], _strip_tags(r["title_html"]).strip()[:40])
            if key in seen:
                continue
            seen.add(key)
            dedup.append(r)
        merged[mod_id] = dedup

    new_html = rewrite_html(html_text, merged)
    HTML_PATH.write_text(new_html, encoding="utf-8")
    INDEX_PATH.write_text(new_html, encoding="utf-8")

    # 打印统计
    print("=== Build summary ===")
    for mod_id in MOD_KEYS:
        rows = merged[mod_id]
        core = sum(1 for r in rows if r["is_core"])
        print(f"  {mod_id} {MOD_TITLE[mod_id]}: {len(rows)} 条 (核心要点 {core})")
    print(f"Total rows merged: {sum(len(v) for v in merged.values())}")
    print(f"Wrote: {HTML_PATH}")
    print(f"Wrote: {INDEX_PATH}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Generate bilingual SVG reading previews. All content is fictional."""
from html import escape
from pathlib import Path

COPY = {
    'zh-CN': {
        'lang': 'zh-CN', 'label': '虚构数据 · 阅读示意', 'title': '纠正记录',
        'subtitle': '汇总本机 Agent 会话中的纠正，供用户回看与核对。',
        'run': '最近一次运行：2026-01-13 11:05', 'summary': '新增 3 条 · 2 个类别',
        'columns': ['类别', '次数', '首次', '最近', '来源', '对应规则', '原话与会话'],
        'categories': ['擅自扩大范围', '忽略已有格式'], 'rule': '无对应规则',
        'quotes': [['“我只让你比较两种方案，', '怎么又开始写实现了？”'],
                   ['“请沿用项目里的日期格式，', '不要再换一种。”']],
        'more': '另有 1 条摘录，见完整示例',
        'footer': '示意仅节选表格；实际输出为 Markdown，包含完整摘录、日期与原文定位。',
        'note': '所有消息、次数、时间和定位均为虚构。',
    },
    'en': {
        'lang': 'en', 'label': 'FICTIONAL DATA / PREVIEW', 'title': 'Correction ledger',
        'subtitle': 'A reviewable record of corrections across local agent sessions.',
        'run': 'Last run: 2026-01-13 11:05', 'summary': '3 new events / 2 categories',
        'columns': ['Category', 'Count', 'First seen', 'Last seen', 'Source', 'Rule', 'Excerpts'],
        'categories': ['Scope expansion', 'Ignored format'], 'rule': 'No matching rule',
        'quotes': [['“I asked for a comparison.', 'Why did you start implementing?”'],
                   ['“Use the existing date format,', 'rather than introducing another.”']],
        'more': '1 more excerpt in the full sample',
        'footer': 'Condensed preview. Markdown output includes full dates, excerpts and source references.',
        'note': 'All messages, counts, timestamps and references are fictional. Runtime output is currently in Chinese.',
    },
}


def generate(language):
    c = COPY[language]
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="1440" height="750" viewBox="0 0 1440 750" role="img" aria-labelledby="title desc" xml:lang="{c["lang"]}">',
             f'<title id="title">{escape(c["title"])} — {escape(c["label"])}</title>',
             f'<desc id="desc">{escape(c["subtitle"])} {escape(c["note"])}</desc>',
             '<rect width="1440" height="750" fill="#f6f5f1"/>',
             '<g font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Noto Sans CJK SC, Microsoft YaHei, sans-serif" fill="#242b28">']
    def text(x, y, value, size=22, color='#242b28', weight=400):
        parts.append(f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" font-weight="{weight}">{escape(value)}</text>')
    def rect(x,y,w,h,color):parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{color}"/>')
    muted='#68716b';green='#405f50'
    text(64,69,'CAIRN / LEDGER',19,green)
    text(1040,69,c['label'],17,muted)
    text(64,151,c['title'],44,weight=600)
    text(64,199,c['subtitle'],24,muted)
    rect(64,226,1312,2,'#dcded8')
    text(64,278,c['run'],21,muted)
    text(1040,278,c['summary'],21,green)
    rect(64,307,1312,56,'#e9ece5')
    xs=[64,264,334,506,678,826,972]
    for x,label in zip(xs,c['columns']):text(x+14,344,label,19,muted)
    for top,height in [(363,138),(501,105)]:
        rect(64,top,1312,height,'#ffffff')
        rect(64,top+height,1312,1,'#dcded8')
    for i,(y,category,count,first,last,sources) in enumerate([
            (410,c['categories'][0],'2','01-12 09:00','01-13 10:00',['claude','codex']),
            (549,c['categories'][1],'1','01-13 11:00','01-13 11:00',['codex'])]):
        text(78,y,category,22 if language=='zh-CN' else 20)
        text(281,y,count,25,green)
        text(348,y,first,20);text(520,y,last,20)
        for j,source in enumerate(sources):text(692,y+j*29,source,20)
        text(840,y,c['rule'],19 if language=='zh-CN' else 17,muted)
        for j,line in enumerate(c['quotes'][i]):text(986,y+j*32,line,21)
    text(986,485,c['more'],18,muted)
    text(64,675,c['footer'],20,muted)
    text(64,711,c['note'],18,muted)
    parts.extend(['</g>','</svg>'])
    target=Path(__file__).parent / f'ledger-preview.{language}.svg'
    target.write_text('\n'.join(parts)+'\n')


if __name__ == '__main__':
    for language in COPY:generate(language)

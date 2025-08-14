#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri May 16 11:17:42 2025

@author: liyifan
"""


#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成 FFL 课程退出曲线交互式 HTML 仪表盘
—— 支持屏蔽指定课程
—— 使用单一下拉菜单同时筛选“类型”和“难度”组合
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import os


def main():
    # —— 路径配置 ——
    desktop = os.path.expanduser('~/Desktop')
    xlsx_path = os.path.join(desktop, 'exit_raw_data_0521.xlsx')
    print(f'📥 读取数据：{xlsx_path}')

    # —— 读取 Excel ——
    df = pd.read_excel(xlsx_path)
    print('🔍 初始课程数量：', df['lesson_name'].nunique(), '，总记录数：', len(df))

    # —— 要屏蔽的课程列表 ——
    excluded_courses = ["Oh Life"]
    if excluded_courses:
        before = df['lesson_name'].nunique()
        df = df[~df['lesson_name'].isin(excluded_courses)]
        after = df['lesson_name'].nunique()
        print(f'🚫 屏蔽课程：{excluded_courses}，课程数 {before} → {after}')

    # —— 重命名字段以统一脚本 ——
    df = df.rename(columns={
        'lesson_seconds': 'standard_seconds',
        'lesson_workout_seconds': 'actual_seconds'
    })

    # —— 类型 & 难度 映射 ——
    type_map = {'CombatFit': 'Combat', 'DanceFit': 'Dance'}
    diff_map = {'Beg': 'Beg', 'Int': 'Int', 'Adv': 'Adv'}

    # —— 筛选支持的类型 & 难度 ——
    df = df[df['lesson_type'].isin(type_map.keys()) & df['lesson_difficulty'].isin(diff_map.keys())]
    df['type_str'] = df['lesson_type'].map(type_map)
    df['diff_str'] = df['lesson_difficulty'].map(diff_map)

    print('类型分布：\n', df['type_str'].value_counts())
    print('难度分布：\n', df['diff_str'].value_counts())

    # —— 构建 traces ——
    percent_axis = np.arange(0, 101, 1)
    traces = []

    # 单课程曲线
    for lesson, grp in df.groupby('lesson_name'):
        std = grp['standard_seconds'].iloc[0]
        y = [(grp['actual_seconds'] >= p/100*std).sum() / len(grp) * 100 for p in percent_axis]
        seconds = [p/100*std for p in percent_axis]
        traces.append(go.Scatter(
            x=percent_axis, y=y, mode='lines', name=lesson,
            legendgroup=f'course-{lesson}',
            hovertemplate=('课程：%{text}<br>进度：%{x:.0f}%<br>留课率：%{y:.1f}%<br>秒数：%{customdata:.0f}/' + str(std)),
            text=[lesson]*len(percent_axis), customdata=seconds, line=dict(width=1), visible=True
        ))

    # 全局平均（按类型）
    for tcode, tname in type_map.items():
        curves = []
        for _, grp in df[df['lesson_type']==tcode].groupby('lesson_name'):
            std = grp['standard_seconds'].iloc[0]
            y = [(grp['actual_seconds'] >= p/100*std).sum() / len(grp) * 100 for p in percent_axis]
            curves.append(y)
        avg_y = np.mean(curves, axis=0)
        traces.append(go.Scatter(
            x=percent_axis, y=avg_y, mode='lines', name=f'{tname} 全局平均',
            legendgroup=f'avg-{tname}', hovertemplate='进度：%{x:.0f}%<br>平均留课率：%{y:.1f}%',
            line=dict(width=4, color='black'), visible=True
        ))

    # 类型×难度平均
    for tcode, tname in type_map.items():
        for dcode, dname in diff_map.items():
            sub = df[(df['lesson_type']==tcode) & (df['lesson_difficulty']==dcode)]
            if sub.empty: continue
            curves = []
            for _, grp in sub.groupby('lesson_name'):
                std = grp['standard_seconds'].iloc[0]
                y = [(grp['actual_seconds'] >= p/100*std).sum() / len(grp) * 100 for p in percent_axis]
                curves.append(y)
            avg_y = np.mean(curves, axis=0)
            traces.append(go.Scatter(
                x=percent_axis, y=avg_y, mode='lines', name=f'{tname}-{dname} 平均',
                legendgroup=f'avg-{tname}-{dname}', hovertemplate='进度：%{x:.0f}%<br>平均留课率：%{y:.1f}%',
                line=dict(width=2, color='black'), visible=True
            ))

    # 构建 Figure
    fig = go.Figure(data=traces)

    # —— 单一下拉：类型 & 难度 组合 ——
    combos = ['Combat', 'Dance', 'Combat Beg', 'Combat Int', 'Combat Adv', 'Dance Beg', 'Dance Int', 'Dance Adv']
    buttons = []
    for combo in combos:
        mask = []
        if ' ' in combo:
            t_sel, d_sel = combo.split()
            for tr in fig.data:
                lg = tr.legendgroup
                if lg.startswith('course-'):
                    ok = (df[df['lesson_name']==tr.name]['type_str'].iloc[0]==t_sel) and (df[df['lesson_name']==tr.name]['diff_str'].iloc[0]==d_sel)
                    mask.append(ok)
                else:
                    mask.append(lg==f'avg-{t_sel}-{d_sel}')
        else:
            t_sel = combo
            for tr in fig.data:
                lg = tr.legendgroup
                if lg.startswith('course-'):
                    ok = (df[df['lesson_name']==tr.name]['type_str'].iloc[0]==t_sel)
                    mask.append(ok)
                else:
                    mask.append(lg.startswith(f'avg-{t_sel}'))
        buttons.append(dict(label=combo, method='update', args=[{'visible': mask}]))

    fig.update_layout(
        updatemenus=[dict(
            buttons=buttons, direction='down', showactive=True,
            x=0, y=1.18, xanchor='left'
        )],
        title='FFL 课程退出曲线', xaxis_title='进度百分比 (%)', yaxis_title='用户留课率 (%)',
        hovermode='closest', legend=dict(orientation='v', x=1.02, y=1.0)
    )

    # 保存 HTML
    out_path = os.path.join(desktop, 'exit_curves0521.html')
    fig.write_html(out_path)
    print(f'✅ 仪表盘已保存：{out_path}')


if __name__ == '__main__':
    main()


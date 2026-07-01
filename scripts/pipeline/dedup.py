#!/usr/bin/env python3
"""
阶段2: Dedup — 跨源去重检测模块。

================================================================================
模块功能
================================================================================
Pipeline 第二阶段：检测并报告来自不同信源的重复文章。
  1. 查询数据库中 content_hash 出现次数 >1 的文章组
  2. 按发布时间排序，最早的作为 canonical（权威版本）
  3. 输出重复文章列表（仅报告，不做删除 —— "软去重"策略）

================================================================================
核心算法
================================================================================
去重基于 content_hash（SHA256(title+link)），而非内容相似度。
这意味着只有完全相同标题+链接的文章才会被识别为重复。
如果同一事件被不同信源用不同标题报道，不会被标记为重复——
这是有意设计，避免误杀不同视角的报道。

去重策略采用"软删除"而非物理删除:
  - 不删除任何数据，保持完整采集记录
  - 后续阶段（Curator / Publisher）可以根据 dedup 标记决定是否展示
  - 保留所有数据用于趋势分析和历史回溯

================================================================================
边界条件
================================================================================
- content_hash 为 NULL 的文章不在去重范围内
- 只有 content_hash 重复次数 ≥2 的才触发检测
- 按 published 字段排序，published 值异常时可能选错 canonical
"""

from datetime import datetime

from . import get_db


def run() -> dict:
    """
    运行去重检测主流程。

    步骤:
      1. GROUP BY content_hash，找出 HAVING COUNT > 1 的重复组
      2. 对每个重复组，ORDER BY published ASC，最早的文章作为 canonical
      3. 输出每条重复组的信息（canonical 标题 + follower 标题列表）

    注意: 当前版本只输出日志，不写入数据库标记——是"报告型"去重而非"标记型"去重。
          后续如果需要在前端过滤重复文章，可以扩展为更新 is_canonical / duplicate_of 字段。

    Returns:
        { "duplicates_found": int } — 发现的重复组数量
    """
    print("🔍 Dedup — detecting cross-source duplicates...")

    conn = get_db()

    # ---- 第一步：查找所有出现超过一次的 content_hash ----
    # 这意味着同一篇文章（相同标题+链接）被不同信源收录了
    dupes = conn.execute("""
        SELECT content_hash, COUNT(*) as cnt
        FROM articles
        WHERE content_hash IS NOT NULL
        GROUP BY content_hash
        HAVING cnt > 1
    """).fetchall()

    if not dupes:
        print(f"   No duplicates found")
        conn.close()
        return {"duplicates_found": 0}

    # ---- 第二步：对每个重复组，找出 canonical 和 duplicates ----
    # 按 published 升序排列，最早发布的作为 canonical（权威版本）
    # 注意: published 字段的数据质量参差不齐（有些信源提供不准确的时间），
    #       极端情况下最早的可能不是真正的首发，但这是合理的启发式近似
    for row in dupes:
        articles = conn.execute("""
            SELECT id, title, published, source_name
            FROM articles
            WHERE content_hash = ?
            ORDER BY published ASC
        """, (row["content_hash"],)).fetchall()

        if len(articles) > 1:
            canonical = articles[0]  # 最早发布的作为 canonical
            dupes_list = [a["title"][:50] for a in articles[1:]]
            print(f"   📎 Dedup: \"{canonical['title'][:50]}...\" "
                  f"({canonical['source_name']}) + {len(dupes_list)} dupes")
            for d in dupes_list:
                print(f"      └─ \"{d}...\"")

    conn.close()
    return {"duplicates_found": len(dupes)}


if __name__ == "__main__":
    run()

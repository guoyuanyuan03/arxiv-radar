import urllib.request
import feedparser
import re
import os
import json
import yaml
import datetime
from datetime import timezone, timedelta
from typing import List, Dict


def load_config(file_path="config.yaml"):
    """读取 YAML 配置文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f) 
        return config
    except FileNotFoundError:
        print(f"❌ 找不到配置文件: {file_path}")
        return {}
    except yaml.YAMLError as exc:
        print(f"❌ YAML 解析错误:\n{exc}")
        return {}


def fetch_arxiv_papers(topic_name: str, topic_config: Dict, days_back: int = 1, max_results: int = 500) -> List[Dict]:
    """
    通用 arXiv 抓取函数：根据研究主题检索获取最新 arXiv 论文
    Args:
        topic_name: str, 研究主题名称
        topic_config: Dict, 研究主题检索过滤配置
        days_back: int, 扫描的天数，默认为 1 天
        max_results: int, 最多获取的论文数量，默认为 500
    Returns:
        List[Dict], 匹配到的 arXiv 论文列表
    """
    # === 1. 设定时间范围 ===
    now_utc = datetime.datetime.now(timezone.utc)
    target_date = (now_utc - timedelta(days=days_back)).date()
    start_dt = datetime.datetime.combine(target_date, datetime.time.min, tzinfo=timezone.utc)
    end_dt = datetime.datetime.combine(target_date, datetime.time.max, tzinfo=timezone.utc)

    # 转换为 arXiv API 要求的格式: YYYYMMDDHHMMSS
    start_api_str = start_dt.strftime("%Y%m%d%H%M%S")
    end_api_str = end_dt.strftime("%Y%m%d%H%M%S")

    print(f"🔍 正在向 arXiv 请求 {topic_name} 相关论文数据...")
    
    # === 2. 构建 arXiv API 查询请求 ===
    # 2.1 设定搜索范围：涵盖 NLP、机器学习、人工智能和多智能体系统
    categories = topic_config.get('categories')
    
    # 2.2 构建 arXiv API 请求 URL (按提交时间倒序排列)
    date_query = f"submittedDate:[{start_api_str}+TO+{end_api_str}]"
    url = f"http://export.arxiv.org/api/query?search_query={categories}+AND+{date_query}&sortBy=submittedDate&sortOrder=descending&max_results={max_results}"
    
    try:
        # 解析 RSS feed
        response = urllib.request.urlopen(url).read()
        feed = feedparser.parse(response)
    except Exception as e:
        print(f"❌ 请求 arXiv API 失败: {e}")
        return []
    
    # === 3. 预编译正则表达式 ===
    # 高精度版：直接锁定核心算法 (用于匹配标题和摘要)
    high_precision_regex = re.compile(topic_config["high_precision"]) if topic_config.get("high_precision") else None
    
    # 高召回率版：Agent 概念 + RL 概念的双重命中 (用于匹配摘要上下文)
    high_recall_regex = re.compile(topic_config["high_recall"]) if topic_config.get("high_recall") else None

    # === 4. 解析与匹配 ===
    matched_papers = []
    for entry in feed.entries:
        # 获取并转换论文发布时间
        published_tuple = entry.published_parsed
        published_dt = datetime.datetime(*published_tuple[:6], tzinfo=timezone.utc)
        
        # 二次校验时间边界（防范 API 边缘误差）
        if not (start_dt <= published_dt <= end_dt):
            continue
            
        title = entry.title.replace('\n', ' ')
        summary = entry.summary.replace('\n', ' ')
        
        # 匹配逻辑：标题命中高精度 OR 摘要命中高精度 OR 摘要命中高召回率双重条件
        match_title = high_precision_regex.search(title)
        match_summary_hp = high_precision_regex.search(summary)
        match_summary_hr = high_recall_regex.search(summary)
        
        if match_title or match_summary_hp or match_summary_hr:
            matched_papers.append({
                'title': title,
                'authors': [author.name for author in entry.authors],
                'link': entry.link,
                'published': published_dt.strftime("%Y-%m-%d"),
                'reason': "标题精准命中" if match_title else ("摘要精准命中" if match_summary_hp else "摘要召回命中"),
                'summary': summary
            })

    # # === 5. 打印预览信息 ===
    # print(f"\n✅ 扫描完毕！在获取到的 {len(feed.entries)} 篇论文中，共发现 {len(matched_papers)} 篇强相关论文:\n")
    # print("-" * 60)
    
    # for i, paper in enumerate(matched_papers, 1):
    #     print(f"[{i}] {paper['title']}")
    #     print(f"👥 作者: {', '.join(paper['authors'][:3])}{' 等' if len(paper['authors']) > 3 else ''}")
    #     print(f"📅 日期: {paper['published']} | 🎯 匹配原因: {paper['reason']}")
    #     print(f"🔗 链接: {paper['link']}")
    #     print("-" * 60)

    return matched_papers


def send_to_feishu(webhook_url: str, papers_dict: Dict[str, List[Dict]], days_back: int = 1):
    """
    将筛选出的 arXiv 论文格式化为 Markdown 并推送到飞书
    Args:
        webhook_url: str, 飞书群聊机器人的 webhook 地址
        papers_dict: Dict[str, List[Dict]], 按研究主题分类，匹配到的 arXiv 论文
        days_back: int, 扫描的天数，默认为 1 天
    """
    date_label = (datetime.datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    if not papers_dict:
        content = f"✅ **今日 arXiv 扫描完毕 ({date_label})**\n未发现您关注领域的前沿论文。今天可以不用刷论文，好好休息一下啦~~"
        header_color = "green"
    else:
        num_papers = sum([len(papers) for papers in papers_dict.values()])
        content = f"🔥 **今日共发现 {num_papers} 篇前沿论文！({date_label})**\n\n"
        header_color = "blue"
        for topic, papers in papers_dict.items():
            # 主题块标题
            content += f"**📚【{topic}】** (共 {len(papers)} 篇)\n"
            content += "---\n"

            for i, paper in enumerate(papers, 1):
                arxiv_id = paper['link'].split('/abs/')[-1] if 'abs' in paper['link'] else '点击阅读 arXiv 原文'

                # 构建富文本/Markdown 格式
                content += f"**[{i}] {paper['title']}**\n"
                content += f"👥 作者: {', '.join(paper['authors'][:3])}{' 等' if len(paper['authors']) > 3 else ''}\n"
                content += f"📅 日期: {paper['published']} | 🎯 匹配原因: {paper['reason']}\n"
                content += f"🔗 [arXiv:{arxiv_id}]({paper['link']})\n\n"
            
            content += "\n"

    # 构建飞书卡片 JSON payload (使用富文本 Markdown 格式)
    payload = {
        "msg_type": "interactive",
        "card": {
            "config": { "wide_screen_mode": True },
            "header": {
                "title": { "tag": "plain_text", "content": "🤖 每日 arXiv 学术雷达" },
                "template": header_color
            },
            "elements": [
                {
                    "tag": "markdown",
                    "content": content.strip()
                }
            ]
        }
    }

    # 发送请求到飞书
    req = urllib.request.Request(
        webhook_url, 
        data=json.dumps(payload).encode('utf-8'), 
        headers={'Content-Type': 'application/json'}
    )
    
    try:
        response = urllib.request.urlopen(req)
        print(f"✅ 飞书推送成功！服务器响应: {response.read().decode('utf-8')}")
    except Exception as e:
        print(f"❌ 飞书推送失败: {e}")
    

if __name__ == "__main__":
    # 1. 读取变量参数
    webhook_url = os.environ.get("FEISHU_WEBHOOK")
    days_to_check = 1

    RESEARCH_TOPICS = load_config("config.yaml")
    if not RESEARCH_TOPICS:
        print("未加载到任何研究主题配置，程序退出。")
        exit()
    
    # 2. 遍历配置字典中的所有研究方向
    all_results = {}
    for topic_name, topic_config in RESEARCH_TOPICS.items():
        print(f"🔍 正在扫描主题: {topic_name}")
        # 这里调用上一轮写的 fetch_papers_by_topic 函数
        papers = fetch_arxiv_papers(topic_name, topic_config, days_to_check)
        if papers:
            all_results[topic_name] = papers
            
    # 3. 推送飞书 (合并所有主题的结果)
    if webhook_url and all_results:
        send_to_feishu(webhook_url, all_results, days_to_check)

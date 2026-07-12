from fastapi import APIRouter, Depends, HTTPException,status, Query
from typing import List, Optional
from datetime import datetime
from core.models.tags import Tags as TagsModel
from core.database import get_db
from sqlalchemy.orm import Session
from schemas.tags import Tags, TagsCreate
from .base import success_response, error_response
from core.auth import get_current_user_or_ak
from core.cache import clear_cache_pattern

# 标签管理API路由
# 提供标签的增删改查功能
# 需要管理员权限执行写操作
router = APIRouter(prefix="/tags", tags=["标签管理"])

@router.get("", 
    summary="获取标签列表",
    description="分页获取所有标签信息")
async def get_tags(offset: int = 0, limit: int = 100, db: Session = Depends(get_db),cur_user: dict = Depends(get_current_user_or_ak)):
    """
    获取标签列表
    
    参数:
    - offset: 跳过记录数，用于分页
    - limit: 每页记录数，默认100
    
    返回:
    - 包含标签列表和分页信息的成功响应
    """
    query = db.query(TagsModel)
    total = query.count()
    tags = query.offset(offset).limit(limit).all()
    return success_response(data={
        "list": tags,
        "page": {
            "limit": limit,
            "offset": offset,
            "total": total
        },
        "total": total
    })

@router.post("",
    summary="创建新标签",
    description="创建一个新的标签"
   )
async def create_tag(tag: TagsCreate, db: Session = Depends(get_db),cur_user: dict = Depends(get_current_user_or_ak)):
    """
    创建新标签
    
    参数:
    - tag: TagsCreate模型，包含标签信息
    
    请求体示例:
    {
        "name": "新标签",
        "cover": "http://example.com/cover.jpg",
        "intro": "新标签的描述",
        "status": 1
    }
    
    返回:
    - 成功: 包含新建标签信息的响应
    - 失败: 错误响应
    """
    import uuid
    try:
        db_tag = TagsModel(
            id=str(uuid.uuid4()),
            name=tag.name or '',
            cover=tag.cover or '',
            intro=tag.intro or '',
            mps_id =tag.mps_id,
            status=tag.status,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        db.add(db_tag)
        db.commit()
        db.refresh(db_tag)
        
        # 清除相关缓存
        clear_cache_pattern("home_page")
        clear_cache_pattern("tag_detail")
        
        return success_response(data=db_tag)
    except Exception as e:
         from core.print  import print_error
         print_error(e)
         raise HTTPException(
            status_code=status.HTTP_201_CREATED,
            detail=error_response(
                code=50001,
                message=f"暂无数据",
            )
        )

@router.get("/{tag_id}", summary="获取单个标签详情",  description="根据标签ID获取标签详细信息")
async def get_tag(tag_id: str, db: Session = Depends(get_db),cur_user: dict = Depends(get_current_user_or_ak)):
    """
    获取单个标签详情
    
    参数:
    - tag_id: 标签ID
    
    返回:
    - 成功: 包含标签详情的响应
    - 失败: 201错误响应(标签不存在)
    """
    tag = db.query(TagsModel).filter(TagsModel.id == tag_id).first()
    if not tag:
        return error_response(code=status.HTTP_201_CREATED, message="Tag not found")
    return success_response(data=tag)

@router.put("/{tag_id}",
    summary="更新标签信息",
    description="根据标签ID更新标签信息",
 )
async def update_tag(tag_id: str, tag_data: TagsCreate, db: Session = Depends(get_db),cur_user: dict = Depends(get_current_user_or_ak)):
    """
    更新标签信息
    
    参数:
    - tag_id: 要更新的标签ID
    - tag_data: TagsCreate模型，包含要更新的标签信息
    
    请求体示例:
    {
        "name": "更新后的标签",
        "cover": "http://example.com/new_cover.jpg",
        "intro": "更新后的描述",
        "status": 1
    }
    
    返回:
    - 成功: 包含更新后标签信息的响应
    - 失败: 404错误响应(标签不存在)或500错误响应(服务器错误)
    """
    try:
        tag = db.query(TagsModel).filter(TagsModel.id == tag_id).first()
        if not tag:
            return error_response(code=404, message="Tag not found")
        
        tag.name = tag_data.name
        tag.cover = tag_data.cover
        tag.intro = tag_data.intro
        tag.status = tag_data.status
        tag.mps_id = tag_data.mps_id
        tag.updated_at = datetime.now()
        
        db.commit()
        db.refresh(tag)
        
        # 清除相关缓存
        clear_cache_pattern("home_page")
        clear_cache_pattern("tag_detail")
        
        return success_response(data=tag)
    except Exception as e:
        return error_response(code=500, message=str(e))

@router.delete("/{tag_id}",
    summary="删除标签",
    description="根据标签ID删除标签",
   )
async def delete_tag(tag_id: str, db: Session = Depends(get_db),cur_user: dict = Depends(get_current_user_or_ak)):
    """
    删除标签
    
    参数:
    - tag_id: 要删除的标签ID
    
    返回:
    - 成功: 删除成功的响应
    - 失败: 404错误响应(标签不存在)或500错误响应(服务器错误)
    """
    try:
        tag = db.query(TagsModel).filter(TagsModel.id == tag_id).first()
        if not tag:
            return error_response(code=status.HTTP_201_CREATED, message="Tag not found")
        db.delete(tag)
        db.commit()
        
        # 清除相关缓存
        clear_cache_pattern("home_page")
        clear_cache_pattern("tag_detail")
        
        return success_response(message="Tag deleted successfully")
    except Exception as e:
        return error_response(code=status.HTTP_201_CREATED, message=str(e))


@router.post("/{tag_id}/summary",
    summary="生成标签下某时间段的文章总结",
    description="对指定标签下指定时间段的文章进行AI总结"
)
async def generate_tag_summary(
    tag_id: str,
    start_time: int = Query(..., description="开始时间戳（秒）"),
    end_time: int = Query(..., description="结束时间戳（秒）"),
    push_notice: bool = Query(False, description="是否推送通知到飞书等渠道"),
    db: Session = Depends(get_db),
    cur_user: dict = Depends(get_current_user_or_ak)
):
    """
    生成标签下某时间段的文章总结
    
    参数:
    - tag_id: 标签ID
    - start_time: 开始时间戳（秒）
    - end_time: 结束时间戳（秒）
    - push_notice: 是否推送通知，默认False
    
    返回:
    - 包含总结内容的响应
    """
    import json
    from core.db import DB
    from core.models.article import Article
    from core.models.feed import Feed
    from jobs.daily_summary import _ai_summarize
    
    session = DB.get_session()
    try:
        # 查询标签信息
        tag = session.query(TagsModel).filter(TagsModel.id == tag_id).first()
        if not tag:
            return error_response(code=404, message="标签不存在")
        
        # 解析关联的公众号ID
        mps_ids = []
        if tag.mps_id:
            try:
                mps_data = json.loads(tag.mps_id)
                mps_ids = [str(mp['id']) for mp in mps_data] if isinstance(mps_data, list) else []
            except (json.JSONDecodeError, TypeError):
                mps_ids = []
        
        if not mps_ids:
            return error_response(code=400, message="该标签未关联任何公众号")
        
        # 查询该时间段内的文章
        arts = session.query(Article).filter(
            Article.mp_id.in_(mps_ids),
            Article.has_content == 1,
            Article.status != 2,
            Article.publish_time >= start_time,
            Article.publish_time <= end_time
        ).order_by(Article.publish_time.desc()).all()
        
        if not arts:
            return error_response(code=400, message="该时间段内没有文章")
        
        # 公众号ID→名称映射
        feeds = session.query(Feed).filter(Feed.id.in_(mps_ids)).all()
        feed_map = {f.id: f.mp_name for f in feeds}
        
        start_date = datetime.fromtimestamp(start_time).strftime("%Y-%m-%d")
        end_date = datetime.fromtimestamp(end_time).strftime("%Y-%m-%d")
        
        # 预提取每篇文章的纯文本和元数据，优先使用数据库缓存的AI摘要
        items = []
        need_ai = []  # 需要调用AI的索引列表
        for idx, a in enumerate(arts):
            pt = datetime.fromtimestamp(a.publish_time).strftime("%H:%M")
            mp_name = feed_map.get(a.mp_id, a.mp_id)
            cached = (a.ai_summary or "").strip() if hasattr(a, "ai_summary") else ""
            full_text = _extract_text(a.content, 4000) if not cached else ""
            items.append({
                "title": a.title or "(无标题)",
                "pt": pt,
                "mp_name": mp_name,
                "full_text": full_text,
                "summary": cached,
                "article_id": a.id,
            })
            if not cached:
                need_ai.append(idx)
        
        # 仅对未缓存的文章并发生成AI摘要
        if need_ai:
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=5) as pool:
                ai_results = list(pool.map(
                    lambda i: _ai_summarize(items[i]["full_text"], items[i]["title"]),
                    need_ai,
                ))
            # 回填摘要并写入数据库缓存
            for i, idx in enumerate(need_ai):
                items[idx]["summary"] = ai_results[i]
                try:
                    art = session.query(Article).filter(Article.id == items[idx]["article_id"]).first()
                    if art is not None:
                        art.ai_summary = ai_results[i]
                    session.commit()
                except Exception as e:
                    pass
        
        # 构建完整的Markdown总结
        lines = [f"### 📰 【{tag.name}】标签内容总结（{start_date} ~ {end_date}）",
                 f"共 {len(items)} 篇文章", ""]
        
        for i, it in enumerate(items, 1):
            lines.append(f"**{i}. {it['title']}**")
            lines.append(f"- ⏰ {it['pt']} ｜ 📢 {it['mp_name']}")
            lines.append(f"- 摘要：{it['summary']}")
            lines.append("")
        
        summary_md = "\n".join(lines)
        
        # 是否推送通知
        if push_notice:
            try:
                from jobs.notice import sys_notice
                title = f"标签总结：{tag.name}（{start_date}~{end_date}）"
                sys_notice(text=summary_md, title=title, tag="标签总结")
            except Exception as e:
                pass
        
        return success_response(data={
            "tag_name": tag.name,
            "start_date": start_date,
            "end_date": end_date,
            "article_count": len(items),
            "summary": summary_md,
            "articles": items
        })
        
    finally:
        session.close()


def _extract_text(html: str, max_len: int = 500) -> str:
    """从 HTML 提取纯文本摘要"""
    from bs4 import BeautifulSoup
    
    soup = BeautifulSoup(html or "", "html.parser")
    text = soup.get_text(separator=" ", strip=True)
    noise = ["微信扫一扫", "知道了", "取消", "允许", "在小说阅读器", "去阅读",
             "在小说阅读器中沉浸阅读", "使用完整服务", "轻点两下取消赞",
             "轻点两下取消在看", "使用小程序"]
    for n in noise:
        text = text.replace(n, "")
    text = " ".join(text.split())
    return text[:max_len]
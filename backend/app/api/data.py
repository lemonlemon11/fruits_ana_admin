"""管理端业务数据查看接口。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..auth import require_permission
from ..db import get_db
from ..models import (
    AiAnalysis,
    DataIssue,
    ImportBatch,
    SaleRecord,
    SettlementSummary,
    SourceFile,
    User,
)


router = APIRouter(prefix="/api/admin/data", tags=["admin-data"])


def _batch_dict(batch: ImportBatch) -> dict:
    return {
        "id": batch.id,
        "file_name": batch.file_name,
        "merchant_no": batch.merchant_no,
        "merchant_no_normalized": batch.merchant_no_normalized,
        "order_no": batch.order_no,
        "order_no_normalized": batch.order_no_normalized,
        "container_no": batch.container_no,
        "vehicle_no": batch.vehicle_no,
        "imported_at": batch.imported_at.isoformat() if batch.imported_at else None,
        "status": batch.status,
        "success_count": batch.success_count,
        "warning_count": batch.warning_count,
        "failure_count": batch.failure_count,
        "error_summary": batch.error_summary,
    }


def _issue_dict(issue: DataIssue) -> dict:
    return {
        "id": issue.id,
        "import_batch_id": issue.import_batch_id,
        "source_file_id": issue.source_file_id,
        "sale_record_id": issue.sale_record_id,
        "row_number": issue.row_number,
        "issue_type": issue.issue_type,
        "severity": issue.severity,
        "field_name": issue.field_name,
        "message": issue.message,
        "raw_value": issue.raw_value,
        "created_at": issue.created_at.isoformat() if issue.created_at else None,
    }


def _source_dict(source: SourceFile) -> dict:
    return {
        "id": source.id,
        "import_batch_id": source.import_batch_id,
        "file_name": source.file_name,
        "file_hash": source.file_hash,
        "storage_path": source.storage_path,
        "stored_at": source.stored_at.isoformat() if source.stored_at else None,
    }


def _ai_dict(item: AiAnalysis) -> dict:
    return {
        "id": item.id,
        "cache_key": item.cache_key,
        "feature": item.feature,
        "model": item.model,
        "content": item.content,
        "created_at": item.created_at.isoformat() if item.created_at else None,
    }


@router.get("/imports")
def list_imports(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("admin:data:view")),
):
    query = db.query(ImportBatch)
    if keyword:
        like = f"%{keyword}%"
        query = query.filter(
            (ImportBatch.merchant_no.ilike(like))
            | (ImportBatch.merchant_no_normalized.ilike(like))
            | (ImportBatch.order_no.ilike(like))
            | (ImportBatch.order_no_normalized.ilike(like))
            | (ImportBatch.file_name.ilike(like))
        )
    if status:
        query = query.filter(ImportBatch.status == status)
    total = query.count()
    items = (
        query.order_by(ImportBatch.imported_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {"items": [_batch_dict(item) for item in items], "total": total}


@router.get("/imports/{batch_id}")
def get_import(
    batch_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("admin:data:view")),
):
    batch = db.get(ImportBatch, batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="导入批次不存在")
    return _batch_dict(batch)


@router.get("/imports/{batch_id}/issues")
def list_import_issues(
    batch_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("admin:data:view")),
):
    batch = db.get(ImportBatch, batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="导入批次不存在")
    issues = (
        db.query(DataIssue)
        .filter(DataIssue.import_batch_id == batch_id)
        .order_by(DataIssue.id)
        .all()
    )
    return {"items": [_issue_dict(issue) for issue in issues], "total": len(issues)}


@router.get("/source-files")
def list_source_files(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("admin:data:view")),
):
    query = db.query(SourceFile)
    total = query.count()
    items = (
        query.order_by(SourceFile.stored_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {"items": [_source_dict(item) for item in items], "total": total}


@router.get("/sales")
def list_sales(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    import_batch_id: int | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("admin:data:view")),
):
    query = db.query(SaleRecord)
    if import_batch_id is not None:
        query = query.filter(SaleRecord.import_batch_id == import_batch_id)
    total = query.count()
    items = (
        query.order_by(SaleRecord.sale_date.desc(), SaleRecord.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "items": [
            {
                "id": item.id,
                "import_batch_id": item.import_batch_id,
                "sale_date": item.sale_date.isoformat(),
                "fruit_type": item.fruit_type,
                "grade": item.grade,
                "grade_raw": item.grade_raw,
                "spec_raw": item.spec_raw,
                "quantity": float(item.quantity),
                "unit_price": float(item.unit_price),
                "amount": float(item.amount),
                "sales_region": item.sales_region,
            }
            for item in items
        ],
        "total": total,
    }


@router.get("/ai-cache")
def list_ai_cache(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("admin:data:view")),
):
    query = db.query(AiAnalysis)
    total = query.count()
    items = (
        query.order_by(AiAnalysis.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {"items": [_ai_dict(item) for item in items], "total": total}


@router.delete("/ai-cache/{cache_id}", status_code=204)
def delete_ai_cache(
    cache_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("admin:data:refresh-cache")),
):
    item = db.get(AiAnalysis, cache_id)
    if item is None:
        raise HTTPException(status_code=404, detail="AI 缓存不存在")
    db.delete(item)
    db.commit()
    return None

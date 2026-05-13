"""
设备批量导入API路由

提供设备批量导入功能:
- POST /api/v1/devices/import - 批量导入设备(Excel/CSV格式)
- GET /api/v1/devices/import/template - 下载导入模板
- POST /api/v1/devices/import/validate - 验证导入数据不提交

支持字段: name, ip_address, device_type, vendor, model, snmp_community, location, idc
支持部分成功(返回成功/失败列表)

响应格式: {"data":..., "code":0, "message":"success"}
"""

import logging
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, UploadFile, File, Query, HTTPException
from pydantic import BaseModel, Field

from api.dependencies import get_current_user, CurrentUser

logger = logging.getLogger(__name__)

router = APIRouter(tags=["设备批量导入"], prefix="/api/v1/devices/import")


# ============== 请求/响应模型 ==============

class ImportValidateRequest(BaseModel):
    """验证导入数据请求"""
    rows: List[Dict[str, Any]] = Field(..., description="待验证的设备数据行")


class ImportValidateItem(BaseModel):
    """验证结果项"""
    row: int = Field(..., description="行号")
    status: str = Field(..., description="验证状态: valid/invalid")
    errors: List[str] = Field(default_factory=list, description="错误信息列表")
    data: Optional[Dict[str, Any]] = Field(None, description="数据")


class ImportValidateResponse(BaseModel):
    """验证结果响应"""
    total: int = Field(..., description="总行数")
    valid_count: int = Field(..., description="有效行数")
    invalid_count: int = Field(..., description="无效行数")
    items: List[ImportValidateItem] = Field(..., description="验证结果详情")


class ImportResultItem(BaseModel):
    """导入结果项"""
    row: int = Field(..., description="行号")
    status: str = Field(..., description="导入状态: success/failed")
    device_id: Optional[int] = Field(None, description="导入成功的设备ID")
    name: Optional[str] = Field(None, description="设备名称")
    error: Optional[str] = Field(None, description="错误信息")


class ImportResultResponse(BaseModel):
    """导入结果响应"""
    total: int = Field(..., description="总行数")
    success_count: int = Field(..., description="成功行数")
    failed_count: int = Field(..., description="失败行数")
    results: List[ImportResultItem] = Field(..., description="导入结果详情")


# ============== 标准响应格式 ==============

def success_response(data: Any = None, message: str = "success", code: int = 0) -> Dict[str, Any]:
    """构建成功响应"""
    return {
        "code": code,
        "message": message,
        "data": data
    }


def error_response(message: str, code: int = 1, data: Any = None) -> Dict[str, Any]:
    """构建错误响应"""
    return {
        "code": code,
        "message": message,
        "data": data
    }


# ============== API 端点 ==============

@router.get("/template", summary="下载设备导入模板")
async def download_template(
    format: str = Query("xlsx", description="模板格式: xlsx 或 csv"),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    下载设备导入Excel/CSV模板
    
    - **format**: 模板格式 (xlsx 或 csv)
    
    模板包含以下列:
    - 设备名称 (必需)
    - IP地址 (必需)
    - 设备类型 (必需): server_linux, network_switch, firewall 等
    - 厂商 (可选)
    - 型号 (可选)
    - SNMP Community (可选)
    - 位置 (可选)
    - 机房 (可选)
    """
    try:
        from fastapi.responses import StreamingResponse
        from modules.business.device_importer import DeviceImporter, ImportFormat
        
        importer = DeviceImporter()
        
        if format.lower() == 'csv':
            content, content_type = importer.generate_template(ImportFormat.CSV)
            filename = "device_import_template.csv"
        else:
            content, content_type = importer.generate_template(ImportFormat.XLSX)
            filename = "device_import_template.xlsx"
        
        return StreamingResponse(
            iter([content]),
            media_type=content_type,
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{filename}"
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"生成导入模板失败: {e}")
        return error_response(message=f"生成导入模板失败: {str(e)}")


@router.post("/validate", summary="验证导入数据")
async def validate_import_data(
    request: ImportValidateRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    验证导入数据(不提交到数据库)
    
    - **rows**: 待验证的设备数据列表，每行包含:
        - name: 设备名称 (必需)
        - ip_address: IP地址 (必需)
        - device_type: 设备类型 (必需)
        - vendor: 厂商 (可选)
        - model: 型号 (可选)
        - snmp_community: SNMP Community (可选)
        - location: 位置 (可选)
        - idc: 机房 (可选)
    
    返回验证结果，包含每行的验证状态和错误信息
    """
    try:
        from modules.business.device_importer import DeviceImporter
        
        importer = DeviceImporter()
        
        # Add row numbers
        rows_with_num = []
        for i, row in enumerate(request.rows, start=1):
            row_copy = row.copy()
            row_copy['_row_num'] = i
            rows_with_num.append(row_copy)
        
        # Validate
        result = importer.validate_data(rows_with_num)
        
        # Build response
        items = []
        valid_count = 0
        invalid_count = 0
        
        for row in rows_with_num:
            row_num = row.get('_row_num', 0)
            is_valid, error = importer.validate_row(row)
            
            if is_valid:
                valid_count += 1
                items.append(ImportValidateItem(
                    row=row_num,
                    status="valid",
                    errors=[],
                    data=row
                ))
            else:
                invalid_count += 1
                items.append(ImportValidateItem(
                    row=row_num,
                    status="invalid",
                    errors=[error],
                    data=row
                ))
        
        return success_response(
            data=ImportValidateResponse(
                total=len(request.rows),
                valid_count=valid_count,
                invalid_count=invalid_count,
                items=items
            ).model_dump(),
            message=f"验证完成: {valid_count}行有效, {invalid_count}行无效"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"验证导入数据失败: {e}")
        return error_response(message=f"验证导入数据失败: {str(e)}")


@router.post("", summary="批量导入设备")
async def import_devices(
    file: UploadFile = File(..., description="导入文件(Excel或CSV)"),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    批量导入设备
    
    - **file**: 导入文件(Excel .xlsx 或 CSV .csv格式)
    
    支持部分成功:
    - 有效的行会创建设备
    - 无效的行会返回错误信息
    - 最终返回成功/失败列表
    
    支持的字段:
    - name: 设备名称 (必需)
    - ip_address: IP地址 (必需)
    - device_type: 设备类型 (必需)
    - vendor: 厂商 (可选)
    - model: 型号 (可选)
    - snmp_community: SNMP Community (可选)
    - location: 位置 (可选)
    - idc: 机房 (可选)
    """
    try:
        from modules.business.device_importer import DeviceImporter, ImportFormat
        
        # Read file content
        content = await file.read()
        
        if not content:
            return error_response(message="上传文件为空")
        
        # Determine format from filename
        filename = file.filename or "import.csv"
        if filename.lower().endswith('.csv'):
            file_format = ImportFormat.CSV
        else:
            file_format = ImportFormat.XLSX
        
        # Parse file
        importer = DeviceImporter()
        try:
            data = importer.parse_file(content, filename, file_format)
        except Exception as e:
            return error_response(message=f"解析文件失败: {str(e)}")
        
        if not data:
            return error_response(message="文件中没有找到有效数据")
        
        # Import devices
        result = importer.import_devices(data, username=current_user.username)
        
        # Build response
        results = []
        for item in result.success:
            results.append(ImportResultItem(
                row=item.get('_row_num', 0),
                status="success",
                device_id=item.get('imported_id'),
                name=item.get('name'),
                error=None
            ))
        
        for item in result.failed:
            results.append(ImportResultItem(
                row=item.get('_row_num', 0),
                status="failed",
                device_id=None,
                name=item.get('name'),
                error=item.get('error')
            ))
        
        # Sort by row number
        results.sort(key=lambda x: x.row)
        
        return success_response(
            data=ImportResultResponse(
                total=result.total,
                success_count=len(result.success),
                failed_count=len(result.failed),
                results=results
            ).model_dump(),
            message=f"导入完成: 成功{len(result.success)}行, 失败{len(result.failed)}行"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量导入设备失败: {e}")
        return error_response(message=f"批量导入设备失败: {str(e)}")


@router.post("/simple", summary="简单批量导入(直接传数据)")
async def import_devices_simple(
    rows: List[Dict[str, Any]],
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    简单批量导入设备(直接传递JSON数据)
    
    - **rows**: 设备数据列表，每行包含:
        - name: 设备名称 (必需)
        - ip_address: IP地址 (必需)
        - device_type: 设备类型 (必需)
        - vendor: 厂商 (可选)
        - model: 型号 (可选)
        - snmp_community: SNMP Community (可选)
        - location: 位置 (可选)
        - idc: 机房 (可选)
    
    适用于小批量导入或API直接调用
    """
    try:
        from modules.business.device_importer import DeviceImporter
        
        if not rows:
            return error_response(message="没有传入任何数据")
        
        # Add row numbers
        rows_with_num = []
        for i, row in enumerate(rows, start=1):
            row_copy = row.copy()
            row_copy['_row_num'] = i
            rows_with_num.append(row_copy)
        
        # Import devices
        importer = DeviceImporter()
        result = importer.import_devices(rows_with_num, username=current_user.username)
        
        # Build response
        results = []
        for item in result.success:
            results.append(ImportResultItem(
                row=item.get('_row_num', 0),
                status="success",
                device_id=item.get('imported_id'),
                name=item.get('name'),
                error=None
            ))
        
        for item in result.failed:
            results.append(ImportResultItem(
                row=item.get('_row_num', 0),
                status="failed",
                device_id=None,
                name=item.get('name'),
                error=item.get('error')
            ))
        
        # Sort by row number
        results.sort(key=lambda x: x.row)
        
        return success_response(
            data=ImportResultResponse(
                total=result.total,
                success_count=len(result.success),
                failed_count=len(result.failed),
                results=results
            ).model_dump(),
            message=f"导入完成: 成功{len(result.success)}行, 失败{len(result.failed)}行"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量导入设备失败: {e}")
        return error_response(message=f"批量导入设备失败: {str(e)}")

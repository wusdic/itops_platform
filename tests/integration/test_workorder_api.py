# -*- coding: utf-8 -*-
"""
工单管理API集成测试

遵循Google测试最佳实践:
- Given-When-Then结构
- 测试通过公共API
- 测试业务工作流，不测试内部实现
- 使用 f 工厂fixture生成所有测试数据
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta


class TestWorkOrderAPI:
    """工单管理API测试类"""

    @pytest.fixture
    def mock_workorder_core(self, db_session):
        """模拟工单核心"""
        with patch("modules.business.workorder.workorder.WorkOrderCore") as mock:
            instance = MagicMock()
            instance.list.return_value = ([], 0)
            instance.get_by_id.return_value = None
            instance.create.return_value = MagicMock(
                id=1,
                order_no="WO-2024-0001",
                title="测试工单",
                status=MagicMock(value="pending"),
                priority=MagicMock(value="P3"),
                order_type=MagicMock(value="fault"),
                creator="admin",
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            instance.update.return_value = True
            instance.delete.return_value = True
            mock.return_value = instance
            yield mock

    # ============== 工单列表接口 ==============

    def test_get_workorders_empty(self, client, admin_headers, mock_workorder_core):
        """Given: 系统中无工单
           When: 获取工单列表
           Then: 返回空列表"""
        mock_workorder_core.return_value.list.return_value = ([], 0)
        
        response = client.get(
            "/api/v1/workorders/",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    def test_get_workorders_with_data(self, client, admin_headers, f, mock_workorder_core):
        """Given: 系统中有工单
           When: 获取工单列表
           Then: 返回工单列表"""
        workorders = [
            MagicMock(
                id=1,
                order_no="WO-2024-0001",
                title="服务器故障",
                status=MagicMock(value="pending"),
                priority=MagicMock(value="P1"),
                order_type=MagicMock(value="fault"),
                creator="admin",
                created_at=datetime.now(),
                updated_at=datetime.now(),
            ),
            MagicMock(
                id=2,
                order_no="WO-2024-0002",
                title="变更申请",
                status=MagicMock(value="processing"),
                priority=MagicMock(value="P2"),
                order_type=MagicMock(value="change"),
                creator="operator",
                created_at=datetime.now(),
                updated_at=datetime.now(),
            ),
        ]
        mock_workorder_core.return_value.list.return_value = (workorders, 2)
        
        response = client.get(
            "/api/v1/workorders/",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2

    def test_get_workorders_with_status_filter(self, client, admin_headers, f, mock_workorder_core):
        """Given: 系统中有多种状态工单
           When: 按状态过滤
           Then: 返回指定状态工单"""
        workorders = [
            MagicMock(
                id=1,
                order_no="WO-2024-0001",
                status=MagicMock(value="pending"),
                priority=MagicMock(value="P3"),
                order_type=MagicMock(value="fault"),
                creator="admin",
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
        ]
        mock_workorder_core.return_value.list.return_value = (workorders, 1)
        
        response = client.get(
            "/api/v1/workorders/?status=pending",
            headers=admin_headers
        )
        
        assert response.status_code == 200

    def test_get_workorders_with_type_filter(self, client, admin_headers, f, mock_workorder_core):
        """Given: 系统中有多种类型工单
           When: 按类型过滤
           Then: 返回指定类型工单"""
        mock_workorder_core.return_value.list.return_value = ([], 0)
        
        response = client.get(
            "/api/v1/workorders/?order_type=fault",
            headers=admin_headers
        )
        
        assert response.status_code == 200

    def test_get_workorders_with_priority_filter(self, client, admin_headers, f, mock_workorder_core):
        """Given: 系统中有多种优先级工单
           When: 按优先级过滤
           Then: 返回指定优先级工单"""
        mock_workorder_core.return_value.list.return_value = ([], 0)
        
        response = client.get(
            "/api/v1/workorders/?priority=P1",
            headers=admin_headers
        )
        
        assert response.status_code == 200

    def test_get_workorders_with_assignee_filter(self, client, admin_headers, f, mock_workorder_core):
        """Given: 系统中有分配给操作员的工单
           When: 按处理人过滤
           Then: 返回指定处理人的工单"""
        mock_workorder_core.return_value.list.return_value = ([], 0)
        
        response = client.get(
            "/api/v1/workorders/?assignee=operator",
            headers=admin_headers
        )
        
        assert response.status_code == 200

    def test_get_workorders_with_pagination(self, client, admin_headers, f, mock_workorder_core):
        """Given: 系统中有多个工单
           When: 请求分页
           Then: 返回指定页的数据"""
        mock_workorder_core.return_value.list.return_value = ([], 100)
        
        response = client.get(
            "/api/v1/workorders/?page=2&page_size=20",
            headers=admin_headers
        )
        
        assert response.status_code == 200

    def test_get_workorders_unauthorized(self, client):
        """Given: 未认证用户
           When: 获取工单列表
           Then: 返回401"""
        response = client.get("/api/v1/workorders/")
        assert response.status_code == 401

    # ============== 创建工单接口 ==============

    def test_create_workorder_success(self, client, admin_headers, f, mock_workorder_core):
        """Given: 有效的工单数据
           When: 创建工单
           Then: 返回创建的工单"""
        wo_data = f.workorder(title="测试工单", priority="P2")
        
        mock_workorder_core.return_value.create.return_value = MagicMock(
            id=1,
            order_no="WO-2024-0001",
            title=wo_data["title"],
            status=MagicMock(value="pending"),
            priority=MagicMock(value="P2"),
            order_type=MagicMock(value="fault"),
            creator="admin",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        
        response = client.post(
            "/api/v1/workorders/",
            json={
                "order_type": "fault",
                "title": wo_data["title"],
                "description": wo_data["description"],
                "priority": wo_data["priority"],
            },
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["title"] == wo_data["title"]

    def test_create_workorder_minimal(self, client, admin_headers, f, mock_workorder_core):
        """Given: 最少工单数据
           When: 创建工单
           Then: 返回创建的工单"""
        mock_workorder_core.return_value.create.return_value = MagicMock(
            id=1,
            order_no="WO-2024-0002",
            title="简单工单",
            status=MagicMock(value="pending"),
            priority=MagicMock(value="P3"),
            order_type=MagicMock(value="fault"),
            creator="admin",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        
        response = client.post(
            "/api/v1/workorders/",
            json={
                "order_type": "fault",
                "title": "简单工单",
            },
            headers=admin_headers
        )
        
        assert response.status_code == 200

    def test_create_workorder_with_device(self, client, admin_headers, f, mock_workorder_core):
        """Given: 工单关联设备
           When: 创建工单
           Then: 返回创建的工单"""
        mock_workorder_core.return_value.create.return_value = MagicMock(
            id=1,
            order_no="WO-2024-0003",
            title="设备故障",
            device_name="web-prod-01",
            device_ip="192.168.1.10",
            status=MagicMock(value="pending"),
            priority=MagicMock(value="P1"),
            order_type=MagicMock(value="fault"),
            creator="admin",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        
        response = client.post(
            "/api/v1/workorders/",
            json={
                "order_type": "fault",
                "title": "设备故障",
                "device_name": "web-prod-01",
                "device_ip": "192.168.1.10",
                "priority": "P1",
            },
            headers=admin_headers
        )
        
        assert response.status_code == 200

    def test_create_workorder_with_assignee(self, client, admin_headers, f, mock_workorder_core):
        """Given: 指定处理人
           When: 创建工单
           Then: 返回创建的工单"""
        mock_workorder_core.return_value.create.return_value = MagicMock(
            id=1,
            order_no="WO-2024-0004",
            title="指派工单",
            assignee="operator01",
            status=MagicMock(value="pending"),
            priority=MagicMock(value="P2"),
            order_type=MagicMock(value="change"),
            creator="admin",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        
        response = client.post(
            "/api/v1/workorders/",
            json={
                "order_type": "change",
                "title": "指派工单",
                "assignee": "operator01",
            },
            headers=admin_headers
        )
        
        assert response.status_code == 200

    # ============== 工单详情接口 ==============

    def test_get_workorder_not_found(self, client, admin_headers, mock_workorder_core):
        """Given: 工单不存在
           When: 获取工单详情
           Then: 返回404"""
        mock_workorder_core.return_value.get_by_id.return_value = None
        
        response = client.get(
            "/api/v1/workorders/9999",
            headers=admin_headers
        )
        
        assert response.status_code == 404

    def test_get_workorder_found(self, client, admin_headers, mock_workorder_core):
        """Given: 工单存在
           When: 获取工单详情
           Then: 返回工单详情"""
        mock_workorder_core.return_value.get_by_id.return_value = MagicMock(
            id=1,
            order_no="WO-2024-0001",
            title="测试工单",
            description="详细描述",
            status=MagicMock(value="processing"),
            priority=MagicMock(value="P2"),
            order_type=MagicMock(value="fault"),
            device_name="web-server",
            device_ip="192.168.1.10",
            creator="admin",
            assignee="operator",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        
        response = client.get(
            "/api/v1/workorders/1",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1

    # ============== 更新工单接口 ==============

    def test_update_workorder_success(self, client, admin_headers, mock_workorder_core):
        """Given: 工单存在且有效数据
           When: 更新工单
           Then: 返回成功"""
        mock_workorder_core.return_value.get_by_id.return_value = MagicMock(
            id=1,
            creator="admin",
        )
        mock_workorder_core.return_value.update.return_value = True
        
        response = client.put(
            "/api/v1/workorders/1",
            json={"title": "更新后的标题"},
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_update_workorder_not_found(self, client, admin_headers, mock_workorder_core):
        """Given: 工单不存在
           When: 更新工单
           Then: 返回404"""
        mock_workorder_core.return_value.update.return_value = False
        
        response = client.put(
            "/api/v1/workorders/9999",
            json={"title": "更新"},
            headers=admin_headers
        )
        
        assert response.status_code == 404

    def test_update_workorder_empty_fields(self, client, admin_headers, mock_workorder_core):
        """Given: 无更新字段
           When: 更新工单
           Then: 返回400"""
        response = client.put(
            "/api/v1/workorders/1",
            json={},
            headers=admin_headers
        )
        
        assert response.status_code == 400

    def test_update_workorder_status(self, client, admin_headers, mock_workorder_core):
        """Given: 工单存在
           When: 更新工单状态
           Then: 返回成功"""
        mock_workorder_core.return_value.get_by_id.return_value = MagicMock(
            id=1,
            creator="admin",
        )
        mock_workorder_core.return_value.update.return_value = True
        
        response = client.put(
            "/api/v1/workorders/1",
            json={"status": "resolved"},
            headers=admin_headers
        )
        
        assert response.status_code == 200

    # ============== 删除工单接口 ==============

    def test_delete_workorder_success(self, client, admin_headers, mock_workorder_core):
        """Given: 工单存在且用户有权限
           When: 删除工单
           Then: 返回成功"""
        mock_workorder_core.return_value.get_by_id.return_value = MagicMock(
            id=1,
            creator="admin",
        )
        mock_workorder_core.return_value.delete.return_value = True
        
        with patch("api.routes.workorder.get_current_user") as mock_user:
            mock_user.return_value.is_admin.return_value = True
            
            response = client.delete(
                "/api/v1/workorders/1",
                headers=admin_headers
            )
            
            assert response.status_code == 200

    def test_delete_workorder_not_found(self, client, admin_headers, mock_workorder_core):
        """Given: 工单不存在
           When: 删除工单
           Then: 返回404"""
        mock_workorder_core.return_value.delete.return_value = False
        
        response = client.delete(
            "/api/v1/workorders/9999",
            headers=admin_headers
        )
        
        assert response.status_code == 404

    def test_delete_workorder_no_permission(self, client, admin_headers, mock_workorder_core):
        """Given: 用户无删除权限
           When: 删除工单
           Then: 返回403"""
        mock_workorder_core.return_value.get_by_id.return_value = MagicMock(
            id=1,
            creator="other_user",
        )
        
        with patch("api.routes.workorder.get_current_user") as mock_user:
            mock_user.return_value.is_admin.return_value = False
            mock_user.return_value.username = "operator"
            
            response = client.delete(
                "/api/v1/workorders/1",
                headers=admin_headers
            )
            
            assert response.status_code == 403

    # ============== 工单流程接口 ==============

    def test_get_workorder_flows(self, client, admin_headers, db_session):
        """Given: 工单有流程记录
           When: 获取工单流程历史
           Then: 返回流程列表"""
        with patch("modules.foundation.db_models.workorder.WorkOrderFlow") as mock_flow:
            mock_query = MagicMock()
            mock_query.filter.return_value.order_by.return_value.all.return_value = []
            db_session.query.return_value = mock_query
            
            response = client.get(
                "/api/v1/workorders/1/flows",
                headers=admin_headers
            )
            
            assert response.status_code == 200

    def test_create_workorder_flow_assign(self, client, admin_headers, mock_workorder_core):
        """Given: 工单存在
           When: 添加工单流程记录(分配)
           Then: 返回成功"""
        mock_workorder_core.return_value.get_by_id.return_value = MagicMock(
            id=1,
            status=MagicMock(value="pending"),
        )
        
        with patch("modules.foundation.db_models.workorder.WorkOrderFlow") as mock_flow:
            response = client.post(
                "/api/v1/workorders/1/flows",
                json={
                    "action": "assign",
                    "comment": "分配给operator",
                    "to_status": "processing"
                },
                headers=admin_headers
            )
            
            assert response.status_code == 200

    def test_create_workorder_flow_resolve(self, client, admin_headers, mock_workorder_core):
        """Given: 工单处理完成
           When: 添加工单流程记录(解决)
           Then: 返回成功"""
        mock_workorder_core.return_value.get_by_id.return_value = MagicMock(
            id=1,
            status=MagicMock(value="processing"),
        )
        
        response = client.post(
            "/api/v1/workorders/1/flows",
            json={
                "action": "resolve",
                "comment": "问题已解决",
            },
            headers=admin_headers
        )
        
        assert response.status_code == 200

    # ============== 辅助接口 ==============

    def test_get_workorder_categories(self, client, admin_headers):
        """Given: 系统有工单分类
           When: 获取工单分类列表
           Then: 返回分类列表"""
        response = client.get(
            "/api/v1/workorders/categories",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    def test_get_workorder_priorities(self, client, admin_headers):
        """Given: 系统有优先级定义
           When: 获取工单优先级列表
           Then: 返回优先级列表"""
        response = client.get(
            "/api/v1/workorders/priorities",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    def test_get_workorder_stats_summary(self, client, admin_headers, mock_workorder_core):
        """Given: 系统有工单
           When: 获取工单统计摘要
           Then: 返回统计信息"""
        mock_workorder_core.return_value.list.return_value = ([], 0)
        
        response = client.get(
            "/api/v1/workorders/stats/summary",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "total" in data

    def test_get_workorder_trend(self, client, admin_headers, mock_workorder_core):
        """Given: 系统有工单
           When: 获取工单趋势
           Then: 返回趋势数据"""
        mock_workorder_core.return_value.list.return_value = ([], 0)
        
        response = client.get(
            "/api/v1/workorders/stats/trend?days=30",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "dates" in data
        assert "created" in data
        assert "resolved" in data

    # ============== 过滤测试 ==============

    def test_filter_by_creator(self, client, admin_headers, mock_workorder_core):
        """Given: 系统中有创建人工单
           When: 按创建人过滤
           Then: 返回指定创建人的工单"""
        mock_workorder_core.return_value.list.return_value = ([], 0)
        
        response = client.get(
            "/api/v1/workorders/?creator=admin",
            headers=admin_headers
        )
        
        assert response.status_code == 200

    def test_filter_by_device_id(self, client, admin_headers, mock_workorder_core):
        """Given: 系统中有关联设备的工单
           When: 按设备ID过滤
           Then: 返回指定设备的工单"""
        mock_workorder_core.return_value.list.return_value = ([], 0)
        
        response = client.get(
            "/api/v1/workorders/?device_id=1",
            headers=admin_headers
        )
        
        assert response.status_code == 200

    def test_filter_by_date_range(self, client, admin_headers, mock_workorder_core):
        """Given: 系统中有日期范围内的工单
           When: 按日期范围过滤
           Then: 返回指定日期范围的工单"""
        mock_workorder_core.return_value.list.return_value = ([], 0)
        
        response = client.get(
            "/api/v1/workorders/?start_date=2024-01-01T00:00:00&end_date=2024-01-31T23:59:59",
            headers=admin_headers
        )
        
        assert response.status_code == 200

    def test_filter_by_keyword(self, client, admin_headers, mock_workorder_core):
        """Given: 系统中有包含关键词的工单
           When: 按关键词搜索
           Then: 返回匹配的工单"""
        mock_workorder_core.return_value.list.return_value = ([], 0)
        
        response = client.get(
            "/api/v1/workorders/?keyword=服务器",
            headers=admin_headers
        )
        
        assert response.status_code == 200

    # ============== 权限测试 ==============

    def test_operator_can_create_workorder(self, client, operator_headers, f, mock_workorder_core):
        """Given: 操作员已认证
           When: 创建工单
           Then: 返回创建的工单"""
        mock_workorder_core.return_value.create.return_value = MagicMock(
            id=1,
            order_no="WO-2024-0001",
            title="操作员工单",
            status=MagicMock(value="pending"),
            priority=MagicMock(value="P3"),
            order_type=MagicMock(value="fault"),
            creator="operator",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        
        response = client.post(
            "/api/v1/workorders/",
            json={
                "order_type": "fault",
                "title": "操作员工单",
            },
            headers=operator_headers
        )
        
        assert response.status_code == 200

    def test_viewer_cannot_create_workorder(self, client, viewer_headers, f, mock_workorder_core):
        """Given: 访客已认证
           When: 创建工单
           Then: 返回403"""
        response = client.post(
            "/api/v1/workorders/",
            json={
                "order_type": "fault",
                "title": "访客工单",
            },
            headers=viewer_headers
        )
        
        assert response.status_code == 403

    # ============== 类型验证 ==============

    def test_create_workorder_invalid_type(self, client, admin_headers, f, mock_workorder_core):
        """Given: 无效的工单类型
           When: 创建工单
           Then: 返回422验证错误"""
        response = client.post(
            "/api/v1/workorders/",
            json={
                "order_type": "invalid_type",
                "title": "测试工单",
            },
            headers=admin_headers
        )
        
        assert response.status_code == 422

    def test_create_workorder_invalid_priority(self, client, admin_headers, f, mock_workorder_core):
        """Given: 无效的优先级
           When: 创建工单
           Then: 返回422验证错误"""
        response = client.post(
            "/api/v1/workorders/",
            json={
                "order_type": "fault",
                "title": "测试工单",
                "priority": "P5",
            },
            headers=admin_headers
        )
        
        assert response.status_code == 422

    def test_create_workorder_title_too_long(self, client, admin_headers, f, mock_workorder_core):
        """Given: 标题过长
           When: 创建工单
           Then: 返回422验证错误"""
        response = client.post(
            "/api/v1/workorders/",
            json={
                "order_type": "fault",
                "title": "A" * 300,
            },
            headers=admin_headers
        )
        
        assert response.status_code == 422
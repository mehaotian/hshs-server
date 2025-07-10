from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from typing import Optional, List, Dict, Any

from app.core.database import Base


class Department(Base):
    """部门模型"""
    __tablename__ = "departments"
    __table_args__ = {'comment': '部门信息表'}
    
    # 部门状态常量
    STATUS_ACTIVE = 1      # 启用
    STATUS_INACTIVE = 0    # 禁用
    STATUS_DELETED = -1    # 删除

    id = Column(Integer, primary_key=True, index=True, comment="部门ID")
    name = Column(String(100), nullable=False, comment="部门名称")
    parent_id = Column(Integer, ForeignKey('departments.id'), nullable=True, comment="上级部门ID")
    manager_id = Column(Integer, ForeignKey('users.id'), nullable=True, comment="负责人ID")
    manager_name = Column(String(100), nullable=True, comment="负责人姓名")
    manager_phone = Column(String(20), nullable=True, comment="负责人手机号")
    manager_email = Column(String(100), nullable=True, comment="负责人邮箱")
    description = Column(Text, nullable=True, comment="部门描述")
    sort_order = Column(Integer, default=0, comment="排序序号")
    status = Column(Integer, default=1, comment="部门状态：1-启用，0-禁用，-1-删除")
    level = Column(Integer, default=1, comment="部门层级")
    path = Column(String(500), nullable=True, comment="部门路径，如：1/2/3")
    remarks = Column(Text, nullable=True, comment="备注信息")
    
    # 时间戳字段
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")

    # 关系映射
    parent = relationship("Department", remote_side=[id], back_populates="children")
    children = relationship("Department", back_populates="parent", cascade="all, delete-orphan")
    manager = relationship("User", foreign_keys=[manager_id])
    
    # 部门成员关系（通过中间表）
    members = relationship("DepartmentMember", back_populates="department", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Department(id={self.id}, name='{self.name}', parent_id={self.parent_id})>"
    
    @property
    def is_active(self) -> bool:
        """检查部门是否激活"""
        return self.status == self.STATUS_ACTIVE
    
    @property
    def is_root(self) -> bool:
        """检查是否为根部门"""
        return self.parent_id is None
    
    def get_full_name(self) -> str:
        """获取部门全名（包含层级路径）"""
        if self.is_root:
            return self.name
        # 这里需要递归获取父部门名称，实际使用时可能需要优化
        return f"{self.parent.get_full_name() if self.parent else ''}/{self.name}"
    
    def update_path(self) -> None:
        """更新部门路径"""
        if self.is_root:
            self.path = str(self.id)
            self.level = 1
        else:
            parent_path = self.parent.path if self.parent else ""
            self.path = f"{parent_path}/{self.id}"
            self.level = (self.parent.level if self.parent else 0) + 1
    
    async def get_ancestors(self, db) -> List['Department']:
        """获取所有祖先部门"""
        if not self.path:
            return []
        
        from sqlalchemy import select
        ancestor_ids = [int(id_str) for id_str in self.path.split('/') if id_str.isdigit() and int(id_str) != self.id]
        
        if not ancestor_ids:
            return []
        
        result = await db.execute(
            select(Department)
            .where(Department.id.in_(ancestor_ids))
            .order_by(Department.level)
        )
        return result.scalars().all()
    
    async def get_descendants(self, db, include_self: bool = False) -> List['Department']:
        """获取所有后代部门"""
        from sqlalchemy import select
        
        if include_self:
            condition = Department.path.like(f"{self.path}%")
        else:
            condition = Department.path.like(f"{self.path}/%")
        
        result = await db.execute(
            select(Department)
            .where(condition)
            .where(Department.status != self.STATUS_DELETED)
            .order_by(Department.level, Department.sort_order)
        )
        return result.scalars().all()
    
    async def get_member_count(self, db) -> int:
        """获取部门成员数量"""
        from sqlalchemy import select, func
        
        result = await db.execute(
            select(func.count(DepartmentMember.id))
            .where(DepartmentMember.department_id == self.id)
            .where(DepartmentMember.status == DepartmentMember.STATUS_ACTIVE)
        )
        return result.scalar() or 0
    
    async def to_dict(self, db=None, include_children: bool = False, include_members: bool = False) -> Dict[str, Any]:
        """转换为字典格式"""
        data = {
            'id': self.id,
            'name': self.name,
            'parent_id': self.parent_id,
            'manager_id': self.manager_id,
            'manager_name': self.manager_name,
            'manager_phone': self.manager_phone,
            'manager_email': self.manager_email,
            'description': self.description,
            'sort_order': self.sort_order,
            'status': self.status,
            'level': self.level,
            'path': self.path,
            'remarks': self.remarks,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_active': self.is_active,
            'is_root': self.is_root,
        }
        
        # 添加管理员信息
        if self.manager:
            data['manager'] = {
                'id': self.manager.id,
                'username': self.manager.username,
                'real_name': self.manager.real_name,
                'display_name': self.manager.display_name
            }
        
        # 添加成员数量
        if db:
            data['member_count'] = await self.get_member_count(db)
        
        # 添加子部门
        if include_children and self.children:
            data['children'] = [await child.to_dict(db, include_children=True) for child in self.children if child.is_active]
        
        # 添加成员列表
        if include_members and db:
            from sqlalchemy import select
            from app.models.user import User
            
            result = await db.execute(
                select(User)
                .join(DepartmentMember, User.id == DepartmentMember.user_id)
                .where(DepartmentMember.department_id == self.id)
                .where(DepartmentMember.status == DepartmentMember.STATUS_ACTIVE)
            )
            members = result.scalars().all()
            data['members'] = [{
                'id': member.id,
                'username': member.username,
                'real_name': member.real_name,
                'display_name': member.display_name,
                'avatar_url': member.avatar_url
            } for member in members]
        
        return data


class DepartmentMember(Base):
    """部门成员关联表"""
    __tablename__ = "department_members"
    __table_args__ = {'comment': '部门成员关联表'}
    
    # 成员状态常量
    STATUS_ACTIVE = 1      # 在职
    STATUS_INACTIVE = 0    # 离职
    STATUS_TRANSFERRED = 2 # 调岗

    id = Column(Integer, primary_key=True, index=True, comment="关联ID")
    department_id = Column(Integer, ForeignKey('departments.id'), nullable=False, comment="部门ID")
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, comment="用户ID")
    position = Column(String(100), nullable=True, comment="职位")
    is_manager = Column(Boolean, default=False, comment="是否为部门负责人")
    status = Column(Integer, default=1, comment="成员状态：1-在职，0-离职，2-调岗")
    joined_at = Column(DateTime, default=func.now(), comment="加入时间")
    left_at = Column(DateTime, nullable=True, comment="离开时间")
    remarks = Column(Text, nullable=True, comment="备注信息")
    
    # 时间戳字段
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")

    # 关系映射
    department = relationship("Department", back_populates="members")
    user = relationship("User")
    
    def __repr__(self) -> str:
        return f"<DepartmentMember(department_id={self.department_id}, user_id={self.user_id}, position='{self.position}')>"
    
    @property
    def is_active(self) -> bool:
        """检查成员是否在职"""
        return self.status == self.STATUS_ACTIVE
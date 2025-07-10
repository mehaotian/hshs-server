from .user import User, UserProfile
from .role import Role, UserRole, Permission
from .script import DramaSociety, Script, ScriptChapter, ScriptAssignment
from .audio import CVRecording, ReviewRecord, FeedbackRecord, AudioTemplate
from .department import Department, DepartmentMember

__all__ = [
    # 用户相关
    "User",
    "UserProfile",
    
    # 角色权限相关
    "Role",
    "UserRole",
    "Permission",
    
    # 剧本相关
    "DramaSociety",
    "Script",
    "ScriptChapter",
    "ScriptAssignment",
    
    # 音频相关
    "CVRecording",
    "ReviewRecord",
    "FeedbackRecord",
    "AudioTemplate",
    
    # 部门相关
    "Department",
    "DepartmentMember",
]
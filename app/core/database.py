from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.pool import NullPool
from typing import AsyncGenerator
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

# 创建异步数据库引擎
if settings.DEBUG:
    # 开发环境使用NullPool，不设置连接池参数
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DATABASE_ECHO,
        poolclass=NullPool,
        future=True,
    )
else:
    # 生产环境使用连接池
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DATABASE_ECHO,
        pool_size=settings.DATABASE_POOL_SIZE,
        max_overflow=settings.DATABASE_MAX_OVERFLOW,
        future=True,
    )

# 创建异步会话工厂
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=True,
    autocommit=False,
)

# 创建基础模型类
Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """获取数据库会话的依赖注入函数"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"数据库会话错误: {e}")
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """初始化数据库表结构"""
    try:
        # 导入所有模型以确保它们被注册到Base.metadata
        from app.models import user, role, script, audio, department  # noqa
        
        async with engine.begin() as conn:
            # 创建所有表
            await conn.run_sync(Base.metadata.create_all)
            logger.info("数据库表结构初始化完成")
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        raise


async def close_db() -> None:
    """关闭数据库连接"""
    await engine.dispose()
    logger.info("数据库连接已关闭")


class DatabaseManager:
    """数据库管理器类，提供便捷的数据库操作方法"""
    
    def __init__(self):
        self.engine = engine
        self.session_factory = AsyncSessionLocal
    
    async def get_session(self) -> AsyncSession:
        """获取数据库会话"""
        return self.session_factory()
    
    async def execute_raw_sql(self, sql: str, params: dict = None):
        """执行原生SQL语句"""
        async with self.session_factory() as session:
            try:
                result = await session.execute(sql, params or {})
                await session.commit()
                return result
            except Exception as e:
                await session.rollback()
                logger.error(f"执行SQL失败: {sql}, 错误: {e}")
                raise
    
    async def health_check(self) -> bool:
        """数据库健康检查"""
        try:
            async with self.session_factory() as session:
                await session.execute("SELECT 1")
                return True
        except Exception as e:
            logger.error(f"数据库健康检查失败: {e}")
            return False


# 创建全局数据库管理器实例
db_manager = DatabaseManager()
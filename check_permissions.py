import asyncio
from app.database import get_db
from sqlalchemy import text

async def check_data():
    async for db in get_db():
        # 检查权限分类
        result = await db.execute(text(
            'SELECT id, name, display_name, level, is_category FROM permissions WHERE is_category = 1 ORDER BY sort_order'
        ))
        rows = result.fetchall()
        print('权限分类:')
        for row in rows:
            print(f'ID: {row[0]}, Name: {row[1]}, Display: {row[2]}, Level: {row[3]}, Category: {row[4]}')
        
        # 检查已分类的权限数量
        result2 = await db.execute(text('SELECT COUNT(*) FROM permissions WHERE parent_id IS NOT NULL'))
        count = result2.scalar()
        print(f'\n已分类的权限数量: {count}')
        
        # 检查一些具体的权限分类情况
        result3 = await db.execute(text(
            'SELECT name, display_name, parent_id, level FROM permissions WHERE parent_id IS NOT NULL LIMIT 10'
        ))
        child_rows = result3.fetchall()
        print('\n部分已分类权限:')
        for row in child_rows:
            print(f'Name: {row[0]}, Display: {row[1]}, Parent ID: {row[2]}, Level: {row[3]}')
        
        break

if __name__ == '__main__':
    asyncio.run(check_data())
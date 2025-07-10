import asyncio
from app.core.database import get_db
from sqlalchemy import text

async def check_data():
    async for db in get_db():
        # 查看系统角色
        result = await db.execute(text('SELECT id, name, display_name FROM roles ORDER BY id'))
        roles = result.fetchall()
        print('系统角色:')
        for role in roles:
            print(f'  ID: {role.id}, Name: {role.name}, Display: {role.display_name}')
        
        # 查看用户列表
        result2 = await db.execute(text('SELECT id, username, email FROM users ORDER BY id'))
        users = result2.fetchall()
        print('\n用户列表:')
        for user in users:
            print(f'  ID: {user.id}, Username: {user.username}, Email: {user.email}')
        
        # 查看用户角色关联
        result3 = await db.execute(text('''
            SELECT ur.user_id, ur.role_id, u.username, r.name as role_name 
            FROM user_roles ur 
            JOIN users u ON ur.user_id = u.id 
            JOIN roles r ON ur.role_id = r.id 
            ORDER BY ur.user_id
        '''))
        user_roles = result3.fetchall()
        print('\n用户角色关联:')
        if user_roles:
            for ur in user_roles:
                print(f'  用户: {ur.username} (ID: {ur.user_id}) -> 角色: {ur.role_name} (ID: {ur.role_id})')
        else:
            print('  暂无用户角色关联')
        
        break

if __name__ == "__main__":
    asyncio.run(check_data())
from xiaozhi_mcp.database import Database, SQLiteCRUD
from xiaozhi_mcp.models import Task, User


def main() -> None:
    """Example usage of CRUD operations."""
    # Create in-memory database
    db = Database(':memory:')

    # Create repositories
    users = SQLiteCRUD(db, User)
    tasks = SQLiteCRUD(db, Task)

    # Create users
    user1 = users.create(User(name='Alice', email='alice@example.com', age=30))
    user2 = users.create(User(name='Bob', email='bob@example.com', age=25))
    print(f'Created users: {user1}, {user2}')

    # Create tasks
    task1 = tasks.create(Task(title='Learn Python', description='Study CRUD', user_id=user1.id))
    task2 = tasks.create(Task(title='Build app', description='Create MCP', user_id=user1.id))
    print(f'Created tasks: {task1}, {task2}')

    # Read
    print(f'\nAll users: {users.get_all()}')
    print(f'User by id: {users.get(1)}')

    # Update
    user1.age = 31
    users.update(user1)
    print(f'\nUpdated user: {users.get(1)}')

    # Find by field
    alice_tasks = tasks.find_by(user_id=user1.id)
    print(f"\nAlice's tasks: {alice_tasks}")

    # Count and exists
    print(f'\nTotal users: {users.count()}')
    print(f'User 1 exists: {users.exists(1)}')

    # Delete
    users.delete(user2.id)
    print(f'\nAfter delete: {users.get_all()}')

    db.close()


if __name__ == '__main__':
    main()

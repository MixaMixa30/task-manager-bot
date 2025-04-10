"""add_categories_and_critical_priority

Revision ID: 4f7a6a5f1c3e
Revises: f869c4a39ba6
Create Date: 2024-06-18 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import datetime
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = '4f7a6a5f1c3e'
down_revision = 'f869c4a39ba6'  # ID последней миграции
branch_labels = None
depends_on = None


def upgrade():
    # Проверяем, существует ли таблица task_categories
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    tables = inspector.get_table_names()
    
    # 1. Создаем таблицу категорий, если она не существует
    if 'task_categories' not in tables:
        op.create_table(
            'task_categories',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(length=50), nullable=False),
            sa.Column('color', sa.String(length=20), nullable=False, server_default='#808080'),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text("(datetime('now'))")),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_task_categories_user_id'), 'task_categories', ['user_id'], unique=False)
    
    # 2. Проверяем, есть ли уже столбец category_id в таблице tasks
    has_category_id = False
    for column in inspector.get_columns('tasks'):
        if column['name'] == 'category_id':
            has_category_id = True
            break
    
    # Добавляем столбец category_id в таблицу tasks, если он не существует
    if not has_category_id:
        # Для SQLite используем batch операции
        with op.batch_alter_table('tasks') as batch_op:
            batch_op.add_column(sa.Column('category_id', sa.Integer(), nullable=True))
            batch_op.create_foreign_key(
                'fk_tasks_category_id',
                'task_categories',
                ['category_id'], ['id'],
                ondelete='SET NULL'
            )
    
    # 3. В SQLite нельзя напрямую изменить тип перечисления
    # Для работы с критическим приоритетом достаточно знать, что оно добавлено в модели
    op.execute("-- Added new value 'critical' to TaskPriority enum in the model")


def downgrade():
    # 1. Удаляем внешний ключ и столбец category_id
    with op.batch_alter_table('tasks') as batch_op:
        batch_op.drop_constraint('fk_tasks_category_id', type_='foreignkey')
        batch_op.drop_column('category_id')
    
    # 2. Удаляем таблицу категорий
    op.drop_index(op.f('ix_task_categories_user_id'), table_name='task_categories')
    op.drop_table('task_categories')
    
    # 3. Нельзя удалить значение из перечисления в SQLite
    op.execute("-- WARNING: Cannot remove value 'critical' from TaskPriority enum, manual intervention required") 
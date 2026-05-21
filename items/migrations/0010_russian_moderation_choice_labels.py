from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('items', '0009_item_moderation'),
    ]

    operations = [
        migrations.AlterField(
            model_name='item',
            name='status',
            field=models.CharField(
                choices=[
                    ('pending', 'На модерации'),
                    ('available', 'Опубликовано'),
                    ('unavailable', 'Недоступно'),
                    ('blocked', 'Заблокировано'),
                ],
                default='available',
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name='itemmoderationrequest',
            name='action',
            field=models.CharField(
                choices=[
                    ('create', 'Создание'),
                    ('update', 'Редактирование'),
                ],
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name='itemmoderationrequest',
            name='status',
            field=models.CharField(
                choices=[
                    ('pending', 'Ожидает рассмотрения'),
                    ('approved', 'Одобрена'),
                    ('rejected', 'Отклонена'),
                ],
                default='pending',
                max_length=20,
            ),
        ),
    ]

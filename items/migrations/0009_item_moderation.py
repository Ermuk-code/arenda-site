from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('items', '0008_rename_items_itemr_item_id_3f6d3c_idx_items_itemr_item_id_fe3bc0_idx_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='item',
            name='status',
            field=models.CharField(
                choices=[
                    ('pending', 'Pending moderation'),
                    ('available', 'Available'),
                    ('unavailable', 'Unavailable'),
                    ('blocked', 'Blocked'),
                ],
                default='available',
                max_length=20,
            ),
        ),
        migrations.CreateModel(
            name='ItemModerationRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(choices=[('create', 'Create'), ('update', 'Update')], max_length=20)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')], default='pending', max_length=20)),
                ('item_snapshot', models.JSONField(blank=True, default=dict)),
                ('user_snapshot', models.JSONField(blank=True, default=dict)),
                ('rejection_reason', models.TextField(blank=True)),
                ('reviewed_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('item', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='moderation_requests', to='items.item')),
                ('reviewed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reviewed_item_moderation_requests', to=settings.AUTH_USER_MODEL)),
                ('submitted_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='item_moderation_requests', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
                'indexes': [
                    models.Index(fields=['status', '-created_at'], name='items_itemm_status_d99610_idx'),
                    models.Index(fields=['submitted_by', '-created_at'], name='items_itemm_submitt_e38cdc_idx'),
                    models.Index(fields=['item', 'status'], name='items_itemm_item_id_534a11_idx'),
                ],
            },
        ),
    ]

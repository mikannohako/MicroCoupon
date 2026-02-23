from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('microcoupon', '0004_alter_card_status_activitylog'),
    ]

    operations = [
        migrations.CreateModel(
            name='TemporaryCardCode',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(db_index=True, max_length=4, verbose_name='一時コード')),
                ('expires_at', models.DateTimeField(db_index=True, verbose_name='有効期限')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='作成日時')),
                ('card', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='temporary_codes', to='microcoupon.card', verbose_name='カード')),
            ],
            options={
                'verbose_name': 'カード一時コード',
                'verbose_name_plural': 'カード一時コード',
                'ordering': ['-created_at'],
            },
        ),
    ]

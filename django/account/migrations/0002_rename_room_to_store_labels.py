from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='room',
            options={
                'ordering': ['display_order', 'name'],
                'verbose_name': '店舗',
                'verbose_name_plural': '店舗',
            },
        ),
        migrations.AlterField(
            model_name='room',
            name='name',
            field=models.CharField(max_length=100, verbose_name='店舗名'),
        ),
        migrations.AlterField(
            model_name='user',
            name='room',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                related_name='users',
                to='account.room',
                verbose_name='所属店舗',
            ),
        ),
    ]

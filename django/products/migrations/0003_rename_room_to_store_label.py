from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0002_rename_room_to_store_labels'),
        ('products', '0002_alter_product_options_alter_product_unique_together_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='product',
            name='room',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='products',
                to='account.room',
                verbose_name='店舗',
            ),
        ),
    ]

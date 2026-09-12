from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [('sales', '0002_alter_invoice_status')]
    operations = [migrations.AddField(
        model_name='invoice', name='payment_status',
        field=models.CharField(choices=[('unpaid', 'دریافت نشده'), ('partial', 'دریافت ناقص'), ('paid', 'تسویه شده')], db_index=True, default='unpaid', max_length=12),
    )]

# Generated by Django 5.1.1 on 2025-02-18 21:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='transaction',
            name='mode_of_transaction',
            field=models.CharField(choices=[('Cash', 'Cash'), ('Bank transfer', 'Bank Transfer'), ('PhonePe', 'PhonePe'), ('Gpay', 'Gpay'), ('Paytm', 'Paytm')], default=1, max_length=20),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='transaction',
            name='category',
            field=models.CharField(default='Other', max_length=50),
        ),
        migrations.AlterField(
            model_name='transaction',
            name='date',
            field=models.DateTimeField(),
        ),
        migrations.AlterField(
            model_name='transaction',
            name='transaction_type',
            field=models.CharField(choices=[('Income', 'Income'), ('Expense', 'Expense')], max_length=10),
        ),
    ]

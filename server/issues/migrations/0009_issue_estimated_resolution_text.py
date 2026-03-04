from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("issues", "0008_merge_20260302_1720"),
    ]

    operations = [
        migrations.AddField(
            model_name="issue",
            name="estimated_resolution_text",
            field=models.CharField(
                blank=True,
                help_text='Human-friendly ETA, e.g. "2–3 business days"',
                max_length=255,
            ),
        ),
    ]


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("issues", "0006_add_soft_delete_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="issue",
            name="is_anonymous",
            field=models.BooleanField(
                default=False,
                help_text="If true, reporter identity is hidden from non-superusers.",
            ),
        ),
    ]


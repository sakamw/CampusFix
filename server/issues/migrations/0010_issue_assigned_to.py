from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("issues", "0009_issue_estimated_resolution_text"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="issue",
            name="assigned_to",
            field=models.ForeignKey(
                blank=True,
                help_text="Staff member currently responsible for this issue",
                null=True,
                on_delete=models.deletion.SET_NULL,
                related_name="assigned_issues",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]


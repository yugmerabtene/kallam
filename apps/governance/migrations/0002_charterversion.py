from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("governance", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="CharterVersion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("version", models.CharField(max_length=20)),
                ("published_at", models.DateTimeField(auto_now_add=True)),
                ("is_current", models.BooleanField(default=True)),
            ],
            options={"ordering": ["-published_at"]},
        ),
    ]

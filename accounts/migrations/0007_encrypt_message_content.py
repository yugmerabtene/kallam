"""
Migration état uniquement : la colonne DB reste TEXT mais Django utilise
désormais EncryptedTextField (chiffrement/déchiffrement transparent via Fernet).
"""
import accounts.encryption
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0006_conversation_message"),
    ]

    operations = [
        migrations.AlterField(
            model_name="message",
            name="content",
            field=accounts.encryption.EncryptedTextField(max_length=2000),
        ),
    ]

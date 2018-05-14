# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('activities', '0002_auto_20180508_0845'),
    ]

    operations = [
        migrations.AddField(
            model_name='track',
            name='file_sha1',
            field=models.CharField(max_length=40, null=True),
            preserve_default=True,
        ),
    ]

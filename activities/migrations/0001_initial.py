# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Activity',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=200)),
                ('comment', models.TextField(blank=True)),
                ('cadence_avg', models.IntegerField(null=True, blank=True)),
                ('cadence_max', models.IntegerField(null=True, blank=True)),
                ('calories', models.IntegerField(null=True, blank=True)),
                ('distance', models.DecimalField(null=True, max_digits=7, decimal_places=3, blank=True)),
                ('elevation_gain', models.IntegerField(null=True, blank=True)),
                ('elevation_loss', models.IntegerField(null=True, blank=True)),
                ('elevation_min', models.IntegerField(null=True, blank=True)),
                ('elevation_max', models.IntegerField(null=True, blank=True)),
                ('hf_max', models.IntegerField(null=True, verbose_name=b'hf_max', blank=True)),
                ('hf_avg', models.IntegerField(null=True, verbose_name=b'hf_avg', blank=True)),
                ('public', models.BooleanField(default=False)),
                ('speed_max', models.DecimalField(null=True, max_digits=4, decimal_places=1, blank=True)),
                ('speed_avg', models.DecimalField(null=True, max_digits=4, decimal_places=1, blank=True)),
                ('speed_avg_movement', models.DecimalField(null=True, max_digits=4, decimal_places=1, blank=True)),
                ('time_elapsed', models.IntegerField(null=True, blank=True)),
                ('time_movement', models.IntegerField(null=True, blank=True)),
                ('weather_stationname', models.CharField(max_length=200, null=True, blank=True)),
                ('weather_temp', models.DecimalField(null=True, max_digits=3, decimal_places=1, blank=True)),
                ('weather_rain', models.DecimalField(null=True, max_digits=3, decimal_places=1, blank=True)),
                ('weather_hum', models.IntegerField(null=True, blank=True)),
                ('weather_windspeed', models.DecimalField(null=True, max_digits=4, decimal_places=1, blank=True)),
                ('weather_winddir', models.CharField(max_length=20, null=True, blank=True)),
                ('date', models.DateTimeField(verbose_name=b'date')),
                ('time', models.IntegerField()),
            ],
            options={
                'verbose_name_plural': 'Activities',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ActivityTemplate',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=200)),
                ('comment', models.TextField(blank=True)),
                ('cadence_avg', models.IntegerField(null=True, blank=True)),
                ('cadence_max', models.IntegerField(null=True, blank=True)),
                ('calories', models.IntegerField(null=True, blank=True)),
                ('distance', models.DecimalField(null=True, max_digits=7, decimal_places=3, blank=True)),
                ('elevation_gain', models.IntegerField(null=True, blank=True)),
                ('elevation_loss', models.IntegerField(null=True, blank=True)),
                ('elevation_min', models.IntegerField(null=True, blank=True)),
                ('elevation_max', models.IntegerField(null=True, blank=True)),
                ('hf_max', models.IntegerField(null=True, verbose_name=b'hf_max', blank=True)),
                ('hf_avg', models.IntegerField(null=True, verbose_name=b'hf_avg', blank=True)),
                ('public', models.BooleanField(default=False)),
                ('speed_max', models.DecimalField(null=True, max_digits=4, decimal_places=1, blank=True)),
                ('speed_avg', models.DecimalField(null=True, max_digits=4, decimal_places=1, blank=True)),
                ('speed_avg_movement', models.DecimalField(null=True, max_digits=4, decimal_places=1, blank=True)),
                ('time_elapsed', models.IntegerField(null=True, blank=True)),
                ('time_movement', models.IntegerField(null=True, blank=True)),
                ('weather_stationname', models.CharField(max_length=200, null=True, blank=True)),
                ('weather_temp', models.DecimalField(null=True, max_digits=3, decimal_places=1, blank=True)),
                ('weather_rain', models.DecimalField(null=True, max_digits=3, decimal_places=1, blank=True)),
                ('weather_hum', models.IntegerField(null=True, blank=True)),
                ('weather_windspeed', models.DecimalField(null=True, max_digits=4, decimal_places=1, blank=True)),
                ('weather_winddir', models.CharField(max_length=20, null=True, blank=True)),
                ('date', models.DateTimeField(null=True, verbose_name=b'date', blank=True)),
                ('time', models.IntegerField(null=True, blank=True)),
            ],
            options={
                'verbose_name_plural': 'ActivityTemplates',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='CalorieFormula',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=200)),
                ('weight_dist_factor', models.FloatField(default=0.0)),
                ('weight_time_factor', models.FloatField(default=0.0)),
                ('public', models.BooleanField(default=False)),
                ('user', models.ForeignKey(blank=True, to=settings.AUTH_USER_MODEL, null=True)),
            ],
            options={
                'ordering': ['name'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Equipment',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=200)),
                ('description', models.TextField(blank=True)),
                ('distance', models.IntegerField(default=0, blank=True)),
                ('archived', models.BooleanField(default=False)),
                ('user', models.ForeignKey(blank=True, to=settings.AUTH_USER_MODEL, null=True)),
            ],
            options={
                'ordering': ['name'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Event',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=200)),
                ('user', models.ForeignKey(blank=True, to=settings.AUTH_USER_MODEL, null=True)),
            ],
            options={
                'ordering': ['name'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Lap',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('date', models.DateTimeField(verbose_name=b'date')),
                ('time', models.IntegerField()),
                ('distance', models.DecimalField(null=True, max_digits=6, decimal_places=3, blank=True)),
                ('speed_max', models.DecimalField(null=True, max_digits=4, decimal_places=1, blank=True)),
                ('speed_avg', models.DecimalField(null=True, max_digits=4, decimal_places=1, blank=True)),
                ('cadence_max', models.IntegerField(null=True, blank=True)),
                ('cadence_avg', models.IntegerField(null=True, blank=True)),
                ('calories', models.IntegerField(null=True, blank=True)),
                ('elevation_gain', models.IntegerField(null=True, blank=True)),
                ('elevation_loss', models.IntegerField(null=True, blank=True)),
                ('elevation_min', models.IntegerField(null=True, blank=True)),
                ('elevation_max', models.IntegerField(null=True, blank=True)),
                ('hf_max', models.IntegerField(null=True, verbose_name=b'hf_max', blank=True)),
                ('hf_avg', models.IntegerField(null=True, verbose_name=b'hf_avg', blank=True)),
                ('activity', models.ForeignKey(to='activities.Activity')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Sport',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=200)),
                ('color', models.CharField(max_length=10)),
                ('speed_as_pace', models.BooleanField(default=False)),
                ('calorie_formula', models.ForeignKey(blank=True, to='activities.CalorieFormula', null=True)),
                ('user', models.ForeignKey(blank=True, to=settings.AUTH_USER_MODEL, null=True)),
            ],
            options={
                'ordering': ['name'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Track',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('trackfile', models.FileField(upload_to=b'uploads/tracks/%Y/%m/%d')),
                ('preview_img', models.FileField(null=True, upload_to=b'uploads/previews/%Y/%m/%d')),
                ('filetype', models.CharField(max_length=10, null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='activitytemplate',
            name='calorie_formula',
            field=models.ForeignKey(blank=True, to='activities.CalorieFormula', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='activitytemplate',
            name='equipment',
            field=models.ManyToManyField(to='activities.Equipment', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='activitytemplate',
            name='event',
            field=models.ForeignKey(blank=True, to='activities.Event', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='activitytemplate',
            name='sport',
            field=models.ForeignKey(blank=True, to='activities.Sport', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='activitytemplate',
            name='track',
            field=models.ForeignKey(blank=True, to='activities.Track', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='activitytemplate',
            name='user',
            field=models.ForeignKey(blank=True, to=settings.AUTH_USER_MODEL, null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='activity',
            name='calorie_formula',
            field=models.ForeignKey(blank=True, to='activities.CalorieFormula', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='activity',
            name='equipment',
            field=models.ManyToManyField(to='activities.Equipment', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='activity',
            name='event',
            field=models.ForeignKey(to='activities.Event'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='activity',
            name='sport',
            field=models.ForeignKey(blank=True, to='activities.Sport', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='activity',
            name='track',
            field=models.ForeignKey(blank=True, to='activities.Track', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='activity',
            name='user',
            field=models.ForeignKey(blank=True, to=settings.AUTH_USER_MODEL, null=True),
            preserve_default=True,
        ),
    ]

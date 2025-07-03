import os
import subprocess
import sys
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Start Celery worker server'

    def add_arguments(self, parser):
        parser.add_argument(
            '--loglevel',
            default='INFO',
            help='Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)'
        )
        parser.add_argument(
            '--concurrency',
            type=int,
            default=None,
            help='Number of worker processes/threads'
        )
        parser.add_argument(
            '--beat',
            action='store_true',
            help='Run celery beat scheduler alongside worker'
        )
        parser.add_argument(
            '--queue',
            default='celery',
            help='Queue to consume from'
        )

    def handle(self, *args, **options):
        cmd = ['celery', '-A', 'zproject', 'worker']
        
        if options['loglevel']:
            cmd.extend(['--loglevel', options['loglevel']])
        
        if options['concurrency']:
            cmd.extend(['--concurrency', str(options['concurrency'])])
        
        if options['queue']:
            cmd.extend(['-Q', options['queue']])
        
        if options['beat']:
            cmd.extend(['--beat'])
        
        self.stdout.write(self.style.SUCCESS(f'Starting Celery worker: {" ".join(cmd)}'))
        
        try:
            subprocess.call(cmd)
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('Celery worker stopped'))
            sys.exit(0)

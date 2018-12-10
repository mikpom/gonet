import subprocess
from django.core.management.base import BaseCommand, CommandError

class Command(BaseCommand):
    help = 'Updates data files specified by parameter'

    def add_arguments(self, parser):
        parser.add_argument('data', type=str)

    def handle(self, *args, **options):
        data = args[0]
        if data == 'go':
            subprocess.check_call(["curl",  "-L", "http://purl.obolibrary.org/obo/go/go-basic.obo",  "|",  "gzip",  "-c",  ">",  "gg.obo.gz"], shell=True)
            self.stdout.write(self.style.SUCCESS('Successfully closed poll "%s"' % poll_id))

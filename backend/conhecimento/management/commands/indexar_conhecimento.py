from django.core.management.base import BaseCommand

from conhecimento.indexacao import indexar


class Command(BaseCommand):
    help = "Indexa data/conhecimento/*.md (trechos, full-text e embeddings)."

    def add_arguments(self, parser):
        parser.add_argument("--forcar", action="store_true", help="reindexa mesmo sem mudança")

    def handle(self, *args, **opts):
        r = indexar(forcar=opts["forcar"])
        self.stdout.write(f"indexados={r['indexados']} pulados={r['pulados']} removidos={r['removidos']}")

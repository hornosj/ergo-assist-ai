from django.core.management.base import BaseCommand

from catalogo.importacao import importar


class Command(BaseCommand):
    help = "Importa data/catalogo/cadeiras_*.json para o banco (idempotente)."

    def handle(self, *args, **opts):
        r = importar()
        self.stdout.write(
            f"criados={r['criados']} atualizados={r['atualizados']} removidos={r['removidos']}"
        )
        for erro in r["erros"]:
            self.stderr.write(f"AVISO: {erro}")

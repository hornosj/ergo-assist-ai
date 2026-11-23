import json
import time

from django.conf import settings
from django.core.management.base import BaseCommand

from evals.avaliacao import PASTA, relatorio_md, rodar


class Command(BaseCommand):
    help = "Roda as avaliações (busca, recomendação e, com --agente, o agente com LLM)."

    def add_arguments(self, parser):
        parser.add_argument("--agente", action="store_true", help="avalia o agente (usa OPENROUTER_APIKEY)")
        parser.add_argument("--juiz", action="store_true", help="LLM-as-judge nas respostas do agente")

    def handle(self, *args, **opts):
        if opts["agente"] and not settings.OPENROUTER_APIKEY:
            self.stderr.write("Sem OPENROUTER_APIKEY: o agente vai rodar no modo sem IA.")
        r = rodar(agente=opts["agente"], juiz=opts["juiz"])
        carimbo = time.strftime("%Y%m%d-%H%M")
        (PASTA / "resultados" / f"{carimbo}.json").write_text(
            json.dumps(r, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
        )
        md = relatorio_md(r)
        (PASTA / "RESULTADOS.md").write_text(md, encoding="utf-8")
        self.stdout.write(md)

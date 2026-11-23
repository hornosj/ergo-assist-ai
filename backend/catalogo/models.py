from django.db import models


class Cadeira(models.Model):
    """Uma cadeira real do mercado, com as medidas da fonte citada.

    Campo `None` = não confirmado na fonte (nunca estimado). O recomendador
    trata desconhecido como risco, não como "atende".
    """

    class Categoria(models.TextChoices):
        ESCRITORIO = "escritorio", "Escritório"
        GAMER = "gamer", "Gamer"
        EXECUTIVA = "executiva", "Executiva"
        OPERACIONAL = "operacional", "Operacional"

    class FaixaPreco(models.TextChoices):
        ECONOMICA = "economica", "Econômica (< R$ 1.000)"
        INTERMEDIARIA = "intermediaria", "Intermediária (R$ 1.000–2.500)"
        ALTA = "alta", "Alta (R$ 2.500–6.000)"
        PREMIUM = "premium", "Premium (> R$ 6.000)"

    slug = models.SlugField(max_length=120, unique=True)
    marca = models.CharField(max_length=80)
    modelo = models.CharField(max_length=120)
    variante = models.CharField(max_length=300, blank=True)
    categoria = models.CharField(max_length=20, choices=Categoria.choices)
    faixa_preco = models.CharField(max_length=20, choices=FaixaPreco.choices, blank=True)
    preco_referencia_brl = models.DecimalField(max_digits=9, decimal_places=2, null=True, blank=True)
    preco_fonte = models.URLField(max_length=600, blank=True)

    altura_assento_min_cm = models.FloatField(null=True, blank=True)
    altura_assento_max_cm = models.FloatField(null=True, blank=True)
    profundidade_assento_min_cm = models.FloatField(null=True, blank=True)
    profundidade_assento_max_cm = models.FloatField(null=True, blank=True)
    regula_profundidade_assento = models.BooleanField(null=True)
    largura_assento_cm = models.FloatField(null=True, blank=True)
    altura_encosto_cm = models.FloatField(null=True, blank=True)
    regula_altura_encosto = models.BooleanField(null=True)

    apoio_lombar = models.CharField(max_length=40, blank=True)
    bracos = models.CharField(max_length=20, blank=True)
    apoio_cabeca = models.CharField(max_length=20, blank=True)
    mecanismo = models.CharField(max_length=30, blank=True)
    regula_tensao_reclinacao = models.BooleanField(null=True)
    travas_reclinacao = models.PositiveSmallIntegerField(null=True, blank=True)
    material_assento = models.CharField(max_length=30, blank=True)
    material_encosto = models.CharField(max_length=30, blank=True)

    carga_maxima_kg = models.FloatField(null=True, blank=True)
    garantia_anos = models.FloatField(null=True, blank=True)
    certificacao_nbr13962 = models.BooleanField(null=True)
    altura_usuario_indicada_cm = models.JSONField(null=True, blank=True)

    fontes = models.JSONField(default=list)
    consultado_em = models.DateField(null=True, blank=True)
    campos_incertos = models.JSONField(default=list, blank=True)
    observacoes = models.TextField(blank=True)

    class Meta:
        ordering = ["marca", "modelo"]

    def __str__(self) -> str:
        return self.nome

    @property
    def nome(self) -> str:
        return f"{self.marca} {self.modelo}"

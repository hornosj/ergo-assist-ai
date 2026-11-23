from django.conf import settings
from django.db import models


class Perfil(models.Model):
    """Medidas e preferências de um usuário. Visível só para o dono."""

    dono = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="perfil")
    estatura_cm = models.FloatField()
    peso_kg = models.FloatField(null=True, blank=True)
    altura_poplitea_cm = models.FloatField(null=True, blank=True)
    comprimento_nadega_poplitea_cm = models.FloatField(null=True, blank=True)
    largura_quadril_cm = models.FloatField(null=True, blank=True)
    altura_mesa_cm = models.FloatField(null=True, blank=True)
    orcamento_brl = models.FloatField(null=True, blank=True)
    horas_por_dia = models.FloatField(null=True, blank=True)
    material_preferido = models.CharField(max_length=20, blank=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    CAMPOS_MEDIDA = [
        "estatura_cm",
        "peso_kg",
        "altura_poplitea_cm",
        "comprimento_nadega_poplitea_cm",
        "largura_quadril_cm",
        "altura_mesa_cm",
    ]

    def __str__(self) -> str:
        return f"Perfil de {self.dono}"

    def medidas_kwargs(self) -> dict:
        return {c: getattr(self, c) for c in self.CAMPOS_MEDIDA}

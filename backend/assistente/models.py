from django.conf import settings
from django.db import models

Usuario = settings.AUTH_USER_MODEL


class Conversa(models.Model):
    dono = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name="conversas")
    titulo = models.CharField(max_length=120, blank=True)
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criada_em"]
        permissions = [("usar_assistente", "Pode usar o assistente de IA")]

    def __str__(self) -> str:
        return self.titulo or f"Conversa {self.pk}"


class Mensagem(models.Model):
    class Papel(models.TextChoices):
        USUARIO = "user"
        ASSISTENTE = "assistant"

    conversa = models.ForeignKey(Conversa, on_delete=models.CASCADE, related_name="mensagens")
    papel = models.CharField(max_length=10, choices=Papel.choices)
    texto = models.TextField()
    modo = models.CharField(max_length=10, blank=True)  # ia | sem_ia
    modelo = models.CharField(max_length=120, blank=True)
    fontes = models.JSONField(default=list, blank=True)
    alertas = models.JSONField(default=list, blank=True)
    latencia_ms = models.PositiveIntegerField(null=True, blank=True)
    tokens_entrada = models.PositiveIntegerField(default=0)
    tokens_saida = models.PositiveIntegerField(default=0)
    custo_usd = models.DecimalField(max_digits=10, decimal_places=6, default=0)
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["criada_em", "id"]


class ChamadaFerramenta(models.Model):
    """Trilha de auditoria: toda ferramenta que o agente executou, por quem."""

    conversa = models.ForeignKey(Conversa, on_delete=models.CASCADE, related_name="chamadas")
    mensagem = models.ForeignKey(Mensagem, on_delete=models.SET_NULL, null=True, related_name="chamadas")
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    ferramenta = models.CharField(max_length=60)
    argumentos = models.JSONField(default=dict)
    resultado = models.JSONField(default=dict)
    ok = models.BooleanField(default=True)
    duracao_ms = models.PositiveIntegerField(default=0)
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["criada_em", "id"]


class ChamadaLLM(models.Model):
    """Custo e latência de cada ida ao modelo (base para os evals)."""

    conversa = models.ForeignKey(Conversa, on_delete=models.CASCADE, null=True, related_name="chamadas_llm")
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, null=True)
    modelo = models.CharField(max_length=120)
    tokens_entrada = models.PositiveIntegerField(default=0)
    tokens_saida = models.PositiveIntegerField(default=0)
    custo_usd = models.DecimalField(max_digits=10, decimal_places=6, default=0)
    latencia_ms = models.PositiveIntegerField(default=0)
    ok = models.BooleanField(default=True)
    erro = models.CharField(max_length=300, blank=True)
    criada_em = models.DateTimeField(auto_now_add=True)


class AcaoPendente(models.Model):
    """O agente não grava nada sozinho: ele propõe e o usuário confirma."""

    class Estado(models.TextChoices):
        PENDENTE = "pendente"
        CONFIRMADA = "confirmada"
        RECUSADA = "recusada"

    dono = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name="acoes")
    conversa = models.ForeignKey(Conversa, on_delete=models.CASCADE, related_name="acoes")
    tipo = models.CharField(max_length=40)  # salvar_perfil
    resumo = models.CharField(max_length=300)
    dados = models.JSONField(default=dict)
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.PENDENTE)
    criada_em = models.DateTimeField(auto_now_add=True)
    decidida_em = models.DateTimeField(null=True, blank=True)

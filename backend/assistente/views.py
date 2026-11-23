from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions, serializers, status
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from medidas.models import Perfil

from .agente import registrar_turno
from .ferramentas import PERMISSAO
from .models import AcaoPendente, ChamadaFerramenta, Conversa, Mensagem


class PodeUsarAssistente(permissions.BasePermission):
    message = "Sua conta não tem permissão para usar o assistente."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.has_perm(PERMISSAO))


# --- autenticação -------------------------------------------------------------


class CadastroSerializer(serializers.Serializer):
    username = serializers.RegexField(r"^[\w.@+-]{3,40}$")
    password = serializers.CharField(write_only=True)

    def validate_username(self, v):
        if get_user_model().objects.filter(username__iexact=v).exists():
            raise serializers.ValidationError("nome de usuário já existe")
        return v

    def validate_password(self, v):
        validate_password(v)
        return v


class CadastroView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "anon"

    @transaction.atomic
    def post(self, request):
        s = CadastroSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        user = get_user_model().objects.create_user(**s.validated_data)
        app, codename = PERMISSAO.split(".")
        user.user_permissions.add(Permission.objects.get(content_type__app_label=app, codename=codename))
        token = Token.objects.create(user=user)
        return Response({"token": token.key, "username": user.username}, status=status.HTTP_201_CREATED)


class EuView(APIView):
    def get(self, request):
        return Response({
            "username": request.user.username,
            "pode_usar_assistente": request.user.has_perm(PERMISSAO),
            "tem_perfil": Perfil.objects.filter(dono=request.user).exists(),
        })


# --- conversas ----------------------------------------------------------------


class MensagemSerializer(serializers.ModelSerializer):
    passos = serializers.SerializerMethodField()

    class Meta:
        model = Mensagem
        fields = ["id", "papel", "texto", "modo", "modelo", "fontes", "alertas", "latencia_ms",
                  "tokens_entrada", "tokens_saida", "criada_em", "passos"]

    def get_passos(self, m):
        return [
            {"ferramenta": c.ferramenta, "argumentos": c.argumentos, "ok": c.ok, "duracao_ms": c.duracao_ms}
            for c in m.chamadas.all()
        ]


def _acao_dict(a: AcaoPendente) -> dict:
    return {"id": a.pk, "tipo": a.tipo, "resumo": a.resumo, "estado": a.estado, "dados": a.dados}


class ConversasView(APIView):
    permission_classes = [PodeUsarAssistente]

    def get(self, request):
        conversas = Conversa.objects.filter(dono=request.user)[:50]
        return Response([{"id": c.pk, "titulo": c.titulo, "criada_em": c.criada_em} for c in conversas])

    def post(self, request):
        c = Conversa.objects.create(dono=request.user)
        return Response({"id": c.pk, "titulo": c.titulo, "criada_em": c.criada_em}, status=201)


class ConversaView(APIView):
    permission_classes = [PodeUsarAssistente]

    def get(self, request, pk):
        # Filtrar pelo dono = isolamento: conversa alheia é 404, não 403
        # (não revela nem que ela existe).
        c = get_object_or_404(Conversa, pk=pk, dono=request.user)
        mensagens = c.mensagens.prefetch_related("chamadas")
        return Response({
            "id": c.pk,
            "titulo": c.titulo,
            "mensagens": MensagemSerializer(mensagens, many=True).data,
            "acoes": [_acao_dict(a) for a in c.acoes.order_by("id")],
        })

    def delete(self, request, pk):
        get_object_or_404(Conversa, pk=pk, dono=request.user).delete()
        return Response(status=204)


class PerguntaSerializer(serializers.Serializer):
    texto = serializers.CharField(max_length=2000, trim_whitespace=True)


class MensagensView(APIView):
    permission_classes = [PodeUsarAssistente]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "assistente"

    def post(self, request, pk):
        c = get_object_or_404(Conversa, pk=pk, dono=request.user)
        s = PerguntaSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        _, msg, resultado = registrar_turno(request.user, c, s.validated_data["texto"])
        dados = MensagemSerializer(msg).data
        dados["acoes"] = resultado.acoes
        return Response(dados, status=201)


class AcaoView(APIView):
    """Confirmar/recusar o que o agente propôs. Só o dono decide."""

    permission_classes = [PodeUsarAssistente]

    @transaction.atomic
    def post(self, request, pk, decisao):
        if decisao not in ("confirmar", "recusar"):
            return Response(status=404)
        acao = get_object_or_404(AcaoPendente.objects.select_for_update(), pk=pk, dono=request.user)
        if acao.estado != AcaoPendente.Estado.PENDENTE:
            return Response({"erro": f"ação já {acao.estado}"}, status=409)
        if decisao == "confirmar":
            if acao.tipo == "salvar_perfil":
                Perfil.objects.update_or_create(dono=request.user, defaults=acao.dados)
            acao.estado = AcaoPendente.Estado.CONFIRMADA
        else:
            acao.estado = AcaoPendente.Estado.RECUSADA
        acao.decidida_em = timezone.now()
        acao.save()
        return Response(_acao_dict(acao))


class AuditoriaView(APIView):
    """As últimas chamadas de ferramenta do próprio usuário (rastreabilidade)."""

    permission_classes = [PodeUsarAssistente]

    def get(self, request):
        chamadas = ChamadaFerramenta.objects.filter(usuario=request.user).order_by("-id")[:100]
        return Response([
            {"id": c.pk, "conversa": c.conversa_id, "ferramenta": c.ferramenta, "argumentos": c.argumentos,
             "ok": c.ok, "duracao_ms": c.duracao_ms, "criada_em": c.criada_em}
            for c in chamadas
        ])

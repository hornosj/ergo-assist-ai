from rest_framework import permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .calculo import MedidaInvalida, calcular
from .models import Perfil
from .recomendacao import Necessidades, recomendar


class EntradaSerializer(serializers.Serializer):
    estatura_cm = serializers.FloatField()
    peso_kg = serializers.FloatField(required=False, allow_null=True)
    altura_poplitea_cm = serializers.FloatField(required=False, allow_null=True)
    comprimento_nadega_poplitea_cm = serializers.FloatField(required=False, allow_null=True)
    largura_quadril_cm = serializers.FloatField(required=False, allow_null=True)
    altura_mesa_cm = serializers.FloatField(required=False, allow_null=True)
    orcamento_brl = serializers.FloatField(required=False, allow_null=True)
    horas_por_dia = serializers.FloatField(required=False, allow_null=True)
    material_preferido = serializers.ChoiceField(
        choices=["tela", "espuma"], required=False, allow_null=True, allow_blank=True
    )
    incluir_gamer = serializers.BooleanField(required=False, default=False)
    quer_apoio_cabeca = serializers.BooleanField(required=False, default=False)
    limite = serializers.IntegerField(required=False, default=5, min_value=1, max_value=20)


def separar(dados: dict) -> tuple[dict, Necessidades, int]:
    medidas = {k: dados.get(k) for k in Perfil.CAMPOS_MEDIDA}
    nec = Necessidades(
        orcamento_brl=dados.get("orcamento_brl"),
        horas_por_dia=dados.get("horas_por_dia"),
        material_preferido=dados.get("material_preferido") or None,
        incluir_gamer=dados.get("incluir_gamer", False),
        quer_apoio_cabeca=dados.get("quer_apoio_cabeca", False),
    )
    return medidas, nec, dados.get("limite", 5)


class CalcularView(APIView):
    """POST medidas do corpo -> medidas ideais do posto + cadeiras recomendadas."""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        entrada = EntradaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        medidas_kw, nec, limite = separar(entrada.validated_data)
        try:
            m = calcular(**medidas_kw)
        except MedidaInvalida as exc:
            return Response({"erro": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        recs = recomendar(m, nec, limite=limite)
        return Response({"medidas": m.como_dict(), "recomendacoes": [r.como_dict() for r in recs]})


class PerfilSerializer(serializers.ModelSerializer):
    class Meta:
        model = Perfil
        exclude = ["id", "dono"]


class PerfilView(APIView):
    """O perfil do próprio usuário (nunca de outro)."""

    def get(self, request):
        perfil = Perfil.objects.filter(dono=request.user).first()
        if perfil is None:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(PerfilSerializer(perfil).data)

    def put(self, request):
        perfil = Perfil.objects.filter(dono=request.user).first()
        s = PerfilSerializer(perfil, data=request.data)
        s.is_valid(raise_exception=True)
        try:
            calcular(**{k: s.validated_data.get(k) for k in Perfil.CAMPOS_MEDIDA})
        except MedidaInvalida as exc:
            return Response({"erro": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        s.save(dono=request.user)
        return Response(s.data)

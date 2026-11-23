from rest_framework import serializers

from .models import Cadeira


class CadeiraSerializer(serializers.ModelSerializer):
    nome = serializers.CharField(read_only=True)

    class Meta:
        model = Cadeira
        exclude = ["id"]

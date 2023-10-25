from pprint import pprint as pp
from typing import Required

from pkg_resources import require
from .models import *
from rest_framework import serializers

# created by todo.org tangle
# Create your serializers here.

from os import read
from pprint import pprint as pp
from .models import *
from rest_framework import serializers


# created by todo.org tangle
# Create your serializers here.
class StorageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Storage
        fields = "__all__"


class StorageSlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = StorageSlot
        fields = "__all__"


class ManufacturerNameSerializer(serializers.ModelSerializer):
    name = serializers.CharField(max_length=255)

    class Meta:
        fields = ["name"]
        model = Manufacturer


class ManufacturerSerializer(serializers.ModelSerializer):
    name = serializers.CharField(max_length=255)

    class Meta:
        model = Manufacturer
        fields = ["name"]


class ProviderNameSerializer(serializers.ModelSerializer):
    name = serializers.CharField(max_length=255)

    class Meta:
        fields = ["name"]
        model = Provider


class ProviderSerializer(serializers.ModelSerializer):
    class Meta:
        fields = ["name"]
        model = Provider


class ArticleNameSerializer(serializers.ModelSerializer):
    name = serializers.CharField(max_length=255)

    class Meta:
        fields = ["name"]
        model = Article


class ArticleProviderSerializer(serializers.ModelSerializer):
    name = serializers.PrimaryKeyRelatedField(queryset=Provider.objects.all())
    description = serializers.CharField(max_length=255, required=False)

    class Meta:
        model = ArticleProvider
        fields = ["name", "description"]


class ArticleSerializer(serializers.ModelSerializer):
    manufacturer = ManufacturerSerializer(required=False, allow_null=True)
    providers = ArticleProviderSerializer(
        source="article.provider_set", many=True, required=False
    )

    class Meta:
        model = Article
        fields = [
            "name",
            "manufacturer",
            "manufacturer_description",
            "sap_number",
            "description",
            "providers",
        ]

    def create(self, validated_data):
        print(1, validated_data)
        if "manufacturer" in validated_data.keys():
            manufactuerdata = validated_data.pop("manufacturer")
            manufacturer, created = Manufacturer.objects.get_or_create(
                **manufactuerdata
            )
            validated_data["manufacturer"] = manufacturer

        if "providers" in validated_data.keys():
            print("Article Serializer found providers key")
            providersdata = validated_data.pop("providers")
            print(providersdata)
            for p in providersdata:
                print(p)
                provider, created = Provider.objects.get_or_create(**p)
                validated_data["providers"].append(provider)
        print(2, validated_data)
        article = Article.objects.create(**validated_data)
        return article

    def validate(self, *args, **kwargs):
        return super().validate(*args, **kwargs)


class BoardArticleSerializer(serializers.ModelSerializer):
    class Meta:
        model = BoardArticle
        fields = "__all__"

    def create(self, validated_data):
        # print("BoardArticel Serializer create:")
        # pp(validated_data)

        ba, created = BoardArticle.objects.update_or_create(
            article=validated_data.get("article", None),
            name=validated_data.get("name", None),
            count=validated_data.get("count", None),
            board=validated_data.get("board", None),
            carrier=validated_data.get("carrier", None),
        )
        return ba


class BoardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Board
        fields = "__all__"

    def create(self, validated_data):
        # print("BoardArticel Serializer create:")
        # pp(validated_data)

        ba, created = BoardArticle.objects.update_or_create(
            article=validated_data.get("article", None),
            name=validated_data.get("name", None),
            count=validated_data.get("count", None),
            board=validated_data.get("board", None),
            carrier=validated_data.get("carrier", None),
        )
        return ba


class BoardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Board
        fields = "__all__"


class CarrierNameSerializer(serializers.ModelSerializer):
    name = serializers.CharField(max_length=255)

    class Meta:
        fields = ["name"]
        model = Carrier


class CarrierSerializer(serializers.ModelSerializer):
    article = serializers.PrimaryKeyRelatedField(
        many=False, queryset=Article.objects.all()
    )
    article_description = serializers.CharField(
        source="article.description", required=False
    )

    article_manufacturer = serializers.CharField(
        source="article.manufacturer", required=False
    )
    article_manufacturer_description = serializers.CharField(
        source="article.manufacturer_description", required=False
    )

    article_sap_number = serializers.CharField(
        source="article.sap_number", required=False
    )

    article_providers = serializers.CharField(
        source="article.providers", required=False
    )

    class Meta:
        model = Carrier
        fields = "__all__"


class JobSerializer(serializers.ModelSerializer):
    class Meta:
        model = Job
        fields = "__all__"


class MachineSerializer(serializers.ModelSerializer):
    class Meta:
        model = Machine
        fields = "__all__"


class MachineSlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = MachineSlot
        fields = "__all__"

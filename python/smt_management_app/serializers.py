

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


class ArticleSerializer(serializers.ModelSerializer):
    manufacturer = ManufacturerSerializer(required=False, allow_null=True)
    provider1 = ProviderSerializer(required=False, allow_null=True)
    provider2 = ProviderSerializer(required=False, allow_null=True)
    provider3 = ProviderSerializer(required=False, allow_null=True)
    provider4 = ProviderSerializer(required=False, allow_null=True)
    provider5 = ProviderSerializer(required=False, allow_null=True)

    class Meta:
        model = Article
        fields = [
            "name",
            "manufacturer",
            "manufacturer_description",
            "provider1",
            "provider1_description",
            "provider2",
            "provider2_description",
            "provider3",
            "provider3_description",
            "provider4",
            "provider4_description",
            "provider5",
            "provider5_description",
            "sap_number",
            "description",
        ]

    def create(self, validated_data):
        if "manufacturer" in validated_data.keys():
            manufactuerdata = validated_data.pop("manufacturer")
            manufacturer, created = Manufacturer.objects.get_or_create(
                **manufactuerdata
            )
            validated_data["manufacturer"] = manufacturer

        if "provider1" in validated_data.keys():
            provider1data = validated_data.pop("provider1")
            provider1, created = Provider.objects.get_or_create(provider1data)
            validated_data["provider1"] = provider1
        if "provider2" in validated_data.keys():
            provider2data = validated_data.pop("provider2")
            provider2, created = Provider.objects.get_or_create(provider2data)
            validated_data["provider2"] = provider2
        if "provider3" in validated_data.keys():
            provider3data = validated_data.pop("provider3")
            provider3, created = Provider.objects.get_or_create(provider3data)
            validated_data["provider3"] = provider3
        if "provider4" in validated_data.keys():
            provider4data = validated_data.pop("provider4")
            provider4, created = Provider.objects.get_or_create(provider4data)
            validated_data["provider4"] = provider4
        if "provider5" in validated_data.keys():
            provider5data = validated_data.pop("provider5")
            provider5, created = Provider.objects.get_or_create(provider5data)
            validated_data["provider5"] = provider5

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

    article_provider1 = serializers.CharField(
        source="article.provider1", required=False
    )

    article_provider1_description = serializers.CharField(
        source="article.provider1_description", required=False
    )

    article_provider2 = serializers.CharField(
        source="article.provider2", required=False
    )
    article_provider2_description = serializers.CharField(
        source="article.provider2_description", required=False
    )

    article_provider3 = serializers.CharField(
        source="article.provider3", required=False
    )
    article_provider3_description = serializers.CharField(
        source="article.provider3_description", required=False
    )
    article_provider4 = serializers.CharField(
        source="article.provider4", required=False
    )
    article_provider4_description = serializers.CharField(
        source="article.provider4_description", required=False
    )
    article_provider5 = serializers.CharField(
        source="article.provider5", required=False
    )
    article_provider5_description = serializers.CharField(
        source="article.provider5_description", required=False
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

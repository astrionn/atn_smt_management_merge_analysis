from pprint import pprint as pp
from . models import *
from rest_framework import serializers
# created by todo.org tangle
# Create your serializers here.

from os import read
from pprint import pprint as pp
from . models import *
from rest_framework import serializers
# created by todo.org tangle
# Create your serializers here.
 
class ManufacturerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Manufacturer
        fields = "__all__"
class ProviderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Provider
        fields = "__all__"
class ArticleSerializer(serializers.ModelSerializer):
    manufacturer = ManufacturerSerializer(read_only=True)
    provider = ProviderSerializer(read_only=True)
    class Meta:
        model = Article
        fields = "__all__"

class BoardArticleSerializer(serializers.ModelSerializer):
    class Meta:
        model = BoardArticle
        fields = "__all__"

    def create(self, validated_data):
        #print("BoardArticel Serializer create:")
        #pp(validated_data)

        ba, created = BoardArticle.objects.update_or_create(
            article=validated_data.get('article',None),
            name=validated_data.get('name',None),
            count=validated_data.get('count',None),
            board=validated_data.get('board',None),
            carrier=validated_data.get('carrier',None),
            )
        return ba
class BoardSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Board
        fields = "__all__"

class CarrierSerializer(serializers.ModelSerializer):
    article = serializers.PrimaryKeyRelatedField(many=False,queryset=Article.objects.all())
    
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
class StorageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Storage
        fields = "__all__"
class StorageSlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = StorageSlot
        fields = "__all__"

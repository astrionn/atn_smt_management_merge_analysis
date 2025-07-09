from pprint import pprint as pp
from .models import (
    Article,
    Board,
    BoardArticle,
    Carrier,
    Job,
    Machine,
    MachineSlot,
    Manufacturer,
    Provider,
    Storage,
    StorageSlot,
)
from rest_framework import serializers

# created by todo.org tangle
# Create your serializers here.


class StorageSlotSerializer(serializers.ModelSerializer):
    # New fields for combined slots
    all_qr_codes = serializers.SerializerMethodField()
    all_slot_names = serializers.SerializerMethodField()
    is_combined = serializers.SerializerMethodField()
    combined_group_size = serializers.SerializerMethodField()

    class Meta:
        model = StorageSlot
        fields = [
            "id",
            "name",
            "storage",
            "led_state",
            "qr_value",
            "diameter",
            "width",
            # New fields
            "qr_codes",
            "related_names",
            "all_qr_codes",
            "all_slot_names",
            "is_combined",
            "combined_group_size",
        ]
        read_only_fields = [
            "all_qr_codes",
            "all_slot_names",
            "is_combined",
            "combined_group_size",
        ]

    def get_all_qr_codes(self, obj):
        """Return all QR codes for this slot including combined ones"""
        return obj.get_all_qr_codes()

    def get_all_slot_names(self, obj):
        """Return all slot names in the combined group"""
        return obj.get_all_slot_names()

    def get_is_combined(self, obj):
        """Return whether this slot is part of a combined group"""
        return obj.is_combined_slot()

    def get_combined_group_size(self, obj):
        """Return the number of slots in this combined group"""
        return len(obj.get_all_slot_names())


# Update the Storage serializer to include combined slots info
class StorageSerializer(serializers.ModelSerializer):
    total_slots = serializers.SerializerMethodField()
    free_slots = serializers.SerializerMethodField()
    occupied_slots = serializers.SerializerMethodField()
    logical_free_slots = serializers.SerializerMethodField()
    logical_total_slots = serializers.SerializerMethodField()

    class Meta:
        model = Storage
        fields = [
            "name",
            "capacity",
            "location",
            "device",
            "ATNPTL_shelf_id",
            "lighthouse_A_yellow",
            "lighthouse_B_yellow",
            "archived",
            "created_at",
            "updated_at",
            # New fields
            "total_slots",
            "free_slots",
            "occupied_slots",
            "logical_free_slots",
            "logical_total_slots",
        ]

    def get_total_slots(self, obj):
        """Physical slot count"""
        return obj.storageslot_set.count()

    def get_free_slots(self, obj):
        """Physical free slot count"""
        return obj.storageslot_set.filter(carrier__isnull=True).count()

    def get_occupied_slots(self, obj):
        """Physical occupied slot count"""
        return obj.storageslot_set.filter(carrier__isnull=False).count()

    def get_logical_free_slots(self, obj):
        """Logical free slot count (combined slots count as one)"""
        free_slots = obj.storageslot_set.filter(carrier__isnull=True)

        counted_slots = set()
        logical_count = 0

        for slot in free_slots:
            if slot.name in counted_slots:
                continue
            all_slot_names = slot.get_all_slot_names()
            counted_slots.update(all_slot_names)
            logical_count += 1

        return logical_count

    def get_logical_total_slots(self, obj):
        """Logical total slot count (combined slots count as one)"""
        all_slots = obj.storageslot_set.all()

        counted_slots = set()
        logical_count = 0

        for slot in all_slots:
            if slot.name in counted_slots:
                continue
            all_slot_names = slot.get_all_slot_names()
            counted_slots.update(all_slot_names)
            logical_count += 1

        return logical_count


# Update Carrier serializer to show combined slot info
class CarrierSerializer(serializers.ModelSerializer):
    storage_slot_info = serializers.SerializerMethodField()

    class Meta:
        model = Carrier
        fields = [
            "name",
            "article",
            "diameter",
            "width",
            "container_type",
            "quantity_original",
            "quantity_current",
            "lot_number",
            "reserved",
            "delivered",
            "collecting",
            "archived",
            "storage",
            "storage_slot",
            "storage_slot_qr_value",
            "machine_slot",
            "nominated_for_slot",
            "created_at",
            "updated_at",
            # New field
            "storage_slot_info",
        ]

    def get_storage_slot_info(self, obj):
        """Return detailed info about the storage slot including combined slots"""
        if not obj.storage_slot:
            return None

        slot = obj.storage_slot
        return {
            "primary_qr": slot.qr_value,
            "all_qr_codes": slot.get_all_qr_codes(),
            "slot_names": slot.get_all_slot_names(),
            "is_combined": slot.is_combined_slot(),
            "group_size": len(slot.get_all_slot_names()),
        }


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

    def create(self, validated_data, *args, **kwargs):
        print("in serialization manufacturer")
        print(validated_data)
        return super().create(validated_data, *args, **kwargs)


class ProviderNameSerializer(serializers.ModelSerializer):
    name = serializers.CharField(max_length=255)

    class Meta:
        model = Provider
        fields = ["name"]


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
    manufacturer = serializers.PrimaryKeyRelatedField(
        queryset=Manufacturer.objects.all(), required=False, allow_null=True
    )
    provider1 = serializers.PrimaryKeyRelatedField(
        queryset=Provider.objects.all(), required=False, allow_null=True
    )
    provider2 = serializers.PrimaryKeyRelatedField(
        queryset=Provider.objects.all(), required=False, allow_null=True
    )
    provider3 = serializers.PrimaryKeyRelatedField(
        queryset=Provider.objects.all(), required=False, allow_null=True
    )
    provider4 = serializers.PrimaryKeyRelatedField(
        queryset=Provider.objects.all(), required=False, allow_null=True
    )
    provider5 = serializers.PrimaryKeyRelatedField(
        queryset=Provider.objects.all(), required=False, allow_null=True
    )

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
            "created_at",
            "updated_at",
            "archived",
        ]

    def create(self, validated_data):
        # print("in serialization article")
        # print(validated_data)
        manufacturer_data = validated_data.pop("manufacturer", None)
        # print("m:    ", manufacturer_data)
        article, _ = Article.objects.get_or_create(**validated_data)
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


class StorageNameSerializer(serializers.ModelSerializer):
    name = serializers.CharField(max_length=255)

    class Meta:
        fields = ["name"]
        model = Storage


class StorageSlotNameSerializer(serializers.ModelSerializer):
    name = serializers.CharField(max_length=255)

    class Meta:
        fields = ["name"]
        model = StorageSlot


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

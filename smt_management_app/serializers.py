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


class StorageSerializer(serializers.ModelSerializer):
    # Physical slot counts
    total_physical = serializers.SerializerMethodField()
    free_physical = serializers.SerializerMethodField()
    occupied_physical = serializers.SerializerMethodField()

    # Logical slot counts (for display to users)
    total_logical = serializers.SerializerMethodField()
    free_logical = serializers.SerializerMethodField()
    occupied_logical = serializers.SerializerMethodField()

    # Keep old field names for backward compatibility
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
            # New preferred field names
            "total_physical",
            "free_physical",
            "occupied_physical",
            "total_logical",
            "free_logical",
            "occupied_logical",
            # Old field names for backward compatibility
            "total_slots",
            "free_slots",
            "occupied_slots",
            "logical_free_slots",
            "logical_total_slots",
        ]

    # Physical slot methods
    def get_total_physical(self, obj):
        """Total physical slot count"""
        return obj.storageslot_set.count()

    def get_free_physical(self, obj):
        """Physical free slot count"""
        return obj.storageslot_set.filter(carrier__isnull=True).count()

    def get_occupied_physical(self, obj):
        """Physical occupied slot count"""
        return obj.storageslot_set.filter(carrier__isnull=False).count()

    # Logical slot methods (combined slots count as one)
    def get_total_logical(self, obj):
        """Total logical slot count (combined slots count as one)"""
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

    def get_free_logical(self, obj):
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

    def get_occupied_logical(self, obj):
        """Logical occupied slot count (combined slots count as one)"""
        occupied_slots = obj.storageslot_set.filter(carrier__isnull=False)
        counted_slots = set()
        logical_count = 0

        for slot in occupied_slots:
            if slot.name in counted_slots:
                continue
            all_slot_names = slot.get_all_slot_names()
            counted_slots.update(all_slot_names)
            logical_count += 1

        return logical_count

    # Backward compatibility methods (delegate to new methods)
    def get_total_slots(self, obj):
        """Physical slot count (backward compatibility)"""
        return self.get_total_physical(obj)

    def get_free_slots(self, obj):
        """Physical free slot count (backward compatibility)"""
        return self.get_free_physical(obj)

    def get_occupied_slots(self, obj):
        """Physical occupied slot count (backward compatibility)"""
        return self.get_occupied_physical(obj)

    def get_logical_free_slots(self, obj):
        """Logical free slot count (backward compatibility)"""
        return self.get_free_logical(obj)

    def get_logical_total_slots(self, obj):
        """Logical total slot count (backward compatibility)"""
        return self.get_total_logical(obj)


# Update Carrier serializer to show combined slot info
class CarrierSerializer(serializers.ModelSerializer):
    storage_slot_info = serializers.SerializerMethodField()

    # Article-related fields that the frontend expects
    article__description = serializers.SerializerMethodField()
    article__manufacturer__name = serializers.SerializerMethodField()
    article__manufacturer_description = serializers.SerializerMethodField()
    article__sap_number = serializers.SerializerMethodField()
    article__provider1__name = serializers.SerializerMethodField()
    article__provider1_description = serializers.SerializerMethodField()
    article__provider2__name = serializers.SerializerMethodField()
    article__provider2_description = serializers.SerializerMethodField()
    article__provider3__name = serializers.SerializerMethodField()
    article__provider3_description = serializers.SerializerMethodField()
    article__provider4__name = serializers.SerializerMethodField()
    article__provider4_description = serializers.SerializerMethodField()
    article__provider5__name = serializers.SerializerMethodField()
    article__provider5_description = serializers.SerializerMethodField()

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
            # Article-related fields
            "article__description",
            "article__manufacturer__name",
            "article__manufacturer_description",
            "article__sap_number",
            "article__provider1__name",
            "article__provider1_description",
            "article__provider2__name",
            "article__provider2_description",
            "article__provider3__name",
            "article__provider3_description",
            "article__provider4__name",
            "article__provider4_description",
            "article__provider5__name",
            "article__provider5_description",
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

    def get_article__description(self, obj):
        """Return article description"""
        return obj.article.description if obj.article else None

    def get_article__manufacturer__name(self, obj):
        """Return article manufacturer name"""
        return (
            obj.article.manufacturer.name
            if obj.article and obj.article.manufacturer
            else None
        )

    def get_article__manufacturer_description(self, obj):
        """Return article manufacturer description"""
        return obj.article.manufacturer_description if obj.article else None

    def get_article__sap_number(self, obj):
        """Return article SAP number"""
        return obj.article.sap_number if obj.article else None

    def get_article__provider1__name(self, obj):
        """Return article provider1 name"""
        return (
            obj.article.provider1.name
            if obj.article and obj.article.provider1
            else None
        )

    def get_article__provider1_description(self, obj):
        """Return article provider1 description"""
        return obj.article.provider1_description if obj.article else None

    def get_article__provider2__name(self, obj):
        """Return article provider2 name"""
        return (
            obj.article.provider2.name
            if obj.article and obj.article.provider2
            else None
        )

    def get_article__provider2_description(self, obj):
        """Return article provider2 description"""
        return obj.article.provider2_description if obj.article else None

    def get_article__provider3__name(self, obj):
        """Return article provider3 name"""
        return (
            obj.article.provider3.name
            if obj.article and obj.article.provider3
            else None
        )

    def get_article__provider3_description(self, obj):
        """Return article provider3 description"""
        return obj.article.provider3_description if obj.article else None

    def get_article__provider4__name(self, obj):
        """Return article provider4 name"""
        return (
            obj.article.provider4.name
            if obj.article and obj.article.provider4
            else None
        )

    def get_article__provider4_description(self, obj):
        """Return article provider4 description"""
        return obj.article.provider4_description if obj.article else None

    def get_article__provider5__name(self, obj):
        """Return article provider5 name"""
        return (
            obj.article.provider5.name
            if obj.article and obj.article.provider5
            else None
        )

    def get_article__provider5_description(self, obj):
        """Return article provider5 description"""
        return obj.article.provider5_description if obj.article else None


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
        # manufacturer_data = validated_data.pop("manufacturer", None)
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

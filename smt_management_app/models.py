import os
from django.db import models
from django.db.models import Q
from django.forms import ValidationError
from django.urls import reverse

# created by todo.org tangle
# Create your models here.

# this comment was appended to models.py by tangle !


class AbstractBaseModel(models.Model):
    name = models.CharField(
        primary_key=True, unique=True, max_length=50, null=False, blank=False
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    archived = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.name:
            raise ValueError("Name field must be set.")
        super().save(*args, **kwargs)

    class Meta:
        abstract = True
        ordering = ("name",)


class LocalFile(models.Model):
    def get_upload_path(self, filename):
        return os.path.join(self.upload_type, filename)

    UPLOAD_TYPE_CHOICES = [
        ("article", "Article"),
        ("carrier", "Carrier"),
        ("board", "Board"),
    ]
    DELIMITER_CHOICES = [(",", 0), (";", 1), ("\t", 2)]
    name = models.BigAutoField(primary_key=True, unique=True, null=False, blank=False)
    upload_type = models.CharField(
        max_length=50, choices=UPLOAD_TYPE_CHOICES, null=False, blank=False
    )
    file_object = models.FileField(upload_to=get_upload_path)
    headers = models.CharField(max_length=5000, null=True, blank=True)
    board_name = models.CharField(max_length=5000, null=True, blank=True)
    lot_number = models.CharField(default=None, max_length=5000, null=True, blank=True)
    _delimiter = models.CharField(max_length=2, choices=DELIMITER_CHOICES)

    @property
    def delimiter(self):
        return self._delimiter.replace("\\t", "\t")

    @delimiter.setter
    def delimiter(self, value):
        self._delimiter = value


class Storage(AbstractBaseModel):
    DEVICE_CHOICES = [("NeoLight", 0), ("Sophia", 1), ("ATNPTL", 2), ("Dummy", 3)]
    capacity = models.IntegerField()
    location = models.CharField(max_length=50, null=True, blank=True)
    device = models.CharField(max_length=5000, choices=DEVICE_CHOICES)
    COM_address = models.CharField(max_length=10, blank=True, null=True)
    COM_baudrate = models.PositiveIntegerField(null=True, blank=True)
    COM_timeout = models.FloatField(null=True, blank=True)
    ATNPTL_shelf_id = models.PositiveIntegerField(null=True, blank=True)
    ip_address = models.CharField(max_length=15, null=True, blank=True)
    ip_port = models.PositiveIntegerField(null=True, blank=True)

    lighthouse_A_green = models.BooleanField(default=False)
    lighthouse_A_yellow = models.BooleanField(default=False)
    lighthouse_B_green = models.BooleanField(default=False)
    lighthouse_B_yellow = models.BooleanField(default=False)

    def get_absolute_url(self):
        return reverse("smt_management_app:storage-detail", kwargs={"name": self.name})


class Manufacturer(models.Model):
    name = models.CharField(primary_key=True, max_length=50, null=False, blank=False)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse(
            "smt_management_app:manufacturer-detail", kwargs={"name": self.name}
        )


class Provider(models.Model):
    name = models.CharField(primary_key=True, max_length=50, null=False, blank=False)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("smt_management_app:provider-detail", kwargs={"name": self.name})


class Article(AbstractBaseModel):
    manufacturer = models.ForeignKey(
        Manufacturer, on_delete=models.CASCADE, null=True, blank=True
    )
    manufacturer_description = models.CharField(max_length=255, null=True, blank=True)

    provider1 = models.ForeignKey(
        Provider,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="provider1",
    )

    provider1_description = models.CharField(max_length=255, null=True, blank=True)
    provider2 = models.ForeignKey(
        Provider,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="provider2",
    )
    provider2_description = models.CharField(max_length=255, null=True, blank=True)
    provider3 = models.ForeignKey(
        Provider,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="provider3",
    )
    provider3_description = models.CharField(max_length=255, null=True, blank=True)
    provider4 = models.ForeignKey(
        Provider,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="provider4",
    )
    provider4_description = models.CharField(max_length=255, null=True, blank=True)
    provider5 = models.ForeignKey(
        Provider,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="provider5",
    )
    provider5_description = models.CharField(max_length=255, null=True, blank=True)

    description = models.CharField(max_length=255, null=True, blank=True)
    sap_number = models.CharField(max_length=50, null=True, blank=True)

    def get_absolute_url(self):
        return reverse("smt_management_app:article-detail", kwargs={"name": self.name})


class Carrier(AbstractBaseModel):
    TYPE_CHOICES = [
        (0, "Reel"),
        (1, "Tray"),
        (2, "Bag"),
        (3, "Single"),
    ]

    article = models.ForeignKey(
        Article, on_delete=models.CASCADE, null=False, blank=False
    )
    diameter = models.IntegerField(default=7, null=True, blank=True)
    width = models.IntegerField(default=12, null=True, blank=True)
    container_type = models.IntegerField(
        default=0, choices=TYPE_CHOICES, null=True, blank=True
    )
    quantity_original = models.IntegerField(blank=True, null=True)
    quantity_current = models.IntegerField(blank=True, null=True)
    lot_number = models.CharField(max_length=20, blank=True, null=True)

    reserved = models.BooleanField(default=False)
    delivered = models.BooleanField(default=False)
    collecting = models.BooleanField(default=False)

    nominated_for_slot = models.OneToOneField(
        "StorageSlot",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="nominated_carrier",
        related_query_name="nominated_carrier",
    )

    storage_slot = models.OneToOneField(
        "StorageSlot",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="carrier",
    )

    storage_slot_qr_value = models.CharField(max_length=5000, blank=True, null=True)
    machine_slot = models.OneToOneField(
        "MachineSlot", on_delete=models.SET_NULL, null=True, blank=True
    )

    storage = models.ForeignKey(
        Storage, on_delete=models.SET_NULL, null=True, blank=True
    )

    def save(self, *args, **kwargs):
        if self.storage_slot:
            slot_storage = self.storage_slot.storage
            storage = Storage.objects.filter(name=slot_storage).first()
            self.storage = storage
            self.storage_slot_qr_value = self.storage_slot.qr_value
        else:
            self.storage = None
            self.storage_slot_qr_value = None

        if not self.quantity_current or self.quantity_current < 0:
            self.quantity_current = 0

        super(Carrier, self).save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("smt_management_app:carrier-detail", kwargs={"name": self.name})

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=Q(storage_slot__isnull=True) | Q(machine_slot__isnull=True),
                name="at_most_one_field_not_null",
            )
        ]


class Machine(AbstractBaseModel):
    capacity = models.IntegerField()
    location = models.CharField(max_length=50, null=True, blank=True)

    def get_absolute_url(self):
        return reverse("smt_management_app:machine-detail", kwargs={"name": self.name})


class MachineSlot(AbstractBaseModel):
    machine = models.ForeignKey(Machine, on_delete=models.CASCADE)

    def get_absolute_url(self):
        return reverse(
            "smt_management_app:machineslot-detail", kwargs={"name": self.name}
        )


class StorageSlot(models.Model):
    name = models.PositiveIntegerField()
    STATE_CHOICES = [(0, "off"), (1, "on")]
    storage = models.ForeignKey(Storage, on_delete=models.CASCADE)
    led_state = models.IntegerField(default=0, choices=STATE_CHOICES)
    qr_value = models.CharField(max_length=5000, blank=True, null=True)
    diameter = models.IntegerField(default=7, null=True, blank=True)
    width = models.IntegerField(default=12, null=True, blank=True)

    # New fields for combined slots feature
    qr_codes = models.JSONField(
        default=list, blank=True, help_text="Additional QR codes for combined slots"
    )
    related_names = models.JSONField(
        default=list,
        blank=True,
        help_text="Related slot LED positions for combined slots",
    )

    def get_absolute_url(self):
        return reverse(
            "smt_management_app:storageslot-detail", kwargs={"name": self.name}
        )

    def __str__(self):
        return str(self.name)

    def get_all_qr_codes(self):
        """Return primary qr_value + qr_codes list, deduplicated"""
        all_codes = []
        if self.qr_value:
            all_codes.append(self.qr_value)
        if self.qr_codes:
            all_codes.extend(self.qr_codes)
        # Remove duplicates while preserving order
        seen = set()
        return [x for x in all_codes if not (x in seen or seen.add(x))]

    def get_all_slot_names(self):
        """Return [self.name] + related_names"""
        names = [self.name]
        if self.related_names:
            names.extend(self.related_names)
        return names

    def is_combined_slot(self):
        """Return bool(self.related_names)"""
        return bool(self.related_names)


class Job(AbstractBaseModel):
    STATUS_CHOICES = [
        (0, "created"),
        (1, "carriers_assigned"),
        (2, "finished"),
    ]

    description = models.CharField(max_length=5000, null=True, blank=True)
    board = models.ForeignKey("Board", on_delete=models.CASCADE)
    machine = models.ForeignKey(
        Machine, on_delete=models.SET_NULL, null=True, blank=True
    )
    project = models.CharField(max_length=50, null=True, blank=True)
    customer = models.CharField(max_length=50, null=True, blank=True)
    count = models.IntegerField()
    start_at = models.DateTimeField(null=True, blank=True)
    finish_at = models.DateTimeField(null=True, blank=True)
    status = models.IntegerField(default=0, choices=STATUS_CHOICES)
    carriers = models.ManyToManyField(Carrier, blank=True)

    def get_absolute_url(self):
        return reverse("smt_management_app:job-detail", kwargs={"name": self.name})


class Board(AbstractBaseModel):
    articles = models.ManyToManyField(Article, through="BoardArticle")
    description = models.CharField(max_length=5000, null=True, blank=True)

    def get_absolute_url(self):
        return reverse("smt_management_app:board-detail", kwargs={"name": self.name})


class BoardArticle(AbstractBaseModel):
    article = models.ForeignKey(Article, on_delete=models.CASCADE)
    board = models.ForeignKey(Board, on_delete=models.CASCADE)
    count = models.PositiveIntegerField()

    def get_absolute_url(self):
        return reverse(
            "smt_management_app:boardarticle-detail", kwargs={"name": self.name}
        )

    def save(self, *args, **kwargs):
        # ensure the board does not have a boardarticle with the same article
        if BoardArticle.objects.filter(article=self.article, board=self.board).exists():
            raise ValidationError(
                {
                    "article": ValidationError(
                        f"Article {self.article.name} is already assigned to this board"
                    )
                }
            )
        super(BoardArticle, self).save(*args, **kwargs)


# Helper function to merge storage slots
def merge_storage_slots(primary_slot, *additional_slots):
    """
    Combine multiple slots into one, delete additional slots.

    Args:
        primary_slot: The StorageSlot that will remain as the combined slot
        *additional_slots: StorageSlot instances to merge into the primary

    Returns:
        The updated primary_slot

    Raises:
        ValueError: If slots are from different storages or if any slot is occupied
    """
    from django.db import transaction

    # Validate all slots are from the same storage
    storage = primary_slot.storage
    for slot in additional_slots:
        if slot.storage != storage:
            raise ValueError(
                f"Cannot merge slots from different storages: {slot.name} is in {slot.storage.name}, not {storage.name}"
            )

    # Check that no slots are occupied
    all_slots = [primary_slot] + list(additional_slots)
    for slot in all_slots:
        if hasattr(slot, "carrier") and slot.carrier:
            raise ValueError(
                f"Cannot merge occupied slot: {slot.name} contains carrier {slot.carrier.name}"
            )
        if hasattr(slot, "nominated_carrier") and slot.nominated_carrier:
            raise ValueError(
                f"Cannot merge slot with nominated carrier: {slot.name} is nominated for carrier {slot.nominated_carrier.name}"
            )

    with transaction.atomic():
        # Collect all QR codes
        additional_qr_codes = []
        for slot in additional_slots:
            if slot.qr_value and slot.qr_value not in additional_qr_codes:
                additional_qr_codes.append(slot.qr_value)
            if slot.qr_codes:
                for qr in slot.qr_codes:
                    if qr not in additional_qr_codes:
                        additional_qr_codes.append(qr)

        # Collect all related names (LED positions)
        related_names = []
        for slot in additional_slots:
            related_names.append(slot.name)
            if slot.related_names:
                related_names.extend(slot.related_names)

        # Update primary slot
        if not primary_slot.qr_codes:
            primary_slot.qr_codes = []
        primary_slot.qr_codes.extend(additional_qr_codes)

        if not primary_slot.related_names:
            primary_slot.related_names = []
        primary_slot.related_names.extend(related_names)

        # Remove duplicates
        primary_slot.qr_codes = list(set(primary_slot.qr_codes))
        primary_slot.related_names = list(set(primary_slot.related_names))

        # Update dimensions if needed (take maximum)
        for slot in additional_slots:
            if slot.diameter and slot.diameter > primary_slot.diameter:
                primary_slot.diameter = slot.diameter
            if slot.width and slot.width > primary_slot.width:
                primary_slot.width = slot.width

        primary_slot.save()

        # Delete additional slots
        for slot in additional_slots:
            slot.delete()

    return primary_slot

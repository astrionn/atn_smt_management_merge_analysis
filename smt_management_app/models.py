import os
from django.db import models
from django.db.models import Q
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
    DELIMITER_CHOICES = [(0, ","), (1, ";"), (2, "\t")]
    name = models.BigAutoField(primary_key=True, unique=True, null=False, blank=False)
    upload_type = models.CharField(
        max_length=50, choices=UPLOAD_TYPE_CHOICES, null=False, blank=False
    )
    file_object = models.FileField(upload_to=get_upload_path)
    headers = models.CharField(max_length=5000, null=True, blank=True)
    board_name = models.CharField(max_length=5000, null=True, blank=True)
    delimiter = models.CharField(max_length=2, choices=DELIMITER_CHOICES)


class Storage(AbstractBaseModel):
    DEVICE_CHOICES = [(0, "NeoLight"), (1, "Sophia"), (2, "ATNPTL"), (3, "Dummy")]
    capacity = models.IntegerField()
    location = models.CharField(max_length=50, null=True, blank=True)
    device = models.CharField(max_length=5000, choices=DEVICE_CHOICES)
    COM_address = models.CharField(max_length=10, blank=True, null=True)
    ATNPTL_shelf_id = models.PositiveIntegerField(null=True, blank=True)
    ip_adress = models.CharField(max_length=15, null=True, blank=True)
    ip_port = models.PositiveIntegerField(null=True, blank=True)

    def get_absolute_url(self):
        return reverse("smt_management_app:storage-detail", kwargs={"name": self.name})


class Manufacturer(AbstractBaseModel):
    def get_absolute_url(self):
        return reverse(
            "smt_management_app:manufacturer-detail", kwargs={"name": self.name}
        )


class Provider(AbstractBaseModel):
    def get_absolute_url(self):
        return reverse("smt_management_app:provider-detail", kwargs={"name": self.name})


class Article(AbstractBaseModel):
    manufacturer = models.ForeignKey(
        Manufacturer, on_delete=models.CASCADE, null=True, blank=True
    )
    manufacturer_description = models.CharField(max_length=50, null=True, blank=True)

    provider1 = models.ForeignKey(
        Provider,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="provider1",
    )
    provider1_description = models.CharField(max_length=50, null=True, blank=True)
    provider2 = models.ForeignKey(
        Provider,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="provider2",
    )
    provider2_description = models.CharField(max_length=50, null=True, blank=True)
    provider3 = models.ForeignKey(
        Provider,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="provider3",
    )
    provider3_description = models.CharField(max_length=50, null=True, blank=True)
    provider4 = models.ForeignKey(
        Provider,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="provider4",
    )
    provider4_description = models.CharField(max_length=50, null=True, blank=True)
    provider5 = models.ForeignKey(
        Provider,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="provider5",
    )
    provider5_description = models.CharField(max_length=50, null=True, blank=True)

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
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="carrier",
    )

    storage_slot_qr_value = models.CharField(max_length=5000, blank=True, null=True)
    machine_slot = models.OneToOneField(
        "MachineSlot", on_delete=models.CASCADE, null=True, blank=True
    )

    storage = models.ForeignKey(
        Storage, on_delete=models.CASCADE, null=True, blank=True
    )

    def save(self, *args, **kwargs):
        # disallow archiving if in a storage-slot
        if self.storage_slot:
            slot_storage = self.storage_slot.storage
            # print(slot_storage)
            storage = Storage.objects.filter(name=slot_storage).first()
            # print(storage)
            self.storage = storage
            self.storage_slot_qr_value = self.storage_slot.qr_value
        else:
            self.storage = None

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

    def get_absolute_url(self):
        return reverse(
            "smt_management_app:storageslot-detail", kwargs={"name": self.name}
        )

    def __str__(self):
        return str(self.name)


class Job(AbstractBaseModel):
    STATUS_CHOICES = [
        (0, "created"),
        (1, "carriers_assigned"),
        (2, "finished"),
    ]

    board = models.ForeignKey("Board", on_delete=models.CASCADE)
    machine = models.ForeignKey(
        Machine, on_delete=models.CASCADE, null=True, blank=True
    )
    project = models.CharField(max_length=50, null=True, blank=True)
    customer = models.CharField(max_length=50, null=True, blank=True)
    count = models.IntegerField()
    start_at = models.DateTimeField()
    finish_at = models.DateTimeField()
    status = models.IntegerField(default=0, choices=STATUS_CHOICES)
    carriers = models.ManyToManyField(Carrier, blank=True)

    def get_absolute_url(self):
        return reverse("smt_management_app:job-detail", kwargs={"name": self.name})


class Board(AbstractBaseModel):
    articles = models.ManyToManyField(Article, through="BoardArticle")

    def get_absolute_url(self):
        return reverse("smt_management_app:board-detail", kwargs={"name": self.name})


class BoardArticle(AbstractBaseModel):
    article = models.OneToOneField(Article, on_delete=models.CASCADE)
    board = models.ForeignKey(Board, on_delete=models.CASCADE)
    count = models.PositiveIntegerField()

    def get_absolute_url(self):
        return reverse(
            "smt_management_app:boardarticle-detail", kwargs={"name": self.name}
        )

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

    def validate_combined_slot_consistency(self):
        """
        Validate that combined slot configuration is consistent.

        Raises:
            ValidationError: If combined slot configuration is invalid
        """
        if not self.is_combined_slot():
            return  # Nothing to validate for non-combined slots

        # Check that all related slot names exist in the same storage
        try:
            related_slots = StorageSlot.objects.filter(
                storage=self.storage, name__in=self.related_names
            ).exclude(pk=self.pk)

            if related_slots.count() != len(self.related_names):
                missing_slots = set(self.related_names) - set(
                    related_slots.values_list("name", flat=True)
                )
                raise ValidationError(
                    f"Combined slot {self.name} references non-existent slots: {missing_slots}"
                )

        except Exception as e:
            if self.pk:  # Only validate if this is an existing slot
                raise ValidationError(f"Error validating combined slot: {str(e)}")

    def validate_combined_slot_occupancy(self):
        """
        Validate that if this slot has a carrier, no related slots in combined group are occupied.

        Raises:
            ValidationError: If combined slot occupancy rules are violated
        """
        if not hasattr(self, "carrier") or not self.carrier:
            return  # No carrier, no occupancy conflict

        if not self.is_combined_slot():
            return  # Not a combined slot, no validation needed

        # Check if any related slots are occupied
        try:
            related_occupied = StorageSlot.objects.filter(
                storage=self.storage, name__in=self.related_names, carrier__isnull=False
            ).exclude(pk=self.pk)

            if related_occupied.exists():
                occupied_slot = related_occupied.first()
                raise ValidationError(
                    f"Cannot store carrier in slot {self.name}: "
                    f"related slot {occupied_slot.name} in combined slot group is occupied by carrier {occupied_slot.carrier.name}"
                )

        except ValidationError:
            raise
        except Exception as e:
            # Don't fail on database errors during validation - log and continue
            import logging

            logging.warning(
                f"Error validating combined slot occupancy for slot {self.name}: {str(e)}"
            )

    def validate_bidirectional_consistency(self):
        """
        Validate that if this slot is combined with others, those slots also reference this one.

        Raises:
            ValidationError: If bidirectional references are inconsistent
        """
        if not self.is_combined_slot():
            return

        try:
            # Check that all related slots reference this slot back
            related_slots = StorageSlot.objects.filter(
                storage=self.storage, name__in=self.related_names
            ).exclude(pk=self.pk)

            for related_slot in related_slots:
                if not related_slot.is_combined_slot():
                    raise ValidationError(
                        f"Slot {self.name} references slot {related_slot.name} as combined, "
                        f"but slot {related_slot.name} is not configured as a combined slot"
                    )

                if self.name not in related_slot.related_names:
                    raise ValidationError(
                        f"Slot {self.name} references slot {related_slot.name} as combined, "
                        f"but slot {related_slot.name} does not reference slot {self.name} back"
                    )

        except ValidationError:
            raise
        except Exception as e:
            if self.pk:  # Only validate if this is an existing slot
                import logging

                logging.warning(
                    f"Error validating bidirectional consistency for slot {self.name}: {str(e)}"
                )

    def save(self, *args, **kwargs):
        """
        Override save to add combined slot validation.
        """
        # Skip validation during bulk operations or when explicitly disabled
        skip_validation = kwargs.pop("skip_combined_slot_validation", False)

        if not skip_validation:
            try:
                # Validate combined slot configuration
                self.validate_combined_slot_consistency()

                # Validate occupancy rules
                self.validate_combined_slot_occupancy()

                # Note: Bidirectional validation is skipped during save to avoid recursion
                # It should be handled at the application level when creating combined slots

            except ValidationError as e:
                # Re-raise validation errors
                raise e
            except Exception as e:
                # Log other errors but don't fail the save
                import logging

                logging.warning(
                    f"Error during combined slot validation for slot {self.name}: {str(e)}"
                )

        super().save(*args, **kwargs)


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
    Improved version that properly handles existing combined slots.

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
        # Collect all QR codes from all slots (including existing ones in primary)
        all_qr_codes = []

        # Start with primary slot's existing QR codes
        if primary_slot.qr_value and primary_slot.qr_value.strip():
            all_qr_codes.append(primary_slot.qr_value.strip())

        if primary_slot.qr_codes:
            for qr in primary_slot.qr_codes:
                if qr and qr.strip() and qr.strip() not in all_qr_codes:
                    all_qr_codes.append(qr.strip())

        # Add QR codes from additional slots
        for slot in additional_slots:
            if slot.qr_value and slot.qr_value.strip():
                qr = slot.qr_value.strip()
                if qr not in all_qr_codes:
                    all_qr_codes.append(qr)

            if slot.qr_codes:
                for qr in slot.qr_codes:
                    if qr and qr.strip() and qr.strip() not in all_qr_codes:
                        all_qr_codes.append(qr.strip())

        # Collect all related names (LED positions)
        all_related_names = []

        # Start with primary slot's existing related names
        if primary_slot.related_names:
            all_related_names.extend(primary_slot.related_names)

        # Add names from additional slots
        for slot in additional_slots:
            # Add the slot's own name
            if slot.name not in all_related_names:
                all_related_names.append(slot.name)

            # Add any existing related names from this slot
            if slot.related_names:
                for name in slot.related_names:
                    if name not in all_related_names:
                        all_related_names.append(name)

        # Update primary slot with all collected data
        # Remove the primary QR from the additional list (it stays as qr_value)
        additional_qr_codes = [qr for qr in all_qr_codes if qr != primary_slot.qr_value]

        # Update primary slot
        primary_slot.qr_codes = additional_qr_codes
        primary_slot.related_names = all_related_names

        # Update dimensions to maximum values
        for slot in additional_slots:
            if slot.diameter and (
                not primary_slot.diameter or slot.diameter > primary_slot.diameter
            ):
                primary_slot.diameter = slot.diameter
            if slot.width and (
                not primary_slot.width or slot.width > primary_slot.width
            ):
                primary_slot.width = slot.width

        # Save with validation disabled to avoid recursion during merge
        primary_slot.save(skip_combined_slot_validation=True)

        # Delete additional slots
        for slot in additional_slots:
            slot.delete()

    return primary_slot

import uuid

from django.db import models
from django.utils import timezone


class InventoryItem(models.Model):
    """
    Repuesto o insumo del inventario.
    Fracttal: módulo Almacenes (vacío en la cuenta observada).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, default="")
    unit_of_measure = models.CharField(max_length=20, default="und")
    current_stock = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    min_stock = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "inventory_inventoryitem"
        ordering = ["name"]

    def __str__(self):
        return f"{self.code} — {self.name}"


class StockMovement(models.Model):
    """Movimiento de inventario (entrada o salida). Las salidas se vinculan a una OT."""

    class MovementType(models.TextChoices):
        IN = "IN", "Entrada"
        OUT = "OUT", "Salida"
        ADJUSTMENT = "ADJUSTMENT", "Ajuste"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    item = models.ForeignKey(
        InventoryItem, on_delete=models.PROTECT,
        related_name="movements"
    )
    movement_type = models.CharField(max_length=10, choices=MovementType.choices)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    work_order = models.ForeignKey(
        "work_orders.WorkOrder", on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="stock_movements"
    )
    reference = models.CharField(max_length=200, blank=True, default="")
    notes = models.TextField(blank=True, default="")
    performed_by = models.ForeignKey(
        "users.User", on_delete=models.PROTECT,
        related_name="stock_movements"
    )
    performed_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "inventory_stockmovement"
        ordering = ["-performed_at"]

    def save(self, *args, **kwargs):
        if self.pk and StockMovement.objects.filter(pk=self.pk).exists():
            raise ValueError("StockMovement es inmutable tras crearse.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("StockMovement es inmutable.")

    def __str__(self):
        return f"{self.movement_type} {self.quantity} × {self.item.code}"

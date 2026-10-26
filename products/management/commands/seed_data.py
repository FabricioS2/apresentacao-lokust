"""
Management command: seed_data

Popula o banco com produtos, tamanhos, usuários e imagens.
IDEMPOTENTE — pode rodar em todo `docker compose up` sem duplicar.
"""

import os
from decimal import Decimal

import requests
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand
from django.db import transaction

from products.models import Product, ProductSize


# ============================================================
# DADOS
# ============================================================

PRODUCTS_DATA = [
    {
        "name": "Classic Black Shirt",
        "description": "A timeless black shirt, perfect for any occasion. Soft cotton blend.",
        "price": Decimal("49.90"),
        "has_sizes": True,
        "sizes": [("S", 10), ("M", 15), ("L", 20), ("XL", 5), ("XXL", 0)],
    },
    {
        "name": "White Linen Shirt",
        "description": "Lightweight linen shirt ideal for warm days.",
        "price": Decimal("59.90"),
        "has_sizes": True,
        "sizes": [("XS", 5), ("S", 12), ("M", 10), ("L", 8), ("XL", 3)],
    },
    {
        "name": "Gold Embroidered Kurta",
        "description": "Traditional kurta with delicate gold embroidery on the neckline.",
        "price": Decimal("89.90"),
        "has_sizes": True,
        "sizes": [("S", 6), ("M", 8), ("L", 6), ("XL", 2)],
    },
    {
        "name": "Ivory Silk Saree",
        "description": "Handwoven silk saree with gold border. A statement piece.",
        "price": Decimal("189.00"),
        "has_sizes": False,
        "sizes": [],
    },
    {
        "name": "Maroon Banarasi Saree",
        "description": "Rich Banarasi silk saree with intricate zari work.",
        "price": Decimal("229.00"),
        "has_sizes": False,
        "sizes": [],
    },
    {
        "name": "Black Embroidered Saree",
        "description": "Elegant black saree with subtle sequin embroidery.",
        "price": Decimal("199.00"),
        "has_sizes": False,
        "sizes": [],
    },
    {
        "name": "Beige Cotton Kurta",
        "description": "Everyday cotton kurta with a relaxed fit.",
        "price": Decimal("39.90"),
        "has_sizes": True,
        "sizes": [("S", 20), ("M", 25), ("L", 15), ("XL", 10)],
    },
    {
        "name": "Navy Pleated Dress",
        "description": "Flowing pleated dress in deep navy. Perfect for evenings.",
        "price": Decimal("119.00"),
        "has_sizes": True,
        "sizes": [("XS", 4), ("S", 6), ("M", 5), ("L", 3)],
    },
]

DEMO_USERS = [
    {"username": "customer",  "email": "customer@example.com",  "password": "Customer@123"},
    {"username": "customer2", "email": "customer2@example.com", "password": "Customer@123"},
]


# ============================================================
# COMMAND
# ============================================================

class Command(BaseCommand):
    help = "Seed initial demo data (products, sizes, users, images). Safe to re-run."

    def handle(self, *args, **options):
        with transaction.atomic():
            self._seed_products()
            self._seed_users()
            self._seed_superuser_if_configured()

        self.stdout.write(self.style.SUCCESS(
            f"✅ Seed concluído. Produtos: {Product.objects.count()} | "
            f"Tamanhos: {ProductSize.objects.count()} | "
            f"Usuários: {User.objects.count()}"
        ))

    # -------------------------------------------------------- products + imagens
    def _seed_products(self):
        created, existing = 0, 0
        for data in PRODUCTS_DATA:
            product, was_created = Product.objects.get_or_create(
                name=data["name"],
                defaults={
                    "description": data["description"],
                    "price": data["price"],
                    "has_sizes": data["has_sizes"],
                    "available": True,
                },
            )
            created += int(was_created)
            existing += int(not was_created)

            if data["has_sizes"]:
                for size, stock in data["sizes"]:
                    ProductSize.objects.get_or_create(
                        product=product,
                        size=size,
                        defaults={"stock": stock},
                    )

            self._attach_image(product)

        self.stdout.write(
            f"  → Produtos: {created} criados, {existing} já existiam."
        )

    def _attach_image(self, product: Product):
        if product.image:
            return

        slug = product.name.lower().replace(" ", "_")
        filename = f"{slug}.jpg"
        rel_path = f"products/{filename}"

        content = self._download_image(product.name)
        if not content:
            self.stdout.write(self.style.WARNING(
                f"    ⚠ Sem imagem para {product.name} (download falhou)"
            ))
            return

        try:
            if default_storage.exists(rel_path):
                default_storage.delete(rel_path)
        except Exception:
            pass

        try:
            product.image.save(filename, ContentFile(content), save=True)
            self.stdout.write(f"    → Imagem anexada: {rel_path}")
        except Exception as e:
            self.stdout.write(self.style.WARNING(
                f"    ⚠ Falha ao salvar imagem de {product.name}: {e}"
            ))

    def _download_image(self, product_name: str) -> bytes | None:
        slug = product_name.lower().replace(" ", "_")
        label = product_name.replace(" ", "+")

        candidates = [
            f"https://picsum.photos/seed/{slug}/600/800",
            f"https://placehold.co/600x800/1a1a1a/c9a24d.jpg?text={label}",
        ]

        for url in candidates:
            try:
                r = requests.get(url, timeout=10)
                if r.status_code == 200 and len(r.content) > 1000:
                    return r.content
            except Exception:
                continue

        return None

    # -------------------------------------------------------------- usuários
    def _seed_users(self):
        for data in DEMO_USERS:
            user, was_created = User.objects.get_or_create(
                username=data["username"],
                defaults={"email": data["email"]},
            )
            if was_created:
                user.set_password(data["password"])
                user.save()
                self.stdout.write(f"  → Usuário criado: {data['username']}")

    # ------------------------------------------------------------ superuser
    def _seed_superuser_if_configured(self):
        username = os.environ.get("DJANGO_SUPERUSER_USERNAME")
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "")
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD")

        if not (username and password):
            return
        if User.objects.filter(username=username).exists():
            return

        User.objects.create_superuser(username=username, email=email, password=password)
        self.stdout.write(self.style.SUCCESS(
            f"  → Superuser criado: {username}"
        ))

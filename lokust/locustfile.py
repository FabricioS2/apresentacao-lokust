import os
import re
import random
from uuid import uuid4

import gevent
from locust import HttpUser, between, task, tag


def env_int(name, default):
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


TEST_USERNAME = os.getenv("LOCUST_USERNAME", "")
TEST_PASSWORD = os.getenv("LOCUST_PASSWORD", "")
TEST_EMAIL = os.getenv("LOCUST_EMAIL", "locust@example.com")
TEST_PASSWORD_FALLBACK = os.getenv("LOCUST_TEST_PASSWORD", "LocustTest@12345")
PRODUCT_ID = os.getenv("LOCUST_PRODUCT_ID", "")
SIZE = os.getenv("LOCUST_SIZE", "")


def csrf_from(html, client):
    m = re.search(
        r'name=["\']csrfmiddlewaretoken["\'][^>]*value=["\']([^"\']+)',
        html,
        re.I,
    )
    if not m:
        m = re.search(
            r'value=["\']([^"\']+)["\'][^>]*name=["\']csrfmiddlewaretoken["\']',
            html,
            re.I,
        )
    if m:
        return m.group(1)
    return client.cookies.get("csrftoken", "")


def hidden_fields(html):
    return dict(
        re.findall(
            r'<input[^>]+type=["\']hidden["\'][^>]*name=["\']([^"\']+)["\'][^>]*value=["\']([^"\']*)',
            html,
            re.I,
        )
    )


def extract_product_ids(html):
    ids = re.findall(r'/products/(\d+)/', html)
    return list(dict.fromkeys(ids))


def extract_cart_item_ids(html):
    ids = re.findall(r'/orders/(?:remove|update)/(\d+)/', html)
    return list(dict.fromkeys(ids))


def extract_size_options(html):
    options = re.findall(
        r'<option[^>]+value=["\']([^"\']+)["\'][^>]*>(.*?)</option>',
        html,
        re.I | re.S,
    )
    return [
        value.strip()
        for value, label in options
        if value.strip() and "select" not in label.lower()
    ]


class StoreUser(HttpUser):
    wait_time = between(0.5, 2.0)

    def on_start(self):
        self.product_ids = []
        self.current_product = PRODUCT_ID or None
        self.current_size = SIZE or None

        if TEST_USERNAME:
            self.username = TEST_USERNAME
            self.password = TEST_PASSWORD
            self.email = TEST_EMAIL
            self.login()
        else:
            self.username = f"locust_{uuid4().hex[:12]}"
            self.password = TEST_PASSWORD_FALLBACK
            self.email = f"{self.username}@example.com"
            self.register_account()
            self.login()

        self.discover_products()

    def ensure_login(self):
        if not self.client.cookies.get("sessionid"):
            self.login()

    def register_account(self):
        with self.client.get(
            "/accounts/register/",
            name="06 - Cadastro - GET",
            catch_response=True,
        ) as r:
            if r.status_code != 200:
                r.failure(f"HTTP {r.status_code}")
                return

            token = csrf_from(r.text, self.client)
            data = hidden_fields(r.text)
            data.update(
                {
                    "username": self.username,
                    "email": self.email,
                    "password1": self.password,
                    "password2": self.password,
                }
            )
            if token:
                data["csrfmiddlewaretoken"] = token

        with self.client.post(
            "/accounts/register/",
            data=data,
            name="06 - Cadastro - POST",
            allow_redirects=False,
            catch_response=True,
        ) as r:
            if r.status_code not in (200, 302):
                r.failure(f"HTTP {r.status_code}")

    def login(self):
        with self.client.get(
            "/accounts/login/",
            name="04 - Login - GET",
            catch_response=True,
        ) as r:
            if r.status_code != 200:
                r.failure(f"HTTP {r.status_code}")
                return
            token = csrf_from(r.text, self.client)

        data = {"username": self.username, "password": self.password}
        if token:
            data["csrfmiddlewaretoken"] = token

        with self.client.post(
            "/accounts/login/",
            data=data,
            name="04 - Login - POST",
            allow_redirects=False,
            catch_response=True,
        ) as r:
            if r.status_code not in (200, 302):
                r.failure(f"HTTP {r.status_code}")

    def discover_products(self):
        with self.client.get(
            "/products/",
            name="02 - Lista de produtos",
            catch_response=True,
        ) as r:
            if r.status_code == 200:
                self.product_ids = extract_product_ids(r.text)
                if not self.current_product and self.product_ids:
                    self.current_product = random.choice(self.product_ids)
            else:
                r.failure(f"HTTP {r.status_code}")

    def product_url(self):
        pid = self.current_product
        if not pid and self.product_ids:
            pid = random.choice(self.product_ids)
            self.current_product = pid
        return f"/products/{pid}/" if pid else None

    def get_product_detail(self):
        url = self.product_url()
        if not url:
            self.discover_products()
            url = self.product_url()
        return url

    def discover_cart_item(self):
        with self.client.get(
            "/orders/",
            name="08 - Carrinho - GET",
            catch_response=True,
        ) as r:
            if r.status_code != 200:
                r.failure(f"HTTP {r.status_code}")
                return None
            ids = extract_cart_item_ids(r.text)
            return ids[0] if ids else None

    def add_product(self, name="09 - Adicionar ao carrinho"):
        self.ensure_login()
        url = self.get_product_detail()
        if not url or not self.current_product:
            return

        with self.client.get(
            url,
            name="03 - Detalhe do produto",
            catch_response=True,
        ) as r:
            if r.status_code != 200:
                r.failure(f"HTTP {r.status_code}")
                return
            token = csrf_from(r.text, self.client)
            sizes = extract_size_options(r.text)
            selected_size = self.current_size or (sizes[0] if sizes else None)

        data = {}
        if selected_size:
            data["size"] = selected_size
        if token:
            data["csrfmiddlewaretoken"] = token

        with self.client.post(
            f"/orders/add/{self.current_product}/",
            data=data,
            name=name,
            allow_redirects=False,
            catch_response=True,
        ) as r:
            if r.status_code not in (200, 302):
                r.failure(f"HTTP {r.status_code}")

    @tag("home")
    @task(3)
    def test_01_home(self):
        with self.client.get(
            "/",
            name="01 - Página inicial",
            catch_response=True,
        ) as r:
            if r.status_code != 200:
                r.failure(f"HTTP {r.status_code}")

    @tag("products")
    @task(5)
    def test_02_product_list(self):
        self.discover_products()

    @tag("products")
    @task(5)
    def test_03_product_detail(self):
        url = self.get_product_detail()
        if url:
            with self.client.get(
                url,
                name="03 - Detalhe do produto",
                catch_response=True,
            ) as r:
                if r.status_code != 200:
                    r.failure(f"HTTP {r.status_code}")

    @tag("auth")
    @task(2)
    def test_04_login(self):
        self.login()

    @tag("auth")
    @task(1)
    def test_05_logout(self):
        self.ensure_login()
        with self.client.get(
            "/accounts/logout/",
            name="05 - Logout",
            allow_redirects=False,
            catch_response=True,
        ) as r:
            if r.status_code not in (200, 302):
                r.failure(f"HTTP {r.status_code}")
        gevent.sleep(0.1)
        self.login()

    @tag("auth")
    @task(1)
    def test_06_registration(self):
        username = f"locust_{uuid4().hex[:12]}"
        password = TEST_PASSWORD_FALLBACK
        email = f"{username}@example.com"

        with self.client.get(
            "/accounts/register/",
            name="06 - Cadastro - GET",
            catch_response=True,
        ) as r:
            if r.status_code != 200:
                r.failure(f"HTTP {r.status_code}")
                return
            token = csrf_from(r.text, self.client)
            data = hidden_fields(r.text)
            data.update(
                {
                    "username": username,
                    "email": email,
                    "password1": password,
                    "password2": password,
                }
            )
            if token:
                data["csrfmiddlewaretoken"] = token

        with self.client.post(
            "/accounts/register/",
            data=data,
            name="06 - Cadastro - POST",
            allow_redirects=False,
            catch_response=True,
        ) as r:
            if r.status_code not in (200, 302):
                r.failure(f"HTTP {r.status_code}")

    @tag("wishlist")
    @task(2)
    def test_07_wishlist(self):
        self.ensure_login()

        with self.client.get(
            "/products/wishlist/",
            name="07 - Wishlist - visualizar",
            catch_response=True,
        ) as r:
            if r.status_code != 200:
                r.failure(f"HTTP {r.status_code}")

        if self.current_product:
            with self.client.get(
                f"/products/wishlist/add/{self.current_product}/",
                name="07 - Wishlist - adicionar",
                allow_redirects=False,
                catch_response=True,
            ) as r:
                if r.status_code not in (200, 302):
                    r.failure(f"HTTP {r.status_code}")

    @tag("cart")
    @task(3)
    def test_08_cart(self):
        self.ensure_login()
        self.discover_cart_item()

    @tag("cart")
    @task(4)
    def test_09_add_to_cart(self):
        self.add_product()

    @tag("cart")
    @task(3)
    def test_10_update_quantity(self):
        self.ensure_login()
        item_id = self.discover_cart_item()

        if not item_id:
            self.add_product()
            item_id = self.discover_cart_item()

        if not item_id:
            return

        with self.client.get(
            "/orders/",
            name="10 - Carrinho antes da atualização",
            catch_response=True,
        ) as r:
            token = csrf_from(r.text, self.client)

        data = {"action": "increase"}
        if token:
            data["csrfmiddlewaretoken"] = token

        with self.client.post(
            f"/orders/update/{item_id}/",
            data=data,
            name="10 - Alterar quantidade",
            catch_response=True,
        ) as r:
            if r.status_code != 200:
                r.failure(f"HTTP {r.status_code}")

    @tag("cart")
    @task(2)
    def test_11_remove_from_cart(self):
        self.ensure_login()
        item_id = self.discover_cart_item()

        if not item_id:
            self.add_product()
            item_id = self.discover_cart_item()

        if not item_id:
            return

        with self.client.get(
            f"/orders/remove/{item_id}/",
            name="11 - Remover do carrinho",
            allow_redirects=False,
            catch_response=True,
        ) as r:
            if r.status_code not in (200, 302):
                r.failure(f"HTTP {r.status_code}")

    @tag("variants")
    @task(2)
    def test_12_size_variant(self):
        self.ensure_login()
        url = self.get_product_detail()
        if not url:
            return

        with self.client.get(
            url,
            name="12 - Variante/tamanho - GET",
            catch_response=True,
        ) as r:
            if r.status_code != 200:
                r.failure(f"HTTP {r.status_code}")
                return
            sizes = extract_size_options(r.text)

        if sizes:
            self.current_size = random.choice(sizes)
            self.add_product("12 - Variante/tamanho - POST")

    @tag("stock", "concurrency")
    @task(2)
    def test_13_stock_concurrency(self):
        self.ensure_login()
        self.add_product("13 - Concorrência de estoque - adicionar")

    @tag("checkout")
    @task(2)
    def test_14_checkout(self):
        self.ensure_login()
        item_id = self.discover_cart_item()
        if not item_id:
            self.add_product()
        with self.client.get(
            "/orders/place-order/",
            name="14 - Checkout - GET",
            catch_response=True,
        ) as r:
            if r.status_code != 200:
                r.failure(f"HTTP {r.status_code}")

    def place_order(self, name):
        self.ensure_login()

        item_id = self.discover_cart_item()
        if not item_id:
            self.add_product(f"{name} - adicionar")
            item_id = self.discover_cart_item()

        if not item_id:
            return False

        with self.client.get(
            "/orders/place-order/",
            name=f"{name} - formulário",
            catch_response=True,
        ) as r:
            if r.status_code != 200:
                r.failure(f"HTTP {r.status_code}")
                return False
            token = csrf_from(r.text, self.client)

        data = {
            "full_name": os.getenv("LOCUST_FULL_NAME", "Locust Test User"),
            "phone": os.getenv("LOCUST_PHONE", "84999999999"),
            "address": os.getenv(
                "LOCUST_ADDRESS",
                "Rua Locust, 100 - Pau dos Ferros/RN",
            ),
        }
        if token:
            data["csrfmiddlewaretoken"] = token

        with self.client.post(
            "/orders/place-order/",
            data=data,
            name=f"{name} - POST",
            allow_redirects=True,
            catch_response=True,
        ) as r:
            ok = r.status_code == 200 and "/orders/success/" in r.url
            if not ok:
                r.failure(f"Pedido não chegou ao sucesso: HTTP {r.status_code} URL={r.url}")
            return ok

    @tag("purchase")
    @task(1)
    def test_15_complete_purchase(self):
        self.place_order("15 - Compra completa")

    @tag("orders", "concurrency")
    @task(1)
    def test_16_concurrent_orders(self):
        self.place_order("16 - Pedido concorrente")

    @tag("stock")
    @task(1)
    def test_17_stock_integrity(self):
        self.ensure_login()
        self.add_product("17 - Integridade do estoque - adicionar")

    @tag("email")
    @task(1)
    def test_18_order_email_flow(self):
        # The application catches SMTP exceptions, so Locust can verify the
        # order-success flow but cannot prove external SMTP delivery.
        self.place_order("18 - E-mail do pedido")

    @tag("sessions")
    @task(2)
    def test_19_concurrent_sessions(self):
        with self.client.get(
            "/",
            name="19 - Sessão simultânea - home",
            catch_response=True,
        ) as r:
            if r.status_code != 200:
                r.failure(f"HTTP {r.status_code}")

        self.ensure_login()

        with self.client.get(
            "/orders/",
            name="19 - Sessão simultânea - carrinho",
            catch_response=True,
        ) as r:
            if r.status_code != 200:
                r.failure(f"HTTP {r.status_code}")

    @tag("stress")
    @task(1)
    def test_20_stress(self):
        url = random.choice(["/", "/products/", "/orders/"])
        with self.client.get(
            url,
            name="20 - Stress",
            catch_response=True,
        ) as r:
            if r.status_code >= 500:
                r.failure(f"HTTP {r.status_code}")



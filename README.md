# A&M Signature — Modificações com Testes de Carga (Locust)

> **Este repositório é baseado no projeto original:**
> 🔗 https://github.com/JESMARIYA-ARUN/am-signature
>
> O projeto original é uma aplicação **Django eCommerce** (A&M Signature — *Wear Your Story*)
> criada como projeto final de Full Stack Development por Jesmariya Arun.
>
> **Modificações aplicadas neste repositório:**
>
> - ✅ Adição da pasta `lokust/` com suíte completa de **testes de carga** (Locust).
> - ✅ Criação do `lokust/locustfile.py` cobrindo **20 cenários** de teste (home, produtos, auth, carrinho, wishlist, checkout, concorrência de estoque, stress, etc.).
> - ✅ Criação do `lokust/stress_shape.py` com perfil de **stress progressivo** (10 → 50 → 100 → 200 usuários em 3 minutos).
> - ✅ Criação do `rodar_locust.sh` — script que executa uma **bateria completa em ~1 minuto** (5 etapas encadeadas).
> - ✅ Ajustes no `docker-compose.yml` e `build.sh` para rodar `seed_data` automaticamente na subida.
> - ✅ Adição da rota `/media/` em `am_signature/urls.py` (necessária para gunicorn sem nginx na frente).
>
> Todo o restante do código (models, views, templates, lógica de negócio original) permanece **inalterado** em relação ao projeto original.

---

## 📋 Sobre o projeto

A&M Signature é uma aplicação Django de e-commerce para uma marca de moda. Permite navegar por produtos, escolher tamanhos, gerenciar carrinho e wishlist, e realizar pedidos com pagamento na entrega (Cash on Delivery).

**Stack:**

- **Backend:** Django 6.0
- **Frontend:** HTML, CSS, Bootstrap
- **Banco:** PostgreSQL 17
- **Servidor:** Gunicorn
- **Deploy:** Docker + Docker Compose
- **Testes de carga:** Locust

**Credenciais de teste (criadas pelo `seed_data`):**

| Usuário | Senha | Papel |
|---|---|---|
| `customer` | `Customer@123` | Cliente |
| `customer2` | `Customer@123` | Cliente |
| `admin` | `Admin@12345` | Superuser (se habilitado no `.env`) |

---

## 🔧 Pré-requisitos

Antes de começar, certifique-se de ter instalado:

- **Docker** e **Docker Compose** (v2)
- **Python 3.12+**
- **Git**

---

## 🚀 Passo a passo — Subir o projeto e rodar o Locust

### 🔧 Passo 0 — Pré-requisitos (só uma vez)

#### 0.1 — Clonar o repositório e confirmar `.env`

```bash
git clone https://github.com/JESMARIYA-ARUN/am-signature.git
cd am-signature

# Confirmar .env na raiz
ls -la .env

# Se não existir, criar a partir do exemplo
cp .env.example .env 2>/dev/null || true
```

> ⚠️ O `docker-compose.yml` usa `env_file: .env`. Se faltar, o Django cai em defaults
> (DEBUG=False, ALLOWED_HOSTS padrão só `127.0.0.1,localhost` — o que serve para o Locust local).

#### 0.2 — Criar e ativar a virtualenv `.venv`

```bash
cd ~/Documentos/am-signature

# Criar a venv (só se ainda não existir)
[ -d .venv ] || python3 -m venv .venv

# Ativar a venv
source .venv/bin/activate

# Conferir o python ativo
which python
python --version

# Atualizar pip (opcional, mas recomendado)
pip install --upgrade pip
```

> ⚠️ A venv **não é usada dentro do Docker** — o container tem seu próprio Python.
> Ela existe apenas para rodar o **Locust** no host.
>
> No `.dockerignore` já estão listados `.venv` e `venv`, então ela não interfere no `docker compose build`.

#### 0.3 — Instalar as dependências na venv

```bash
# Dependência principal da venv: o Locust
pip install -r lokust/requirements.txt

# (Opcional) Instalar também as dependências Django, caso queira
# rodar `python manage.py ...` fora do container
pip install -r requirements.txt

# Confirmar que o Locust está instalado e acessível
locust --version
```

---

### 🐳 Passo 1 — Subir o Docker (Django + Postgres)

```bash
cd ~/Documentos/am-signature

# Parar qualquer container anterior (SEM -v para preservar o banco)
docker compose down

# Build + up em background
docker compose up -d --build
```

O `docker-compose.yml` já executa, na subida do `web`:

```
migrate → collectstatic → seed_data → gunicorn am_signature.wsgi
```

---

### 🔍 Passo 2 — Confirmar que o servidor está pronto

```bash
# Ver os containers ativos
docker compose ps

# Acompanhar os logs (Ctrl+C para sair)
docker compose logs -f web

# Teste rápido do endpoint
curl -I http://localhost:8000/
```

Você deve ver `HTTP/1.1 200 OK` (ou 302 para `/accounts/login/`) e, nos logs, a linha:

```
✅ Seed concluído. Produtos: 8 | Tamanhos: 26 | Usuários: 3
```

---

### 🦗 Passo 3 — Rodar o Locust (interface web)

```bash
cd ~/Documentos/am-signature
source .venv/bin/activate
locust -f lokust/locustfile.py --host http://localhost:8000
```

Abra no navegador: **http://localhost:8089**

Preencha:

- **Number of users:** 20
- **Spawn rate:** 5
- **Host:** `http://localhost:8000`
- Clique em **Start swarming**

---

### 🦗 Passo 4 — Rodar o Locust (headless, sem UI)

**Um único comando**, sem variáveis (o `locustfile.py` registra usuários automaticamente):

```bash
cd ~/Documentos/am-signature && source .venv/bin/activate && locust -f lokust/locustfile.py --host http://localhost:8000 --headless -u 20 -r 5 -t 60s --csv=report --html=report.html
```

---

### 🦗 Passo 5 — Rodar por categoria (tags)

```bash
# Só carrinho
locust -f lokust/locustfile.py --host http://localhost:8000 --headless -u 10 -r 5 -t 30s --tags cart

# Só autenticação
locust -f lokust/locustfile.py --host http://localhost:8000 --headless -u 10 -r 5 -t 30s --tags auth

# Concorrência de estoque
locust -f lokust/locustfile.py --host http://localhost:8000 --headless -u 20 -r 5 -t 30s --tags stock concurrency orders

# Stress progressivo (shape 10→50→100→200 em 3min)
locust -f lokust/stress_shape.py --headless --host http://localhost:8000
```

**Tags disponíveis:** `home`, `products`, `auth`, `wishlist`, `cart`, `variants`,
`stock`, `concurrency`, `checkout`, `purchase`, `orders`, `email`, `sessions`, `stress`.

---

### 🚀 Passo 6 — Rodar a bateria completa (script pronto)

O projeto inclui o `rodar_locust.sh` — ele faz 5 etapas (smoke, core, concorrência, compra, stress) em ~1 min:

```bash
cd ~/Documentos/am-signature
source .venv/bin/activate

chmod +x rodar_locust.sh
./rodar_locust.sh
```

O relatório final fica em `report.html` + `report_*.csv` na raiz.

---

### 🛑 Passo 7 — Parar / limpar

```bash
# Parar os containers (mantém o banco e volumes)
docker compose down

# Parar + apagar banco/volumes (reset total — perde dados)
docker compose down -v

# Ver logs completos de uma etapa
docker compose logs web --tail=200

# Entrar no shell do Django (para rodar manage.py avulso)
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py shell

# Sair da venv no host
deactivate
```

---

# 🧪 Testes de Carga — Detalhamento Técnico

Toda a suíte está em `lokust/locustfile.py`. O arquivo define uma classe
`StoreUser(HttpUser)` com `wait_time = between(0.5, 2.0)` — ou seja, cada
usuário virtual espera entre 0,5 s e 2 s antes de executar a próxima task.

## 🔧 Infraestrutura comum da suíte

Antes de qualquer task rodar, o método `on_start()` prepara o usuário virtual:

1. **Autenticação:**
   - Se `LOCUST_USERNAME` estiver definida → faz login com essas credenciais
     (útil para testes reproduzíveis e para exercitar um usuário pré-existente).
   - Se **não** estiver definida → registra automaticamente um usuário novo
     `locust_<uuid12>` com senha padrão `LocustTest@12345` e depois faz login.
     **Este é o caminho padrão** — por isso as variáveis de ambiente são
     opcionais.

2. **Descoberta de produtos:**
   - Faz `GET /products/`, extrai todos os IDs via regex `/products/(\d+)/`,
     guarda a lista e escolhe um produto inicial aleatório.

### Helpers internos usados por várias tasks

| Helper | O que faz |
|---|---|
| `csrf_from(html, client)` | Extrai o `csrfmiddlewaretoken` do HTML do formulário; se não encontrar, cai para o cookie `csrftoken`. |
| `hidden_fields(html)` | Retorna um `dict` com todos os `<input type="hidden">` do HTML. |
| `extract_product_ids(html)` | Regex `/products/(\d+)/` → lista de IDs de produto. |
| `extract_cart_item_ids(html)` | Regex `/orders/(?:remove\|update)/(\d+)/` → lista de IDs de itens do carrinho. |
| `extract_size_options(html)` | Regex em `<option>` → lista de tamanhos disponíveis (XS, S, M, L, XL, XXL). |
| `ensure_login()` | Re-loga se o cookie `sessionid` sumiu (sessão expirada). |
| `add_product()` | Fluxo completo: GET do produto → extrai CSRF + tamanhos → POST `/orders/add/<id>/`. |
| `place_order()` | Fluxo completo: verifica carrinho → GET `/orders/place-order/` → POST com nome/telefone/endereço → verifica redirect para `/orders/success/`. |

---

## 📖 As 20 tasks (com peso, tag, endpoints e o que valida)

As tasks possuem **pesos** (`@task(n)`) que definem a proporção de execução:
uma task com peso 5 roda 5× mais que uma task com peso 1.

---

### ✅ `test_01_home` — `home` — peso **3**

**O que faz:** simples `GET /`.

**O que valida:** status HTTP `200`.

**Por que importa:** é o caminho mais quente do site. Se cair, tudo cai junto.

---

### ✅ `test_02_product_list` — `products` — peso **5**

**O que faz:** chama `discover_products()` → `GET /products/`, extrai IDs
de todos os produtos da página e atualiza o cache interno do usuário virtual.

**O que valida:** status `200`.

**Por que importa:** a listagem é o "hub" que alimenta todos os outros testes
de produto. Também é o principal entrypoint de navegação real.

---

### ✅ `test_03_product_detail` — `products` — peso **5**

**O que faz:** pega um produto aleatório do cache (ou descobre novos se o cache
estiver vazio) e faz `GET /products/<id>/`.

**O que valida:** status `200`.

**Por que importa:** exercita a renderização de produto, incluindo o bloco de
tamanhos e a verificação de estoque (`ProductSize`).

---

### ✅ `test_04_login` — `auth` — peso **2**

**O que faz:**
1. `GET /accounts/login/` → extrai CSRF do formulário.
2. `POST /accounts/login/` com `username` e `password` (sem seguir redirect).

**O que valida:** `GET` deve retornar `200`; `POST` deve retornar `200` ou `302`.

**Por que importa:** o Django faz hashing de senha (PBKDF2 + salt) — é uma
das rotas mais caras em CPU do sistema. Esse teste mede o *throughput* real
do `authenticate()`.

---

### ✅ `test_05_logout` — `auth` — peso **1**

**O que faz:**
1. Garante que está logado (`ensure_login()`).
2. `GET /accounts/logout/` sem seguir redirect.
3. Faz login de novo (porque o teste precisa continuar logado para as próximas tasks).

**O que valida:** status `200` ou `302`.

**Por que importa:** testa a limpeza de sessão (cookie + tabela `django_session`)
e o comportamento das mensagens pendentes.

---

### ✅ `test_06_registration` — `auth` — peso **1**

**O que faz:**
1. Gera `username = locust_<uuid12>`, `email = <username>@example.com`,
   senha `LocustTest@12345`.
2. `GET /accounts/register/` → extrai CSRF + hidden fields.
3. `POST /accounts/register/` com `username`, `email`, `password1`, `password2`.

**O que valida:** `GET` = `200`; `POST` = `200` ou `302` (redirect para login
em caso de sucesso).

**Por que importa:** exercita criação de usuário, hashing de senha e validação
do `RegisterForm` (comparação `password1 == password2`). Cria lixo real no banco
(usuários `locust_*`) — é intencional, para simular pico de cadastros.

---

### ✅ `test_07_wishlist` — `wishlist` — peso **2**

**O que faz:**
1. `GET /products/wishlist/` para visualizar.
2. `GET /products/wishlist/add/<current_product>/` para adicionar um produto
   (sem seguir redirect).

**O que valida:** ambas as chamadas = `200` / `200`-ou-`302`.

**Por que importa:** exercita a tabela `Wishlist` + `WishlistItem`, o
`get_or_create()` que evita duplicatas, e o `select_related('product')` na view.

---

### ✅ `test_08_cart` — `cart` — peso **3**

**O que faz:** `GET /orders/` para visualizar o carrinho e, internamente,
extrair os IDs dos itens (`/orders/remove/<id>/` e `/orders/update/<id>/`).

**O que valida:** status `200`.

**Por que importa:** é a base dos testes 10 e 11 — se o carrinho não retorna
os IDs, os próximos testes não conseguem sequer disparar.

---

### ✅ `test_09_add_to_cart` — `cart` — peso **4**

**O que faz:** chama `add_product()`, que:
1. `GET /products/<id>/` para obter CSRF e os `<option>` de tamanho.
2. `POST /orders/add/<id>/` com `size` escolhido (primeiro tamanho disponível
   ou o definido em `LOCUST_SIZE`) + CSRF.

**O que valida:** `POST` retorna `200` ou `302`.

**Por que importa:** é o endpoint mais crítico do fluxo de compra. Também
valida a mensagem de erro `"Only N available for size X"` quando o estoque
`ProductSize.stock` está baixo — o teste passa mesmo com a mensagem porque a
view redireciona com `302`.

---

### ✅ `test_10_update_quantity` — `cart` — peso **3**

**O que faz:**
1. Descobre um item do carrinho (`discover_cart_item()`).
2. Se não houver, adiciona um primeiro via `add_product()`.
3. `GET /orders/` novamente para CSRF fresco.
4. `POST /orders/update/<item_id>/` com `action=increase`.

**O que valida:** `POST` retorna `200` (é um endpoint AJAX, retorna JSON com
`quantity`, `item_total`, `cart_total`).

**Por que importa:** valida a lógica de `update_cart_item` — inclusive o
`decrease` que remove o item quando `quantity` chega a 1 (o teste só exercita
o `increase`, mas o código do `decrease` é exercitado pelo teste 11 via remove).

---

### ✅ `test_11_remove_from_cart` — `cart` — peso **2**

**O que faz:**
1. Descobre ou cria um item no carrinho.
2. `GET /orders/remove/<item_id>/` sem seguir redirect.

**O que valida:** `200` ou `302`.

**Por que importa:** exercita o `get_object_or_404(CartItem, id=item_id, cart__user=request.user)` — que é a **única barreira** que impede um usuário de remover itens do carrinho de outro. Se esse teste começasse a falhar com 500, seria sinal de quebra no filtro de autorização.

---

### ✅ `test_12_size_variant` — `variants` — peso **2**

**O que faz:**
1. `GET /products/<id>/` → extrai `<option>` de tamanhos.
2. Escolhe um tamanho aleatório da lista.
3. Chama `add_product()` passando o `LOCUST_SIZE` já populado.

**O que valida:** o `POST` retorna `200` ou `302`.

**Por que importa:** força a view `add_to_cart` a percorrer o ramo
`product.has_sizes == True`, que faz `get_object_or_404(ProductSize, product, size)`
e valida `ps.stock > 0`. Produtos sem variante (sarees) são cobertos pelos
outros testes (test_09 usa qualquer produto do cache).

---

### ✅ `test_13_stock_concurrency` — `stock` + `concurrency` — peso **2**

**O que faz:** chama `add_product()` sob a tag `stock` e `concurrency`.

**O que valida:** `POST` retorna `200` ou `302`.

**Por que importa:** com **20–50 usuários simultâneos** disparando este teste,
vários deles tentam adicionar o mesmo tamanho ao carrinho ao mesmo tempo.
Se o backend tivesse uma race condition ingênua (ler `ps.stock` → decrementar
→ salvar), dois usuários poderiam "comprar" a última unidade. Aqui é onde
a correção com `select_for_update()` em `place_order()` se prova necessária
(e este teste é o detector do problema antes da correção).

> Este teste **não decrementa** estoque — o decremento só acontece em
> `place_order()`. O papel dele é popular carrinhos concorrentes, preparando
> o terreno para o `test_16` (que efetivamente fecha pedidos em paralelo).

---

### ✅ `test_14_checkout` — `checkout` — peso **2**

**O que faz:**
1. Garante que há um item no carrinho (senão adiciona).
2. `GET /orders/place-order/` para carregar o formulário de endereço.

**O que valida:** status `200`.

**Por que importa:** valida a pré-condição do checkout (a view redireciona
para `/orders/` se o carrinho estiver vazio — o teste garante que está cheio).
Não faz o `POST` (isso fica para o `test_15`).

---

### ✅ `test_15_complete_purchase` — `purchase` — peso **1**

**O que faz:** chama `place_order()`, que executa o fluxo completo:
1. Verifica se o carrinho tem itens (senão adiciona).
2. `GET /orders/place-order/` → extrai CSRF.
3. `POST /orders/place-order/` com `full_name`, `phone`, `address`.
4. Segue o redirect (`allow_redirects=True`) e verifica que a URL final
   contém `/orders/success/`.

**O que valida:** o pedido terminou em sucesso — ou seja, o backend:
- Fez `transaction.atomic()` inteiro.
- Fez `select_for_update()` no `ProductSize`.
- Criou `Order` + `OrderItem`s.
- Decrementou `ps.stock`.
- Deletou os `CartItem`s.
- Disparou e-mail de admin + cliente (as falhas de SMTP são silenciadas
  na view, então o teste passa mesmo se o Brevo estiver fora).

**Por que importa:** é o teste mais caro e mais crítico. Cada execução cria
uma linha em `orders_order`, N em `orders_orderitem` e consome estoque real.

---

### ✅ `test_16_concurrent_orders` — `orders` + `concurrency` — peso **1**

**O que faz:** chama o mesmo `place_order()` do teste 15, mas sob a tag
`concurrency` — executado com **20+ usuários simultâneos**.

**O que valida:** o pedido chega em `/orders/success/` (não 500, não 409).

**Por que importa:** aqui é onde se prova a **correção da race condition
de estoque**. Sem `select_for_update()`, dois usuários passariam na validação
`ps.stock >= item.quantity` ao mesmo tempo e ambos venderiam a mesma unidade.
Com a correção, o segundo espera o lock e recebe `messages.error(...)` +
redirect para `/orders/` (que o teste **não** considera falha — a falha só
ocorre em 500).

**Como interpretar o resultado:**
- `0` HTTP 500 → correção funcionando ✅
- Algum HTTP 500 → a transação estourou, provavelmente `IntegrityError` ou
  `DeadlockDetected` (não deveria acontecer com Postgres + `select_for_update`).

---

### ✅ `test_17_stock_integrity` — `stock` — peso **1**

**O que faz:** chama `add_product()` sob a tag `stock`.

**O que valida:** status `200` / `302`.

**Por que importa:** é o "termômetro de estoque" — em paralelo com os testes
13 e 16, ajuda a correlacionar falhas. Se o log mostrar `test_17` com sucesso
mas `test_16` com 500, o problema é claramente no *commit* do estoque, não
na leitura.

---

### ✅ `test_18_order_email_flow` — `email` — peso **1**

**O que faz:** chama `place_order()` sob a tag `email`.

**O que valida:** só o fluxo HTTP até `/orders/success/`. Não verifica SMTP.

**Por que importa:** a view `place_order` captura `Exception` ao redor de
`send_admin_order_email()` e `send_customer_order_email()` — se o Brevo
estiver fora do ar, o pedido **ainda assim** é concluído. Este teste garante
essa degradação graciosa: o sucesso não depende do provedor de e-mail.

> Se quiser **provar entrega real**, use um servidor SMTP fake
> (ex.: `mailhog`, `mailpit`) e inspecione a caixa de entrada manualmente.
> O Locust sozinho não tem como verificar entrega externa.

---

### ✅ `test_19_concurrent_sessions` — `sessions` — peso **2**

**O que faz:**
1. `GET /` (home, deslogado ou logado).
2. `ensure_login()`.
3. `GET /orders/` (carrinho).

**O que valida:** ambos `200`.

**Por que importa:** simula o usuário que abre a home em uma aba, o carrinho
em outra e mantém a sessão ativa entre as duas. Se houver vazamento de
sessão, o segundo `GET` falha com `302` para login.

---

### ✅ `test_20_stress` — `stress` — peso **1**

**O que faz:** escolhe aleatoriamente entre `GET /`, `GET /products/` e
`GET /orders/`.

**O que valida:** status **`< 500`** (aceita `200`, `302`, `403`, `404`).

**Por que importa:** é o teste de resiliência do servidor em si — sob carga
de 30+ usuários simultâneos, detecta se o gunicorn está derrubando workers
(erro clássico `worker timeout` / `502 Bad Gateway` se houver proxy).

---

## 📊 Resumo das tasks (tabela)

| # | Task | Tag | Peso | Endpoints | Correção testada |
|---|---|---|---|---|---|
| 01 | `test_01_home` | `home` | 3 | `GET /` | Renderização base |
| 02 | `test_02_product_list` | `products` | 5 | `GET /products/` | Listagem + cache de IDs |
| 03 | `test_03_product_detail` | `products` | 5 | `GET /products/<id>/` | Tamanhos + disponibilidade |
| 04 | `test_04_login` | `auth` | 2 | `GET/POST /accounts/login/` | Hashing PBKDF2 |
| 05 | `test_05_logout` | `auth` | 1 | `GET /accounts/logout/` | Limpeza de sessão |
| 06 | `test_06_registration` | `auth` | 1 | `GET/POST /accounts/register/` | Criação de usuário |
| 07 | `test_07_wishlist` | `wishlist` | 2 | `GET /products/wishlist/` + `/add/<id>/` | `get_or_create` + `select_related` |
| 08 | `test_08_cart` | `cart` | 3 | `GET /orders/` | Extração de item IDs |
| 09 | `test_09_add_to_cart` | `cart` | 4 | `GET product` + `POST /orders/add/<id>/` | Validação de estoque |
| 10 | `test_10_update_quantity` | `cart` | 3 | `GET /orders/` + `POST /orders/update/<id>/` | AJAX de quantidade |
| 11 | `test_11_remove_from_cart` | `cart` | 2 | `GET /orders/remove/<id>/` | Autorização por `cart__user` |
| 12 | `test_12_size_variant` | `variants` | 2 | `POST /orders/add/<id>/` com `size` | `ProductSize.stock` |
| 13 | `test_13_stock_concurrency` | `stock`, `concurrency` | 2 | `POST /orders/add/<id>/` | Carrinhos concorrentes |
| 14 | `test_14_checkout` | `checkout` | 2 | `GET /orders/place-order/` | Pré-condição do form |
| 15 | `test_15_complete_purchase` | `purchase` | 1 | `GET` + `POST /orders/place-order/` | `transaction.atomic` + email |
| 16 | `test_16_concurrent_orders` | `orders`, `concurrency` | 1 | `POST /orders/place-order/` | **Race condition de estoque** |
| 17 | `test_17_stock_integrity` | `stock` | 1 | `POST /orders/add/<id>/` | Correlação com #16 |
| 18 | `test_18_order_email_flow` | `email` | 1 | `POST /orders/place-order/` | Degradação graciosa se SMTP cair |
| 19 | `test_19_concurrent_sessions` | `sessions` | 2 | `GET /` + `GET /orders/` | Sessão entre abas |
| 20 | `test_20_stress` | `stress` | 1 | `GET /`, `/products/`, `/orders/` | Resiliência do gunicorn |

---

## 🎯 `stress_shape.py` — Perfil progressivo

Arquivo separado (`lokust/stress_shape.py`) contendo a classe
`StressShape(LoadTestShape)` com 4 estágios:

| Estágio | Duração | Usuários | Spawn rate |
|---|---|---|---|
| 1 | 30 s | 10 | 2/s |
| 2 | 60 s | 50 | 5/s |
| 3 | 120 s | 100 | 10/s |
| 4 | 180 s | 200 | 20/s |

Total: **3 minutos subindo até 200 usuários** simultâneos. Ideal para achar
o "joelho" de degradação do gunicorn.

> ⚠️ **Importante:** nunca importar `stress_shape.py` dentro de
> `locustfile.py` — o Locust auto-detecta qualquer `LoadTestShape` e passa
> a ignorar `-u / -r / -t`. Por isso ele vive em arquivo separado e deve
> ser invocado com `-f lokust/stress_shape.py`.

---

## 📜 `rodar_locust.sh` — Bateria completa em ~1 min

Executa 5 fases encadeadas, interrompendo se o servidor estiver fora:

| Fase | Users | Spawn | Duração | Tags | Objetivo |
|---|---|---|---|---|---|
| 1. **SMOKE** | 5 | 2 | 8 s | (todas) | Teste rápido + gerar `report.html` |
| 2. **CORE** | 10 | 5 | 10 s | `products home auth wishlist cart variants checkout` | Fluxos principais |
| 3. **CONCORRÊNCIA** | 20 | 5 | 10 s | `stock concurrency orders` | Race conditions de estoque |
| 4. **COMPRA** | 5 | 2 | 8 s | `purchase email sessions` | Fluxo real de compra (usa `customer`) |
| 5. **STRESS** | 30 | 10 | 8 s | `stress` | Resiliência do gunicorn |

Antes de rodar, o script valida:
- `manage.py` existe na raiz
- `.venv` existe e ativa
- `locust` está instalado
- Sintaxe do `locustfile.py` compila
- **Não há `LoadTestShape`** no locustfile (senão `-u/-r/-t` seriam ignorados)
- Servidor responde em `http://localhost:8000`

> ℹ️ A Fase 4 (COMPRA) do `rodar_locust.sh` **exporta** `LOCUST_USERNAME=customer`
> internamente porque essa fase precisa de um usuário real para exercitar o
> fluxo completo de compra. As demais fases funcionam com o auto-registro.

---

## 🧪 Interpretação dos resultados

Após rodar o Locust, o `report.html` mostra três tabelas principais:

### 1. Requests Statistics
- **# Requests** — total de requisições por endpoint.
- **# Fails** — quantas falharam (esperado: `0`).
- **Median / 95%ile / 99%ile (ms)** — distribuição de latência.
- **RPS** — requisições por segundo.

### 2. Response Time Statistics
Percentis completos (50% a 100%). Útil para detectar *outliers*: se o
`99%ile` disparar mas a mediana ficar baixa, há uma rota específica lenta
(geralmente `POST /orders/place-order/` por causa do `select_for_update`).

### 3. Failures Statistics
**Esperado: tabela vazia.** Qualquer linha aqui indica HTTP 4xx/5xx ou
`CatchResponseError`.

### 🚨 Sinais de alerta

| Sintoma | Causa provável |
|---|---|
| HTTP 500 em `/orders/place-order/` | Race condition **não corrigida** no `select_for_update()` |
| HTTP 502 em qualquer rota | Gunicorn morreu (`worker timeout`) |
| HTTP 403 em `/orders/remove/` | Quebra no filtro de autorização |
| Latência `95%ile` > 1000 ms | Banco de dados subdimensionado ou `pool` mal configurado |
| `CatchResponseError('HTTP 0')` | Servidor caiu no meio do teste (conexão recusada) |

---

## 🔗 Créditos

- **Projeto original:** [JESMARIYA-ARUN/am-signature](https://github.com/JESMARIYA-ARUN/am-signature) — criado por Jesmariya Arun como projeto final de Full Stack Development.
- **Modificações (Locust + ajustes Docker):** contribuição deste repositório.

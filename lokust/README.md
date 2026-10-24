# Locust — A&M Signature

Esta pasta concentra os testes de carga do projeto Django `am-signature`.

## Testes implementados

1. Página inicial
2. Lista de produtos
3. Detalhe de produto
4. Login
5. Logout
6. Cadastro
7. Wishlist
8. Visualização do carrinho
9. Adicionar ao carrinho
10. Alterar quantidade
11. Remover do carrinho
12. Variante/tamanho
13. Concorrência de estoque
14. Checkout
15. Compra completa
16. Pedidos concorrentes
17. Integridade do estoque
18. Fluxo de e-mail do pedido
19. Sessões simultâneas
20. Stress

## Instalação

Dentro da virtualenv do projeto:

```bash
pip install locust
```

## Configuração recomendada

Defina pelo menos um usuário real de teste:

```bash
export LOCUST_USERNAME="usuario_de_teste"
export LOCUST_PASSWORD="senha_do_usuario"
```

Opcionalmente, fixe um produto:

```bash
export LOCUST_PRODUCT_ID="1"
export LOCUST_SIZE="M"
```

Também é possível definir:

```bash
export LOCUST_FULL_NAME="Locust Test User"
export LOCUST_PHONE="84999999999"
export LOCUST_ADDRESS="Rua Locust, 100"
```

Se `LOCUST_USERNAME` não for informado, o teste tenta criar usuários automaticamente com nomes `locust_...`.

## Execução

### Interface web

```bash
cd ~/Documentos/am-signature
source .venv/bin/activate
locust -f lokust/locustfile.py
```

Depois abra a interface indicada pelo Locust.

### Execução sem interface

Exemplo com 20 usuários por 60 segundos:

```bash
locust -f lokust/locustfile.py \
  --headless \
  -u 20 \
  -r 5 \
  -t 60s
```

### Testar somente uma categoria

Exemplo:

```bash
locust -f lokust/locustfile.py \
  --headless \
  -u 20 \
  -r 5 \
  -t 60s \
  --tags cart
```

Tags disponíveis:

- `home`
- `products`
- `auth`
- `wishlist`
- `cart`
- `variants`
- `stock`
- `concurrency`
- `checkout`
- `purchase`
- `orders`
- `email`
- `sessions`
- `stress`

### Stress progressivo

O arquivo também possui `StressShape`.

```bash
locust -f lokust/locustfile.py \
  --headless \
  --shape-class StressShape
```

O perfil sobe progressivamente para 10, 50, 100 e 200 usuários.

## Observação importante sobre estoque

O teste 13/16 coloca vários usuários Locust para executar operações concorrentes. Isso serve para procurar problemas de corrida no estoque.

Para avaliar o resultado, observe:

- quantidade de requisições com erro;
- HTTP 500;
- pedidos aceitos quando o estoque deveria estar esgotado;
- quantidade final do estoque;
- quantidade de pedidos criados.

O código atual valida o estoque antes do `select_for_update()`. O teste de concorrência é especialmente útil para verificar esse comportamento sob carga real.

## Observação importante sobre e-mail

O teste 18 verifica o fluxo HTTP do pedido até `/orders/success/`.

Ele não consegue provar que uma mensagem chegou ao servidor SMTP externo porque a própria view captura exceções de e-mail e continua o fluxo do pedido.

Para validar entrega SMTP de verdade, use um servidor de teste de e-mail ou verifique o serviço de e-mail configurado.

## Endpoints usados

Os testes foram montados de acordo com as URLs fornecidas:

- `/`
- `/products/`
- `/products/<id>/`
- `/products/wishlist/`
- `/products/wishlist/add/<id>/`
- `/accounts/register/`
- `/accounts/login/`
- `/accounts/logout/`
- `/orders/`
- `/orders/add/<id>/`
- `/orders/update/<id>/`
- `/orders/remove/<id>/`
- `/orders/place-order/`
- `/orders/success/`

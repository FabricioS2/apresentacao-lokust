#!/usr/bin/env bash
# ============================================================
# Locust — bateria completa v5 (realmente < 1min)
# Requer: StressShape REMOVIDO de lokust/locustfile.py
# ============================================================

PROJECT_DIR="$HOME/Documentos/am-signature"
HOST="http://localhost:8000"
LOCUST_FILE="lokust/locustfile.py"
LOG="locust_$(date +%Y%m%d_%H%M%S).log"

exec > >(tee -a "$LOG") 2>&1
START_TS=$(date +%s)

echo "════════════════════════════════════════════════════════"
echo " 0. VALIDAÇÕES"
echo "════════════════════════════════════════════════════════"

[ ! -d "$PROJECT_DIR" ] && { echo "✖ Pasta: $PROJECT_DIR"; read -r -p "ENTER..." _; exit 1; }
cd "$PROJECT_DIR" || { echo "✖ cd falhou"; read -r -p "ENTER..." _; exit 1; }
[ ! -f ".venv/bin/activate" ] && { echo "✖ Sem .venv"; read -r -p "ENTER..." _; exit 1; }
# shellcheck disable=SC1091
source .venv/bin/activate

command -v locust >/dev/null 2>&1 || { echo "✖ locust não instalado"; read -r -p "ENTER..." _; exit 1; }
echo "✔ $(locust --version)"
python -m py_compile "$LOCUST_FILE" 2>/dev/null && echo "✔ Sintaxe OK" || { echo "✖ Sintaxe"; read -r -p "ENTER..." _; exit 1; }

# Sanity: garantir que NÃO há LoadTestShape no locustfile
if grep -q "LoadTestShape" "$LOCUST_FILE"; then
  echo "✖ '$LOCUST_FILE' ainda contém 'LoadTestShape'."
  echo "  Remova/Comente a classe StressShape (veja instruções) ou os -t serão ignorados."
  read -r -p "ENTER..." _; exit 1
fi
echo "✔ Sem LoadTestShape em $LOCUST_FILE (good)"

CODE=$(curl -s -o /dev/null --max-time 2 -w "%{http_code}" "$HOST/")
[ "$CODE" = "000" ] && { echo "✖ Django fora em $HOST"; read -r -p "ENTER..." _; exit 1; }
echo "✔ Servidor OK ($CODE)"

# ------------------------------------------------------------------
run_locust() {
  echo
  echo "────────────────────────────────────────────────────────"
  echo " $*"
  echo "────────────────────────────────────────────────────────"
  locust -f "$LOCUST_FILE" --host "$HOST" "$@" || \
    echo "⚠ locust saiu com código $? (não fatal)"
}

# ------------------------------------------------------------------
echo
echo " 1/5 SMOKE — todas as tasks (8s, com CSV/HTML)"
run_locust --headless -u 5 -r 2 -t 8s --csv=report --html=report.html

echo
echo " 2/5 CORE — products, home, auth, wishlist, cart, variants, checkout (10s)"
run_locust --headless -u 10 -r 5 -t 10s \
  --tags products home auth wishlist cart variants checkout

echo
echo " 3/5 CONCORRÊNCIA — stock, concurrency, orders (10s)"
run_locust --headless -u 20 -r 5 -t 10s \
  --tags stock concurrency orders

echo
echo " 4/5 COMPRA — purchase, email, sessions (8s)"
export LOCUST_USERNAME=customer
export LOCUST_PASSWORD=Customer@123
export LOCUST_PRODUCT_ID=1
export LOCUST_SIZE=M
run_locust --headless -u 5 -r 2 -t 8s \
  --tags purchase email sessions

echo
echo " 5/5 STRESS — tag stress (8s, 30 users, spawn 10)"
run_locust --headless -u 30 -r 10 -t 8s --tags stress

# ------------------------------------------------------------------
END_TS=$(date +%s)
echo
echo "════════════════════════════════════════════════════════"
echo " ✅ BATERIA COMPLETA em $((END_TS - START_TS))s"
echo "════════════════════════════════════════════════════════"
echo " Log:      $(pwd)/$LOG"
echo " Relatório: report.html | report_stats.csv | report_failures.csv"
echo
echo " Achados esperados nesta carga:"
echo "  • POST /orders/place-order/ SEM 500 → race condition corrigida ✓"
echo "  • GET /accounts/* e /products/ SEM 500 → gunicorn OK ✓"
echo "  • Para load test real: locust -f lokust/stress_shape.py --headless --host http://localhost:8000"
echo
read -r -p "Pressione ENTER para fechar..." _
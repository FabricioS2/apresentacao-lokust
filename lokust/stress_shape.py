"""
Perfil de stress progressivo — isolado em arquivo próprio.

Uso (SOMENTE quando quiser rodar stress real de 3 min):
    locust -f lokust/stress_shape.py --headless --host http://localhost:8000

⚠ NUNCA importe este arquivo em locustfile.py. O Locust auto-detecta
qualquer LoadTestShape e passa a ignorar -u / -r / -t.
"""
from locust import LoadTestShape

# Locust precisa achar a User class. Import relativo funciona porque
# o Locust adiciona lokust/ ao sys.path quando carrega -f lokust/stress_shape.py.
from locustfile import StoreUser  # noqa: F401


class StressShape(LoadTestShape):
    """
    10 → 50 → 100 → 200 users em 3 minutos.

    Se quiser tudo em 30s, use:
        stages = [
            {"duration": 10, "users": 20,  "spawn_rate": 5},
            {"duration": 20, "users": 50,  "spawn_rate": 10},
            {"duration": 30, "users": 100, "spawn_rate": 20},
        ]
    """

    stages = [
        {"duration": 30,  "users": 10,  "spawn_rate": 2},
        {"duration": 60,  "users": 50,  "spawn_rate": 5},
        {"duration": 120, "users": 100, "spawn_rate": 10},
        {"duration": 180, "users": 200, "spawn_rate": 20},
    ]

    def tick(self):
        run_time = self.get_run_time()
        for stage in self.stages:
            if run_time < stage["duration"]:
                return stage["users"], stage["spawn_rate"]
        return None

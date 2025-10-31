# Tycherion — MT5 MVP (Hexagonal, com Watchlist e Use Cases)

## Visão

MVP de automação para MetaTrader 5 em arquitetura Hexagonal (Ports & Adapters).

- **Domain**: regras (estratégias) independentes de tecnologia.
- **Ports**: contratos (interfaces) para dados de mercado, trading, conta e watchlist.
- **Adapters**: implementações concretas (aqui, MT5).
- **Application (Use Cases)**: orquestra casos de uso chamando apenas **Ports**. Não conhece adapters.

Termo financeiro: **watchlist** = conjunto de instrumentos a monitorar/negociar (sinônimo prático de “universe”).
Mantivemos “watchlist” por ser mais claro ao usuário e comum em mesas/traders.

## Como rodar

1. Abra o Terminal do MT5 e faça login em **DEMO** (ou configure `.env` com login/senha).
2. Crie e ative um venv. Instale:
   - `pip install -r requirements.txt` **(modo dev simples)**, ou
   - `pip install -e .` **(editable)**, ou
   - `pip install .` **(build formal)**.
3. Execute: `python scripts/run_demo.py`.

Por padrão está em **DRY_RUN** e **require_demo=true**. Nada é enviado em conta real.

## Config (resumo)

Arquivo `configs/demo.yaml`:

- `symbol`: compat de `run_once` (um ativo único).
- `timeframe`, `lookback_days`.
- `strategy.sma_cross.fast_period/slow_period`.
- `trading`: `dry_run`, `require_demo`, `deviation_points`, `volume_mode`, `fixed_volume`.
- `application.usecase.name`: nome do caso de uso (ex.: `sma_cross`).
- `application.watchlist`: modo/itens da watchlist (static | market_watch | pattern).
- `application.scan`: política de loop contínuo.

## Layout

```bash
src/tycherion/
├─ app/                        # Composition root (wiring)
├─ application/
│  ├─ usecases/                # Casos de uso (orquestração via Ports)
│  │  ├─ run_sma_cross.py
│  │  └─ loop_engine.py
│  └─ services/
│     └─ watchlist_service.py  # serviços de aplicação (ranking/filtragem)
├─ domain/
│  └─ strategies/
│     └─ sma_cross.py
├─ ports/                      # Ports (interfaces) – sem dependência de MT5
│  ├─ market_data.py
│  ├─ trading.py
│  ├─ account.py
│  └─ watchlist.py
├─ adapters/mt5/               # Adapters – usam a lib MetaTrader5
│  ├─ market_data_mt5.py
│  ├─ trading_mt5.py
│  ├─ account_mt5.py
│  └─ watchlist_mt5.py
└─ shared/
   ├─ config.py                # leitura de YAML/.env tipada
   ├─ decorators.py            # @demo_only, @logged
   └─ types.py
```

## Avisos

- Educacional. Risco financeiro existe.
- Envio em REAL bloqueado por padrão (require_demo=true).

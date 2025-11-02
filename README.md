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
Tycherion/
├─ configs/
│  └─ demo.yaml                 ← Config principal do MVP (sem segredos; .env tem precedência)
├─ scripts/
│  └─ run_demo.py               ← Entrypoint: injeta src/ e chama o app
├─ src/
│  └─ tycherion/
│     ├─ app/
│     │  └─ main.py             ← Composition root: carrega config, inicializa MT5 e delega ao run_mode
│     ├─ application/
│     │  ├─ runmodes/
│     │  │  └─ live_multimodel.py  ← Loop “live” que orquestra tudo (MVP)
│     │  ├─ services/
│     │  │  ├─ coverage_selector.py  ← Seleção de símbolos (coverage) a partir do universo
│     │  │  ├─ ensemble.py           ← Combina decisões de múltiplos modelos
│     │  │  └─ sizer.py              ← Regras simples de sizing (min|fixed)
│     │  └─ plugins/
│     │     └─ registry.py        ← Registro/descoberta de indicators e models por tags/playbook
│     ├─ domain/
│     │  ├─ indicators/
│     │  │  ├─ trend_donchian.py  ← Exemplo: canal de Donchian (mede “trend”)
│     │  │  ├─ volatility_atr.py  ← Exemplo: ATR (mede “volatility”)
│     │  │  └─ stretch_zscore.py  ← Exemplo: Z-score (mede “stretch”/distância da média)
│     │  └─ models/
│     │     ├─ trend_following.py ← Modelo de tendência (usa trend + volatility)
│     │     └─ mean_reversion.py  ← Modelo de reversão (usa stretch + volatility)
│     ├─ ports/
│     │  ├─ market_data.py        ← Interface p/ dados de mercado (bars/candles)
│     │  ├─ trading.py            ← Interface p/ execução (comprar/vender)
│     │  ├─ account.py            ← Interface p/ info da conta
│     │  └─ universe.py           ← Interface p/ universo de símbolos (visíveis, por padrão)
│     ├─ adapters/
│     │  └─ mt5/
│     │     ├─ market_data_mt5.py ← Implementação MT5 do MarketDataPort
│     │     ├─ trading_mt5.py     ← Implementação MT5 do TradingPort
│     │     ├─ account_mt5.py     ← Implementação MT5 do AccountPort
│     │     └─ universe_mt5.py    ← Implementação MT5 do UniversePort
│     └─ shared/
│        ├─ config.py             ← Carregador de YAML + .env (com precedência do .env)
│        ├─ decorators.py         ← @demo_only (bloqueia real), @logged (logs simples)
│        └─ types.py              ← Tipos auxiliares
├─ .env.example                   ← Exemplo de variáveis sensíveis (login/servidor)
├─ requirements.txt               ← Dependências p/ quem não quiser usar editable
└─ pyproject.toml                 ← Empacotamento/instalação (pip install -e .)

```

## Avisos

- Educacional. Risco financeiro existe.
- Envio em REAL bloqueado por padrão (require_demo=true).

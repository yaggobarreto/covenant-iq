"""A fabricated quarterly financial statement excerpt for the same
fictional borrower as sample_agreement.py — deliberately written so the
DSCR covenant comes out breached (matching the "Aurora Indústria Ltda —
DSCR ≥ 1.20x — Breach" row in docs/dashboard.png) while leverage stays
compliant, so the demo exercises both a pass and a fail in one run.
"""

from __future__ import annotations

PERIOD_LABEL = "2026-T3"

STATEMENT_TEXT = """\
AURORA INDÚSTRIA E COMÉRCIO LTDA.
Demonstrativo Financeiro Resumido — 3º Trimestre de 2026

1. Indicadores de Endividamento
Dívida Líquida em 30/09/2026: R$ 19.762.000,00
EBITDA acumulado nos últimos 12 meses: R$ 8.200.000,00
(Dívida Líquida / EBITDA = 2,41x)

2. Serviço da Dívida
Geração de caixa operacional disponível para serviço da dívida no trimestre: \
R$ 1.744.000,00
Serviço da dívida devido no trimestre (principal + juros): R$ 1.600.000,00
(Índice de Cobertura do Serviço da Dívida = 1,09x)

3. Posição de Caixa
Caixa e equivalentes de caixa em 30/09/2026: R$ 2.180.000,00
"""

"""A fabricated, two-page credit agreement excerpt used for the demo script
and as documentation of the input shape the API expects. The borrower
("Aurora Indústria e Comércio Ltda.") is the same fictional company used in
the dashboard mockup in docs/dashboard.png, for continuity across the
project's demo material. None of this describes a real company or deal.
"""

from __future__ import annotations

PAGE_1 = """\
INSTRUMENTO PARTICULAR DE CONTRATO DE EMPRÉSTIMO

CREDOR: Fundo de Investimento em Direitos Creditórios Meridiano
DEVEDORA: Aurora Indústria e Comércio Ltda., pessoa jurídica de direito \
privado, doravante denominada "Devedora".

CLÁUSULA 1 — DO OBJETO
O Credor concede à Devedora um empréstimo no valor principal de \
R$ 8.200.000,00 (oito milhões e duzentos mil reais), sujeito aos encargos \
e condições descritos neste instrumento.

CLÁUSULA 2 — DA REMUNERAÇÃO
Sobre o valor principal incidirão juros remuneratórios de 14,5% (quatorze \
inteiros e cinco décimos por cento) ao ano, calculados sobre o saldo devedor.

CLÁUSULA 3 — DO VENCIMENTO
O vencimento final desta operação ocorrerá em 30 de junho de 2029, ressalvadas \
as hipóteses de vencimento antecipado previstas na Cláusula 6.
"""

PAGE_2 = """\
CLÁUSULA 4 — DOS COVENANTS FINANCEIROS

4.1. Índice de Alavancagem. A Devedora obriga-se a manter, ao final de cada \
trimestre civil, razão entre Dívida Líquida e EBITDA (apurados nos últimos \
doze meses) igual ou inferior a 3,00x (três vezes). O descumprimento desta \
obrigação não estará sujeito a prazo de cura.

4.2. Índice de Cobertura do Serviço da Dívida. A Devedora obriga-se a manter, \
ao final de cada trimestre civil, o Índice de Cobertura do Serviço da Dívida \
("DSCR"), apurado nos termos do Anexo II, igual ou superior a 1,20x (um \
vírgula vinte). Em caso de descumprimento, a Devedora terá prazo de cura de \
30 (trinta) dias corridos, contados da respectiva data de apuração, para \
regularizar o índice antes de caracterizado o vencimento antecipado.

CLÁUSULA 5 — DAS OBRIGAÇÕES DE REPORTE
A Devedora obriga-se a enviar ao Credor, em até 30 (trinta) dias após o \
encerramento de cada trimestre civil, suas demonstrações financeiras \
acompanhadas do demonstrativo de apuração dos índices previstos na \
Cláusula 4.
"""

AGREEMENT_PAGES: list[dict[str, object]] = [
    {"page": 1, "text": PAGE_1},
    {"page": 2, "text": PAGE_2},
]

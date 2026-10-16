"""Finalidades do vídeo: um clique ajusta público, objetivo e tom da narração."""

FINALIDADES = [
    {"id": "onboarding_colaboradores", "nome": "Onboarding de colaboradores", "icone": "users",
     "publico": "novos colaboradores", "objetivo": "ensinar a usar o produto no dia a dia", "tom": "acolhedor e didático"},
    {"id": "onboarding_clientes", "nome": "Onboarding de clientes", "icone": "handshake",
     "publico": "novos clientes", "objetivo": "mostrar como começar e gerar valor rápido", "tom": "claro, confiante e didático"},
    {"id": "capacitacao_cs", "nome": "Capacitação de CS", "icone": "headset",
     "publico": "time de Customer Success", "objetivo": "capacitar para apoiar clientes no uso do produto",
     "tom": "técnico e prático"},
    {"id": "time_comercial", "nome": "Time comercial", "icone": "chart",
     "publico": "time comercial e pré-venda", "objetivo": "demonstrar valor e diferenciais em uma apresentação",
     "tom": "objetivo e persuasivo, com foco em valor"},
    {"id": "marketing", "nome": "Marketing", "icone": "megaphone",
     "publico": "mercado e potenciais clientes", "objetivo": "despertar interesse pelo produto",
     "tom": "inspirador e direto"},
    {"id": "suporte", "nome": "Suporte e tutorial", "icone": "lifebuoy",
     "publico": "usuários do produto", "objetivo": "explicar passo a passo como fazer uma tarefa",
     "tom": "simples, passo a passo"},
]
POR_ID = {f["id"]: f for f in FINALIDADES}


def aplicar(briefing: dict) -> dict:
    """Preenche público, objetivo e tom vazios a partir da finalidade escolhida."""
    f = POR_ID.get(briefing.get("finalidade") or "")
    if f:
        for campo in ("publico", "objetivo", "tom"):
            if not briefing.get(campo):
                briefing[campo] = f[campo]
    return briefing

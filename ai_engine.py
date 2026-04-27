import json
from typing import List, Dict

from services.ai_client import AIClientError, generate_financial_response

CATEGORIES = [
    'Alimentação', 'Transporte', 'Saúde', 'Lazer', 'Compras', 'Assinaturas', 'Serviços', 'Outros'
]


def _extract_json(text: str):
    raw = text.strip()
    if raw.startswith('```'):
        raw = raw.split('\n', 1)[1]
        raw = raw.rsplit('```', 1)[0]
    return json.loads(raw)


def categorize_transactions(transactions: List[Dict]) -> List[Dict]:
    if not transactions:
        return []

    prompt = {
        'instrucao': 'Classifique cada transação em uma categoria permitida.',
        'categorias_permitidas': CATEGORIES,
        'saida_json': {'items': [{'index': 0, 'category': 'Alimentação'}]},
        'transacoes': transactions,
    }

    try:
        text = generate_financial_response(
            prompt=json.dumps(prompt, ensure_ascii=False),
            system_instruction='Você responde somente JSON válido e objetivo.'
        )
        data = _extract_json(text)
        mapping = {int(i['index']): i['category'] for i in data.get('items', []) if i.get('category') in CATEGORIES}
        return [{**t, 'category': mapping.get(idx, 'Outros')} for idx, t in enumerate(transactions)]
    except Exception:
        return [{**t, 'category': 'Outros'} for t in transactions]


def convert_goal_to_plan(goal_text, income, expenses_summary) -> Dict:
    fallback = {
        'title': 'Meta personalizada',
        'target_amount': 0.0,
        'deadline': '12 meses',
        'weekly_actions': ['Separar um valor fixo por semana.', 'Revisar gastos e cortar excessos.'],
        'monthly_milestones': ['Guardar o valor planejado do mês.', 'Acompanhar o progresso da meta.'],
        'annual_projection': 'Com constância, você avança no seu objetivo durante o ano.'
    }

    payload = {
        'objetivo_usuario': goal_text,
        'renda_mensal': income,
        'resumo_gastos': expenses_summary,
        'saida': {
            'title': 'string',
            'target_amount': 'float',
            'deadline': 'string',
            'weekly_actions': ['string'],
            'monthly_milestones': ['string'],
            'annual_projection': 'string'
        }
    }

    try:
        text = generate_financial_response(
            prompt=json.dumps(payload, ensure_ascii=False),
            system_instruction='Escreva em português do Brasil simples, acolhedor e retorne somente JSON.'
        )
        return _extract_json(text)
    except Exception:
        return fallback


def generate_financial_plan(income, expenses_by_category, investments_summary, goals, balance) -> Dict:
    negative = balance < 0
    fallback = {
        'situacao_atual': 'Ainda não consegui analisar com IA agora, mas seus dados já estão salvos.',
        'orcamento_semanal': 'Divida seus gastos essenciais por 4 semanas e reserve um valor para imprevistos.',
        'meta_poupanca_mensal': max(0.0, income * 0.1),
        'projecao_anual': 'Com consistência mensal, seu cenário tende a melhorar ao longo de 12 meses.',
        'recomendacoes': [
            'Anote os gastos da semana e compare com sua renda.',
            'Defina um teto para gastos não essenciais.'
        ],
        'alertas': [],
        'resumo_saude': 'Seu painel segue funcionando normalmente para controle manual.'
    }

    payload = {
        'renda_total': income,
        'gastos_por_categoria': expenses_by_category,
        'resumo_investimentos': investments_summary,
        'metas': goals,
        'saldo_mensal': balance,
        'saida': {
            'situacao_atual': 'string',
            'orcamento_semanal': 'string',
            'meta_poupanca_mensal': 'float',
            'projecao_anual': 'string',
            'recomendacoes': ['string'],
            'alertas': ['string'],
            'resumo_saude': 'string',
            'plano_emergencia': 'string somente quando saldo negativo'
        }
    }

    try:
        text = generate_financial_response(
            prompt=json.dumps(payload, ensure_ascii=False),
            system_instruction='Português do Brasil simples, calmo e direto. Sem jargão. Retorne apenas JSON válido.'
        )
        data = _extract_json(text)
        if negative:
            recs = data.get('recomendacoes') or []
            if not recs or 'recuper' not in recs[0].lower():
                data['recomendacoes'] = [
                    'Plano de recuperação: corte gastos não essenciais imediatamente, renegocie dívidas e reserve um valor semanal fixo para sair do negativo.'
                ] + recs
            if not data.get('plano_emergencia'):
                data['plano_emergencia'] = 'Priorize contas essenciais, pause gastos opcionais por 30 dias e negocie dívidas com parcelas que caibam no seu orçamento.'
        return data
    except AIClientError as exc:
        fallback['alertas'] = [exc.message]
        if negative:
            fallback['plano_emergencia'] = 'Priorize contas essenciais, pause gastos opcionais por 30 dias e negocie dívidas com parcelas que caibam no seu orçamento.'
            fallback['recomendacoes'] = [
                'Plano de recuperação: corte gastos não essenciais imediatamente, renegocie dívidas e reserve um valor semanal fixo para sair do negativo.',
                *fallback['recomendacoes']
            ]
        return fallback
    except Exception:
        fallback['alertas'] = ['Não foi possível gerar o plano com IA agora. Tente novamente em alguns instantes.']
        return fallback

import json
import os
from typing import List, Dict
from groq import Groq

MODEL = 'llama-3.1-70b-versatile'
CATEGORIES = [
    'Alimentação', 'Transporte', 'Saúde', 'Lazer', 'Compras', 'Assinaturas', 'Serviços', 'Outros'
]


def _client():
    key = os.getenv('GROQ_API_KEY')
    if not key:
        return None
    return Groq(api_key=key)


def _extract_json(text: str):
    text = text.strip()
    if text.startswith('```'):
        text = text.split('\n', 1)[1]
        text = text.rsplit('```', 1)[0]
    return json.loads(text)


def categorize_transactions(transactions: List[Dict]) -> List[Dict]:
    client = _client()
    if not client:
        enriched = []
        for t in transactions:
            item = dict(t)
            item['category'] = 'Outros'
            enriched.append(item)
        return enriched

    prompt = {
        'instrucao': 'Classifique cada transação em uma categoria permitida.',
        'categorias_permitidas': CATEGORIES,
        'retorno': 'JSON array com objetos: index, category',
        'transacoes': transactions,
    }

    try:
        completion = client.chat.completions.create(
            model=MODEL,
            temperature=0.1,
            response_format={'type': 'json_object'},
            messages=[
                {'role': 'system', 'content': 'Você responde apenas JSON válido.'},
                {'role': 'user', 'content': json.dumps(prompt, ensure_ascii=False)},
            ],
        )
        data = _extract_json(completion.choices[0].message.content)
        mapping = {int(i['index']): i['category'] for i in data.get('items', []) if i.get('category') in CATEGORIES}
        result = []
        for idx, t in enumerate(transactions):
            item = dict(t)
            item['category'] = mapping.get(idx, 'Outros')
            result.append(item)
        return result
    except Exception:
        return [{**t, 'category': 'Outros'} for t in transactions]


def convert_goal_to_plan(goal_text, income, expenses_summary) -> Dict:
    client = _client()
    fallback = {
        'title': 'Meta personalizada',
        'target_amount': 0.0,
        'deadline': '12 meses',
        'weekly_actions': ['Separar um valor fixo por semana.', 'Revisar gastos e cortar excessos.'],
        'monthly_milestones': ['Guardar o valor planejado do mês.', 'Acompanhar o progresso da meta.'],
        'annual_projection': 'Com constância, você avança no seu objetivo durante o ano.'
    }
    if not client:
        return fallback

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
        completion = client.chat.completions.create(
            model=MODEL,
            temperature=0.2,
            response_format={'type': 'json_object'},
            messages=[
                {'role': 'system', 'content': 'Escreva em português do Brasil simples e acolhedor. Retorne só JSON.'},
                {'role': 'user', 'content': json.dumps(payload, ensure_ascii=False)}
            ]
        )
        return _extract_json(completion.choices[0].message.content)
    except Exception:
        return fallback


def generate_financial_plan(income, expenses_by_category, investments_summary, goals, balance) -> Dict:
    client = _client()
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
        'alertas': ['Não foi possível conectar à IA no momento. Tente novamente em instantes.'],
        'resumo_saude': 'Seu painel segue funcionando normalmente para controle manual.'
    }
    if negative:
        fallback['plano_emergencia'] = 'Priorize contas essenciais, pause gastos opcionais por 30 dias e negocie dívidas com parcelas que caibam no seu orçamento.'
        fallback['recomendacoes'] = [
            'Plano de recuperação: corte gastos não essenciais imediatamente, renegocie dívidas e reserve um valor semanal fixo para sair do negativo.',
            *fallback['recomendacoes']
        ]

    if not client:
        return fallback

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
            'plano_emergencia': 'string quando saldo negativo'
        }
    }

    try:
        completion = client.chat.completions.create(
            model=MODEL,
            temperature=0.3,
            response_format={'type': 'json_object'},
            messages=[
                {'role': 'system', 'content': 'Responda em português do Brasil simples, tom calmo, sem jargão. Retorne apenas JSON válido.'},
                {'role': 'user', 'content': json.dumps(payload, ensure_ascii=False)}
            ]
        )
        data = _extract_json(completion.choices[0].message.content)
        if negative and (not data.get('recomendacoes') or 'recuper' not in data['recomendacoes'][0].lower()):
            data['recomendacoes'] = [
                'Plano de recuperação: corte gastos não essenciais imediatamente, renegocie dívidas e reserve um valor semanal fixo para sair do negativo.'
            ] + data.get('recomendacoes', [])
        return data
    except Exception:
        return fallback

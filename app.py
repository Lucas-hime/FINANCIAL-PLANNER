import json
from collections import defaultdict
from datetime import datetime
import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from werkzeug.utils import secure_filename

from ai_engine import categorize_transactions, convert_goal_to_plan, generate_financial_plan
from database import get_conn, init_db, now_iso, to_dicts
from parser import parse_csv_statement, parse_pdf_statement

load_dotenv()
init_db()

app = Flask(__name__)
UPLOAD_DIR = Path('data/uploads')
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def current_month():
    return datetime.now().strftime('%Y-%m')


def brl(v):
    v = float(v or 0)
    sign = '-' if v < 0 else ''
    x = f"{abs(v):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    return f"{sign}R$ {x}"


def health_for_month(month):
    conn = get_conn()
    cur = conn.cursor()
    income = cur.execute('SELECT salary, extra_income, investment_returns FROM income WHERE month=? ORDER BY id DESC LIMIT 1', (month,)).fetchone()
    txs = to_dicts(cur.execute('SELECT amount, category FROM transactions WHERE month=?', (month,)).fetchall())
    inv = cur.execute('SELECT COALESCE(SUM(current_value),0) AS t FROM investments').fetchone()['t']
    goals = to_dicts(cur.execute('SELECT * FROM goals').fetchall())
    conn.close()

    total_income = sum((income[k] or 0) for k in ['salary', 'extra_income', 'investment_returns']) if income else 0
    total_spent = sum(t['amount'] or 0 for t in txs)
    balance = total_income - total_spent

    score = 50
    reasons = []
    if total_spent > total_income and total_income > 0:
        score = 0
        reasons.append('Você gastou mais do que ganhou no mês.')
    savings_rate = ((balance / total_income) if total_income else 0)
    if savings_rate >= 0.2:
        score += 25
        reasons.append('Sua taxa de economia está ótima.')
    elif savings_rate >= 0.1:
        score += 10
        reasons.append('Sua taxa de economia está em bom caminho.')
    elif savings_rate >= 0:
        score -= 10
        reasons.append('Sua margem de economia está baixa.')
    else:
        score -= 30
        reasons.append('Seu saldo ficou negativo neste mês.')

    by_cat = defaultdict(float)
    for t in txs:
        by_cat[t.get('category') or 'Outros'] += float(t.get('amount') or 0)
    if total_spent > 0:
        max_share = max(by_cat.values()) / total_spent
        if max_share > 0.35:
            score -= 12
            reasons.append('Um único tipo de gasto está concentrando boa parte do seu orçamento.')

    if inv > 0:
        score += 10
        reasons.append('Você já tem investimentos ativos, isso ajuda sua segurança futura.')

    active_with_progress = [g for g in goals if (g.get('status') or 'Em andamento') == 'Em andamento' and (g.get('current_amount') or 0) > 0]
    if active_with_progress:
        score += 10
        reasons.append('Você está avançando em metas importantes.')

    score = max(0, min(100, int(score)))
    if score >= 80:
        label = 'Saudável 💚'
    elif score >= 60:
        label = 'Estável 💛'
    elif score >= 40:
        label = 'Atenção ⚠️'
    elif score >= 20:
        label = 'Em Risco 🔴'
    else:
        label = 'Crítico 🚨'

    reason = reasons[0] if reasons else 'Adicione mais dados para uma leitura mais precisa da sua saúde financeira.'

    conn = get_conn()
    conn.execute('INSERT INTO health_snapshots(month, score, label, details, created_at) VALUES (?,?,?,?,?)',
                 (month, score, label, reason, now_iso()))
    conn.commit()
    conn.close()
    return {'score': score, 'label': label, 'reason': reason, 'color': label}


@app.get('/')
def index():
    return render_template('index.html', groq_configured=bool(os.getenv('GROQ_API_KEY')))


@app.get('/api/dashboard')
def dashboard():
    month = request.args.get('month', current_month())
    conn = get_conn()
    cur = conn.cursor()
    income_row = cur.execute('SELECT salary, extra_income, investment_returns FROM income WHERE month=? ORDER BY id DESC LIMIT 1', (month,)).fetchone()
    txs = to_dicts(cur.execute('SELECT * FROM transactions WHERE month=? ORDER BY date DESC, id DESC', (month,)).fetchall())
    inv_total = cur.execute('SELECT COALESCE(SUM(current_value),0) AS total FROM investments').fetchone()['total']
    plan = cur.execute('SELECT * FROM plans WHERE month=? ORDER BY id DESC LIMIT 1', (month,)).fetchone()
    conn.close()

    income = sum((income_row[k] or 0) for k in ['salary', 'extra_income', 'investment_returns']) if income_row else 0
    spent = sum(t['amount'] or 0 for t in txs)
    balance = income - spent
    by_cat = defaultdict(float)
    for t in txs:
        by_cat[t.get('category') or 'Outros'] += float(t.get('amount') or 0)
    top5 = sorted(txs, key=lambda x: x.get('amount') or 0, reverse=True)[:5]
    health = health_for_month(month)
    return jsonify({
        'month': month,
        'income_total': income,
        'spent_total': spent,
        'balance': balance,
        'invested_total': inv_total,
        'balance_brl': brl(balance),
        'negative': balance < 0,
        'negative_message': f"⚠️ Você gastou mais do que ganhou esse mês. Você está {brl(abs(balance))} no negativo." if balance < 0 else '',
        'by_category': by_cat,
        'top_transactions': top5,
        'transactions_count': len(txs),
        'latest_plan': dict(plan) if plan else None,
        'health': health
    })


@app.post('/api/income')
def save_income():
    data = request.get_json(force=True)
    conn = get_conn()
    conn.execute('INSERT INTO income(month, salary, extra_income, investment_returns, created_at) VALUES (?,?,?,?,?)',
                 (data.get('month'), data.get('salary'), data.get('extra_income'), data.get('investment_returns'), now_iso()))
    conn.commit()
    conn.close()
    return jsonify({'ok': True, 'message': 'Renda salva com carinho. ✨'})


@app.get('/api/income/<month>')
def get_income(month):
    conn = get_conn()
    row = conn.execute('SELECT * FROM income WHERE month=? ORDER BY id DESC LIMIT 1', (month,)).fetchone()
    conn.close()
    return jsonify(dict(row) if row else {})


@app.post('/api/upload-statement')
def upload_statement():
    if 'file' not in request.files:
        return jsonify({'error': 'Selecione um arquivo PDF ou CSV para continuar.'}), 400
    f = request.files['file']
    month = request.form.get('month', current_month())
    filename = secure_filename(f.filename)
    ext = Path(filename).suffix.lower()
    dst = UPLOAD_DIR / f"{datetime.now().timestamp()}_{filename}"
    f.save(dst)

    if ext == '.pdf':
        txs = parse_pdf_statement(dst)
    elif ext == '.csv':
        txs = parse_csv_statement(dst)
    else:
        return jsonify({'error': 'Formato não suportado. Use PDF ou CSV.'}), 400

    categorized = categorize_transactions(txs)
    conn = get_conn()
    for t in categorized:
        conn.execute(
            'INSERT INTO transactions(month, date, description, amount, category, source, created_at) VALUES (?,?,?,?,?,?,?)',
            (month, t.get('date'), t.get('description'), t.get('amount'), t.get('category'), filename, now_iso())
        )
    conn.commit()
    conn.close()
    return jsonify({'ok': True, 'count': len(categorized)})


@app.get('/api/transactions/<month>')
def get_transactions(month):
    conn = get_conn()
    rows = to_dicts(conn.execute('SELECT * FROM transactions WHERE month=? ORDER BY date DESC, id DESC', (month,)).fetchall())
    conn.close()
    return jsonify(rows)


@app.post('/api/investments')
def add_investment():
    d = request.get_json(force=True)
    conn = get_conn()
    conn.execute('INSERT INTO investments(name, type, invested_amount, current_value, date, notes) VALUES (?,?,?,?,?,?)',
                 (d.get('name'), d.get('type'), d.get('invested_amount'), d.get('current_value'), d.get('date'), d.get('notes')))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


@app.get('/api/investments')
def get_investments():
    conn = get_conn()
    rows = to_dicts(conn.execute('SELECT * FROM investments ORDER BY id DESC').fetchall())
    conn.close()
    return jsonify(rows)


@app.patch('/api/investments/<int:item_id>')
def update_investment(item_id):
    d = request.get_json(force=True)
    conn = get_conn()
    conn.execute('UPDATE investments SET name=?, type=?, invested_amount=?, current_value=?, date=?, notes=? WHERE id=?',
                 (d.get('name'), d.get('type'), d.get('invested_amount'), d.get('current_value'), d.get('date'), d.get('notes'), item_id))
    conn.commit(); conn.close()
    return jsonify({'ok': True})


@app.delete('/api/investments/<int:item_id>')
def delete_investment(item_id):
    conn = get_conn(); conn.execute('DELETE FROM investments WHERE id=?', (item_id,)); conn.commit(); conn.close()
    return jsonify({'ok': True})


@app.post('/api/goals')
def add_goal():
    d = request.get_json(force=True)
    month = d.get('month', current_month())
    conn = get_conn()
    income = conn.execute('SELECT salary, extra_income, investment_returns FROM income WHERE month=? ORDER BY id DESC LIMIT 1', (month,)).fetchone()
    txs = to_dicts(conn.execute('SELECT category, amount FROM transactions WHERE month=?', (month,)).fetchall())
    exp_sum = defaultdict(float)
    for t in txs:
        exp_sum[t['category'] or 'Outros'] += float(t['amount'] or 0)
    income_total = sum((income[k] or 0) for k in ['salary', 'extra_income', 'investment_returns']) if income else 0
    plan = convert_goal_to_plan(d.get('description', ''), income_total, dict(exp_sum))
    status = 'Em andamento'
    cur = conn.execute('INSERT INTO goals(title, description, target_amount, current_amount, deadline, status, created_at) VALUES (?,?,?,?,?,?,?)',
                       (plan.get('title'), d.get('description'), plan.get('target_amount'), 0, plan.get('deadline'), status, now_iso()))
    goal_id = cur.lastrowid
    for m in plan.get('monthly_milestones', []):
        conn.execute('INSERT INTO milestones(goal_id, description, completed, created_at) VALUES (?,?,?,?)', (goal_id, m, 0, now_iso()))
    conn.commit(); conn.close()
    return jsonify({'ok': True, 'goal': plan})


@app.get('/api/goals')
def get_goals():
    conn = get_conn()
    goals = to_dicts(conn.execute('SELECT * FROM goals ORDER BY id DESC').fetchall())
    for g in goals:
        ms = to_dicts(conn.execute('SELECT * FROM milestones WHERE goal_id=? ORDER BY id ASC', (g['id'],)).fetchall())
        if g.get('current_amount') and g.get('target_amount') and g['current_amount'] >= g['target_amount']:
            g['status'] = 'Concluída'
        elif g.get('deadline'):
            try:
                if datetime.now().date() > datetime.strptime(g['deadline'][:10], '%Y-%m-%d').date() and g['status'] != 'Concluída':
                    g['status'] = 'Atrasada'
            except Exception:
                pass
        g['milestones'] = ms
    conn.close()
    return jsonify(goals)


@app.patch('/api/goals/<int:goal_id>')
def patch_goal(goal_id):
    d = request.get_json(force=True)
    conn = get_conn()
    conn.execute('UPDATE goals SET current_amount=?, status=? WHERE id=?', (d.get('current_amount'), d.get('status', 'Em andamento'), goal_id))
    conn.commit(); conn.close()
    return jsonify({'ok': True})


@app.post('/api/milestones/<int:goal_id>')
def add_milestone(goal_id):
    d = request.get_json(force=True)
    conn = get_conn()
    if d.get('milestone_id'):
        conn.execute('UPDATE milestones SET completed=? WHERE id=? AND goal_id=?', (1 if d.get('completed') else 0, d.get('milestone_id'), goal_id))
    else:
        conn.execute('INSERT INTO milestones(goal_id, description, completed, created_at) VALUES (?,?,?,?)',
                     (goal_id, d.get('description'), 0, now_iso()))
    conn.commit(); conn.close()
    return jsonify({'ok': True})


@app.post('/api/generate-plan')
def gen_plan():
    month = request.get_json(force=True).get('month', current_month())
    conn = get_conn()
    income_row = conn.execute('SELECT salary, extra_income, investment_returns FROM income WHERE month=? ORDER BY id DESC LIMIT 1', (month,)).fetchone()
    txs = to_dicts(conn.execute('SELECT amount, category FROM transactions WHERE month=?', (month,)).fetchall())
    inv = to_dicts(conn.execute('SELECT * FROM investments').fetchall())
    goals = to_dicts(conn.execute('SELECT * FROM goals').fetchall())

    income_total = sum((income_row[k] or 0) for k in ['salary', 'extra_income', 'investment_returns']) if income_row else 0
    by_cat = defaultdict(float)
    for t in txs:
        by_cat[t['category'] or 'Outros'] += float(t['amount'] or 0)
    spent = sum(t['amount'] or 0 for t in txs)
    balance = income_total - spent

    inv_summary = {
        'total_investido': sum(float(i.get('invested_amount') or 0) for i in inv),
        'valor_atual': sum(float(i.get('current_value') or 0) for i in inv)
    }

    content = generate_financial_plan(income_total, dict(by_cat), inv_summary, goals, balance)

    conn.execute('INSERT INTO plans(month, content, weekly_plan, monthly_plan, annual_plan, created_at) VALUES (?,?,?,?,?,?)',
                 (month, json.dumps(content, ensure_ascii=False), content.get('orcamento_semanal'), str(content.get('meta_poupanca_mensal')), content.get('projecao_anual'), now_iso()))
    conn.commit(); conn.close()
    health_for_month(month)
    return jsonify(content)


@app.get('/api/plans')
def get_plans():
    conn = get_conn(); rows = to_dicts(conn.execute('SELECT * FROM plans ORDER BY id DESC').fetchall()); conn.close()
    for r in rows:
        try:
            r['content'] = json.loads(r['content'])
        except Exception:
            r['content'] = {}
    return jsonify(rows)


@app.get('/api/journey')
def journey():
    conn = get_conn()
    months = [r['month'] for r in conn.execute('SELECT DISTINCT month FROM income UNION SELECT DISTINCT month FROM transactions ORDER BY month').fetchall()]
    out = []
    for m in months:
        inc = conn.execute('SELECT salary, extra_income, investment_returns FROM income WHERE month=? ORDER BY id DESC LIMIT 1', (m,)).fetchone()
        tx = conn.execute('SELECT COALESCE(SUM(amount),0) AS total FROM transactions WHERE month=?', (m,)).fetchone()['total']
        inv = conn.execute('SELECT COALESCE(SUM(current_value),0) AS total FROM investments').fetchone()['total']
        hs = conn.execute('SELECT score, label FROM health_snapshots WHERE month=? ORDER BY id DESC LIMIT 1', (m,)).fetchone()
        inc_total = sum((inc[k] or 0) for k in ['salary', 'extra_income', 'investment_returns']) if inc else 0
        out.append({'month': m, 'receita': inc_total, 'gastos': tx, 'saldo': inc_total - tx, 'investido': inv,
                    'saude_score': hs['score'] if hs else None, 'saude_label': hs['label'] if hs else 'Sem leitura'})
    conn.close()
    return jsonify(out)


@app.get('/api/health-score/<month>')
def health_score(month):
    return jsonify(health_for_month(month))


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

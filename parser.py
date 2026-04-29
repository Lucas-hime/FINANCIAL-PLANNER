import re
from datetime import datetime
import pdfplumber
import pandas as pd


def _norm_date(raw, base_date=None):
    if not raw:
        return None
    raw = str(raw).strip()
    ref = base_date or datetime.now()

    for fmt in ('%d/%m/%Y', '%d/%m/%y', '%Y-%m-%d', '%d-%m-%Y'):
        try:
            return datetime.strptime(raw, fmt).strftime('%Y-%m-%d')
        except ValueError:
            continue

    m = re.search(r'(\d{2})/(\d{2})', raw)
    if m:
        day, month = int(m.group(1)), int(m.group(2))
        year = ref.year
        if month > ref.month + 1:
            year -= 1
        try:
            return datetime(year, month, day).strftime('%Y-%m-%d')
        except ValueError:
            return None
    return None


def _to_amount(v):
    if v is None:
        return None

    s = str(v).strip().replace('R$', '').replace(' ', '')
    s = s.replace('\u00a0', '')
    s = re.sub(r'[^0-9,\.\-]', '', s)
    if not s:
        return None

    last_comma = s.rfind(',')
    last_dot = s.rfind('.')

    if last_comma != -1 and last_dot != -1:
        if last_comma > last_dot:
            s = s.replace('.', '')
            s = s.replace(',', '.')
        else:
            s = s.replace(',', '')
    elif last_comma != -1:
        s = s.replace('.', '')
        s = s.replace(',', '.')
    else:
        if s.count('.') > 1:
            parts = s.split('.')
            s = ''.join(parts[:-1]) + '.' + parts[-1]

    try:
        return float(s)
    except ValueError:
        return None


def parse_pdf_statement(filepath):
    transactions = []
    pattern = re.compile(r'(\d{2}/\d{2}(?:/\d{2,4})?)\s+(.+?)\s+(-?\s?R?\$?\s?[\d\.,]+)$')
    ref_date = datetime.now()
    with pdfplumber.open(filepath) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ''
            for line in text.splitlines():
                line = line.strip()
                m = pattern.search(line)
                if not m:
                    continue
                date_raw, description, amount_raw = m.groups()
                amount = _to_amount(amount_raw)
                date = _norm_date(date_raw, ref_date)
                if date and amount is not None and description:
                    transactions.append({'date': date, 'description': description.strip(), 'amount': amount})

            tables = page.extract_tables() or []
            for table in tables:
                if not table:
                    continue
                for row in table:
                    if not row or len(row) < 3:
                        continue
                    date = _norm_date(row[0], ref_date)
                    amount = _to_amount(row[-1])
                    description = str(row[1]).strip() if row[1] else ''
                    if date and description and amount is not None:
                        transactions.append({'date': date, 'description': description, 'amount': amount})

    unique = []
    seen = set()
    for t in transactions:
        key = (t['date'], t['description'], round(float(t['amount']), 2))
        if key not in seen:
            seen.add(key)
            unique.append(t)
    return unique


def parse_csv_statement(filepath):
    df = pd.read_csv(filepath, sep=None, engine='python')
    cols = {c.lower().strip(): c for c in df.columns}

    def pick(names):
        for name in names:
            for k, original in cols.items():
                if name in k:
                    return original
        return None

    date_col = pick(['data', 'date'])
    desc_col = pick(['descrição', 'descricao', 'lançamento', 'lancamento', 'histórico', 'historico', 'título', 'titulo'])
    amount_col = pick(['valor', 'amount'])

    if not (date_col and desc_col and amount_col):
        raise ValueError('Não consegui identificar as colunas Data, Descrição e Valor no CSV.')

    transactions = []
    ref_date = datetime.now()
    for _, row in df.iterrows():
        date = _norm_date(row.get(date_col), ref_date)
        description = str(row.get(desc_col) or '').strip()
        amount = _to_amount(row.get(amount_col))
        if date and description and amount is not None:
            transactions.append({'date': date, 'description': description, 'amount': amount})
    return transactions

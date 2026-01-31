"""
Gera um relatório HTML detalhado sobre o estado das palavras no banco de dados

USO:
    python backend/scripts/generate_words_report.py
    python backend/scripts/generate_words_report.py --output relatorio.html
    
    docker exec idiomasbr-backend python scripts/generate_words_report.py
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import func, or_

from app.core.database import SessionLocal
from app.models.word import Word


def generate_html_report(output_path: Path):
    """Gera relatório HTML com estatísticas detalhadas"""
    
    db = SessionLocal()
    
    try:
        # Estatísticas gerais
        total = db.query(func.count(Word.id)).scalar()
        
        # Por campo
        empty_ipa = db.query(func.count(Word.id)).filter(
            or_(Word.ipa == None, Word.ipa == '')
        ).scalar()
        
        empty_word_type = db.query(func.count(Word.id)).filter(
            or_(Word.word_type == None, Word.word_type == '')
        ).scalar()
        
        empty_definition_en = db.query(func.count(Word.id)).filter(
            or_(Word.definition_en == None, Word.definition_en == '')
        ).scalar()
        
        empty_definition_pt = db.query(func.count(Word.id)).filter(
            or_(Word.definition_pt == None, Word.definition_pt == '')
        ).scalar()
        
        empty_example_en = db.query(func.count(Word.id)).filter(
            or_(Word.example_en == None, Word.example_en == '')
        ).scalar()
        
        empty_example_pt = db.query(func.count(Word.id)).filter(
            or_(Word.example_pt == None, Word.example_pt == '')
        ).scalar()
        
        # Por nível
        levels = db.query(Word.level, func.count(Word.id)).group_by(Word.level).all()
        
        # Palavras completas
        complete = db.query(func.count(Word.id)).filter(
            Word.ipa != None,
            Word.ipa != '',
            Word.word_type != None,
            Word.word_type != '',
            Word.definition_en != None,
            Word.definition_en != '',
            Word.definition_pt != None,
            Word.definition_pt != '',
            Word.example_en != None,
            Word.example_en != '',
            Word.example_pt != None,
            Word.example_pt != ''
        ).scalar()
        
        # Top 10 palavras incompletas por nível A1
        incomplete_a1 = db.query(Word).filter(
            Word.level == 'A1',
            or_(
                Word.definition_en == None,
                Word.definition_en == '',
                Word.example_en == None,
                Word.example_en == ''
            )
        ).limit(20).all()
        
        # Gerar HTML
        html = f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Relatório de Palavras - IdiomaBR</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            padding: 40px;
        }}
        
        h1 {{
            color: #667eea;
            font-size: 2.5em;
            margin-bottom: 10px;
            text-align: center;
        }}
        
        .subtitle {{
            text-align: center;
            color: #666;
            margin-bottom: 40px;
            font-size: 1.1em;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }}
        
        .stat-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            transition: transform 0.3s;
        }}
        
        .stat-card:hover {{
            transform: translateY(-5px);
        }}
        
        .stat-card h3 {{
            font-size: 0.9em;
            opacity: 0.9;
            margin-bottom: 10px;
        }}
        
        .stat-card .number {{
            font-size: 2.5em;
            font-weight: bold;
        }}
        
        .stat-card .percent {{
            font-size: 1.2em;
            opacity: 0.8;
        }}
        
        .section {{
            margin: 40px 0;
        }}
        
        .section h2 {{
            color: #667eea;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
            margin-bottom: 20px;
            font-size: 1.8em;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            background: white;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        }}
        
        th, td {{
            padding: 15px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }}
        
        th {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            font-weight: 600;
        }}
        
        tr:hover {{
            background: #f8f9ff;
        }}
        
        .progress-bar {{
            width: 100%;
            height: 30px;
            background: #e0e0e0;
            border-radius: 15px;
            overflow: hidden;
            margin: 10px 0;
        }}
        
        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            transition: width 1s ease;
        }}
        
        .alert {{
            padding: 20px;
            margin: 20px 0;
            border-radius: 10px;
            border-left: 5px solid;
        }}
        
        .alert-warning {{
            background: #fff3cd;
            border-color: #ffc107;
            color: #856404;
        }}
        
        .alert-info {{
            background: #d1ecf1;
            border-color: #17a2b8;
            color: #0c5460;
        }}
        
        .alert-success {{
            background: #d4edda;
            border-color: #28a745;
            color: #155724;
        }}
        
        .badge {{
            display: inline-block;
            padding: 5px 10px;
            border-radius: 5px;
            font-size: 0.85em;
            font-weight: bold;
            margin: 2px;
        }}
        
        .badge-danger {{
            background: #dc3545;
            color: white;
        }}
        
        .badge-warning {{
            background: #ffc107;
            color: #333;
        }}
        
        .badge-success {{
            background: #28a745;
            color: white;
        }}
        
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 2px solid #eee;
            text-align: center;
            color: #666;
        }}
        
        .recommendations {{
            background: #f8f9ff;
            padding: 25px;
            border-radius: 10px;
            border-left: 5px solid #667eea;
        }}
        
        .recommendations h3 {{
            color: #667eea;
            margin-bottom: 15px;
        }}
        
        .recommendations ol {{
            padding-left: 20px;
        }}
        
        .recommendations li {{
            margin: 10px 0;
        }}
        
        code {{
            background: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
            color: #e83e8c;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📚 Relatório de Palavras</h1>
        <p class="subtitle">IdiomaBR - Gerado em {datetime.now().strftime('%d/%m/%Y às %H:%M')}</p>
        
        <!-- Estatísticas Principais -->
        <div class="stats-grid">
            <div class="stat-card">
                <h3>Total de Palavras</h3>
                <div class="number">{total:,}</div>
            </div>
            <div class="stat-card">
                <h3>Palavras Completas</h3>
                <div class="number">{complete:,}</div>
                <div class="percent">{(complete/total*100):.1f}%</div>
            </div>
            <div class="stat-card">
                <h3>Precisam Enriquecimento</h3>
                <div class="number">{total-complete:,}</div>
                <div class="percent">{((total-complete)/total*100):.1f}%</div>
            </div>
        </div>
        
        <!-- Status Geral -->
        <div class="section">
            <h2>📊 Status Geral</h2>
            
            <div class="alert {'alert-success' if (complete/total*100) >= 80 else 'alert-warning' if (complete/total*100) >= 50 else 'alert-warning'}">
                <strong>Status:</strong> 
                {"✅ Excelente! Mais de 80% das palavras estão completas." if (complete/total*100) >= 80 else 
                 "⚠️ Atenção! Apenas {:.1f}% das palavras estão completas.".format(complete/total*100) if (complete/total*100) >= 50 else
                 "❌ Crítico! Apenas {:.1f}% das palavras estão completas. Enriquecimento urgente necessário.".format(complete/total*100)}
            </div>
            
            <table>
                <thead>
                    <tr>
                        <th>Campo</th>
                        <th>Vazios</th>
                        <th>Preenchidos</th>
                        <th>Progresso</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td><strong>IPA (Pronúncia)</strong></td>
                        <td>{empty_ipa:,} ({empty_ipa/total*100:.1f}%)</td>
                        <td>{total-empty_ipa:,} ({(total-empty_ipa)/total*100:.1f}%)</td>
                        <td>
                            <div class="progress-bar">
                                <div class="progress-fill" style="width: {(total-empty_ipa)/total*100:.1f}%">
                                    {(total-empty_ipa)/total*100:.1f}%
                                </div>
                            </div>
                        </td>
                    </tr>
                    <tr>
                        <td><strong>Tipo (word_type)</strong></td>
                        <td>{empty_word_type:,} ({empty_word_type/total*100:.1f}%)</td>
                        <td>{total-empty_word_type:,} ({(total-empty_word_type)/total*100:.1f}%)</td>
                        <td>
                            <div class="progress-bar">
                                <div class="progress-fill" style="width: {(total-empty_word_type)/total*100:.1f}%">
                                    {(total-empty_word_type)/total*100:.1f}%
                                </div>
                            </div>
                        </td>
                    </tr>
                    <tr>
                        <td><strong>Definição EN</strong></td>
                        <td>{empty_definition_en:,} ({empty_definition_en/total*100:.1f}%)</td>
                        <td>{total-empty_definition_en:,} ({(total-empty_definition_en)/total*100:.1f}%)</td>
                        <td>
                            <div class="progress-bar">
                                <div class="progress-fill" style="width: {(total-empty_definition_en)/total*100:.1f}%">
                                    {(total-empty_definition_en)/total*100:.1f}%
                                </div>
                            </div>
                        </td>
                    </tr>
                    <tr>
                        <td><strong>Definição PT</strong></td>
                        <td>{empty_definition_pt:,} ({empty_definition_pt/total*100:.1f}%)</td>
                        <td>{total-empty_definition_pt:,} ({(total-empty_definition_pt)/total*100:.1f}%)</td>
                        <td>
                            <div class="progress-bar">
                                <div class="progress-fill" style="width: {(total-empty_definition_pt)/total*100:.1f}%">
                                    {(total-empty_definition_pt)/total*100:.1f}%
                                </div>
                            </div>
                        </td>
                    </tr>
                    <tr>
                        <td><strong>Exemplo EN</strong></td>
                        <td>{empty_example_en:,} ({empty_example_en/total*100:.1f}%)</td>
                        <td>{total-empty_example_en:,} ({(total-empty_example_en)/total*100:.1f}%)</td>
                        <td>
                            <div class="progress-bar">
                                <div class="progress-fill" style="width: {(total-empty_example_en)/total*100:.1f}%">
                                    {(total-empty_example_en)/total*100:.1f}%
                                </div>
                            </div>
                        </td>
                    </tr>
                    <tr>
                        <td><strong>Exemplo PT</strong></td>
                        <td>{empty_example_pt:,} ({empty_example_pt/total*100:.1f}%)</td>
                        <td>{total-empty_example_pt:,} ({(total-empty_example_pt)/total*100:.1f}%)</td>
                        <td>
                            <div class="progress-bar">
                                <div class="progress-fill" style="width: {(total-empty_example_pt)/total*100:.1f}%">
                                    {(total-empty_example_pt)/total*100:.1f}%
                                </div>
                            </div>
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>
        
        <!-- Distribuição por Nível -->
        <div class="section">
            <h2>📈 Distribuição por Nível CEFR</h2>
            <table>
                <thead>
                    <tr>
                        <th>Nível</th>
                        <th>Quantidade</th>
                        <th>Porcentagem</th>
                    </tr>
                </thead>
                <tbody>
                    {"".join(f'''
                    <tr>
                        <td><span class="badge badge-{'success' if level == 'A1' else 'warning' if level in ('A2','B1') else 'danger'}">{level}</span></td>
                        <td>{count:,}</td>
                        <td>{count/total*100:.1f}%</td>
                    </tr>
                    ''' for level, count in sorted(levels, key=lambda x: ['A1','A2','B1','B2','C1','C2'].index(x[0]) if x[0] in ['A1','A2','B1','B2','C1','C2'] else 999))}
                </tbody>
            </table>
        </div>
        
        <!-- Palavras Incompletas Prioritárias (A1) -->
        <div class="section">
            <h2>⚠️ Palavras A1 Incompletas (Top 20)</h2>
            <div class="alert alert-warning">
                <strong>Atenção:</strong> Estas são palavras do nível A1 (iniciante) que estão incompletas. 
                Priorize o enriquecimento dessas palavras pois são as mais usadas por alunos iniciantes.
            </div>
            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Inglês</th>
                        <th>Português</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    {"".join(f'''
                    <tr>
                        <td>{word.id}</td>
                        <td><strong>{word.english}</strong></td>
                        <td>{word.portuguese}</td>
                        <td>
                            {'<span class="badge badge-danger">Sem def EN</span>' if not word.definition_en else ''}
                            {'<span class="badge badge-danger">Sem def PT</span>' if not word.definition_pt else ''}
                            {'<span class="badge badge-warning">Sem ex EN</span>' if not word.example_en else ''}
                            {'<span class="badge badge-warning">Sem ex PT</span>' if not word.example_pt else ''}
                        </td>
                    </tr>
                    ''' for word in incomplete_a1)}
                </tbody>
            </table>
        </div>
        
        <!-- Recomendações -->
        <div class="recommendations">
            <h3>💡 Próximos Passos Recomendados</h3>
            <ol>
                <li>
                    <strong>Importar dados do CSV:</strong><br>
                    <code>docker exec idiomasbr-backend python scripts/update_words_from_csv.py --import --apply</code>
                </li>
                <li>
                    <strong>Marcar palavras incompletas:</strong><br>
                    <code>docker exec idiomasbr-backend python scripts/update_words_from_csv.py --mark-for-enrichment --apply</code>
                </li>
                <li>
                    <strong>Enriquecer com APIs:</strong><br>
                    <code>docker exec idiomasbr-backend python scripts/enrich_words_api.py --tags needs_enrichment --batch 50</code>
                </li>
                <li>
                    <strong>Gerar novo relatório para verificar progresso:</strong><br>
                    <code>docker exec idiomasbr-backend python scripts/generate_words_report.py</code>
                </li>
            </ol>
        </div>
        
        <div class="footer">
            <p>📚 IdiomaBR - Sistema de Aprendizado de Inglês</p>
            <p>Para mais informações, consulte: <code>WORDS_UPDATE_GUIDE.md</code></p>
        </div>
    </div>
</body>
</html>
"""
        
        # Salvar arquivo
        output_path.write_text(html, encoding='utf-8')
        print(f"\n✅ Relatório gerado com sucesso!")
        print(f"📄 Arquivo: {output_path.absolute()}")
        print(f"\n🌐 Abra o arquivo no navegador para visualizar o relatório completo.")
        
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(
        description='Gera relatório HTML sobre o estado das palavras'
    )
    
    parser.add_argument(
        '--output',
        '-o',
        type=Path,
        default=Path('words_report.html'),
        help='Caminho do arquivo HTML de saída (padrão: words_report.html)'
    )
    
    args = parser.parse_args()
    
    generate_html_report(args.output)


if __name__ == '__main__':
    main()

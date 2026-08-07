<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Painel — SoftPax (Craft Framework)</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="/app-assets/grid.css">
    <link rel="stylesheet" href="/css/console.css">
    <style>
        body { background-color: #f3f3f3; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
        .win-window { display: flex; flex-direction: column; height: 100vh; }
        .win-titlebar { background: #ffffff; border-bottom: 1px solid #e5e5e5; height: 40px; display: flex; align-items: center; padding: 0 16px; gap: 8px; }
        .win-titlebar .brand { background: #0067c0; color: #fff; width: 24px; height: 24px; border-radius: 4px; display: flex; align-items: center; justify-content: center; font-weight: bold; }
        .win-body { display: flex; flex: 1; overflow: hidden; }
        .win-nav { width: 240px; background: #ffffff; border-right: 1px solid #e5e5e5; padding: 16px; display: flex; flex-direction: column; gap: 4px; }
        .win-nav-section { font-size: 11px; font-weight: bold; color: #8a8a8a; text-transform: uppercase; margin-bottom: 8px; }
        .win-nav-item { display: flex; align-items: center; gap: 10px; padding: 8px 12px; border-radius: 6px; color: #1a1a1a; text-decoration: none; font-size: 13px; font-weight: 500; }
        .win-nav-item:hover { background: #f0f0f0; }
        .win-nav-item.active { background: #e8f1fb; color: #0067c0; font-weight: 600; }
        .win-content { flex: 1; padding: 24px; overflow-y: auto; background: #f3f3f3; }
        .console-stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; }
        .console-stat { background: #ffffff; border: 1px solid #e5e5e5; border-radius: 8px; padding: 16px; display: flex; flex-direction: column; gap: 4px; }
        .console-stat-label { font-size: 12px; color: #5b5b5b; font-weight: 500; }
        .console-stat-value { font-size: 24px; font-weight: bold; color: #1a1a1a; }
        .console-stat--danger .console-stat-value { color: #b4231f; }
        .console-stat--ok .console-stat-value { color: #0f7b34; }
        .console-stat--accent .console-stat-value { color: #0067c0; }
        .console-panel { background: #ffffff; border: 1px solid #e5e5e5; border-radius: 8px; overflow: hidden; }
        .console-toolbar { padding: 14px 16px; border-bottom: 1px solid #e5e5e5; }
        .console-toolbar-title { font-size: 15px; font-weight: 600; color: #1a1a1a; margin: 0; }
        .console-table { width: 100%; border-collapse: collapse; text-align: left; font-size: 13px; }
        .console-table th { background: #fbfbfb; padding: 10px 16px; border-bottom: 1px solid #e5e5e5; font-size: 12px; color: #8a8a8a; font-weight: 600; text-transform: uppercase; }
        .console-table td { padding: 12px 16px; border-bottom: 1px solid #e5e5e5; }
        .console-badge { display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 600; }
        .console-badge.is-ok { background: #e6f4ea; color: #0f7b34; }
        .console-badge.is-warn { background: #fdf3d7; color: #9a6700; }
    </style>
</head>
<body class="bg-slate-100 font-sans text-slate-800 antialiased">
    <div class="win-window">
        <!-- Titlebar Mica -->
        <header class="win-titlebar">
            <span class="brand">✠</span>
            <span class="font-semibold text-sm">SoftPax ERP</span>
            <span class="text-slate-400">—</span>
            <span class="text-slate-600 text-xs">Gestão Funerária & Cemitério</span>
            <div class="win-winctrls">
                <span class="text-xs text-slate-500 px-2">Craft Framework (Python)</span>
            </div>
        </header>

        <div class="win-body">
            <!-- Sidebar Navigation -->
            <aside class="win-nav">
                <div class="win-nav-section">Áreas de Negócio</div>
                <a href="/dashboard" class="win-nav-item active"><span class="ico">🏠</span><span class="lbl">Painel</span></a>
                <a href="/associates" class="win-nav-item"><span class="ico">👥</span><span class="lbl">Associados</span></a>
                <a href="/service-orders" class="win-nav-item"><span class="ico">✝️</span><span class="lbl">Ordens de Serviço</span></a>
                <a href="/cemeteries" class="win-nav-item"><span class="ico">🪦</span><span class="lbl">Cemitério</span></a>
                <a href="/finance/installments" class="win-nav-item"><span class="ico">💳</span><span class="lbl">Financeiro</span></a>
                <a href="/vehicles" class="win-nav-item"><span class="ico">🚐</span><span class="lbl">Frota</span></a>
                <a href="/employees" class="win-nav-item"><span class="ico">👔</span><span class="lbl">Recursos Humanos</span></a>
                <a href="/products" class="win-nav-item"><span class="ico">📦</span><span class="lbl">Estoque</span></a>
                <a href="/calls" class="win-nav-item"><span class="ico">📞</span><span class="lbl">Atendimento 24h</span></a>
                <a href="/leads" class="win-nav-item"><span class="ico">📊</span><span class="lbl">Leads & CRM</span></a>
                <a href="/workflows" class="win-nav-item"><span class="ico">⚡</span><span class="lbl">Automações</span></a>
            </aside>

            <!-- Main Content Area -->
            <main class="win-content">
                <div class="page-head">
                    <div>
                        <h1 class="page-title">Painel Operacional</h1>
                        <p class="page-sub">Visão geral da operação em tempo real</p>
                    </div>
                </div>

                <div class="console-stats mb-6">
                    <div class="console-stat">
                        <span class="console-stat-label">Contratos Ativos</span>
                        <span class="console-stat-value">1.482</span>
                    </div>
                    <div class="console-stat console-stat--danger">
                        <span class="console-stat-label">Parcelas Vencidas</span>
                        <span class="console-stat-value">34</span>
                    </div>
                    <div class="console-stat console-stat--ok">
                        <span class="console-stat-label">Recebido Hoje</span>
                        <span class="console-stat-value">R$ 14.850,00</span>
                    </div>
                    <div class="console-stat console-stat--accent">
                        <span class="console-stat-label">Atendimentos em Aberto</span>
                        <span class="console-stat-value">6</span>
                    </div>
                </div>

                <div class="console-panel">
                    <div class="console-toolbar">
                        <h2 class="console-toolbar-title">Óbitos & Atendimentos Recentes</h2>
                    </div>
                    <div class="console-table-wrap">
                        <table class="console-table">
                            <thead>
                                <tr>
                                    <th>Protocolo</th>
                                    <th>Falecido / Titular</th>
                                    <th>Data / Hora</th>
                                    <th>Status</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr>
                                    <td><span class="console-resource-name">OS-2026-0801</span></td>
                                    <td>João da Silva</td>
                                    <td>02/08/2026 14:30</td>
                                    <td><span class="console-badge is-ok">Em Cerimonial</span></td>
                                </tr>
                                <tr>
                                    <td><span class="console-resource-name">OS-2026-0802</span></td>
                                    <td>Maria de Souza</td>
                                    <td>02/08/2026 16:15</td>
                                    <td><span class="console-badge is-warn">Em Preparação</span></td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </main>
        </div>
    </div>
</body>
</html>

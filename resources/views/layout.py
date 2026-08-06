"""Layout Helper for SoftPax Windows Native Desktop UI Presentation (Categorized & Grouped Menu)."""

def render_desktop_app(title: str, active_tab: str, content_html: str) -> str:
    # Categorized Navigation Grouping
    nav_categories = [
        ("CORE & VISÃO GERAL", [
            ("dashboard", "Painel Geral", "🏠", "/dashboard"),
            ("support-login", "Suporte Master & Impersonação", "🛡️", "/support-login"),
        ]),
        ("ATENDIMENTO & OPERACIONAL 24H", [
            ("incidents", "Incident Intake / Óbitos 24h", "🚨", "/incidents"),
            ("service-orders", "Ordens de Serviço & Timeline", "✝️", "/service-orders"),
            ("wake-signage", "Sinalização Velório (TV)", "🖥️", "/wake-signage"),
            ("vehicles", "Frota & Traslado", "🚐", "/vehicles"),
            ("florist", "Floricultura & Coroas", "🌸", "/florist"),
            ("equipment-loans", "Equipamentos Convalescentes", "♿", "/equipment-loans"),
            ("calls", "Plantão 24h & Chamadas", "📞", "/calls"),
        ]),
        ("CEMITÉRIO & CREMATÓRIO", [
            ("cemeteries", "Jazigos & Sepulcros", "🪦", "/cemeteries"),
            ("cremations", "Cemitério & Crematório", "🔥", "/cremations"),
        ]),
        ("GESTÃO DE ASSOCIADOS & DRIVE", [
            ("associates", "Associados (CTR-ID)", "👥", "/associates"),
            ("drive", "Drive Contratos CTR-ID", "📁", "/drive"),
            ("leads", "CRM & Captação Leads", "📊", "/leads"),
        ]),
        ("FINANCEIRO & CNAB 240/400", [
            ("finance", "Financeiro & Carnês", "💳", "/finance/installments"),
            ("payment-gateway", "Gateways & Split CNAB", "🏦", "/payment-gateway"),
        ]),
        ("PORTAL DO CLIENTE & HELPDESK", [
            ("portal", "Portal do Cliente 360°", "🌐", "/portal"),
            ("helpdesk", "Helpdesk & Central Chamados", "💬", "/helpdesk"),
            ("ai-orchestrator", "AI Orchestrator & Chatbot 24h", "🤖", "/ai-orchestrator"),
        ]),
        ("ADMINISTRAÇÃO & RECURSOS", [
            ("tenant-management", "Multi-CNPJ & Limites", "🏢", "/tenant-management"),
            ("plans", "Planos dos Associados", "📑", "/plans"),
            ("rbac", "RBAC & Permissões", "🔐", "/rbac"),
            ("employees", "Recursos Humanos (RH)", "👔", "/employees"),
            ("products", "Estoque & Urnas Funerárias", "📦", "/products"),
            ("workflows", "Engine Automações", "⚡", "/workflows"),
            ("print-manager", "Gerenciador de Impressão", "🖨️", "/print-manager"),
            ("cms", "CMS & Landings Tenant", "🌐", "/cms"),
        ]),
    ]

    nav_html = ""
    for category_name, items in nav_categories:
        nav_html += f'<div class="px-3 pt-3 pb-1 text-[10px] font-bold tracking-wider text-slate-400 uppercase select-none">{category_name}</div>'
        for tab_id, label, icon, url in items:
            is_active = "active" if tab_id == active_tab else ""
            nav_html += f"""
            <a href="{url}" class="win-nav-item {is_active}">
                <span class="ico">{icon}</span>
                <span class="lbl">{label}</span>
            </a>
            """

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{title} — SoftPax ERP</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body {{ background-color: #f0f2f5; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; overflow: hidden; user-select: none; }}
        .win-window {{ display: flex; flex-direction: column; height: 100vh; width: 100vw; background: #f0f2f5; }}
        
        /* Windows Titlebar & Control Buttons */
        .win-titlebar {{ background: #ffffff; border-bottom: 1px solid #dcdcdc; height: 36px; display: flex; align-items: center; justify-content: space-between; padding: 0 0 0 12px; font-size: 12px; color: #333; }}
        .win-title-info {{ display: flex; align-items: center; gap: 8px; font-weight: 500; }}
        .win-title-info .brand {{ background: #0067c0; color: #fff; width: 20px; height: 20px; border-radius: 3px; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 11px; }}
        .win-controls {{ display: flex; height: 100%; }}
        .win-btn {{ width: 46px; height: 100%; display: flex; align-items: center; justify-content: center; font-size: 11px; color: #555; transition: background 0.1s; cursor: default; }}
        .win-btn:hover {{ background: #e5e5e5; }}
        .win-btn.close:hover {{ background: #e81123; color: #fff; }}

        /* Windows App Header & Ribbon Menu */
        .win-header {{ background: #f3f3f3; border-bottom: 1px solid #d0d0d0; padding: 6px 16px; display: flex; align-items: center; justify-content: space-between; }}
        .win-app-title {{ font-size: 13px; font-weight: 600; color: #1a1a1a; }}
        .win-ribbon-tabs {{ display: flex; gap: 2px; }}
        .win-tab {{ padding: 6px 14px; font-size: 12px; color: #444; border-radius: 4px 4px 0 0; cursor: pointer; text-decoration: none; display: flex; align-items: center; gap: 6px; }}
        .win-tab:hover {{ background: #e8e8e8; }}
        .win-tab.active {{ background: #ffffff; color: #0067c0; font-weight: 600; border-bottom: 2px solid #0067c0; }}

        /* Workspace Desktop Layout */
        .win-workspace {{ display: flex; flex: 1; overflow: hidden; }}
        
        /* Windows Left Navigation Sidebar */
        .win-sidebar {{ width: 250px; background: #ffffff; border-right: 1px solid #dcdcdc; display: flex; flex-direction: column; overflow-y: auto; padding-bottom: 12px; flex-shrink: 0; }}
        .win-nav-item {{ display: flex; align-items: center; gap: 10px; padding: 7px 14px; font-size: 12px; color: #333; text-decoration: none; transition: all 0.1s; border-left: 3px solid transparent; margin: 1px 4px; border-radius: 4px; }}
        .win-nav-item:hover {{ background: #f0f4f9; color: #0067c0; }}
        .win-nav-item.active {{ background: #e5f0fa; color: #005a9e; font-weight: 600; border-left-color: #0067c0; }}
        .win-nav-item .ico {{ font-size: 14px; width: 18px; text-align: center; }}

        /* Main Workspace Canvas */
        .win-canvas {{ flex: 1; padding: 20px; overflow-y: auto; background: #f8fafc; }}

        /* Windows Statusbar */
        .win-statusbar {{ background: #0067c0; color: #ffffff; height: 24px; display: flex; align-items: center; justify-content: space-between; padding: 0 12px; font-size: 11px; flex-shrink: 0; }}
        .win-status-left {{ display: flex; align-items: center; gap: 16px; }}
        .win-status-right {{ display: flex; align-items: center; gap: 12px; }}
        .win-pill {{ background: rgba(255,255,255,0.2); padding: 1px 8px; border-radius: 10px; font-size: 10px; }}
    </style>
</head>
<body>
    <div class="win-window">
        <!-- Windows Top Titlebar -->
        <div class="win-titlebar">
            <div class="win-title-info">
                <div class="brand">S</div>
                <span>SoftPax Enterprise ERP (v1.0.r0349) — Multi-Tenant (Master Node)</span>
            </div>
            <div class="win-controls">
                <div class="win-btn" title="Minimizar">🗕</div>
                <div class="win-btn" title="Maximizar">🗖</div>
                <div class="win-btn close" title="Fechar Application">✕</div>
            </div>
        </div>

        <!-- Windows App Ribbon Header -->
        <div class="win-header">
            <div class="win-app-title">📍 Módulo Ativo: {title}</div>
            <div class="win-ribbon-tabs">
                <a href="/dashboard" class="win-tab {'active' if active_tab == 'dashboard' else ''}">🏠 Painel Central</a>
                <a href="/tenant-management" class="win-tab {'active' if active_tab == 'tenant-management' else ''}">🏢 Multi-CNPJ</a>
                <a href="/associates" class="win-tab {'active' if active_tab == 'associates' else ''}">👥 Associados</a>
                <a href="/plans" class="win-tab {'active' if active_tab == 'plans' else ''}">📑 Planos</a>
                <a href="/rbac" class="win-tab {'active' if active_tab == 'rbac' else ''}">🔐 RBAC</a>
                <a href="/payment-gateway" class="win-tab {'active' if active_tab == 'payment-gateway' else ''}">💳 CNAB240</a>
            </div>
        </div>

        <!-- Desktop Workspace -->
        <div class="win-workspace">
            <!-- Categorized Left Sidebar -->
            <div class="win-sidebar">
                {nav_html}
            </div>

            <!-- Content Canvas -->
            <div class="win-canvas">
                {content_html}
            </div>
        </div>

        <!-- Windows Statusbar -->
        <div class="win-statusbar">
            <div class="win-status-left">
                <span>● Conectado ao Master Engine: softpax.test:8301</span>
                <span>Tenant Ativo: <strong class="underline">Grupo Pax Dignidade (CNPJ 24.151.343/0001-15)</strong></span>
                <span class="win-pill">PostgreSQL 16 Multi-Tenant</span>
            </div>
            <div class="win-status-right">
                <span>SLA: 99.9%</span>
                <span>CPU: 1.2%</span>
                <span>RAM: 142MB</span>
                <span>03/08/2026</span>
            </div>
        </div>
    </div>
</body>
</html>
"""

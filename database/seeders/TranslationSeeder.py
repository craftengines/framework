"""Seeds the `translations` table from the locale catalog.

Locales follow BCP 47. `pt` is European Portuguese and `pt-BR` is Brazilian —
they are genuinely different copy, not a relabel. Lookups fall back
`pt-BR -> pt -> en`, so a locale only needs the keys where it differs.
"""
# Codepy Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from codepy.facades import DB
from codepy.seeding import Seeder

#: Interface strings, keyed by locale. Source of truth for the shipped UI.
#: The richer, semantically-keyed catalog lives in resources/lang/catalog.json.
TRANSLATIONS = {
    "en": {
        "greeting": "Hello",
        "welcome": "Welcome to Codepy",
        "discuss": "Discuss",
        "contribute": "Contribute",
        "learn": "Learn",
        "dashboard": "Dashboard",
        "download": "Download",
        "login": "Log In",
        "register": "Register",
        "logout": "Log Out",
        "why_codepy": "Why Codepy?",
        "small_footprint_title": "Framework with a small footprint",
        "small_footprint_desc": "Codepy has zero hot-start footprint and lazy dependency imports, keeping memory usage minimal.",
        "exceptional_perf_title": "Exceptional performance",
        "exceptional_perf_desc": "Built on ASGI pipelines and direct database drivers, Codepy handles requests in microseconds.",
        "simple_solutions_title": "Simple solutions over complexity",
        "simple_solutions_desc": "Codepy favours a standard MVC layout, an autowired container and Active Record models without forced configuration.",
        "strong_security_title": "Strong security",
        "strong_security_desc": "Ships with CSRF protection, signed sessions, hashed passwords and CAPTCHA support.",
        "recent_posts": "Recent Posts",
        "small_framework_title": "The small framework with powerful features",
        "learn_more": "Learn more",
        "framework_description": "Codepy is a Python MVC framework with a very small footprint, built for developers who want a simple, elegant toolkit for full-featured web applications.",
    },
    # European Portuguese.
    "pt": {
        "greeting": "Olá",
        "welcome": "Bem-vindo ao Codepy",
        "discuss": "Fórum",
        "contribute": "Contribuir",
        "learn": "Aprender",
        "dashboard": "Painel de Controlo",
        "download": "Transferir",
        "login": "Iniciar sessão",
        "register": "Registar",
        "logout": "Terminar sessão",
        "why_codepy": "Porquê o Codepy?",
        "small_footprint_title": "Framework com consumo mínimo",
        "small_footprint_desc": "O Codepy tem consumo nulo de arranque a quente e importações preguiçosas de dependências, mantendo a utilização de memória no mínimo.",
        "exceptional_perf_title": "Desempenho excecional",
        "exceptional_perf_desc": "Assente em pipelines ASGI e controladores de base de dados diretos, o Codepy responde a pedidos em microssegundos.",
        "simple_solutions_title": "Simplicidade acima da complexidade",
        "simple_solutions_desc": "O Codepy privilegia a estrutura MVC padrão, um contentor com injeção automática e modelos Active Record sem configuração forçada.",
        "strong_security_title": "Segurança robusta",
        "strong_security_desc": "Inclui proteção CSRF, sessões assinadas, palavras-passe cifradas e suporte a CAPTCHA.",
        "recent_posts": "Publicações recentes",
        "small_framework_title": "O framework pequeno com funcionalidades poderosas",
        "learn_more": "Saber mais",
        "framework_description": "O Codepy é uma framework MVC em Python com consumo mínimo de recursos, criada para programadores que procuram um conjunto de ferramentas simples e elegante para aplicações web completas.",
    },
    # Brazilian Portuguese.
    "pt-BR": {
        "greeting": "Olá",
        "welcome": "Bem-vindo ao Codepy",
        "discuss": "Fórum",
        "contribute": "Contribuir",
        "learn": "Aprender",
        "dashboard": "Painel de Controle",
        "download": "Baixar",
        "login": "Entrar",
        "register": "Criar conta",
        "logout": "Sair",
        "why_codepy": "Por que o Codepy?",
        "small_footprint_title": "Framework com consumo mínimo",
        "small_footprint_desc": "O Codepy tem consumo zero de inicialização a quente e importações preguiçosas de dependências, mantendo o uso de memória no mínimo.",
        "exceptional_perf_title": "Desempenho excepcional",
        "exceptional_perf_desc": "Construído sobre pipelines ASGI e drivers de banco diretos, o Codepy responde a requisições em microssegundos.",
        "simple_solutions_title": "Simplicidade acima de complexidade",
        "simple_solutions_desc": "O Codepy incentiva o layout MVC padrão, container com injeção automática e models Active Record sem configuração forçada.",
        "strong_security_title": "Segurança robusta",
        "strong_security_desc": "Vem com proteção CSRF, sessões assinadas, senhas com hash e suporte a CAPTCHA.",
        "recent_posts": "Postagens recentes",
        "small_framework_title": "O framework pequeno com recursos poderosos",
        "learn_more": "Saiba mais",
        "framework_description": "O Codepy é um framework MVC em Python com consumo mínimo de recursos, feito para quem quer um conjunto de ferramentas simples e elegante para aplicações web completas.",
    },
    "es": {
        "greeting": "Hola",
        "welcome": "Bienvenido a Codepy",
        "discuss": "Foro",
        "contribute": "Contribuir",
        "learn": "Aprender",
        "dashboard": "Panel de Control",
        "download": "Descargar",
        "login": "Iniciar sesión",
        "register": "Crear cuenta",
        "logout": "Cerrar sesión",
        "why_codepy": "¿Por qué Codepy?",
        "small_footprint_title": "Framework con consumo mínimo",
        "small_footprint_desc": "Codepy tiene un consumo nulo de arranque en caliente e importaciones perezosas de dependencias, manteniendo el uso de memoria al mínimo.",
        "exceptional_perf_title": "Rendimiento excepcional",
        "exceptional_perf_desc": "Construido sobre canalizaciones ASGI y controladores de base de datos directos, Codepy responde a las solicitudes en microsegundos.",
        "simple_solutions_title": "Simplicidad sobre complejidad",
        "simple_solutions_desc": "Codepy favorece el diseño MVC estándar, un contenedor con inyección automática y modelos Active Record sin configuración forzada.",
        "strong_security_title": "Seguridad sólida",
        "strong_security_desc": "Incluye protección CSRF, sesiones firmadas, contraseñas con hash y compatibilidad con CAPTCHA.",
        "recent_posts": "Publicaciones recientes",
        "small_framework_title": "El framework pequeño con potentes características",
        "learn_more": "Saber más",
        "framework_description": "Codepy es un framework MVC en Python con un consumo mínimo de recursos, pensado para quienes buscan un conjunto de herramientas simple y elegante para aplicaciones web completas.",
    },
}


class TranslationSeeder(Seeder):
    def run(self):
        DB.statement("DELETE FROM translations")

        for locale, entries in TRANSLATIONS.items():
            for key, value in entries.items():
                DB.statement(
                    "INSERT INTO translations (key, locale, value) VALUES (?, ?, ?)",
                    [key, locale, value],
                )

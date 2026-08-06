"""Framework tables seeder — populates translations, modules, roles, and permissions."""

from codepy.seeding import Seeder
from codepy.facades import DB
from app.Models.Translation import Translation
from app.Models.Module import Module
from app.Models.Role import Role
from app.Models.Permission import Permission


class FrameworkSeeder(Seeder):
    def run(self):
        # 1. Clean tables
        DB.statement("DELETE FROM permission_role")
        DB.statement("DELETE FROM role_user")
        DB.statement("DELETE FROM permissions")
        DB.statement("DELETE FROM roles")
        DB.statement("DELETE FROM modules")
        DB.statement("DELETE FROM translations")

        # 2. Seed translations
        # English
        Translation.create({"key": "greeting", "locale": "en", "value": "Hello"})
        Translation.create({"key": "welcome", "locale": "en", "value": "Welcome to Codepy"})
        Translation.create({"key": "discuss", "locale": "en", "value": "Discuss"})
        Translation.create({"key": "contribute", "locale": "en", "value": "Contribute"})
        Translation.create({"key": "learn", "locale": "en", "value": "Learn"})
        Translation.create({"key": "dashboard", "locale": "en", "value": "Dashboard"})
        Translation.create({"key": "download", "locale": "en", "value": "Download"})
        Translation.create({"key": "login", "locale": "en", "value": "Log In"})
        Translation.create({"key": "register", "locale": "en", "value": "Register"})
        Translation.create({"key": "why_codepy", "locale": "en", "value": "Why Codepy?"})
        Translation.create({"key": "small_footprint_title", "locale": "en", "value": "Framework with a small footprint"})
        Translation.create({"key": "small_footprint_desc", "locale": "en", "value": "Codepy has zero hot-start footprint and dynamic lazy dependency imports, keeping memory usage minimal."})
        Translation.create({"key": "exceptional_perf_title", "locale": "en", "value": "Exceptional performance"})
        Translation.create({"key": "exceptional_perf_desc", "locale": "en", "value": "Powered by ASGI FastAPI pipelines and high-speed SQLAlchemy pooling, Codepy handles requests in microseconds."})
        Translation.create({"key": "simple_solutions_title", "locale": "en", "value": "Simple solutions over complexity"})
        Translation.create({"key": "simple_solutions_desc", "locale": "en", "value": "Codepy encourages standard MVC layout, autowired dependency container, and Active Record schemas without forced configurations."})
        Translation.create({"key": "strong_security_title", "locale": "en", "value": "Strong Security"})
        Translation.create({"key": "strong_security_desc", "locale": "en", "value": "Comes standard with CSRF validations, alpha CAPTCHA bot protection, and Winternitz Post-Quantum session signatures."})
        Translation.create({"key": "recent_posts", "locale": "en", "value": "Recent Posts"})
        Translation.create({"key": "small_framework_title", "locale": "en", "value": "The small framework with powerful features"})
        Translation.create({"key": "learn_more", "locale": "en", "value": "Learn more"})
        Translation.create({"key": "framework_description", "locale": "en", "value": "Codepy is a powerful Python MVC framework with a very small footprint, built for developers who need a simple and elegant toolkit to create full-featured web applications."})

        # Portuguese (pt)
        Translation.create({"key": "greeting", "locale": "pt", "value": "Olá"})
        Translation.create({"key": "welcome", "locale": "pt", "value": "Bem-vindo ao Codepy"})
        Translation.create({"key": "discuss", "locale": "pt", "value": "Fórum"})
        Translation.create({"key": "contribute", "locale": "pt", "value": "Contribuir"})
        Translation.create({"key": "learn", "locale": "pt", "value": "Aprender"})
        Translation.create({"key": "dashboard", "locale": "pt", "value": "Painel de Controle"})
        Translation.create({"key": "download", "locale": "pt", "value": "Baixar"})
        Translation.create({"key": "login", "locale": "pt", "value": "Entrar"})
        Translation.create({"key": "register", "locale": "pt", "value": "Registrar"})
        Translation.create({"key": "why_codepy", "locale": "pt", "value": "Por que o Codepy?"})
        Translation.create({"key": "small_footprint_title", "locale": "pt", "value": "Framework com consumo mínimo"})
        Translation.create({"key": "small_footprint_desc", "locale": "pt", "value": "O Codepy possui consumo zero de inicialização a quente e importações dinâmicas e preguiçosas de dependências, mantendo o uso de memória no mínimo."})
        Translation.create({"key": "exceptional_perf_title", "locale": "pt", "value": "Desempenho excepcional"})
        Translation.create({"key": "exceptional_perf_desc", "locale": "pt", "value": "Alimentado por pipelines ASGI FastAPI e pooling SQLAlchemy de alta velocidade, o Codepy gerencia requisições em microssegundos."})
        Translation.create({"key": "simple_solutions_title", "locale": "pt", "value": "Simplicidade acima de complexidade"})
        Translation.create({"key": "simple_solutions_desc", "locale": "pt", "value": "O Codepy incentiva o layout MVC padrão, contêiner de dependências com injeção automática e esquemas Active Record sem configurações forçadas."})
        Translation.create({"key": "strong_security_title", "locale": "pt", "value": "Segurança robusta"})
        Translation.create({"key": "strong_security_desc", "locale": "pt", "value": "Vem de fábrica com validações CSRF, proteção contra bots alpha CAPTCHA e assinaturas de sessão Winternitz pós-quânticas."})
        Translation.create({"key": "recent_posts", "locale": "pt", "value": "Postagens Recentes"})
        Translation.create({"key": "small_framework_title", "locale": "pt", "value": "O framework pequeno com recursos poderosos"})
        Translation.create({"key": "learn_more", "locale": "pt", "value": "Saiba mais"})
        Translation.create({"key": "framework_description", "locale": "pt", "value": "O Codepy é um poderoso framework MVC em Python com consumo mínimo de recursos, desenvolvido para programadores que precisam de um conjunto de ferramentas simples e elegante para criar aplicações web completas."})

        # Spanish (es)
        Translation.create({"key": "greeting", "locale": "es", "value": "Hola"})
        Translation.create({"key": "welcome", "locale": "es", "value": "Bienvenido a Codepy"})
        Translation.create({"key": "discuss", "locale": "es", "value": "Foro"})
        Translation.create({"key": "contribute", "locale": "es", "value": "Contribuir"})
        Translation.create({"key": "learn", "locale": "es", "value": "Aprender"})
        Translation.create({"key": "dashboard", "locale": "es", "value": "Panel de Control"})
        Translation.create({"key": "download", "locale": "es", "value": "Descargar"})
        Translation.create({"key": "login", "locale": "es", "value": "Iniciar sesión"})
        Translation.create({"key": "register", "locale": "es", "value": "Registrarse"})
        Translation.create({"key": "why_codepy", "locale": "es", "value": "¿Por qué Codepy?"})
        Translation.create({"key": "small_footprint_title", "locale": "es", "value": "Framework con consumo mínimo"})
        Translation.create({"key": "small_footprint_desc", "locale": "es", "value": "Codepy tiene un consumo de inicio en caliente cero y de dependencias perezosas dinámicas, manteniendo el uso de memoria al mínimo."})
        Translation.create({"key": "exceptional_perf_title", "locale": "es", "value": "Rendimiento excepcional"})
        Translation.create({"key": "exceptional_perf_desc", "locale": "es", "value": "Alimentado por canalizaciones ASGI FastAPI y agrupación de SQLAlchemy de alta velocidad, Codepy maneja solicitudes en microsegundos."})
        Translation.create({"key": "simple_solutions_title", "locale": "es", "value": "Simplicidad sobre complejidad"})
        Translation.create({"key": "simple_solutions_desc", "locale": "es", "value": "Codepy fomenta el diseño MVC estándar, contenedor de dependencias con inyección automática y esquemas de Active Record sin configuraciones forzadas."})
        Translation.create({"key": "strong_security_title", "locale": "es", "value": "Seguridad sólida"})
        Translation.create({"key": "strong_security_desc", "locale": "es", "value": "Viene de serie con validaciones CSRF, protección contra bots alpha CAPTCHA y firmas de sesión post-cuánticas de Winternitz."})
        Translation.create({"key": "recent_posts", "locale": "es", "value": "Publicaciones Recientes"})
        Translation.create({"key": "small_framework_title", "locale": "es", "value": "El framework pequeño con potentes características"})
        Translation.create({"key": "learn_more", "locale": "es", "value": "Saber más"})
        Translation.create({"key": "framework_description", "locale": "es", "value": "Codepy es un potente framework MVC en Python con un consumo mínimo de recursos, diseñado para programadores que necesitan un conjunto de herramientas simple y elegante para crear aplicaciones web completas."})

        # 3. Seed modules
        Module.create({"name": "Inventory Management", "slug": "inventory", "enabled": True})
        Module.create({"name": "Billing Services", "slug": "billing", "enabled": True})

        # 4. Seed Roles
        admin_role = Role.create({"name": "Administrator", "slug": "admin"})
        user_role = Role.create({"name": "User", "slug": "user"})

        # 5. Seed Permissions
        create_post = Permission.create({"name": "Create Posts", "slug": "create-post"})
        delete_post = Permission.create({"name": "Delete Posts", "slug": "delete-post"})
        manage_users = Permission.create({"name": "Manage Users", "slug": "manage-users"})

        # 6. Populate Pivot Tables (permission_role)
        # admin gets all permissions
        DB.statement(
            "INSERT INTO permission_role (role_id, permission_id) VALUES (:role, :perm)",
            {"role": admin_role.get_attribute("id"), "perm": create_post.get_attribute("id")}
        )
        DB.statement(
            "INSERT INTO permission_role (role_id, permission_id) VALUES (:role, :perm)",
            {"role": admin_role.get_attribute("id"), "perm": delete_post.get_attribute("id")}
        )
        DB.statement(
            "INSERT INTO permission_role (role_id, permission_id) VALUES (:role, :perm)",
            {"role": admin_role.get_attribute("id"), "perm": manage_users.get_attribute("id")}
        )

        # user gets create and delete posts
        DB.statement(
            "INSERT INTO permission_role (role_id, permission_id) VALUES (:role, :perm)",
            {"role": user_role.get_attribute("id"), "perm": create_post.get_attribute("id")}
        )
        DB.statement(
            "INSERT INTO permission_role (role_id, permission_id) VALUES (:role, :perm)",
            {"role": user_role.get_attribute("id"), "perm": delete_post.get_attribute("id")}
        )

        # 7. Associate Users to Roles (role_user)
        from app.Models.User import User
        admin_user = User.query().where("email", "admin@codepy.local").first()
        jane_user = User.query().where("email", "user@codepy.local").first()

        if admin_user:
            DB.statement(
                "INSERT INTO role_user (user_id, role_id) VALUES (:user, :role)",
                {"user": admin_user.get_attribute("id"), "role": admin_role.get_attribute("id")}
            )
        if jane_user:
            DB.statement(
                "INSERT INTO role_user (user_id, role_id) VALUES (:user, :role)",
                {"user": jane_user.get_attribute("id"), "role": user_role.get_attribute("id")}
            )

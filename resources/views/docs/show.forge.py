{#
  show.forge.py — Preprocessed layout for rendering Markdown documentation pages.
  Category: View (Presentation Layer).
  Relations:
    - Preprocessed by Forge view engine, extends [layouts/app.forge.py](file:///d:/data/www/codepy/resources/views/layouts/app.forge.py).
    - Renders variables sent by [DocsController.py](file:///d:/data/www/codepy/app/Http/Controllers/Blog/DocsController.py).
  References:
    - Documentation: [documentation/routing.md](file:///d:/data/www/codepy/documentation/routing.md)
    - Skill: `codepy-development` ([SKILL.md](file:///d:/data/www/codepy/.agents/skills/codepy-development/SKILL.md))
#}

@extends("layouts.app")

@section("title", page_title ~ " — Codepy Documentation")

@section("content")
<div class="max-w-7xl mx-auto w-full flex-1 flex">
    <!-- Left Sidebar: Documentation Navigation -->
    <aside class="w-72 flex-shrink-0 bg-white border-r border-slate-250/60 p-8 hidden md:block select-none">
        <nav class="space-y-8 sticky top-24">
            {# Built from the files in documentation/ — adding a guide needs no
               change here. See DocsController.navigation(). #}
            @foreach(navigation as group)
                <div>
                    <h4 class="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3">{{ group.heading }}</h4>
                    <ul class="space-y-2 text-sm font-medium">
                        @foreach(group['items'] as item)
                            <li>
                                <a href="/docs/{{ item.slug }}"
                                   class="flex items-center px-3 py-2 rounded-lg transition duration-150 {% if current_page == item.slug %}bg-orange-50 text-orange-600{% else %}text-slate-600 hover:bg-slate-50 hover:text-slate-900{% endif %}">
                                    {{ item.title }}
                                </a>
                            </li>
                        @endforeach
                    </ul>
                </div>
            @endforeach
        </nav>
    </aside>

    <!-- Main Content Area -->
    <main class="flex-1 min-w-0 bg-white px-6 py-10 md:px-12 lg:px-16 overflow-y-auto">
        <div class="max-w-3xl prose-docs">
            {{ content | safe }}
        </div>
    </main>
</div>

<!-- Styles for markdown rendered elements -->
<style>
    .prose-docs h1 {
        font-size: 2.25rem;
        font-weight: 800;
        color: #1e293b;
        letter-spacing: -0.025em;
        margin-bottom: 1.5rem;
        line-height: 1.25;
    }
    .prose-docs h2 {
        font-size: 1.5rem;
        font-weight: 700;
        color: #ea580c;
        letter-spacing: -0.02em;
        margin-top: 2.5rem;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 1px solid #f1f5f9;
    }
    .prose-docs h3 {
        font-size: 1.25rem;
        font-weight: 600;
        color: #334155;
        margin-top: 2rem;
        margin-bottom: 0.75rem;
    }
    .prose-docs p {
        color: #475569;
        line-height: 1.75;
        margin-bottom: 1.25rem;
        font-size: 0.95rem;
    }
    .prose-docs p strong {
        color: #1e293b;
        font-weight: 600;
    }
    .prose-docs blockquote {
        border-left: 4px solid #f97316;
        background-color: #fff7ed;
        padding: 1rem 1.25rem;
        margin: 1.5rem 0;
        border-radius: 0.5rem;
    }
    .prose-docs blockquote p {
        margin-bottom: 0;
        color: #c2410c;
        font-weight: 500;
    }
    .prose-docs blockquote p strong {
        color: #ea580c;
    }
    .prose-docs ul, .prose-docs ol {
        margin-bottom: 1.25rem;
        padding-left: 1.5rem;
    }
    .prose-docs ul {
        list-style-type: disc;
    }
    .prose-docs ol {
        list-style-type: decimal;
    }
    .prose-docs li {
        color: #475569;
        margin-bottom: 0.5rem;
        line-height: 1.6;
        font-size: 0.95rem;
    }
    .prose-docs pre {
        background-color: #0f172a;
        color: #e2e8f0;
        padding: 1.25rem;
        border-radius: 0.75rem;
        overflow-x: auto;
        margin-top: 1rem;
        margin-bottom: 1.5rem;
        font-size: 0.85rem;
        line-height: 1.6;
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
    }
    .prose-docs code {
        background-color: #f1f5f9;
        color: #0f172a;
        padding: 0.2rem 0.4rem;
        border-radius: 0.25rem;
        font-size: 0.85em;
        font-weight: 600;
    }
    .prose-docs pre code {
        background-color: transparent;
        color: inherit;
        padding: 0;
        border-radius: 0;
        font-weight: inherit;
    }
    .prose-docs table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 1.5rem;
        margin-bottom: 1.5rem;
        font-size: 0.9rem;
    }
    .prose-docs th, .prose-docs td {
        border: 1px solid #e2e8f0;
        padding: 0.75rem 1rem;
        text-align: left;
    }
    .prose-docs th {
        background-color: #f8fafc;
        font-weight: 600;
        color: #334155;
    }
    .prose-docs td {
        color: #475569;
    }
    .prose-docs hr {
        border: 0;
        border-top: 1px solid #e2e8f0;
        margin: 2.5rem 0;
    }
</style>
@endsection

{#
    The control panel shell.

    Extended by every page under `/panel`. Rendered for any signed-in account —
    an ordinary user gets their own workspace, an administrator additionally
    gets the sections that manage other people.

    The sidebar is built from the `nav` registry
    (`engine/support/navigation.py`, declared in
    `app/Providers/PanelServiceProvider.py`), filtered by what this visitor may
    actually reach. It replaced an icon-only rail that expanded on hover *over*
    the content: labels were invisible until you guessed where to point, and
    the expanded rail covered the page underneath. Here the sidebar is always
    labelled, and the content area is offset by its width instead of sitting
    beneath it.

    Sections yielded by pages: `title`, `heading`, `subheading`, `actions`,
    `content`.

    Context expected:
      nav_sections  list  [{key, title, items: [{label, url, icon, badge, active}]}]
      current_user  User
#}<!DOCTYPE html>
<html lang="{{ locale() }}" class="h-full">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>@yield("title", "Panel") — Craft</title>
    <link rel="stylesheet" href="{{ asset('assets/css/craft-theme.css') }}">
    <link rel="stylesheet" href="{{ asset('assets/css/craft-components.css') }}">
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        /* The sidebar is a fixed column; the content pane is pushed over by
           exactly its width. Overlaying instead of offsetting is what made the
           old rail cover the page whenever it expanded. */
        :root { --panel-sidebar: 16rem; }
        @media (min-width: 1024px) {
            .panel-shell { padding-left: var(--panel-sidebar); }
        }
        /* Mobile: the sidebar slides in, and the checkbox below is the toggle —
           no JavaScript, so the panel works before a single script loads. */
        #panel-toggle:checked ~ .panel-sidebar { transform: translateX(0); }
        #panel-toggle:checked ~ .panel-scrim { display: block; }
    </style>
</head>
<body class="h-full bg-slate-100 text-slate-900 antialiased">

<input type="checkbox" id="panel-toggle" class="hidden peer">

{# Scrim: tapping outside closes the drawer on small screens. #}
<label for="panel-toggle" class="panel-scrim hidden fixed inset-0 z-30 bg-slate-950/50 lg:hidden"></label>

<aside class="panel-sidebar fixed inset-y-0 left-0 z-40 w-64 flex flex-col bg-slate-950 text-slate-300
              -translate-x-full lg:translate-x-0 transition-transform duration-200 ease-out">

    <div class="flex items-center gap-2.5 h-16 px-5 border-b border-white/5 flex-shrink-0">
        <span class="w-8 h-8 rounded-lg bg-gradient-to-br from-orange-400 to-orange-600 flex items-center justify-center text-white font-black text-sm">C</span>
        <span class="text-lg font-extrabold tracking-tight text-white">Craft</span>
        <span class="ml-auto text-[9px] font-bold uppercase font-mono bg-white/5 text-slate-400 border border-white/10 px-1.5 py-0.5 rounded">
            {{ config('app.version') }}
        </span>
    </div>

    <nav class="flex-1 overflow-y-auto py-5 px-3 space-y-6">
        {# Sections with no visible items never reach the template — an
           ordinary account does not stare at an empty "System" heading. #}
        @foreach(nav_sections as section)
            <div>
                <p class="px-3 mb-2 text-[10px] font-bold uppercase tracking-widest text-slate-500">{{ section['title'] }}</p>
                <ul class="space-y-0.5">
                    @foreach(section['items'] as item)
                        <li>
                            <a href="{{ item['url'] }}"
                               class="flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition
                                      {% if item['active'] %}bg-orange-600 text-white shadow-sm{% else %}text-slate-400 hover:text-white hover:bg-white/5{% endif %}">
                                <span class="w-5 h-5 flex-shrink-0 opacity-90">{{ panel_icon(item['icon'])|safe }}</span>
                                <span class="truncate">{{ item['label'] }}</span>
                                @if(item['badge'] is not none)
                                    <span class="ml-auto text-[10px] font-bold font-mono px-1.5 py-0.5 rounded
                                                 {% if item['active'] %}bg-white/20 text-white{% else %}bg-white/5 text-slate-400{% endif %}">{{ item['badge'] }}</span>
                                @endif
                            </a>
                        </li>
                    @endforeach
                </ul>
            </div>
        @endforeach
    </nav>

    <div class="border-t border-white/5 p-3 flex-shrink-0">
        <a href="/panel/profile" class="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-white/5 transition">
            <span class="w-8 h-8 rounded-full bg-orange-600/20 text-orange-400 flex items-center justify-center text-xs font-bold flex-shrink-0">
                {{ (current_user.get_attribute('name') or '?')[:1]|upper }}
            </span>
            <span class="min-w-0">
                <span class="block text-xs font-semibold text-white truncate">{{ current_user.get_attribute('name') }}</span>
                <span class="block text-[11px] text-slate-500 truncate">{{ current_user.get_attribute('email') }}</span>
            </span>
        </a>
        <form action="/logout" method="POST" class="mt-1">
            @csrf
            <button type="submit" class="flex items-center gap-3 w-full px-3 py-2 rounded-lg text-sm font-medium text-slate-400 hover:text-rose-300 hover:bg-rose-950/30 transition">
                <span class="w-5 h-5 flex-shrink-0">{{ panel_icon('logout')|safe }}</span>
                Sign out
            </button>
        </form>
    </div>
</aside>

<div class="panel-shell min-h-full flex flex-col">
    <header class="sticky top-0 z-20 h-16 flex items-center gap-4 px-4 sm:px-8 bg-white/90 backdrop-blur border-b border-slate-200">
        <label for="panel-toggle" class="lg:hidden p-2 -ml-2 rounded-lg text-slate-500 hover:bg-slate-100 cursor-pointer" aria-label="Open menu">
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"/></svg>
        </label>
        {# `heading`/`subheading` come from the controller's context, not from a
           template section: they are usually computed (the visitor's name, a
           row count), and a Jinja block cannot be rendered twice anyway — it is
           needed here and again in the page header below. #}
        <h1 class="text-sm font-bold text-slate-900 truncate">{{ heading|default('Dashboard') }}</h1>
        <div class="ml-auto flex items-center gap-3">
            <a href="/" class="text-xs font-semibold text-slate-500 hover:text-orange-600 transition">View site →</a>
        </div>
    </header>

    <main class="flex-1 px-4 sm:px-8 py-8">
        <div class="max-w-6xl mx-auto space-y-8">
            <div class="flex flex-wrap items-end justify-between gap-4">
                <div>
                    <h2 class="text-2xl font-extrabold tracking-tight text-slate-900">{{ heading|default('Dashboard') }}</h2>
                    <p class="text-sm text-slate-500 mt-1">{{ subheading|default('') }}</p>
                </div>
                <div class="flex items-center gap-2">@yield("actions", "")</div>
            </div>

            @yield("content")
        </div>
    </main>

    <footer class="px-4 sm:px-8 py-6 text-xs text-slate-400 border-t border-slate-200">
        Craft {{ config('app.version') }} {{ config('app.release') }}
    </footer>
</div>

</body>
</html>

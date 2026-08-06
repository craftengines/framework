<!DOCTYPE html>
<html lang="en" class="h-full bg-slate-50 text-slate-900">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>@yield("title", "Codepy Framework")</title>
    <!-- Google Fonts: Plus Jakarta Sans -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <!-- Tailwind CSS Play CDN -->
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {
            theme: {
                extend: {
                    fontFamily: {
                        sans: ['"Plus Jakarta Sans"', 'sans-serif'],
                    },
                    colors: {
                        primary: {
                            50: '#fff7ed',
                            100: '#ffedd5',
                            500: '#f97316',
                            600: '#ea580c',
                            700: '#c2410c',
                        },
                        dark: {
                            800: '#1e293b',
                            900: '#0f172a',
                            950: '#020617',
                        }
                    }
                }
            }
        }
    </script>
</head>
<body class="min-h-full font-sans antialiased bg-slate-50/50 flex flex-col">
    {% if not show_sidebar %}
    <!-- Public Header (CodeIgniter style) -->
    <header class="bg-white border-b border-slate-200 text-slate-600 sticky top-0 z-40 w-full shadow-sm">
        <div class="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
            <div class="flex items-center space-x-10">
                <!-- Logo -->
                <a href="/" class="flex items-center space-x-2">
                    <svg class="w-6 h-6 text-orange-600 fill-current" viewBox="0 0 24 24">
                        <path d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"/>
                        <path d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"/>
                    </svg>
                    <span class="text-xl font-bold tracking-tight text-orange-600 font-sans">Codepy</span>
                </a>
            </div>
            
            <div class="flex items-center space-x-6 text-sm font-semibold">
                <!-- Locale Switcher -->
                <div class="flex items-center space-x-2 text-[10px] font-mono border-r border-slate-200 pr-4 mr-2">
                    <a href="?lang=en" class="{% if config('app.locale') == 'en' %}text-orange-600 font-bold{% else %}text-slate-400 hover:text-slate-600{% endif %}">EN</a>
                    <span class="text-slate-300">|</span>
                    <a href="?lang=pt" class="{% if config('app.locale') == 'pt' %}text-orange-600 font-bold{% else %}text-slate-400 hover:text-slate-600{% endif %}">PT</a>
                    <span class="text-slate-300">|</span>
                    <a href="?lang=es" class="{% if config('app.locale') == 'es' %}text-orange-600 font-bold{% else %}text-slate-400 hover:text-slate-600{% endif %}">ES</a>
                </div>

                <a href="/posts" class="hover:text-orange-600 transition duration-150">{{ __('discuss') }}</a>
                <a href="https://github.com" target="_blank" class="hover:text-orange-600 transition duration-150">{{ __('contribute') }}</a>
                <a href="/docs" class="hover:text-orange-600 transition duration-150">{{ __('learn') }}</a>
                
                @auth
                    <span class="text-xs text-slate-400 font-mono hidden md:inline">Profile: <strong class="text-slate-600">{{ auth().get_attribute('name') }}</strong></span>
                    <a href="/admin" class="bg-orange-600 hover:bg-orange-700 text-white font-bold px-4 py-2 rounded-lg shadow-md transition duration-150 font-sans">
                        {{ __('dashboard') }}
                    </a>
                    <form action="/logout" method="POST" class="inline">
                        @csrf
                        <button type="submit" class="text-xs font-bold text-rose-500 hover:text-rose-600">Logout</button>
                    </form>
                @endauth
                @guest
                    <a href="/login" class="hover:text-orange-600 transition duration-150 font-sans">{{ __('login') }}</a>
                    <a href="/register" class="bg-orange-600 hover:bg-orange-700 text-white font-bold px-4 py-2 rounded-lg shadow-md transition duration-150 font-sans">
                        {{ __('download') }}
                    </a>
                @endguest
            </div>
        </div>
    </header>
    {% endif %}

    {% if show_sidebar %}
    <!-- Sidebar (Desktop) -->
    <aside class="group fixed inset-y-0 left-0 z-30 hidden md:flex md:flex-col w-16 hover:w-64 bg-slate-950 text-slate-400 border-r border-slate-900 transition-all duration-300 ease-in-out overflow-x-hidden">
        <!-- Logo Header -->
        <div class="flex items-center h-16 px-4.5 border-b border-slate-900 overflow-hidden whitespace-nowrap">
            <a href="/" class="flex items-center space-x-2">
                <span class="w-7 h-7 rounded-lg bg-gradient-to-br from-orange-400 to-orange-600 flex items-center justify-center text-white font-black text-sm flex-shrink-0">C</span>
                <span class="text-xl font-extrabold tracking-tight text-white opacity-0 group-hover:opacity-100 transition-opacity duration-300 delay-75">Codepy</span>
                <span class="text-[9px] font-bold uppercase bg-orange-500/10 text-orange-400 border border-orange-500/20 px-1.5 py-0.5 rounded font-mono opacity-0 group-hover:opacity-100 transition-opacity duration-300 delay-75 whitespace-nowrap">{{ config('app.version') }} {{ config('app.release') }}</span>
            </a>
        </div>
        
        <!-- Navigation Links -->
        <div class="flex-1 flex flex-col justify-between py-6 px-3.5 overflow-hidden">
            <nav class="space-y-1.5">
                <a href="/" class="flex items-center px-2 py-2.5 text-sm font-semibold rounded-xl text-slate-200 hover:text-white hover:bg-slate-900 transition duration-150">
                    <svg class="w-5 h-5 flex-shrink-0 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"></path></svg>
                    <span class="opacity-0 group-hover:opacity-100 transition-opacity duration-300 delay-75 ml-0 group-hover:ml-3 whitespace-nowrap overflow-hidden">Dashboard</span>
                </a>
                <a href="/posts" class="flex items-center px-2 py-2.5 text-sm font-semibold rounded-xl text-slate-400 hover:text-white hover:bg-slate-900 transition duration-150">
                    <svg class="w-5 h-5 flex-shrink-0 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v12a2 2 0 01-2 2zM0 0h24v24H0z" stroke="none"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 22V12h6v10M8 12h8"></path></svg>
                    <span class="opacity-0 group-hover:opacity-100 transition-opacity duration-300 delay-75 ml-0 group-hover:ml-3 whitespace-nowrap overflow-hidden">System Posts</span>
                </a>
                @auth
                    <a href="/posts/create" class="flex items-center px-2 py-2.5 text-sm font-semibold rounded-xl text-slate-400 hover:text-white hover:bg-slate-900 transition duration-150">
                        <svg class="w-5 h-5 flex-shrink-0 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"></path></svg>
                        <span class="opacity-0 group-hover:opacity-100 transition-opacity duration-300 delay-75 ml-0 group-hover:ml-3 whitespace-nowrap overflow-hidden">Create Post</span>
                    </a>
                @endauth
            </nav>

            <!-- Authentication Panel (Bottom of Sidebar) -->
            <div class="border-t border-slate-900 pt-6">
                @auth
                    <div class="px-2 mb-4 whitespace-nowrap overflow-hidden">
                        <div class="text-[10px] font-bold uppercase tracking-wider text-slate-500 mb-1 opacity-0 group-hover:opacity-100 transition-opacity duration-300">Authenticated</div>
                        <div class="text-xs font-semibold text-white truncate opacity-0 group-hover:opacity-100 transition-opacity duration-300">{{ auth().get_attribute('name') if auth() else 'Active Profile' }}</div>
                    </div>
                    <form action="/logout" method="POST" class="block w-full">
                        @csrf
                        <button type="submit" class="flex items-center w-full px-2 py-2.5 text-sm font-semibold rounded-xl text-rose-400 hover:text-rose-300 hover:bg-rose-950/20 transition duration-150">
                            <svg class="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"></path></svg>
                            <span class="opacity-0 group-hover:opacity-100 transition-opacity duration-300 delay-75 ml-0 group-hover:ml-3 whitespace-nowrap overflow-hidden">Log Out</span>
                        </button>
                    </form>
                @endauth
                @guest
                    <div class="space-y-2">
                        <a href="/login" class="flex items-center justify-center w-full px-2 py-2.5 text-sm font-bold rounded-xl text-white bg-slate-900 hover:bg-slate-800 transition">
                            <span class="hidden group-hover:inline">Log In</span>
                        </a>
                        <a href="/register" class="flex items-center justify-center w-full px-2 py-2.5 text-sm font-bold rounded-xl text-white bg-orange-600 hover:bg-orange-700 transition">
                            <span class="hidden group-hover:inline">Register</span>
                        </a>
                    </div>
                @endguest
            </div>
        </div>
    </aside>
    {% endif %}

    <!-- Mobile Top Navigation Bar -->
    <header class="md:hidden flex items-center justify-between h-16 px-6 bg-slate-950 text-white border-b border-slate-900 w-full z-20">
        <a href="/" class="flex items-center space-x-2">
            <span class="text-xl font-extrabold tracking-tight text-white">Codepy</span>
        </a>
        <div class="flex items-center space-x-4">
            <a href="/" class="text-sm font-semibold text-slate-300 hover:text-white">Dashboard</a>
            @guest
                <a href="/login" class="text-sm font-semibold text-slate-300 hover:text-white">Login</a>
            @endguest
            @auth
                <form action="/logout" method="POST" class="inline">
                    @csrf
                    <button type="submit" class="text-sm font-semibold text-rose-400 hover:text-rose-300">Logout</button>
                </form>
            @endauth
        </div>
    </header>

    <!-- Main Content Frame -->
    <div class="flex-1 {% if show_sidebar %}md:pl-16{% endif %} flex flex-col min-h-screen">
        {% if show_sidebar %}
        <!-- Top Toolbar Header (Desktop) -->
        <header class="hidden md:flex items-center justify-between h-16 px-8 bg-white border-b border-slate-200/80 shadow-[0_1px_2px_rgba(0,0,0,0.01)]">
            <div class="flex items-center space-x-3">
                <span class="w-2.5 h-2.5 bg-emerald-500 rounded-full animate-pulse"></span>
                <span class="text-xs font-semibold text-slate-500 uppercase tracking-wider font-mono">Dynamic Operations Active</span>
            </div>
            <div class="flex items-center space-x-4">
                <span class="text-xs text-slate-400 font-mono">Port: 8300 &mdash; SQLite/PgSQL</span>
            </div>
        </header>
        {% endif %}

        <!-- Dynamic Content Body -->
        <main class="flex-grow p-6 md:p-10">
            <div class="{% if show_sidebar %}w-full{% else %}max-w-7xl mx-auto{% endif %}">
                @yield("content")
            </div>
        </main>

        <!-- Footer -->
        <footer class="bg-white border-t border-slate-200/60 py-6 text-center text-xs text-slate-400 mt-auto">
            <p>Codepy Framework {{ config('app.version') }} ({{ config('app.release') }}) &copy; 2026. All rights reserved.</p>
        </footer>
    </div>
</body>
</html>

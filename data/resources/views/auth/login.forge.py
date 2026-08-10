{#
    Sign in.

    Rendered by `app/Http/Controllers/Auth/AuthController.py::show_login`, and
    again by `login()` when authentication fails. `GET /login` is open;
    `POST /login` is throttled per IP and route (`routes/web.py`) — the CAPTCHA
    stops naive scripted attempts, but only a rate limit bounds automated ones.

    The form carries `@csrf` and a CAPTCHA; both are verified server-side, and a
    failed attempt costs the same time whether or not the email exists, so
    timing does not reveal which accounts are real.

    Context:
      captcha_html  str   pre-rendered, obfuscated CAPTCHA markup
      error         str   set on a failed attempt
      old           dict  the submitted email, so it is not retyped
#}
@extends("layouts.app")

@section("title", "Sign In & Onboard — Craft Enterprise")

@section("content")
<div class="max-w-4xl mx-auto bg-white rounded-2xl shadow-xl border border-slate-200 overflow-hidden flex flex-col md:flex-row">
    <!-- Left panel: Onboarding branding -->
    <div class="md:w-1/2 bg-gradient-to-br from-slate-900 via-slate-800 to-orange-950 p-8 text-white flex flex-col justify-between relative overflow-hidden">
        <div class="absolute -right-10 -bottom-10 w-48 h-48 bg-orange-500/10 rounded-full blur-2xl pointer-events-none"></div>
        
        <div>
            <span class="inline-flex items-center px-3 py-0.5 rounded-full text-xs font-semibold bg-orange-500/20 text-orange-400 border border-orange-500/20 mb-6 font-mono">
                System Access
            </span>
            <h2 class="text-2xl md:text-3xl font-black tracking-tight text-white mb-4">
                Welcome to your <br><span class="text-orange-500">Craft Control Center</span>.
            </h2>
            <p class="text-slate-300 text-sm leading-relaxed mb-6">
                Connect and manage your dynamic business modules, real-time translations, and role-based permissions from a single interface.
            </p>
        </div>

        <div class="space-y-4">
            <div class="flex items-center space-x-3 text-xs text-slate-300 font-medium">
                <svg class="w-5 h-5 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"></path></svg>
                <span>Encrypted JWT Sessions</span>
            </div>
            <div class="flex items-center space-x-3 text-xs text-slate-300 font-medium">
                <svg class="w-5 h-5 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
                <span>Async-first Execution</span>
            </div>
        </div>
    </div>

    <!-- Right panel: Login form -->
    <div class="md:w-1/2 p-8 md:p-12 flex flex-col justify-center">
        <h3 class="text-xl font-bold text-slate-900 mb-2">Sign In</h3>
        <p class="text-slate-500 text-sm mb-6">Enter your credentials to access the ERP/CRM cockpit.</p>

        @if(error is defined)
            <div class="bg-rose-50 border border-rose-200 text-rose-600 rounded-lg p-3 text-sm mb-6 flex items-center space-x-2">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path></svg>
                <span>{{ error }}</span>
            </div>
        @endif

        <form action="/login" method="POST" class="space-y-4">
            @csrf
            <div>
                <label for="email" class="block text-xs font-semibold text-slate-600 uppercase mb-1">Email Address</label>
                <input type="email" name="email" id="email" required placeholder="admin@example.com"
                       class="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-slate-800 text-sm placeholder-slate-400 focus:outline-none focus:border-orange-500 focus:bg-white transition">
            </div>

            <div>
                <label for="password" class="block text-xs font-semibold text-slate-600 uppercase mb-1">Password</label>
                <input type="password" name="password" id="password" required placeholder="••••••••"
                       class="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-slate-800 text-sm placeholder-slate-400 focus:outline-none focus:border-orange-500 focus:bg-white transition">
            </div>

            <div>
                <label for="captcha" class="block text-xs font-semibold text-slate-600 uppercase mb-1">CAPTCHA Security Code</label>
                <div class="flex items-center space-x-3">
                    <div class="bg-slate-100 border border-slate-200 rounded-xl px-4 py-2 flex items-center justify-center font-mono tracking-widest text-lg font-bold select-none h-11">
                        {{ captcha_html | safe }}
                    </div>
                    <input type="text" name="captcha" id="captcha" required placeholder="Enter code" autocomplete="off"
                           class="flex-1 px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-slate-800 text-sm placeholder-slate-400 focus:outline-none focus:border-orange-500 focus:bg-white transition h-11">
                </div>
            </div>

            <button type="submit" class="w-full bg-orange-500 hover:bg-orange-600 text-white font-bold py-3 rounded-xl shadow-md transition duration-200">
                Authenticate Access
            </button>
        </form>

        <p class="mt-8 text-center text-xs text-slate-500">
            Don't have an account?
            <a href="/register" class="text-orange-500 hover:text-orange-600 font-bold transition">Register Profile</a>
        </p>

        @if(config("app.APP_DEBUG"))
            <div class="mt-6 pt-6 border-t border-dashed border-slate-200">
                <p class="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-2">Demo accounts (debug only)</p>
                <table class="w-full text-xs text-slate-500 font-mono">
                    <tr><td class="py-0.5 pr-3 text-slate-700 font-semibold">admin@craft.local</td><td>craft — full admin</td></tr>
                    <tr><td class="py-0.5 pr-3 text-slate-700 font-semibold">tenant@craft.local</td><td>craft — tenant-manager</td></tr>
                    <tr><td class="py-0.5 pr-3 text-slate-700 font-semibold">user@craft.local</td><td>craft — basic user</td></tr>
                </table>
            </div>
        @endif
    </div>
</div>
@endsection

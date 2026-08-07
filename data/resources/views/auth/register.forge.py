@extends("layouts.app")

@section("title", "Register Profile — Craft Enterprise")

@section("content")
<div class="max-w-4xl mx-auto bg-white rounded-2xl shadow-xl border border-slate-200 overflow-hidden flex flex-col md:flex-row">
    <!-- Left panel: Onboarding branding -->
    <div class="md:w-1/2 bg-gradient-to-br from-slate-900 via-slate-800 to-orange-950 p-8 text-white flex flex-col justify-between relative overflow-hidden">
        <div class="absolute -right-10 -bottom-10 w-48 h-48 bg-orange-500/10 rounded-full blur-2xl pointer-events-none"></div>
        
        <div>
            <span class="inline-flex items-center px-3 py-0.5 rounded-full text-xs font-semibold bg-orange-500/20 text-orange-400 border border-orange-500/20 mb-6 font-mono">
                Profile Registration
            </span>
            <h2 class="text-2xl md:text-3xl font-black tracking-tight text-white mb-4">
                Deploy your cloud <br><span class="text-orange-500">ERP/CRM instance</span>.
            </h2>
            <p class="text-slate-300 text-sm leading-relaxed mb-6">
                Register a new profile to connect users, assign Roles, configure bilinguality, and manage background queues.
            </p>
        </div>

        <div class="space-y-4">
            <div class="flex items-center space-x-3 text-xs text-slate-300 font-medium">
                <svg class="w-5 h-5 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"></path></svg>
                <span>Automated DB Seeding</span>
            </div>
            <div class="flex items-center space-x-3 text-xs text-slate-300 font-medium">
                <svg class="w-5 h-5 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"></path></svg>
                <span>Role-Based Permissions</span>
            </div>
        </div>
    </div>

    <!-- Right panel: Registration form -->
    <div class="md:w-1/2 p-8 md:p-12 flex flex-col justify-center">
        <h3 class="text-xl font-bold text-slate-900 mb-2">Create Profile</h3>
        <p class="text-slate-500 text-sm mb-6">Initialize your personal dashboard space.</p>

        <form action="/register" method="POST" class="space-y-4">
            @csrf
            <div>
                <label for="name" class="block text-xs font-semibold text-slate-600 uppercase mb-1">Full Name</label>
                <input type="text" name="name" id="name" required placeholder="John Doe"
                       class="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-slate-800 text-sm placeholder-slate-400 focus:outline-none focus:border-orange-500 focus:bg-white transition">
            </div>

            <div>
                <label for="email" class="block text-xs font-semibold text-slate-600 uppercase mb-1">Email Address</label>
                <input type="email" name="email" id="email" required placeholder="john@example.com"
                       class="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-slate-800 text-sm placeholder-slate-400 focus:outline-none focus:border-orange-500 focus:bg-white transition">
            </div>

            <div>
                <label for="password" class="block text-xs font-semibold text-slate-600 uppercase mb-1">Password</label>
                <input type="password" name="password" id="password" required placeholder="••••••••"
                       class="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-slate-800 text-sm placeholder-slate-400 focus:outline-none focus:border-orange-500 focus:bg-white transition">
            </div>

            <button type="submit" class="w-full bg-orange-500 hover:bg-orange-600 text-white font-bold py-3 rounded-xl shadow-md transition duration-200">
                Initialize Profile
            </button>
        </form>

        <p class="mt-8 text-center text-xs text-slate-500">
            Already have an account? 
            <a href="/login" class="text-orange-500 hover:text-orange-600 font-bold transition">Sign In Instead</a>
        </p>
    </div>
</div>
@endsection

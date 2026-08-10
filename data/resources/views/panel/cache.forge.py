{#
    Panel — Cache.

    Rendered by `PanelController::cache` at `GET /panel/cache`, behind
    `auth` + `role:admin`. The flush posts to `/panel/cache/flush`.

    Two values, deliberately both shown: what the config *asks* for and which
    store actually resolved. They differ when a driver is unavailable — the
    cache manager degrades to the array store rather than failing the request —
    and "configured redis, running array" is precisely the sort of thing that
    otherwise goes unnoticed until a second worker appears and the two stop
    sharing anything.

    Context:
      configured  str   the `cache.default` setting
      store       str   the class that actually resolved
      flushed     bool  set after a successful flush
#}
@extends("layouts.panel")

@section("title", "Cache")

@section("content")

@if(flushed)
    <div class="bg-emerald-50 border border-emerald-200 rounded-2xl px-5 py-4">
        <p class="text-sm font-bold text-emerald-900">Cache emptied.</p>
    </div>
@endif

<div class="grid gap-4 sm:grid-cols-2">
    <div class="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm">
        <p class="text-xs font-bold uppercase tracking-wider text-slate-400">Configured</p>
        <p class="mt-2 text-2xl font-extrabold text-slate-900 font-mono">{{ configured }}</p>
        <p class="mt-1 text-xs text-slate-500">From <code class="font-mono">config/cache.py</code></p>
    </div>
    <div class="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm">
        <p class="text-xs font-bold uppercase tracking-wider text-slate-400">Actually running</p>
        <p class="mt-2 text-2xl font-extrabold text-slate-900 font-mono">{{ store }}</p>
        <p class="mt-1 text-xs text-slate-500">Resolved at runtime</p>
    </div>
</div>

<div class="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm">
    <p class="text-sm font-bold text-slate-900">Empty the cache</p>
    <p class="text-sm text-slate-500 mt-1 mb-4">
        Drops every entry in the store above. Harmless — anything cached is by
        definition rebuildable — but it will be briefly slower afterwards.
    </p>
    {# POST with CSRF: a GET that mutates can be triggered by a prefetch. #}
    <form action="/panel/cache/flush" method="POST">
        @csrf
        <button type="submit" class="bg-slate-900 hover:bg-slate-800 text-white text-sm font-bold px-5 py-2.5 rounded-xl transition">
            Flush cache
        </button>
    </form>
</div>

@endsection

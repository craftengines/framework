{#
    Panel — Dashboard.

    Rendered by `app/Http/Controllers/Panel/PanelController.py::index` at
    `GET /panel`, behind `auth`. Every signed-in account reaches this page; what
    it contains differs by account.

    The figures are scoped to the visitor on purpose. An ordinary user counts
    their own posts and their own access; the installation-wide row only
    appears for administrators, because the size of the system is itself
    information an account that cannot see its contents should not be handed.

    Context:
      stats        list[{label, value, hint}]  always shown
      admin_stats  list[{label, value, hint}]  administrators only, may be []
      my_posts     list[Post]                  five most recent, by this user
#}
@extends("layouts.panel")

@section("title", "Dashboard")
{# `heading` and `subheading` are context values from the controller, not
   sections — they are computed (the visitor's name, a row count) and the
   layout renders them in two places. #}

@section("content")

<section>
    <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        @foreach(stats as stat)
            <div class="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm">
                <p class="text-xs font-bold uppercase tracking-wider text-slate-400">{{ stat['label'] }}</p>
                <p class="mt-2 text-3xl font-extrabold text-slate-900 tabular-nums">{{ stat['value'] }}</p>
                <p class="mt-1 text-xs text-slate-500 truncate">{{ stat['hint'] }}</p>
            </div>
        @endforeach
    </div>
</section>

@if(admin_stats|length > 0)
    {# Only administrators get this row — see the note at the top. #}
    <section>
        <h3 class="text-xs font-bold uppercase tracking-widest text-slate-400 mb-3">This installation</h3>
        <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            @foreach(admin_stats as stat)
                <div class="bg-slate-900 text-white rounded-2xl p-5 shadow-sm">
                    <p class="text-xs font-bold uppercase tracking-wider text-slate-400">{{ stat['label'] }}</p>
                    <p class="mt-2 text-3xl font-extrabold tabular-nums">{{ stat['value'] }}</p>
                    <p class="mt-1 text-xs text-slate-500 truncate">{{ stat['hint'] }}</p>
                </div>
            @endforeach
        </div>
    </section>
@endif

<section>
    <div class="flex items-center justify-between mb-3">
        <h3 class="text-xs font-bold uppercase tracking-widest text-slate-400">Your latest posts</h3>
        <a href="/panel/posts" class="text-xs font-semibold text-orange-600 hover:text-orange-700">See all →</a>
    </div>

    <div class="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        @if(my_posts|length > 0)
            <ul class="divide-y divide-slate-100">
                @foreach(my_posts as post)
                    <li class="flex items-center gap-4 px-5 py-4">
                        <div class="min-w-0 flex-1">
                            <a href="/posts/{{ post.get_attribute('id') }}" class="text-sm font-semibold text-slate-900 hover:text-orange-600 truncate block">
                                {{ post.get_attribute('title') }}
                            </a>
                            <p class="text-xs text-slate-400 font-mono mt-0.5">{{ post.get_attribute('created_at') }}</p>
                        </div>
                        <a href="/posts/{{ post.get_attribute('id') }}/edit" class="text-xs font-semibold text-slate-500 hover:text-orange-600 flex-shrink-0">Edit</a>
                    </li>
                @endforeach
            </ul>
        @else
            {# Empty state: say what is missing and offer the next step, rather
               than showing a blank card that reads like a loading failure. #}
            <div class="px-5 py-12 text-center">
                <p class="text-sm font-semibold text-slate-900">You have not written anything yet.</p>
                <p class="text-xs text-slate-500 mt-1 mb-4">Your posts will show up here once you do.</p>
                @can("create-post")
                    <a href="/posts/create" class="inline-block bg-orange-600 hover:bg-orange-700 text-white text-sm font-bold px-5 py-2.5 rounded-xl shadow-sm transition">
                        Write your first post
                    </a>
                @endcan
            </div>
        @endif
    </div>
</section>

@endsection
